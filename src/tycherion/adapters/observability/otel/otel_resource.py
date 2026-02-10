from __future__ import annotations

from typing import Mapping

from tycherion.ports.observability import semconv


def build_resource(
    *,
    runner_id: str,
    run_id: str,
    schema_version: str,
    deployment_env: str | None = None,
):
    """Best-effort builder for the OpenTelemetry Resource used by Tycherion."""

    try:
        from opentelemetry.sdk.resources import Resource  # type: ignore
    except Exception as e:  # pragma: no cover - dependency missing is handled by caller
        raise RuntimeError("opentelemetry-sdk is required for OTel resource creation") from e

    attrs: Mapping[str, str] = {
        semconv.SERVICE_NAME: "tycherion",
        semconv.SERVICE_INSTANCE_ID: runner_id,
        semconv.TYCHERION_RUNNER_ID: runner_id,
        semconv.TYCHERION_RUN_ID: run_id,
        semconv.TYCHERION_SCHEMA_VERSION: schema_version,
    }

    if deployment_env:
        attrs = dict(attrs)
        attrs[semconv.DEPLOYMENT_ENVIRONMENT] = deployment_env

    return Resource.create(attrs)
