# Python Greeting and Math Helpers

**Capability.** Provides a Python greeting class, a pi-based top function, an identity decorator, and an import-time result assignment.

Readers of the Python sample will find a class with a shared greeting attribute, a top function adding π plus an optional offset, and a no-op identity decorator. A module-level statement computes a result at import time.

Parent: [Scripting Language Greeting Demos](scripting-language-greeting-demos.md)

## Units (4)

<a id="u-f87d430c7f6f"></a>
### `sample.py-greeter-class`

`class Greeter:` · [src/sample.py:L15-L20][f1]

Python class with class attribute greeting = "hi" and a docstring; greet(name) returns an f-string "{self.greeting}, {name}", so instances share the greeting unless it is overridden on the instance or subclass.

<a id="u-e15f83a913dc"></a>
### `sample.py-top-with-inner-closure`

`def top(a, b=1):` · [src/sample.py:L8-L10][f1]

top takes a and an optional b defaulting to 1, defines inner(x) returning x + math.pi, and returns inner(a) + b, i.e., a + π + b.

It is decorated with the identity decorate, which does not change it.

<a id="u-b716c1de2d31"></a>
### `decorate`

`def decorate(fn):` · [src/sample.py:L4-L5][f1]

Identity decorator: takes a function and returns the same function object unchanged, so decorating with it has no effect.

<a id="u-0f2c7163203c"></a>
### `sample.py module code (L21–L24)`

`module_region` · [src/sample.py:L21-L24][f1]

Module-level statement assigning result = top(1), which evaluates to 1 + π + 1; it executes at import time.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.py
