from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Mapping, Optional, Tuple

import pandas as pd

from tycherion.domain.portfolio.entities import PortfolioSnapshot, Signal, SignalsBySymbol
from tycherion.domain.signals.entities import (
    IndicatorOutput,
    ModelDecision,
    ModelStageResult,
    SymbolState,
)
from tycherion.domain.signals.models.base import SignalModel
from tycherion.domain.signals.indicators.base import BaseIndicator
from tycherion.ports.market_data import MarketDataPort

from tycherion.ports.observability import semconv
from tycherion.ports.observability.observability import ObservabilityPort
from tycherion.ports.observability.traces import SpanPort
from tycherion.ports.observability.logs import LoggerPort
from tycherion.ports.observability.types import Severity, TYCHERION_SCHEMA_VERSION

from .config import PipelineConfig, PipelineStageConfig
from .result import PipelineRunResult


@dataclass(slots=True)
class ModelPipelineService:
    """Façade that runs the ordered per-symbol model pipeline."""

    market_data: MarketDataPort
    model_registry: Mapping[str, SignalModel]
    indicator_picker: Callable[[str, Optional[str]], BaseIndicator]
    timeframe: str
    lookback_days: int
    playbook: str | None = None

    def run(
        self,
        universe_symbols: list[str],
        portfolio_snapshot: PortfolioSnapshot,
        pipeline_config: PipelineConfig,
        *,
        observability: ObservabilityPort,
    ) -> PipelineRunResult:
        tracer = observability.traces.get_tracer("tycherion.pipeline", version=TYCHERION_SCHEMA_VERSION)
        logger = observability.logs.get_logger("tycherion.pipeline", version=TYCHERION_SCHEMA_VERSION)

        held_symbols = set(portfolio_snapshot.positions.keys())

        with tracer.start_as_current_span(
            semconv.SPAN_PIPELINE,
            attributes={
                "symbols_count": int(len(universe_symbols)),
                "stages": [st.name for st in pipeline_config.stages],
                "timeframe": self.timeframe,
                "lookback_days": int(self.lookback_days),
            },
        ) as span:
            # 1) Init per-symbol state
            states: Dict[str, SymbolState] = {
                sym: SymbolState(symbol=sym, is_held=(sym in held_symbols))
                for sym in universe_symbols
            }

            # 2) Resolve models
            resolved = self._resolve_models(pipeline_config)

            # 3) Determine indicator needs once for the whole pipeline
            needed_keys: set[str] = set()
            for _, model in resolved:
                try:
                    needed_keys.update(model.requires() or set())
                except Exception:
                    pass

            # 4) Time window for analysis
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=int(self.lookback_days))

            stage_stats: Dict[str, int] = {st.name: 0 for st in pipeline_config.stages}
            stage_passed: Dict[str, int] = {st.name: 0 for st in pipeline_config.stages}

            for st in pipeline_config.stages:
                attrs = {"stage": st.name}
                if st.drop_threshold is not None:
                    attrs["threshold"] = float(st.drop_threshold)
                span.add_event(
                    semconv.EVT_PIPELINE_STAGE_STARTED,
                    attrs,
                )

            for symbol, state in states.items():
                if not state.alive and not state.is_held:
                    continue

                df = self._safe_get_bars(symbol, start, end, state, span, logger)
                if df is None or df.empty:
                    if not state.is_held:
                        logger.emit(
                            "pipeline.symbol_dropped",
                            Severity.WARN,
                            {
                                semconv.ATTR_CHANNEL: "audit",
                                "symbol": symbol,
                                "reason": "no_market_data",
                            },
                        )
                        state.alive = False
                    continue

                if logger.is_enabled(Severity.DEBUG):
                    try:
                        logger.emit(
                            "market_data.sample",
                            Severity.DEBUG,
                            {
                                semconv.ATTR_CHANNEL: "debug",
                                "symbol": symbol,
                                "rows": int(len(df)),
                                "columns": list(df.columns)[:20],
                                "head": df.head(2).to_dict(orient="list"),
                                "tail": df.tail(2).to_dict(orient="list"),
                            },
                        )
                    except Exception:
                        pass

                bundle = self._compute_indicators(df, needed_keys, state, span, logger)

                # Pipeline execution per stage
                for stage_cfg, model in resolved:
                    if not state.alive and not state.is_held:
                        break

                    stage_passed[stage_cfg.name] = int(stage_passed.get(stage_cfg.name, 0)) + 1
                    score = self._run_stage(symbol, stage_cfg, model, bundle, state, span, logger)

                    # Drop policy
                    if stage_cfg.drop_threshold is not None and score < float(stage_cfg.drop_threshold):
                        if state.is_held:
                            state.notes[f"below_threshold_{stage_cfg.name}"] = 1.0
                            continue
                        state.alive = False
                        state.notes[f"dropped_by_{stage_cfg.name}"] = 1.0
                        stage_stats[stage_cfg.name] = int(stage_stats.get(stage_cfg.name, 0)) + 1
                        logger.emit(
                            "pipeline.symbol_dropped",
                            Severity.INFO,
                            {
                                semconv.ATTR_CHANNEL: "audit",
                                "symbol": symbol,
                                "stage": stage_cfg.name,
                                "score": float(score),
                                "threshold": float(stage_cfg.drop_threshold),
                                "reason": "below_threshold",
                            },
                        )
                        break

                # Final signal fields (simple v1 rule: last stage score)
                last_score = float(state.pipeline_results[-1].score) if state.pipeline_results else 0.0
                state.alpha_score = last_score
                state.notes["final_confidence"] = abs(last_score)

            # 5) Convert states into SignalsBySymbol
            signals: SignalsBySymbol = {}
            for symbol, state in states.items():
                if not state.alive and not state.is_held:
                    continue
                signed = float(state.alpha_score)
                confidence = float(state.notes.get("final_confidence", abs(signed)))
                signals[symbol] = Signal(symbol=symbol, signed=signed, confidence=confidence)
                logger.emit(
                    "pipeline.signal_emitted",
                    Severity.INFO,
                    {
                        semconv.ATTR_CHANNEL: "audit",
                        "symbol": symbol,
                        "signed": signed,
                        "confidence": confidence,
                    },
                )

            for st in pipeline_config.stages:
                dropped = int(stage_stats.get(st.name, 0))
                passed = int(stage_passed.get(st.name, 0))
                span.add_event(
                    semconv.EVT_PIPELINE_STAGE_COMPLETED,
                    {
                        "stage": st.name,
                        "passed_count": passed,
                        "dropped_count": dropped,
                        **(
                            {"threshold": float(st.drop_threshold)}
                            if st.drop_threshold is not None
                            else {}
                        ),
                    },
                )

            span.add_event(
                semconv.EVT_PIPELINE_SUMMARY,
                {
                    "signals_count": int(len(signals)),
                    "alive_count": int(sum(1 for s in states.values() if s.alive or s.is_held)),
                },
            )

            return PipelineRunResult(
                pipeline_config=pipeline_config,
                states_by_symbol=states,
                signals_by_symbol=signals,
                stage_stats=stage_stats,
            )

    def _resolve_models(self, pipeline_config: PipelineConfig) -> list[Tuple[PipelineStageConfig, SignalModel]]:
        pipeline: list[Tuple[PipelineStageConfig, SignalModel]] = []
        for stage in pipeline_config.stages:
            name = stage.name
            model = self.model_registry.get(name)
            if model is None:
                available = ", ".join(sorted(self.model_registry.keys()))
                raise RuntimeError(f"Model not found: {name!r}. Available models: {available}")
            pipeline.append((stage, model))
        return pipeline

    def _safe_get_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        state: SymbolState,
        span: SpanPort,
        logger: LoggerPort,
    ) -> pd.DataFrame | None:
        try:
            return self.market_data.get_bars(symbol, self.timeframe, start, end)
        except Exception as e:
            state.notes["data_error"] = 1.0
            span.record_exception(e)
            logger.emit(
                "error.exception",
                Severity.ERROR,
                {
                    semconv.ATTR_CHANNEL: "ops",
                    "symbol": symbol,
                    "exception_type": type(e).__name__,
                    "message": str(e),
                    "stage": "get_bars",
                },
            )
            return None

    def _compute_indicators(
        self,
        df: pd.DataFrame,
        needed_keys: set[str],
        state: SymbolState,
        span: SpanPort,
        logger: LoggerPort,
    ) -> Dict[str, IndicatorOutput]:
        bundle: Dict[str, IndicatorOutput] = {}
        for key in needed_keys:
            try:
                ind = self.indicator_picker(key, self.playbook)
                bundle[key] = ind.compute(df.copy())
            except Exception as e:
                state.notes[f"indicator_error_{key}"] = 1.0
                span.record_exception(e)
                logger.emit(
                    "error.exception",
                    Severity.ERROR,
                    {
                        semconv.ATTR_CHANNEL: "ops",
                        "exception_type": type(e).__name__,
                        "message": str(e),
                        "stage": "indicator",
                        "indicator": key,
                    },
                )
                bundle[key] = IndicatorOutput(score=0.0, features={})
        return bundle

    def _run_stage(
        self,
        symbol: str,
        stage_cfg: PipelineStageConfig,
        model: SignalModel,
        indicators: Dict[str, IndicatorOutput],
        state: SymbolState,
        span: SpanPort,
        logger: LoggerPort,
    ) -> float:
        stage_name = stage_cfg.name
        try:
            if logger.is_enabled(Severity.DEBUG):
                try:
                    logger.emit(
                        "model.input_snapshot",
                        Severity.DEBUG,
                        {
                            semconv.ATTR_CHANNEL: "debug",
                            "symbol": symbol,
                            "stage": stage_name,
                            "model": stage_name,
                            "indicator_keys": list(indicators.keys())[:30],
                            "features_keys": {
                                k: list(v.features.keys())[:20]
                                for k, v in indicators.items()
                                if getattr(v, "features", None)
                            },
                        },
                    )
                except Exception:
                    pass

            decision = model.decide(indicators)
        except Exception as e:
            state.notes[f"model_error_{stage_name}"] = 1.0
            span.record_exception(e)
            logger.emit(
                "error.exception",
                Severity.ERROR,
                {
                    semconv.ATTR_CHANNEL: "ops",
                    "symbol": symbol,
                    "stage": stage_name,
                    "model": stage_name,
                    "exception_type": type(e).__name__,
                    "message": str(e),
                    "stage_kind": "model",
                },
            )
            decision = ModelDecision(side="HOLD", weight=0.0, confidence=0.0)

        score = self._decision_to_score(decision)
        state.pipeline_results.append(ModelStageResult(model_name=stage_name, score=score))

        logger.emit(
            "model.decided",
            Severity.INFO,
            {
                semconv.ATTR_CHANNEL: "audit",
                "symbol": symbol,
                "stage": stage_name,
                "model": stage_name,
                "score": float(score),
                "side": decision.side,
                "weight": float(decision.weight or 0.0),
                "confidence": float(decision.confidence or 0.0),
            },
        )
        return score

    @staticmethod
    def _decision_to_score(d: ModelDecision) -> float:
        """Map a ModelDecision into a numeric score in [-1, 1]."""
        side = (d.side or "HOLD").upper()
        w = float(d.weight or 0.0)
        w = max(0.0, min(1.0, w))
        if side == "BUY":
            s = w
        elif side == "SELL":
            s = -w
        else:
            s = 0.0
        return max(-1.0, min(1.0, s))
