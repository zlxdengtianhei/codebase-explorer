# Java Counter Main Class

**Capability.** Provides a Java Main class holding a constructor-set count with add operations and a nested empty-run class.

Readers of the Java sample will find a class capturing a count at construction, a method adding that count to a value, and a static nested class with an empty run method. It is a minimal illustration of instance state and nesting.

Parent: [Polyglot Language Samples Repository](polyglot-language-samples-repository.md)

## Units (3)

<a id="u-e13ef76009f5"></a>
### `Sample.java-main-class-with-count-field`

`class Main` · [src/Sample.java:L5-L6][f1]

Main holds a private int count set by its constructor and exposes add to add that stored count to a value.

The constructor takes count as its only parameter; no validation or clamping occurs.

<a id="u-c4caf0e8afff"></a>
### `Sample.java-nested-class`

`class Nested` · [src/Sample.java:L16-L17][f1]

A static nested class Nested inside Main with a package-private run method whose body is empty, so calling run returns normally with no effect.

<a id="u-677df74ceec7"></a>
### `Main.add`

`public int add(int value)` · [src/Sample.java:L12-L14][f1]

Returns the given value plus the instance's count field captured at construction.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../source/src/Sample.java
