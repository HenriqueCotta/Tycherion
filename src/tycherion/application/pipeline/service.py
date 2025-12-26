from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Mapping, Optional, Protocol, Tuple, Any

import pandas as pd

from tycherion.domain.portfolio.entities import PortfolioSnapshot, Signal, SignalsBySymbol
from tycherion.domain.signals.entities import (
    IndicatorOutput,
    ModelDecision,
    ModelStageResult,
    SymbolState,
)
from tycherion.ports.market_data import MarketDataPort

from .config import PipelineConfig, PipelineStageConfig
from .result import PipelineRunResult


class TelemetrySink(Protocol):
    def emit(self, event: str, payload: Dict[str, Any]) -> None: ...


class ModelLike(Protocol):
    def requires(self) -> set[str]: ...
    def decide(self, indicators: Dict[str, IndicatorOutput]) -> ModelDecision: ...


@dataclass(slots=True)
class ModelPipelineService:
    """Façade that runs the ordered per-symbol model pipeline."""

    market_data: MarketDataPort
    model_registry: Mapping[str, ModelLike]
    indicator_picker: Callable[[str, Optional[str]], Any]  # returns indicator instance with .compute(df)
    timeframe: str
    lookback_days: int
    playbook: str | None = None
    telemetry_sink: TelemetrySink | None = None

    def run(
        self,
        universe_symbols: list[str],
        portfolio_snapshot: PortfolioSnapshot,
        pipeline_config: PipelineConfig,
    ) -> PipelineRunResult:
        held_symbols = set(portfolio_snapshot.positions.keys())

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
                # a model might not implement requires()
                pass

        # 4) Time window for analysis
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=int(self.lookback_days))

        stage_stats: Dict[str, int] = {st.name: 0 for st in pipeline_config.stages}

        for symbol, state in states.items():
            if not state.alive and not state.is_held:
                continue

            df = self._safe_get_bars(symbol, start, end, state)
            if df is None or df.empty:
                if not state.is_held:
                    state.alive = False
                continue

            bundle = self._compute_indicators(df, needed_keys, state)

            # Pipeline execution per stage
            for stage_cfg, model in resolved:
                if not state.alive and not state.is_held:
                    break

                score = self._run_stage(symbol, stage_cfg, model, bundle, state)

                # Drop policy
                if stage_cfg.drop_threshold is not None and score < float(stage_cfg.drop_threshold):
                    if state.is_held:
                        state.notes[f"below_threshold_{stage_cfg.name}"] = 1.0
                        continue
                    state.alive = False
                    state.notes[f"dropped_by_{stage_cfg.name}"] = 1.0
                    stage_stats[stage_cfg.name] = int(stage_stats.get(stage_cfg.name, 0)) + 1
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

        return PipelineRunResult(
            pipeline_config=pipeline_config,
            states_by_symbol=states,
            signals_by_symbol=signals,
            stage_stats=stage_stats,
        )

    def _resolve_models(self, pipeline_config: PipelineConfig) -> list[Tuple[PipelineStageConfig, ModelLike]]:
        pipeline: list[Tuple[PipelineStageConfig, ModelLike]] = []
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
    ) -> pd.DataFrame | None:
        try:
            return self.market_data.get_bars(symbol, self.timeframe, start, end)
        except Exception as e:
            state.notes["data_error"] = 1.0
            self._telemetry("data_error", {"symbol": symbol, "error": str(e)})
            return None

    def _compute_indicators(
        self,
        df: pd.DataFrame,
        needed_keys: set[str],
        state: SymbolState,
    ) -> Dict[str, IndicatorOutput]:
        bundle: Dict[str, IndicatorOutput] = {}
        for key in needed_keys:
            try:
                ind = self.indicator_picker(key, self.playbook)
                bundle[key] = ind.compute(df.copy())
            except Exception as e:
                state.notes[f"indicator_error_{key}"] = 1.0
                self._telemetry("indicator_error", {"key": key, "error": str(e)})
                bundle[key] = IndicatorOutput(score=0.0, features={})
        return bundle

    def _run_stage(
        self,
        symbol: str,
        stage_cfg: PipelineStageConfig,
        model: ModelLike,
        indicators: Dict[str, IndicatorOutput],
        state: SymbolState,
    ) -> float:
        stage_name = stage_cfg.name
        try:
            decision = model.decide(indicators)
        except Exception as e:
            state.notes[f"model_error_{stage_name}"] = 1.0
            self._telemetry("model_error", {"symbol": symbol, "model": stage_name, "error": str(e)})
            decision = ModelDecision(side="HOLD", weight=0.0, confidence=0.0)

        score = self._decision_to_score(decision)
        state.pipeline_results.append(ModelStageResult(model_name=stage_name, score=score))
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

    def _telemetry(self, event: str, payload: Dict[str, Any]) -> None:
        if self.telemetry_sink is None:
            return
        try:
            self.telemetry_sink.emit(event, payload)
        except Exception:
            # never break the run due to telemetry
            return
