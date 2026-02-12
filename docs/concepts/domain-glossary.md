# Domain Glossary

Audience: strategy and platform contributors.
Goal: define domain terms used by signal, allocation, and rebalancing logic.

- Coverage: set of symbols considered in a cycle.
- Stage: one model execution step inside `application.models.pipeline`.
- Drop threshold: stage threshold used to remove non-held symbols early.
- Signal: normalized directional intent (`signed`, `confidence`) per symbol.
- Allocation: target portfolio weights derived from signals.
- Rebalance: transition from current weights to target weights.
- Churn: unnecessary frequent rebalances caused by small fluctuations.
- Dry run: execution path that does not place real orders.
- Threshold weight: minimum weight delta that triggers rebalance action.

## Links

- Next: [Risk, Sizing, and Churn](./risk-sizing-churn.md)
- See also: [Domain Contracts](../architecture/domain-contracts.md)
