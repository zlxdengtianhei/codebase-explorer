# Kotlin Greeter and Utilities

**Capability.** Provides a Kotlin greeting class, a singleton Util object with a constant helper, and a function adding a list's size.

Readers of the Kotlin sample will find a name-storing class with greet, the Util singleton returning 1, and a function that adds the size of a three-element list to its argument.

Parent: [Scripting Language Greeting Demos](scripting-language-greeting-demos.md)

## Units (3)

<a id="u-83d3fca19643"></a>
### `sample.kt-greeter-class`

`class Greeter(private val name: String) { fun greet(): String { return "hi " + name } }` · [src/sample.kt:L8-L9][f1]

Kotlin class whose primary constructor stores a private val name; greet returns "hi " concatenated with that stored name.

<a id="u-695938b6aaa0"></a>
### `sample.kt-util-object`

`object Util { fun helper(): Int { return 1 } }` · [src/sample.kt:L14-L15][f1]

Singleton object Util whose helper method takes no arguments and returns the constant 1.

<a id="u-cc97a6a80490"></a>
### `top`

`fun top(a: Int): Int { val numbers = listOf(1, 2, 3) return a + numbers.size }` · [src/sample.kt:L3-L6][f1]

Builds a local list of the three literals 1, 2, 3 and returns its integer argument plus the list's size, i.e., a + 3.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.kt
