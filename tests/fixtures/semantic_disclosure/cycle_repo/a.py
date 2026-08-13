def duplicate(value: int) -> int:
    return value + 1


def cold_path(value: int) -> int:
    return value - 1


def hot_leaf(value: int) -> int:
    return duplicate(value)


def hot_caller(value: int) -> int:
    return hot_leaf(value)


def cycle_a(value: int) -> int:
    return cycle_b(value)


def cycle_b(value: int) -> int:
    return cycle_a(value)


class Outer:
    def method(self, value: int) -> int:
        return hot_caller(value)

    def nested_parent(self, value: int) -> int:
        def inner() -> int:
            return duplicate(value)

        return inner()
