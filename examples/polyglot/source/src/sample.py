import math


def decorate(fn):
    return fn


@decorate
def top(a, b=1):
    def inner(x):
        return x + math.pi
    return inner(a) + b


class Greeter:
    """A greeter."""

    greeting = "hi"

    def greet(self, name):
        return f"{self.greeting}, {name}"


result = top(1)
