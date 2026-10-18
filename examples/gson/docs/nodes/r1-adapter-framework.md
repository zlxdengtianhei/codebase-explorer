# TypeAdapter Framework

**Capability.** Defines the abstract TypeAdapter contract (read/write, nullSafe wrapping, toJson/toJsonTree conveniences), the serialization-delegation marker and runtime-type wrapper used by the factory chain, and factory plumbing shared by custom adapters.

Use this subtree to understand how adapters compose and delegate and how the runtime-type wrapper picks the serialization adapter; the tree-style bridge is its child.

**Children.**

- [Tree-Style Serializer Bridge](r1-tree-adapter-bridge.md) `r1-tree-adapter-bridge` · 13 unit(s)

**Depends on.**

- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 5 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 1 edge(s)
- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 1 edge(s)
- [Tree-Bound Writer](r2-tree-writer.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Built-in Type Adapters](r1-builtin-adapters.md) · graph-confirmed · 4 edge(s) · Built-in adapters compose through TypeAdapter.nullSafe and the runtime-type wrapper of the framework.
- [Gson Facade and Conversion API](r1-facade-api.md) · model-inferred · 0 edge(s) · The facade performs adapter lookup, caching, and delegate resolution through the TypeAdapter framework when running conversions.
- [java.time Adapters](r1-java-time-adapters.md) · graph-confirmed · 4 edge(s)
- [Primitive and Utility Type Adapters](r2-primitive-adapters.md) · graph-only · 2 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (13)

<a id="u-98025607c27a"></a>
### `TypeAdapter`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L122-L124][f1]

Abstract base class converting Java objects of type T to and from JSON; subclasses implement write(JsonWriter, T) and read(JsonReader), which must each handle exactly one JSON value (and must tolerate nulls unless wrapped with nullSafe).

The public no-arg constructor is empty. Convenience methods wrap the abstract pair: toJson(Writer, T) creates a default-configured JsonWriter and delegates to write; fromJson(Reader) creates a default JsonReader (LEGACY_STRICT strictness, trailing data and extra top-level values tolerated) and delegates to read; fromJson(String) delegates to fromJson(Reader) via a StringReader; fromJsonTree(JsonElement) reads through a JsonTreeReader and converts any IOException into JsonIOException. Adapters should be stateless and thread-safe for Gson's thread-safety guarantees to hold.

**Notes.**

- contract: write must emit exactly one value and read must consume exactly one; converting too few or too many values can break the stream.
- failure: fromJsonTree and the String-based toJson convert IOException from the delegate into unchecked JsonIOException; fromJson(Reader) and toJson(Writer) propagate IOException.

**Uncertainties.**

- JsonTreeReader behavior for malformed trees is defined in the internal bind package, not here.

<a id="u-c7dd40fc556f"></a>
### `TypeAdapter.nullSafe`

`public final TypeAdapter<T> nullSafe()` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L292-L297][f1]

Wraps this adapter so nulls are handled without boilerplate.

If this is already a NullSafeTypeAdapter it is returned unchanged; otherwise a new inner NullSafeTypeAdapter is created. The wrapper's write emits out.nullValue() for a null value and otherwise delegates to the outer adapter's write; its read peeks, consumes nextNull() and returns null on a JSON null, and otherwise delegates to the outer adapter's read; toString reads NullSafeTypeAdapter[outer]. Because NullSafeTypeAdapter is an inner (non-static) class, delegation reaches the specific outer instance nullSafe was called on.

<a id="u-032efc7fe817"></a>
### `typeadapter-nullsafetypeadapter`

`class NullSafeTypeAdapter extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L299-L300][f1]

Private inner class produced by nullSafe that adds null tolerance around the enclosing TypeAdapter instance.

Its write(JsonWriter, T) writes a JSON null when the value is null and otherwise calls the outer adapter's write; its read(JsonReader) checks reader.peek() for JsonToken.NULL, consumes the null token and returns null, otherwise calls the outer adapter's read; its toString renders "NullSafeTypeAdapter[" + outer adapter + "]". IOExceptions from the delegates propagate unchanged.

<a id="u-9d560dd0ec9a"></a>
### `gson/src/main/java/com/google/gson/TypeAdapter.java:TypeAdapter.toJson`

`public final String toJson(T value)` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L160-L168][f1]

Serializes the value to a String.

It writes through an Appendable writer obtained from Streams.writerForAppendable wrapping a StringBuilder, reusing toJson(Writer, T); any IOException thrown by write is caught and rethrown as an unchecked JsonIOException wrapping the original. Returns the accumulated document; the value may be null per the write contract.

calls: [TypeAdapter](r1-adapter-framework.md#u-98025607c27a), [Streams](r2-infrastructure.md#u-931987e48ef4)

<a id="u-1c904480f4f6"></a>
### `TypeAdapter.toJsonTree`

`public final JsonElement toJsonTree(T value)` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L179-L187][f1]

Serializes the value into an in-memory JsonElement tree.

It writes through a fresh JsonTreeWriter, calls write, and returns jsonWriter.get(), which may be JsonNull for a null value; IOException from write is caught and rethrown as JsonIOException.

calls: [JsonTreeWriter.get](r2-tree-writer.md#u-58a4de8f7ae3)

<a id="u-2009145cec79"></a>
### `serializationdelegatingtypeadapter.java-class`

`class SerializationDelegatingTypeAdapter<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java:L22-L27][f2]

