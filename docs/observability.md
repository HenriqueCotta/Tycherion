# Observabilidade no Tycherion

Este guia ensina **como funciona a observabilidade** do projeto, onde tocar no código e como ativar/exportar telemetria. Serve tanto para onboarding quanto como referência rápida.

---

## Visão geral (hexagonal + OTel)
- **Core (application/domain)** não conhece OpenTelemetry. Ele fala apenas com **ports**:
  - `ObservabilityPort` → `traces`, `logs`, `metrics`
  - Providers retornam objetos `TracerPort`, `LoggerPort`, `MeterPort`.
- **Adapters** implementam os ports:
  - `adapters/observability/otel/*` (principal)
  - `adapters/observability/noop/*` (fallback)
- **OTel SDK** só aparece no adapter OTel.

Fluxo simplificado:
```
bootstrap/main.py → _build_observability() → (OtelObservability | NoopObservability)
    ↳ application/runmodes/live_multimodel.py usa obs.traces/logs/metrics
    ↳ application/pipeline/service.py cria spans, eventos e logs
```

---

## Onde estão as peças

### Ports (API estável)
- `src/tycherion/ports/observability/observability.py` — facade com `traces`, `logs`, `metrics`.
- `src/tycherion/ports/observability/traces.py` — `TracerProviderPort`, `TracerPort`, `SpanPort`.
- `src/tycherion/ports/observability/logs.py` — `LoggerProviderPort`, `LoggerPort`.
- `src/tycherion/ports/observability/metrics.py` — `MeterProviderPort`, `MeterPort`.
- `src/tycherion/ports/observability/semconv.py` — nomes de spans/eventos/atributos prefixados `tycherion.*`.
- `src/tycherion/ports/observability/types.py` — tipos base, severidade, schema version.

### Adapters
- `src/tycherion/adapters/observability/otel/`
  - `otel_observability.py` — cria resource, providers OTel, console, OTLP exporters.
  - `otel_traces.py` — implementa `TracerProviderPort`, `TracerPort`, `SpanPort`.
  - `otel_logs.py` — logger com **pretty** (dev) e **json** (prod/collector); filtro por canal.
  - `otel_metrics.py` — minimal meter/counter wrapper.
  - `otel_export.py` — OTLP (grpc|http), headers, `otlp_insecure` (auto infere http→true/https→false).
  - `otel_resource.py` — resource attrs (service.name, runner_id, run_id, schema_version, deployment.environment).
  - `console_dev.py` — saída humana para dev.
- `src/tycherion/adapters/observability/noop/` — implementações vazias para fallback.

### Bootstrap
- `src/tycherion/bootstrap/main.py` → `_build_observability(cfg, config_path)` decide OTel vs Noop e injeta em toda a app.

### Configuração
- `shared/config.py` → classe `ObservabilityCfg` (alias legacy `telemetry` é aceito com warning).
- YAML (`configs/*.yaml`), seção `observability:`:
  ```yaml
  observability:
    console_enabled: true
    console_min_level: INFO
    console_channels: [ops]        # filtra por tycherion.channel
    log_format: pretty             # pretty|json
    otlp_enabled: false
    otlp_endpoint: http://localhost:4317
    otlp_protocol: grpc            # grpc|http
    otlp_headers: null             # ex: "authorization=Bearer x,y=z"
    otlp_insecure: null            # null => auto (http->true, https->false)
    deployment_env: dev
  ```
  Env overrides: `TYCHERION_OTLP_ENABLED`, `TYCHERION_OTLP_ENDPOINT`, `TYCHERION_OTLP_PROTOCOL`, `TYCHERION_OTLP_HEADERS`, `TYCHERION_OTLP_INSECURE`, `TYCHERION_DEPLOYMENT_ENV`, `TYCHERION_LOG_FORMAT`, `TYCHERION_CONSOLE_ENABLED`, `TYCHERION_CONSOLE_MIN_LEVEL`, `TYCHERION_CONSOLE_CHANNELS`.

---

## Como instrumentar no core

