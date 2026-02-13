# Plugins and Registry Reference

Audience: developers.
Goal: define canonical behavior for plugin registration and selection.

## Plugin Types

| Type | Base | Decorator | Folder |
| --- | --- | --- | --- |
| Indicator | `BaseIndicator` | `@register_indicator(key, method, tags)` | `domain/signals/indicators` |
| Model | `SignalModel` | `@register_model(name, tags)` | `domain/signals/models` |
| Allocator | `BaseAllocator` | `@register_allocator(name, tags)` | `domain/portfolio/allocators` |
| Balancer | `BaseBalancer` | `@register_balancer(name, tags)` | `domain/portfolio/balancers` |

## Discovery

- `application/plugins/registry.py::auto_discover()` imports plugin modules at bootstrap.
- Registration happens at import time through decorators.

## Indicator Resolution Rules (Canonical)

Given `(key, playbook)`, resolver applies:

1. Start from all indicators registered for `key`.
2. If `playbook` is set and at least one indicator has that tag, keep only tagged indicators.
3. Prefer indicators tagged `default`.
4. If `DEFAULT_METHOD[key]` exists, prefer matching `method`.
5. Fall back to first remaining candidate.

## Model, Allocator, and Balancer Resolution

- Models are selected explicitly by name from `application.models.pipeline`.
- Allocator and balancer are selected by exact config names in `application.portfolio.*`.
- Playbook does not currently auto-select models, allocators, or balancers.

## Failure Cases

- No indicator for key: raises `KeyError`.
- Unknown model, allocator, or balancer name: runtime error at run mode startup.

## Best Practices

- Keep names stable and explicit.
- Use `default` tag for baseline behavior.
- Avoid side effects in module import.
- Add tests whenever resolver rules change.

## Links

- Next: [Development Guide](./development.md)
- See also: [ADR-0003 Plugin Resolution Rules](../architecture/decisions/adr-0003-plugin-resolution-rules.md)
