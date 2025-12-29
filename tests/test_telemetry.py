from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from tycherion.application.pipeline.config import PipelineConfig, PipelineStageConfig
from tycherion.application.pipeline.service import ModelPipelineService
from tycherion.application.telemetry.hub import TelemetryHub
from tycherion.adapters.telemetry.memory import InMemoryTelemetrySink
from tycherion.domain.portfolio.entities import PortfolioSnapshot
from tycherion.domain.signals.entities import ModelDecision
from tycherion.domain.signals.models.base import SignalModel
from tycherion.ports.telemetry import TelemetryLevel


class TestTelemetryHub(unittest.TestCase):
    def test_enabled_any_sink_accepts(self) -> None:
        sink = InMemoryTelemetrySink(
            enabled_flag=True,
            channels={"debug"},
            min_level=TelemetryLevel.DEBUG,
        )
        hub = TelemetryHub(sinks=[sink])

        self.assertTrue(hub.enabled("debug", "DEBUG"))
        self.assertFalse(hub.enabled("audit", "INFO"))


class _DummyMarketData:
    def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        _ = (symbol, timeframe, start, end)
        # Minimal but realistic-ish OHLC frame
        return pd.DataFrame(
            {
                "time": [datetime(2020, 1, 1, tzinfo=timezone.utc)],
                "open": [1.0],
                "high": [1.0],
                "low": [1.0],
                "close": [1.0],
                "tick_volume": [1],
            }
        )


class _DummyModel(SignalModel):
    def requires(self) -> set[str]:
        return set()

    def decide(self, indicators):  # type: ignore[override]
        _ = indicators
        return ModelDecision(side="BUY", weight=0.5, confidence=0.1)


class TestDebugGating(unittest.TestCase):
    def test_debug_events_not_emitted_when_debug_disabled(self) -> None:
        sink = InMemoryTelemetrySink(
            enabled_flag=True,
            channels={"audit", "ops"},
            min_level=TelemetryLevel.INFO,
        )
        hub = TelemetryHub(sinks=[sink])

        svc = ModelPipelineService(
            market_data=_DummyMarketData(),
            model_registry={"dummy": _DummyModel()},
            indicator_picker=lambda key, pb: None,  # type: ignore[return-value]
            timeframe="D1",
            lookback_days=10,
            playbook=None,
            telemetry=hub,
        )

        pipeline_config = PipelineConfig(stages=[PipelineStageConfig(name="dummy", drop_threshold=None)])
        portfolio = PortfolioSnapshot(equity=1000.0, positions={})

        svc.run(
            universe_symbols=["AAA"],
            portfolio_snapshot=portfolio,
            pipeline_config=pipeline_config,
            run_id="test-run",
        )

        self.assertTrue(len(sink.events) > 0)
        self.assertEqual(0, sum(1 for e in sink.events if e.channel == "debug"))


if __name__ == "__main__":
    unittest.main()
