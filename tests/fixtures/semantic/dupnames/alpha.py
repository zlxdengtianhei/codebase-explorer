class Alpha:
    def __init__(self, value: int) -> None:
        self.value = value

    def run(self) -> int:
        return self.value


class Beta:
    def __init__(self, value: int) -> None:
        self.value = value


def shared(value: int) -> int:
    return value + 1
