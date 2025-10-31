from __future__ import annotations
from typing import Protocol

class AccountPort(Protocol):
    def is_demo(self) -> bool: ...
