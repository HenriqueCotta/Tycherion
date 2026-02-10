"""Tycherion observability semantic conventions.

These constants keep attribute keys and common span/event names in one place
so instrumentation stays consistent while remaining independent from the
OpenTelemetry SDK.
"""

# Resource attributes
SERVICE_NAME = "service.name"
SERVICE_INSTANCE_ID = "service.instance.id"
DEPLOYMENT_ENVIRONMENT = "deployment.environment"
TYCHERION_RUNNER_ID = "tycherion.runner_id"
TYCHERION_RUN_ID = "tycherion.run_id"
TYCHERION_SCHEMA_VERSION = "tycherion.schema_version"

# Span names (prefixed to avoid collisions across services)
SPAN_BOOTSTRAP_DISCOVER = "tycherion.bootstrap.discover"
SPAN_PIPELINE = "tycherion.pipeline"
SPAN_COVERAGE_FETCH = "tycherion.coverage.fetch"
SPAN_ALLOCATOR = "tycherion.allocator"
SPAN_BALANCER = "tycherion.balancer"
SPAN_EXECUTION = "tycherion.execution"
SPAN_RUN = "tycherion.run"

# Event names (prefixed)
EVT_PIPELINE_STAGE_STARTED = "tycherion.pipeline.stage_started"
EVT_PIPELINE_STAGE_COMPLETED = "tycherion.pipeline.stage_completed"
EVT_PIPELINE_SUMMARY = "tycherion.pipeline.summary"
EVT_PIPELINE_RUN_SUMMARY = "tycherion.pipeline.run_summary"
EVT_COVERAGE_SUMMARY = "tycherion.coverage.summary"
EVT_ALLOCATOR_COMPLETED = "tycherion.allocator.completed"
EVT_REBALANCE_PLAN_BUILT = "tycherion.rebalance.plan_built"
EVT_ORDERS_BUILT = "tycherion.orders.built"

# Common attribute keys
ATTR_CHANNEL = "tycherion.channel"
ATTR_SYMBOL = "symbol"
ATTR_STAGE = "stage"
ATTR_SCORE = "score"
ATTR_THRESHOLD = "threshold"
ATTR_CONFIG_HASH = "config_hash"
ATTR_CONFIG_PATH = "config_path"
ATTR_RUN_MODE = "run_mode"