SerializationDelegatingTypeAdapter is an abstract TypeAdapter<T> subclass marking adapters that may delegate serialization to another adapter.

It declares the abstract getSerializationDelegate() as its only member; subclasses must return the adapter used for writing, which may itself be another delegating adapter. The class adds no state or default behavior.

**Uncertainties.**

- Concrete delegation semantics depend on subclasses outside this batch.

<a id="u-ca408b4a1f52"></a>
### `SerializationDelegatingTypeAdapter.getSerializationDelegate`

`public abstract TypeAdapter<T> getSerializationDelegate();` · [gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java:L27-L27][f2]

Abstract method each subclass must implement, returning the TypeAdapter actually used for serialization — possibly this adapter itself, and possibly another SerializationDelegatingTypeAdapter, so delegation can form a chain resolved only at runtime.

**Uncertainties.**

- No concrete subclass is present in this file, so how the delegate is chosen cannot be established here.

<a id="u-868542f9339b"></a>
### `typeAdapterRuntimeTypeWrapper-constructor`

`class TypeAdapterRuntimeTypeWrapper<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L28-L33][f3]

Final internal TypeAdapter that holds a Gson context, a delegate adapter, and the declared Type, all assigned in the constructor.

Its read is a pure delegation: it simply returns delegate.read(in) with no runtime-type resolution, so only serialization is affected by this wrapper.

<a id="u-283e3401a504"></a>
### `TypeAdapterRuntimeTypeWrapper.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L44-L78][f3]

Chooses the serialization adapter by runtime type with the documented preference order: first an adapter registered for the runtime type, then the declared-type delegate, then a reflective adapter for the runtime type if the delegate is not itself reflective, otherwise the delegate.

It computes the runtime type via getRuntimeTypeIfMoreSpecific; if that differs from the declared type (reference comparison), it fetches context.getAdapter(TypeToken.get(runtimeType)). If that adapter is not a ReflectiveTypeAdapterFactory.Adapter, it is chosen (a user registered an adapter for the runtime type); if it is reflective but the delegate is not reflective, the delegate wins (declared-type user adapter preferred over runtime reflection); otherwise the runtime-type adapter is used. The chosen adapter then writes the value. The instanceof check intentionally examines only the bare ReflectiveTypeAdapterFactory.Adapter, not other wrapping adapters, for backward compatibility.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613), [TypeAdapterRuntimeTypeWrapper.isReflective](r1-adapter-framework.md#u-132af90a9a5c)

**Uncertainties.**

- Reference equality (runtimeType != type) is deliberate; two equal but distinct Type instances would be treated as 'not more specific' — this is annotated but its broader implications depend on Gson's type caching, not visible here.

<a id="u-132af90a9a5c"></a>
### `TypeAdapterRuntimeTypeWrapper.isReflective`

`private static boolean isReflective(TypeAdapter<?> typeAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L85-L100][f3]

Reports whether an adapter ultimately serializes via reflection.

It unwraps chains of SerializationDelegatingTypeAdapter in a loop, following getSerializationDelegate each step; a delegate identical to the current adapter (self-reference) breaks the loop to avoid infinite iteration. The final unwrapped adapter is reflective exactly when it is a ReflectiveTypeAdapterFactory.Adapter.

**Uncertainties.**

- Behavior when a delegation chain is cyclic without a self-referential link is unguarded in the source; only the direct self-delegate case is handled.

<a id="u-e0483a1bc713"></a>
### `TypeAdapterRuntimeTypeWrapper.getRuntimeTypeIfMoreSpecific`

`private static Type getRuntimeTypeIfMoreSpecific(Type type, Object value)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L103-L121][f3]

Static helper deciding whether a more specific runtime type can be used.

A null value returns the declared type unchanged. Wildcard declared types are replaced by their first upper bound, since a wildcard conveys nothing more specific than its bound; when that bound is a parameterized type the declared type is kept anyway (the runtime class would lose type arguments). If the resulting declared type is a Class or TypeVariable, the value's actual class is returned; for other Type kinds (e.g. parameterized or generic array types) the original type is returned unchanged.

**Uncertainties.**

- Returning value.getClass() for a TypeVariable discards the variable's name; the caller must handle generic adapters for such runtime types, which is outside this file.

<a id="u-72fcd7199bd5"></a>
### `TypeAdapterRuntimeTypeWrapper.java module code (L1–L27)`

`module_region` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L1-L27][f3]

License header and imports only.

<a id="u-f0100da72154"></a>
### `jsonadapterannotationtypeadapterfactory-java-residual`

`module_region`

License header, package declaration, and imports for the JsonAdapterAnnotationTypeAdapterFactory file; non-behavioral material.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java