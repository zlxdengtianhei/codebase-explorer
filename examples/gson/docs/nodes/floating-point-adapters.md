# Floating-Point Adapters

**Capability.** Provides double and float TypeAdapters with a strict flag rejecting NaN and infinities unless explicitly allowed.

A small module for JSON floating-point conversion. Its strictness check points users to GsonBuilder.serializeSpecialFloatingPointValues when non-finite values are encountered.

Parent: [Built-in Adapter Implementations](built-in-adapter-implementations.md)

## Units (3)

<a id="u-c5817acfdfed"></a>
### `TypeAdapters.java-doubleadapter`

`class DoubleAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L490-L491][f1]

TypeAdapter<Number> for doubles with a strict flag.

read returns null for a null token, otherwise nextDouble(). write: null writes null; strict mode validates via checkValidFloatingPoint before emitting the double.

<a id="u-b2f4746d9026"></a>
### `TypeAdapters.java-floatadapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L454-L457][f1]

TypeAdapter<Number> for floats with a strict flag.

read returns null for a null token, otherwise (float) nextDouble(). write: null writes null; otherwise converts to float and, when strict, validates via checkValidFloatingPoint; it deliberately passes the original Float object (or the widened value) to JsonWriter.value(Number) for backward compatibility with custom writers.

<a id="u-6753c300a7c7"></a>
### `TypeAdapters.checkValidFloatingPoint`

`private static void checkValidFloatingPoint(double value)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L520-L527][f1]

Throws IllegalArgumentException for NaN or infinite doubles, pointing to GsonBuilder.serializeSpecialFloatingPointValues() as the override; otherwise returns normally.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