### Spans
```python
tracer = observability.traces.get_tracer("tycherion.pipeline", version=TYCHERION_SCHEMA_VERSION)
with tracer.start_as_current_span(semconv.SPAN_PIPELINE, attributes={
    "timeframe": cfg.timeframe,
    "lookback_days": cfg.lookback_days,
}):
    ...
```

### Eventos no span
```python
span.add_event(
    semconv.EVT_PIPELINE_STAGE_STARTED,
    {"stage": st.name, "threshold": float(st.drop_threshold) if st.drop_threshold else None},
)
```

### Logs correlacionados
```python
logger = observability.logs.get_logger("tycherion.pipeline", version=TYCHERION_SCHEMA_VERSION)
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
```
O logger pega `trace_id/span_id` do contexto OTel automaticamente.

### Métricas (mínimas)
```python
meter = observability.metrics.get_meter("tycherion.pipeline")
counter = meter.create_counter("tycherion.signals.emitted")
counter.add(1, {"symbol": symbol})
```

---

## Como rodar local
1) Dependências: `opentelemetry-sdk` instalados no venv.
2) Ativar console dev:
   ```bash
   export TYCHERION_CONSOLE_ENABLED=true
   export TYCHERION_LOG_FORMAT=pretty   # ou json para stdout estruturado
   python scripts/run_demo.py
   ```
3) Para não ficar em loop, ajuste `run_forever: false` no YAML de demo.

Saída típica (pretty):
```
17:34:19 [SPAN] ... tycherion.pipeline started | trace=... span=...
17:34:19 [EVT] stage=trend_following ... tycherion.pipeline.stage_started | trace=...
17:34:19 [INFO] tycherion.channel=audit ... pipeline.signal_emitted | trace=...
```

---

## Como enviar para Alloy/Collector (OTLP)
1) Suba seu collector/local Alloy ouvindo em `http://localhost:4317` (gRPC) ou `http://localhost:4318` (HTTP).
2) Exporte variáveis:
   ```bash
   export TYCHERION_OTLP_ENABLED=true
   export TYCHERION_OTLP_ENDPOINT=http://localhost:4317   # ou 4318 + protocol=http
   export TYCHERION_OTLP_PROTOCOL=grpc                    # ou http
   export TYCHERION_OTLP_HEADERS="authorization=Bearer xyz"
   ```
3) Rode a app. Traces e métricas irão para o collector. Logs: use `TYCHERION_LOG_FORMAT=json` + promtail/collector lendo stdout.

---

## Decisões e garantias
- **Boundary:** core nunca importa `opentelemetry.*`.
- **SemConv:** nomes prefixados `tycherion.*` para spans/eventos/attrs.
- **IDs:** trace/span IDs gerados pelo OTel SDK.
- **Logs:** correlacionados por contexto; saída dev pretty, prod JSON.
- **Fallback:** se OTel falhar ou libs não existirem, cai para Noop sem quebrar o app.

---

## Perguntas frequentes

**Q: Quero adicionar um novo evento. Onde coloco o nome?**  
Adicione em `ports/observability/semconv.py` seguindo o prefixo `tycherion.*`.

**Q: Preciso de uma métrica nova. Como?**  
Use `observability.metrics.get_meter(...).create_counter(...)` e chame `counter.add(...)`. Se OTLP estiver on, o collector envia; se não, fica no no-op.

**Q: Como desabilitar logs verbosos?**  
`TYCHERION_CONSOLE_MIN_LEVEL` (INFO/ERROR...). Para filtrar por canal, ajuste `console_channels` no YAML/ENV (`["ops"]`, `["audit"]`, etc.).

**Q: E se o collector usar TLS?**  
Se o endpoint for `https://...`, `otlp_insecure` vira `False` automaticamente. Pode forçar via `TYCHERION_OTLP_INSECURE=false`.

---

## Checklist para modificar/estender
- [ ] Criou/atualizou nomes em `semconv.py`?
- [ ] Manteve imports de OTel somente no adapter?
- [ ] Ajustou config (`observability` section) e documentou variáveis?
- [ ] Testou com `TYCHERION_CONSOLE_ENABLED=true` (dev) e, se preciso, com `TYCHERION_OTLP_ENABLED=true`?

Pronto! Com isso você deve conseguir navegar, instrumentar e evoluir a observabilidade do Tycherion com segurança.
