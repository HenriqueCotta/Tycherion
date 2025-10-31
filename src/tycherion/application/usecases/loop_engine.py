from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Callable

@dataclass
class LoopPolicy:
    run_forever: bool = False
    interval_seconds: int = 60

def run_loop(step: Callable[[], None], policy: LoopPolicy) -> None:
    if not policy.run_forever:
        step()
        return
    while True:
        try:
            step()
            time.sleep(max(1, policy.interval_seconds))
        except KeyboardInterrupt:
            print("Parando por teclado.")
            break
        except Exception as e:
            print("Erro no loop:", e)
            time.sleep(3)
