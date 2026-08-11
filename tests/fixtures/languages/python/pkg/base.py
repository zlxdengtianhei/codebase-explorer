from typing import Protocol
class Base(Protocol):
    def run(self) -> str: ...
def same() -> str:
    return "base"
