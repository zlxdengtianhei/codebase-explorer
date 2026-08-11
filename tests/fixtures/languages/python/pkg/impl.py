from .base import Base
class Worker(Base):
    def run(self) -> str:
        return "ok"
def same() -> str:
    return "impl"
