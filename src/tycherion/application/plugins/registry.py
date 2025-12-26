from __future__ import annotations
from typing import Dict, List, Callable, Iterable

from tycherion.domain.signals.indicators.base import BaseIndicator
from tycherion.domain.signals.models.base import SignalModel
from tycherion.domain.portfolio.allocators.base import BaseAllocator
from tycherion.domain.portfolio.balancers.base import BaseBalancer

INDICATORS: Dict[str, List[BaseIndicator]] = {}
MODELS: Dict[str, SignalModel] = {}
ALLOCATORS: Dict[str, BaseAllocator] = {}
BALANCERS: Dict[str, BaseBalancer] = {}
DEFAULT_METHOD: Dict[str, str] = {}


def register_indicator(*, key: str, method: str, tags: set[str]):
    """
    Register an indicator implementation for a given logical key (e.g. "trend")
    and method (e.g. "donchian_50_50").
    """
    def deco(cls):
        inst = cls()
        inst.key = key
        inst.method = method
        inst.tags = tags
        INDICATORS.setdefault(key, []).append(inst)
        return cls
    return deco


def register_model(*, name: str, tags: set[str]):
    """
    Register a per-symbol signal model.
    """
    def deco(cls):
        inst = cls()
        inst.name = name
        inst.tags = tags
        MODELS[name] = inst
        return cls
    return deco


def register_allocator(*, name: str, tags: set[str]):
    """
    Register a portfolio allocator strategy.
    """
    def deco(cls):
        inst = cls()
        inst.name = name
        inst.tags = tags
        ALLOCATORS[name] = inst
        return cls
    return deco


def register_balancer(*, name: str, tags: set[str]):
    """
    Register a portfolio balancer / rebalancer strategy.
    """
    def deco(cls):
        inst = cls()
        inst.name = name
        inst.tags = tags
        BALANCERS[name] = inst
        return cls
    return deco


def set_default_indicator_method(key: str, method: str) -> None:
    DEFAULT_METHOD[key] = method


def pick_indicator_for(key: str, playbook: str | None = None) -> BaseIndicator:
    """
    Pick an indicator instance for a given key and (optionally) playbook.
    Preference order:
    - indicators whose tags contain the playbook name
    - indicators whose tags contain "default"
    - otherwise, the first registered
    If DEFAULT_METHOD[key] is set, prefer that method among candidates.
    """
    candidates: Iterable[BaseIndicator] = INDICATORS.get(key, [])
    candidates = list(candidates)
    if not candidates:
        raise KeyError(f"No indicators registered for key={key!r}")

    # filter by tags / playbook
    if playbook:
        tagged = [
            ind for ind in candidates
            if playbook in getattr(ind, "tags", set())
        ]
        if tagged:
            candidates = tagged

    # then prefer "default"
    defaults = [
        ind for ind in candidates
        if "default" in getattr(ind, "tags", set())
    ]
    if defaults:
        candidates = defaults

    # lastly, prefer DEFAULT_METHOD if configured
    method = DEFAULT_METHOD.get(key)
    if method:
        for ind in candidates:
            if getattr(ind, "method", None) == method:
                return ind

    return candidates[0]


def auto_discover() -> None:
    """
    Import all plugin modules so that their decorators run and fill the
    registries above. This is called once during application startup.
    """
    import importlib
    import pkgutil

    bases = (
        "tycherion.domain.signals.indicators",
        "tycherion.domain.signals.models",
        "tycherion.domain.portfolio.allocators",
        "tycherion.domain.portfolio.balancers",
    )

    for base in bases:
        try:
            pkg = importlib.import_module(base)
        except Exception as e:
            print(f"[plugins] base import failed: {base} -> {e}")
            continue

        pkg_path = getattr(pkg, "__path__", None)
        if not pkg_path:
            continue

        for mod in pkgutil.walk_packages(pkg_path, pkg.__name__ + "."):
            try:
                importlib.import_module(mod.name)
            except Exception as e:
                print(f"[plugins] import failed: {mod.name} -> {e}")

    print(
        f"[plugins] discovered "
        f"indicators={sum(len(v) for v in INDICATORS.values())} "
        f"models={len(MODELS)} "
        f"allocators={len(ALLOCATORS)} "
        f"balancers={len(BALANCERS)}"
    )
