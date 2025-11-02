from __future__ import annotations
from typing import Dict, List

INDICATORS: Dict[str, List[object]] = {}
MODELS: Dict[str, object] = {}
DEFAULT_METHOD: Dict[str, str] = {}

def register_indicator(*, key: str, method: str, tags: set[str]):
    def deco(cls):
        inst = cls()
        inst.key = key
        inst.method = method
        inst.tags = tags
        INDICATORS.setdefault(key, []).append(inst)
        DEFAULT_METHOD.setdefault(key, method)
        return cls
    return deco

def register_model(*, name: str, tags: set[str]):
    def deco(cls):
        inst = cls()
        inst.name = name
        inst.tags = tags
        MODELS[name] = inst
        return cls
    return deco

def pick_indicator_for(key: str, playbook: str = "default"):
    candidates = INDICATORS.get(key, [])
    for ind in candidates:
        if playbook in getattr(ind, "tags", set()):
            return ind
    for ind in candidates:
        if getattr(ind, "method", None) == DEFAULT_METHOD.get(key):
            return ind
    raise KeyError(f"No indicator registered for key={key}")

# --- auto-discovery of plugins ---
def auto_discover() -> None:
    """Importa todos os módulos em tycherion.domain.indicators e .models
    para que os decorators registrem indicadores e models automaticamente."""
    import importlib, pkgutil

    for base in ("tycherion.domain.indicators", "tycherion.domain.models"):
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

    print(f"[plugins] discovered indicators={len(INDICATORS)} models={len(MODELS)}")
