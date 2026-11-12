# PHP Swift Shape Examples

**Capability.** Groups PHP and Swift Greeter, Shape, top-closure, and Swift Point examples that demonstrate parallel class, interface, and closure syntax.

Come here for paired PHP/Swift examples of greeting classes, area declarations, and top closures. PHP includes file-level result assignment; Swift adds a Point struct.

Parent: [Cross-Language Object Utilities](cross-language-object-utilities.md)

## Units (8)

<a id="u-88e0baafda6d"></a>
### `sample.php-greeter-class`

`class Greeter` · [src/sample.php:L11-L15][f1]

Greeter stores a name set by its constructor and greet returns "hi " concatenated with that name.

The constructor assigns the argument; greet has no other logic.

<a id="u-4a89fcec4cf6"></a>
### `sample.php-shape-interface`

`interface Shape` · [src/sample.php:L26-L28][f1]

Shape declares an area method returning float.

The interface has no implementation in this file.

<a id="u-4a40275063d8"></a>
### `sample.swift-greeter-class`

`class Greeter` · [src/sample.swift:L13-L16][f2]

Greeter stores a name set by init and greet returns "hi " plus that name.

The init assigns the argument to the let property; greet has no other logic.

<a id="u-7dc29ea08c46"></a>
### `sample.swift-shape-protocol`

`protocol Shape` · [src/sample.swift:L25-L26][f2]

Shape declares an area method returning Double.

The protocol has no implementation in this file.

<a id="u-c0815b079aab"></a>
### `src/sample.php:top`

`function top(int $a): int` · [src/sample.php:L5-L9][f1]

top defines a closure that adds one to its argument and returns the closure applied to the input, so it returns the input plus one.

<a id="u-3848539b8815"></a>
### `sample.php module code (L29–L31)`

`module_region` · [src/sample.php:L29-L31][f1]

The file-level statement evaluates top(1) and assigns the result to $result.

Since top returns its argument plus one, the assigned value is 2.

<a id="u-2e851c088e68"></a>
### `src/sample.swift:Point`

`struct Point` · [src/sample.swift:L3-L6][f2]

Point is a Swift struct with two Int fields, x and y.

<a id="u-33954026b773"></a>
### `src/sample.swift:top`

`func top(_ a: Int) -> Int` · [src/sample.swift:L8-L11][f2]

top defines a closure that adds one to its argument and returns the closure applied to the input.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: ../../source/src/sample.php
[f2]: ../../source/src/sample.swift
