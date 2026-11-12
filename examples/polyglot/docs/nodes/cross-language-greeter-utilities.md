# Cross-Language Greeter Utilities

**Capability.** Collects Java, Kotlin, and Ruby examples of Greeter, constant Util helpers, and top computations with file-level result assignment.

Use this module to compare parallel Greeter, Util, and top examples across Java, Kotlin, and Ruby. It contains constructor/name storage, greeting strings, constant helper returns, and top computations; Ruby also assigns top(1) to result.

Parent: [Cross-Language Object Utilities](cross-language-object-utilities.md)

## Units (9)

<a id="u-e7b61e80ba87"></a>
### `Sample.java-greeter-interface`

`interface Greeter` · [src/Sample.java:L22-L23][f1]

Greeter declares greet taking a name and returning a string.

The interface has no implementation in this file.

<a id="u-46070565c144"></a>
### `Sample.java-main-and-nested`

`class Main` · [src/Sample.java:L5-L6][f1]

Main stores a count set by its constructor and adds it to an input; Nested.run is empty.

The constructor assigns count; add returns value plus count; run has no statements. No exception path is present.

<a id="u-83d3fca19643"></a>
### `sample.kt-greeter-class`

`class Greeter(private val name: String) { fun greet(): String { return "hi " + name } }` · [src/sample.kt:L8-L9][f2]

Greeter stores a name supplied through its constructor and greet returns "hi " plus that name.

No validation or exception path is present.

<a id="u-695938b6aaa0"></a>
### `sample.kt-util-object`

`object Util { fun helper(): Int { return 1 } }` · [src/sample.kt:L14-L15][f2]

Util exposes a helper method that returns the constant 1.

<a id="u-8384eb4dd77f"></a>
### `sample.rb-greeter-class`

`class Greeter` · [src/sample.rb:L10-L11][f3]

Greeter stores @name in initialize and greet returns "hi " plus @name.

No explicit guard or exception path is present in the source.

<a id="u-049f856be847"></a>
### `sample.rb-util-module`

`module Util` · [src/sample.rb:L20-L21][f3]

Util exposes a module method helper that returns the constant 1.

<a id="u-cc97a6a80490"></a>
### `top`

`fun top(a: Int): Int { val numbers = listOf(1, 2, 3) return a + numbers.size }` · [src/sample.kt:L3-L6][f2]

top creates a list of three integers and returns its argument plus the list size, so it adds three.

<a id="u-253924c67d7f"></a>
### `src/sample.rb:top`

`def top(a, b = 1)` · [src/sample.rb:L5-L8][f3]

top defines a lambda that adds one to its argument and returns the lambda result plus b; b defaults to 1.

<a id="u-b5433bc7df9b"></a>
### `sample.rb module code (L24–L26)`

`module_region` · [src/sample.rb:L24-L26][f3]

The file-level statement evaluates top(1) and assigns the result to result.

Since top adds one through its lambda and then adds the default b of 1, the assigned value is 3.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: ../../source/src/Sample.java
[f2]: ../../source/src/sample.kt
[f3]: ../../source/src/sample.rb
