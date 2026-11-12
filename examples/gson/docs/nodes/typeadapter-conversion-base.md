# TypeAdapter conversion base

**Capability.** Defines abstract TypeAdapter conversion and convenience methods for writers, readers, strings, and trees.

Come here for the base adapter contract and convenience serialization/deserialization entry points. Units show writer/reader delegation and tree conversion.

Parent: [Built-in Java type adapters](built-in-java-type-adapters.md)

## Units (8)

<a id="u-a946cc996262"></a>
### `TypeAdapter.java-typeadapter`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L131-L143][f1]

Creates a default JsonWriter over the supplied Writer and delegates to write.

It does not configure, flush, or close the writer; IOException from write propagates.

<a id="u-ec0c9b1d8091"></a>
### `TypeAdapter.java-typeadapter-2`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L146-L160][f1]

Serializes into a StringBuilder through Streams.writerForAppendable and the Writer-based toJson.

Any IOException is caught and rethrown as JsonIOException; returns the accumulated JSON string.

<a id="u-f458b7367825"></a>
### `TypeAdapter.java-typeadapter-3`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L168-L179][f1]

Writes into a JsonTreeWriter and returns the resulting JsonElement from get().

Any IOException is caught and rethrown as JsonIOException.

<a id="u-b8dd2277e078"></a>
### `TypeAdapter.java-typeadapter-4`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L195-L211][f1]

Creates a default JsonReader over the Reader and delegates to read.

IOException propagates. It does not reject multiple top-level JSON elements or trailing data.

<a id="u-6cf2b803ab0b"></a>
### `TypeAdapter.java-typeadapter-5`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L214-L230][f1]

Wraps the string in a StringReader and delegates to fromJson(Reader).

IOException propagates; no trailing-data check is added.

<a id="u-948131312dbb"></a>
### `TypeAdapter.java-typeadapter-6`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L232-L242][f1]

Creates a JsonTreeReader over the supplied tree and delegates to read.

Any IOException is caught and rethrown as JsonIOException.

<a id="u-64c22665bf4d"></a>
### `TypeAdapter.java-typeadapter-contract`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L122-L124][f1]

TypeAdapter is the abstract base for converting one Java object to and from one JSON value.

The no-argument constructor does nothing. Subclasses implement write and read; write may receive null, read may return null, and both may throw IOException. The base class does not enforce null handling or single-value consumption.

<a id="u-f97e814a0641"></a>
### `TypeAdapters.java-typeadapters-container`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L63-L64][f2]

Container for static adapters and factories for basic Java types.

Its private constructor throws UnsupportedOperationException to prevent instantiation.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
