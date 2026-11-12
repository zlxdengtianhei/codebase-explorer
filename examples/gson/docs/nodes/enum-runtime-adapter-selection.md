# Enum runtime adapter selection

**Capability.** Implements enum adapters and runtime type adapter selection for serialization.

Use for enum conversion and runtime-type adapter wrapping. Units show enum lookup maps, enum read/write, and runtime adapter selection.

**Depends on.**

- [Generic type reflection](generic-type-reflection.md) · graph-confirmed · 1 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 1 edge(s)

Parent: [Type resolution and enums](type-resolution-and-enums.md)

## Units (9)

<a id="u-9dcfe1b22534"></a>
### `EnumTypeAdapter.java-enumtypeadapter-class`

`class EnumTypeAdapter<T extends Enum<T>> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L35-L38][f1]

EnumTypeAdapter is a TypeAdapter for enum classes, excluding the base Enum class, that maps JSON names and enum toString values to constants and maps constants back to serialized names.

The factory and construction details are separate.

<a id="u-4de6e1f09f48"></a>
### `EnumTypeAdapter.java-enumtypeadapter-construction-and-capacity`

`private static int calculateHashMapCapacity(int numMappings)` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L56-L58][f1]

Builds the enum adapter's lookup maps by reflecting over declared fields and retaining only enum constants.

It trims the field array, sizes three HashMaps from the constant count, makes the fields accessible, and for each constant records its name, toString value, and serialized name. If a SerializedName annotation is present, its value replaces the name and each alternate is also added to the name map. An IllegalAccessException is converted to AssertionError. The capacity helper returns ceil(numMappings / 0.75F).

<a id="u-67954c98dcdb"></a>
### `TypeAdapterRuntimeTypeWrapper.java-runtime-type-wrapper`

`class TypeAdapterRuntimeTypeWrapper<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L28-L29][f2]

TypeAdapterRuntimeTypeWrapper holds a Gson context, a delegate adapter, and the declared type; read simply delegates.

write chooses between the delegate and a runtime-type adapter.

<a id="u-37911ed505c0"></a>
### `EnumTypeAdapter.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L38-L50][f1]

The enum factory returns null unless the raw type is assignable to Enum and is not Enum itself.

If the raw type is not an enum, it uses its superclass to handle anonymous subclasses, then constructs an EnumTypeAdapter for that class.

<a id="u-68637a954b9c"></a>
### `EnumTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L113-L123][f1]

Reads an enum constant from a JSON string, returning null for JSON null.

It first looks up the string in the serialized-name map, then falls back to the toString map, and returns null if neither contains the key.

<a id="u-1e88a24ca68f"></a>
### `EnumTypeAdapter.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L125-L128][f1]

Writes an enum constant as its serialized name, or writes JSON null when the value is null.

If the constant is absent from the reverse map, the lookup yields null and the writer receives null.

<a id="u-e0483a1bc713"></a>
### `TypeAdapterRuntimeTypeWrapper.getRuntimeTypeIfMoreSpecific`

`private static Type getRuntimeTypeIfMoreSpecific(Type type, Object value)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L103-L121][f2]

Returns the declared type for a null value.

For a wildcard, uses its first upper bound for the decision. If the resulting declared type is a Class or TypeVariable, returns the value's runtime class; otherwise returns the original declared type, so parameterized types keep their type arguments.

<a id="u-132af90a9a5c"></a>
### `TypeAdapterRuntimeTypeWrapper.isReflective`

`private static boolean isReflective(TypeAdapter<?> typeAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L85-L100][f2]

Unwraps a chain of SerializationDelegatingTypeAdapter delegates until there is no delegate or the delegate is the same object, then reports whether the final adapter is a ReflectiveTypeAdapterFactory.Adapter.

<a id="u-283e3401a504"></a>
### `TypeAdapterRuntimeTypeWrapper.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L44-L78][f2]

Chooses the adapter for serialization.

It starts with the delegate and computes a more-specific runtime type. If the runtime type differs, it gets the runtime adapter: a runtime adapter that is not a direct ReflectiveTypeAdapterFactory.Adapter is chosen; otherwise, if the delegate is not reflective, the delegate is chosen; otherwise the runtime adapter is chosen. The direct instanceof check does not unwrap delegating wrappers, so a delegating wrapper around a reflective adapter is treated as non-reflective. If the runtime type is not more specific, the delegate is used.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java
