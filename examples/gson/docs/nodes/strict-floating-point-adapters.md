# Strict floating-point adapters

**Capability.** Implements Double and Float adapters with strict validation rejecting NaN and infinite JSON values.

Use for floating-point adapter behavior and special-value validation. Units show strict flags and IllegalArgumentException for non-finite doubles.

Parent: [Built-in Java type adapters](built-in-java-type-adapters.md)

## Units (3)

<a id="u-c5817acfdfed"></a>
### `TypeAdapters.java-doubleadapter`

`class DoubleAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L490-L491][f1]

Double adapter with a strict flag.

Reading null returns null, otherwise nextDouble. Writing null emits null; it computes doubleValue, optionally validates it when strict, then writes doubleValue.

<a id="u-b2f4746d9026"></a>
### `TypeAdapters.java-floatadapter`

`class FloatAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L457-L458][f1]

Float adapter with a strict flag.

Reading null returns null, otherwise casts nextDouble to float. Writing null emits null; it computes floatValue, optionally validates it when strict, then writes the original value if it is a Float or the floatValue otherwise.

<a id="u-6753c300a7c7"></a>
### `TypeAdapters.checkValidFloatingPoint`

`private static void checkValidFloatingPoint(double value)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L520-L527][f1]

Validates a double for JSON serialization: NaN or infinite values throw IllegalArgumentException with a message pointing to the special-floating-point builder option.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
