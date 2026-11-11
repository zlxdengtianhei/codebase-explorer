# Internal Reflection Utilities

**Capability.** Exposes internal JsonReader access to other Gson classes and provides primitive/wrapper type utilities.

A small internal-support module: the bridge that lets other classes promote a reader's name to a value, and the Primitives helper for wrapper-type checks and wrap/unwrap conversions.

**Depended on by.**

- [Map Serialization](map-serialization.md) · graph-confirmed · 1 edge(s)

Parent: [Primitives and Map Adapters](primitives-and-map-adapters.md)

## Units (3)

<a id="u-249349fe42e0"></a>
### `JsonReaderInternalAccess.java-jsonreaderinternalaccess`

`class JsonReaderInternalAccess` · [gson/src/main/java/com/google/gson/internal/JsonReaderInternalAccess.java:L23-L26][f1]

Abstract internal bridge exposing JsonReader internals to other Gson classes: a volatile static INSTANCE initialized by JsonReader during class loading, and an abstract promoteNameToValue(JsonReader) that retypes the current property-name token as a string value.

Used by MapTypeAdapterFactory to read a key as a value.

<a id="u-0bb4b374b198"></a>
### `Primitives.java-primitives`

`class Primitives` · [gson/src/main/java/com/google/gson/internal/Primitives.java:L27-L28][f2]

Static utility for primitive/wrapper types.

isPrimitive checks Class.isPrimitive; isWrapperType matches the nine wrapper classes by reference; wrap maps each primitive class to its wrapper and returns any other type unchanged (idempotent); unwrap is the exact inverse, mapping wrappers to primitives and passing others through.

<a id="u-286507388910"></a>
### `Primitives.java-primitives-javadoc-regions`

`class Primitives` · [gson/src/main/java/com/google/gson/internal/Primitives.java:L33-L41][f2]

These symbols are javadoc-only regions of Primitives preceding the wrapper-type checks and the wrap/unwrap conversions; they contain no executable code.

Their comment text documents the contracts (nine wrapper types, idempotence of wrap and unwrap) that the following methods implement.

**Uncertainties.**

- The symbol list labels these as 'class Primitives' regions, but the supplied source at those lines contains only comments; no separate class body is visible there.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/JsonReaderInternalAccess.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Primitives.java
