"""A successfully parsed Python source unit with zero AST calls."""


CONSTANT = "zero-call"


class ZeroCall:
    label = CONSTANT

    def describe(self) -> str:
        return self.label

