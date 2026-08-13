from functools import lru_cache


def decorate(function):
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)

    return wrapper


@decorate
def decorated(value: int) -> int:
    return value + 1


@lru_cache(
    maxsize=16,
)
def multiline_decorated(value: int) -> int:
    return value * 2


class Outer:
    class Inner:
        def method(self, value: int) -> int:
            def closure(delta: int) -> int:
                return value + delta

            return closure(value)
