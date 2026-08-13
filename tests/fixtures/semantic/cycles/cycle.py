def a(value: int) -> int:
    return b(value) + 1


def b(value: int) -> int:
    return c(value) + 1


def c(value: int) -> int:
    if value <= 0:
        return 0
    return a(value - 1)


def self_recursive(value: int) -> int:
    if value <= 0:
        return 0
    return self_recursive(value - 1) + 1
