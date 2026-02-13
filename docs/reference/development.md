# Development Guide

Audience: contributors.
Goal: add and evolve plugins safely with stable conventions.

## Tooling and Quality

- Python 3.10+, install with `pip install -e .`.
- Type checks: `mypy --strict`.
- Style checks: `ruff` with line length 100.
- Domain code must remain infrastructure-agnostic.

## Add an Indicator

1. Create a module in `domain/signals/indicators/`.
2. Inherit `BaseIndicator`.
3. Register with `@register_indicator(key, method, tags)`.
4. Return `IndicatorOutput(score, features)`.

Example:

```python
@register_indicator(key="momentum", method="roc_10", tags={"default", "swing"})
class Roc10(BaseIndicator):
    period = 10

    def compute(self, df: pd.DataFrame) -> IndicatorOutput:
        if df.empty or len(df) < self.period + 1:
            return IndicatorOutput(score=0.0, features={})
        roc = (df["close"].iloc[-1] / df["close"].iloc[-(self.period + 1)]) - 1
        return IndicatorOutput(score=float(max(-1.0, min(1.0, roc))), features={"roc": float(roc)})
```

## Add a Signal Model

1. Create a module in `domain/signals/models/`.
2. Inherit `SignalModel`.
3. Implement `requires()` and `decide(...)`.
4. Register with `@register_model(name, tags)`.

Example:

```python
@register_model(name="momentum_pullback", tags={"swing"})
class MomentumPullback(SignalModel):
    def requires(self) -> set[str]:
        return {"trend", "stretch"}

    def decide(self, indicators: dict[str, IndicatorOutput]) -> ModelDecision:
        trend = indicators["trend"].score
        stretch = indicators["stretch"].score
        if trend > 0.3 and stretch < -0.4:
            return ModelDecision(side="BUY", weight=0.7, confidence=0.65)
        if trend < -0.3 and stretch > 0.4:
            return ModelDecision(side="SELL", weight=0.7, confidence=0.65)
        return ModelDecision(side="HOLD", weight=0.0, confidence=0.2)
```

## Verify Playbook and Tags Resolution

Use this example to force indicator selection by playbook tag:

```yaml
application:
  playbook: swing
  models:
    pipeline:
      - name: momentum_pullback
```

Validation command:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.application.plugins.registry import auto_discover, pick_indicator_for; from tycherion.adapters.observability.noop.noop_observability import NoopObservability; auto_discover(observability=NoopObservability()); ind = pick_indicator_for('momentum', 'swing'); print(ind.method, sorted(ind.tags))"
```

## Add Allocator or Balancer

- Allocator: inherit `BaseAllocator`, implement `allocate(signals)`.
- Balancer: inherit `BaseBalancer`, implement `plan(portfolio, target, threshold)`.
- Register with `@register_allocator(...)` or `@register_balancer(...)`.

## Plugin Not Found: Fast Debug

1. Confirm decorator exists in code:

   ```powershell
   rg -n "@register_model\(name=\"momentum_pullback\"" src/tycherion/domain
   ```

2. Confirm auto-discovery can see it:

   ```powershell
   .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'src'); from tycherion.application.plugins.registry import auto_discover, MODELS; from tycherion.adapters.observability.noop.noop_observability import NoopObservability; auto_discover(observability=NoopObservability()); print(sorted(MODELS.keys()))"
   ```

## Testing Expectations

- Add or update tests for every plugin or runtime behavior change.
- Cover edge conditions (empty data, unknown symbols, threshold edges).
- Follow [Testing Reference](./testing.md).

## Observability Expectations

- Inject and use `ObservabilityPort`.
- Use names from `semconv.py`; avoid ad-hoc event names.
- Follow [Observability Instrumentation](./observability/instrumentation.md).

## Pull Request Checklist

- [ ] Plugin is registered and discoverable.
- [ ] Type and style checks pass.
- [ ] Tests cover new or changed behavior.
- [ ] Docs and config are updated when behavior changes.

## Links

- Next: [Testing Reference](./testing.md)
- See also: [Plugins and Registry Reference](./plugins.md)
