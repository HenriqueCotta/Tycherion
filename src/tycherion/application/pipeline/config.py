from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from tycherion.shared.config import AppConfig, PipelineStageCfg


@dataclass(frozen=True, slots=True)
class PipelineStageConfig:
    """Configuration of a single pipeline stage (application-level, YAML-agnostic)."""

    name: str
    drop_threshold: float | None = None


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Internal normalized pipeline configuration.

    This object is the only thing the pipeline execution should consume.
    It is intentionally decoupled from YAML and Pydantic.
    """

    stages: List[PipelineStageConfig]


def build_pipeline_config(cfg: AppConfig) -> PipelineConfig:
    """Build a PipelineConfig from the current AppConfig.

    The AppConfig is created by YAML/adapters, but the rest of the application
    should not read YAML-derived structures directly.
    """
    stages_in: Iterable[PipelineStageCfg] = cfg.application.models.pipeline or []
    stages: list[PipelineStageConfig] = []
    for st in stages_in:
        stages.append(
            PipelineStageConfig(
                name=str(st.name),
                drop_threshold=(float(st.drop_threshold) if st.drop_threshold is not None else None),
            )
        )
    if not stages:
        raise RuntimeError(
            "No model pipeline configured. Please set application.models.pipeline in your YAML."
        )
    return PipelineConfig(stages=stages)
