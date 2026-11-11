from contextlib import nullcontext
from .helper import helper

def decorate(fn):
    return fn

@decorate
class Example:
    def method(self):
        return helper(1)

def run(items):
    with nullcontext() as value:
        for item in items:
            value = item
    return Example().method()
