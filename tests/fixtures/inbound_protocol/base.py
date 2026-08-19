"""Small source-only inbound protocol fixture.

The module deliberately keeps receiver and call shapes explicit.  It is
authored independently of Codebase Explorer output; the paired oracle is
written from the Python AST and the frozen T2A rules.
"""

from typing import final


def direct_target(value: object = None) -> object:
    """Repository-local direct binding target."""
    return value


def imported_target() -> str:
    """Repository-local target reached through an import alias."""
    return "imported"


class Base:
    def save(self) -> str:
        return "base"

    def call_self(self) -> str:
        return self.save()


class Child(Base):
    def save(self) -> str:
        return "child"

    def inherited_call(self) -> str:
        return self.save()


class InheritedOnly(Base):
    """Exercises C3 lookup when the child has no local member."""

    def run(self) -> str:
        return self.save()


class DeepReceiver:
    """Exercises an initial ``self`` attribute chain as a visible gap."""

    def run(self) -> str:
        return self.backend.save()


class Root:
    def save(self) -> str:
        return "root"


class Left(Root):
    def save(self) -> str:
        return "left"


class Right(Root):
    def save(self) -> str:
        return "right"


class Diamond(Left, Right):
    def call(self) -> str:
        return self.save()


class DiamondChild(Diamond):
    def save(self) -> str:
        return "diamond-child"


class UnknownChild(UnknownExternalBase):
    def call(self) -> object:
        return self.save()


@final
class FinalClass:
    def save(self) -> str:
        return "final-class"

    def call(self) -> str:
        return self.save()


class FinalMethod:
    @final
    def save(self) -> str:
        return "final-method"

    def call(self) -> str:
        return self.save()


class Audit:
    def save(self) -> str:
        return "audit"


class Other:
    """Unrelated union arm for the unsupported-union receiver case."""


class MissingCaller:
    def call(self) -> object:
        return self.missing()


class ClassReceiver:
    @staticmethod
    def static_build() -> str:
        return "static-built"

    def build(self) -> str:
        return "built"

    @classmethod
    def call(cls) -> str:
        return cls.build()


def make_base() -> Base:
    """Factory used to force a visible call-result gap at its caller."""
    return Base()


def decorator_factory(tag: str):
    """Wrapper-returning decorator factory used by a decorated callable."""

    def decorator(function):
        def wrapped(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapped

    return decorator


@decorator_factory("protocol")
def wrapped_target() -> str:
    return "wrapped"
