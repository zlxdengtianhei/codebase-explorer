# Python Greeter and Decorator

**Capability.** Collects Python examples of a greeting class, a top function using math.pi, an identity decorator, and file-level result assignment.

Use this module for Python-only examples of class greeting, nested top computation, and a no-op decorator. The file-level statement evaluates top(1) and stores result.

Parent: [Cross-Language Object Utilities](cross-language-object-utilities.md)

## Units (4)

<a id="u-f87d430c7f6f"></a>
### `sample.py-greeter-class`

`class Greeter:` · [src/sample.py:L15-L20][f1]

Greeter has a class attribute greeting set to "hi"; greet returns that greeting, a comma, and the supplied name.

The method uses the instance attribute greeting.

<a id="u-13ecedc20985"></a>
### `sample.py-top-and-inner`

`def top(a, b=1):` · [src/sample.py:L8-L10][f1]

top defines inner, which adds math.pi to its argument, and returns inner(a) plus b; b defaults to 1.

The decorate decorator returns top unchanged, so no wrapper is added.

<a id="u-b716c1de2d31"></a>
### `decorate`

`def decorate(fn):` · [src/sample.py:L4-L5][f1]

decorate returns the function it receives unchanged.

<a id="u-0f2c7163203c"></a>
### `sample.py module code (L21–L24)`

`module_region` · [src/sample.py:L21-L24][f1]

The file-level statement evaluates top(1) and assigns the result to result.

With the default b of 1 and inner adding math.pi, the assigned value is 2 plus math.pi.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: ../../source/src/sample.py
