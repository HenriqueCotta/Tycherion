from __future__ import annotations

from typing import Mapping


def _parse_headers(raw: str | Mapping[str, str] | None) -> dict[str, str]:
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return {str(k).strip(): str(v).strip() for k, v in raw.items() if str(k).strip()}

    parsed: dict[str, str] = {}
    for part in str(raw).split(","):
        if not part.strip():
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        elif ":" in part:
            k, v = part.split(":", 1)
        else:
            continue
        k = k.strip()
        v = v.strip()
        if k:
            parsed[k] = v
    return parsed


def _infer_insecure(endpoint: str, insecure: bool | None) -> bool:
    if insecure is not None:
        return bool(insecure)
    return not str(endpoint).lower().startswith("https://")


def build_span_exporter(endpoint: str, protocol: str, headers: str | Mapping[str, str] | None, insecure: bool | None = None):
    proto = (protocol or "grpc").strip().lower()
    hdrs = _parse_headers(headers)
    try:
        if proto == "http":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore

            return OTLPSpanExporter(endpoint=endpoint, headers=hdrs)

        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore

        return OTLPSpanExporter(endpoint=endpoint, headers=hdrs, insecure=_infer_insecure(endpoint, insecure))
    except Exception as exc:
        print(f"[tycherion] OTLP span exporter init failed: {exc}")
        return None


def build_metric_reader(
    *,
    endpoint: str,
    protocol: str,
    headers: str | Mapping[str, str] | None,
    insecure: bool | None = None,
):
    proto = (protocol or "grpc").strip().lower()
    hdrs = _parse_headers(headers)
    try:
        if proto == "http":
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter  # type: ignore
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # type: ignore

            exporter = OTLPMetricExporter(endpoint=endpoint, headers=hdrs)
            return PeriodicExportingMetricReader(exporter)

        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter  # type: ignore
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader  # type: ignore

        exporter = OTLPMetricExporter(endpoint=endpoint, headers=hdrs, insecure=_infer_insecure(endpoint, insecure))
        return PeriodicExportingMetricReader(exporter)
    except Exception as exc:
        print(f"[tycherion] OTLP metric exporter init failed: {exc}")
        return None
