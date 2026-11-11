# PHP and Swift Greeting Samples

**Capability.** Demonstrates the same greeting class and incrementing top function in PHP and Swift for cross-language comparison.

Readers comparing parallel implementations of a simple class and a plus-one function across PHP and Swift should come here. Both files mirror each other: a name-storing class with a greet method and a top function using a local closure/arrow function.

Parent: [Scripting Language Greeting Demos](scripting-language-greeting-demos.md)

## Units (5)

<a id="u-88e0baafda6d"></a>
### `sample.php-greeter-class`

`class Greeter` · [src/sample.php:L11-L15][f1]

PHP class storing a private string name set by its constructor; greet returns "hi " concatenated with the stored name using the string concatenation operator.

<a id="u-4a40275063d8"></a>
### `sample.swift-greeter-class`

`class Greeter` · [src/sample.swift:L13-L16][f2]

Swift class with an immutable name: String set by its designated init(name:); greet returns "hi " concatenated with the stored name.

<a id="u-c0815b079aab"></a>
### `src/sample.php:top`

`function top(int $a): int` · [src/sample.php:L5-L9][f1]

Defines a local arrow function $inner that returns its argument plus one, then returns $inner($a), so top(a) yields a + 1.

<a id="u-3848539b8815"></a>
### `sample.php module code (L29–L31)`

`module_region` · [src/sample.php:L29-L31][f1]

File-level statement assigning $result = top(1), which evaluates to 2 given top's definition; it runs on every include of the file.

<a id="u-33954026b773"></a>
### `src/sample.swift:top`

`func top(_ a: Int) -> Int` · [src/sample.swift:L8-L11][f2]

Defines a closure inner returning its argument plus one and returns inner(a), so top(a) yields a + 1.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/sample.php
[f2]: ../../source/src/sample.swift
