from .base import Base
from .impl import Worker as Alias
from .impl import same as impl_same
__all__ = ["Alias", "entry"]
def same() -> str:
    return "api"
def entry(worker: Base) -> str:
    worker.run()
    missing()
    print(worker)
    return impl_same()
def dynamic(obj):
    return obj.run()
