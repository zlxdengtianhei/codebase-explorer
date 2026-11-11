# Reflective type adapter factory

**Capability.** Builds TypeAdapters by reflecting over class fields, applying naming strategies, exclusion rules, and access filters to bind JSON members.

This module is the core of reflective (de)serialization: it collects BoundFields across the class hierarchy, resolves JSON names via FieldNamingStrategy and @SerializedName, and produces adapters for ordinary classes. It also enforces duplicate-name and accessibility rules.

**Depends on.**

- [Reflection and record support](reflection-and-record-support.md) · graph-confirmed · 13 edge(s) · The reflective factory uses reflection utilities and record introspection to bind fields.
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 6 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 3 edge(s)
- [Reflection access filtering](reflection-access-filtering.md) · graph-only · 3 edge(s)
- [Generic Type Reflection](generic-type-reflection.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Reflection and record support](reflection-and-record-support.md) · graph-confirmed · 2 edge(s)

Parent: [Field Binding and Introspection](field-binding-and-introspection.md)

## Units (14)

<a id="u-a4791acef45d"></a>
### `FieldNamingStrategy.java-field-naming-strategy`

`String translateName(Field f);` · [gson/src/main/java/com/google/gson/FieldNamingStrategy.java:L43-L43][f1]

Interface for translating Java field names to JSON member names, with a default hook for deserialization-time alternate names.

translateName is abstract; implementors map a reflective Field to its serialized name. alternateNames has a default implementation returning an immutable empty list, so strategies only override it when they support alternate names, mirroring SerializedName.alternate().

<a id="u-936665cbc535"></a>
### `ReflectiveTypeAdapterFactory.java-adapter-base-class`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L481-L498][f2]

Common TypeAdapter base for this factory's adapters, parameterized by result type T and accumulator type A (the class is public because external code instanceof-checks it).

write emits null for null, otherwise an object writing each serializedFields BoundField, converting IllegalAccessException via ReflectionHelper.createExceptionForUnexpectedIllegalAccess. read returns null on JSON null; otherwise it creates an accumulator, iterates object members skipping names absent from deserializedFields, and delegates each match to the abstract readField; IllegalStateException from malformed JSON structure is wrapped as JsonSyntaxException, IllegalAccessException as the unexpected-illegal-access exception. Finally the abstract finalize converts the accumulator into the T instance. Subclasses supply createAccumulator, readField and finalize.

<a id="u-8c3d12c4e5ca"></a>
### `ReflectiveTypeAdapterFactory.java-anonymous-local-class-null-adapter`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L109-L124][f2]

create returns null for primitives (raw not assignable to Object).

For anonymous or non-static local classes it returns a compatibility adapter that skips any JSON on read returning null and writes JSON null on write, deliberately ignoring values rather than failing; toString identifies it as AnonymousOrNonStaticLocalClassAdapter.

<a id="u-505aacc01b4c"></a>
### `ReflectiveTypeAdapterFactory.java-boundfield`

`class BoundField` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L452-L454][f2]

Abstract per-field binding holding the serialization name, the reflected Field, and the field's Java name.

Subclasses implement write (serialize the field's value), readIntoArray (fill a record-constructor argument slot) and readIntoField (set the field on an existing instance).

<a id="u-0ad7dc5b6faf"></a>
### `ReflectiveTypeAdapterFactory.java-createboundfield-and-its-boundfield-implementation`

`private BoundField createBoundField( Gson context, Field field, Method accessor, Stri…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L181-L236][f2]

Creates the per-field BoundField.

It resolves the field's TypeAdapter: a @JsonAdapter annotation on the field takes precedence via jsonAdapterFactory.getTypeAdapter (unsafe cast, user must match types), otherwise context.getAdapter(fieldType). For serialization it wraps the adapter in TypeAdapterRuntimeTypeWrapper unless a @JsonAdapter was present, so runtime subtypes serialize with their own adapter; when not serializing the write adapter is the plain one (never used). The returned anonymous BoundField: write() first performs the accessibility check once (cached in a non-volatile knownAccessible flag; benign race since the check is idempotent — negative results are never cached), then obtains the value via the record accessor (wrapping InvocationTargetException as JsonIOException naming the accessor) or field.get, silently skips self-referential fields (fieldValue == source) to avoid infinite recursion, and otherwise writes name + value. readIntoArray() reads via the type adapter and throws JsonParseException on null for primitive record components before storing into the constructor-args slot. readIntoField() reads the value; null for a primitive is ignored (field keeps default), otherwise it re-checks accessibility when blocked, or throws JsonIOException for static final fields (reflection cannot set them), then field.set — IllegalAccessException propagates to the caller.

<a id="u-63b3fb4a08f5"></a>
### `ReflectiveTypeAdapterFactory.java-fieldreflectionadapter`

`class FieldReflectionAdapter<T> extends Adapter<T, T>` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L567-L568][f2]

Adapter for ordinary classes: the accumulator is a fresh instance from the stored ObjectConstructor (created up front, so construction failures surface at read time), readField sets values directly onto that instance via BoundField.readIntoField, and finalize returns the accumulator itself.

<a id="u-b87a045ce544"></a>
### `ReflectiveTypeAdapterFactory.java-fieldsdata`

`class FieldsData` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L312-L313][f2]

Immutable value object pairing a LinkedHashMap of JSON member name → BoundField used during deserialization with the ordered list of BoundFields used for serialization; EMPTY is the shared instance for interfaces.

<a id="u-2f2a3615a795"></a>
### `ReflectiveTypeAdapterFactory.java-reflectivetypeadapterfactory`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L60-L61][f2]

TypeAdapterFactory that reflects over a class's fields and methods; the constructor stores the ConstructorConstructor, FieldNamingStrategy, Excluder, JsonAdapterAnnotationTypeAdapterFactory and ReflectionAccessFilter list used by all later adapter construction.

<a id="u-9616a5e5f747"></a>
### `ReflectiveTypeAdapterFactory.checkAccessible`

`private static <M extends AccessibleObject & Member> void checkAccessible( Object obj…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L168-L179][f2]

Static guard that throws JsonIOException, with the member's accessible-object description, when the member is not accessible and the filters only permit already-accessible members; the access check uses null as the instance for static members.

<a id="u-069bef61622b"></a>
### `gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:ReflectiveTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L138-L166][f2]

Main create: rejects primitives, substitutes the null adapter for anonymous/non-static local classes, then evaluates the ReflectionAccessFilters — BLOCK_ALL throws JsonIOException telling the user to register a TypeAdapter or adjust the filter; BLOCK_INACCESSIBLE sets a flag threaded into field handling.

If the raw type is a record it returns a RecordAdapter built from getBoundFields(..., isRecord=true); otherwise it obtains an ObjectConstructor from ConstructorConstructor (which may throw for missing no-arg constructors) and returns a FieldReflectionAdapter over getBoundFields(..., isRecord=false).

<a id="u-54bcdf126a95"></a>
### `ReflectiveTypeAdapterFactory.createDuplicateFieldException`

`private static IllegalArgumentException createDuplicateFieldException( Class<?> decla…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L326-L339][f2]

Builds and throws IllegalArgumentException for two fields mapping to the same JSON name, naming the declaring class, the duplicate name, both fields (via ReflectionHelper.fieldToString) and a troubleshooting-guide URL.

Note it always throws despite returning a value.

<a id="u-3c962fb8d736"></a>
### `ReflectiveTypeAdapterFactory.getBoundFields`

`private FieldsData getBoundFields( Gson context, TypeToken<?> type, Class<?> raw, boo…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L341-L450][f2]

Collects BoundFields by walking the class hierarchy from raw up to (excluding) Object.

Interfaces yield FieldsData.EMPTY. For each superclass level it first re-evaluates the reflection filters when the level is an inherited class with fields: BLOCK_ALL throws JsonIOException naming the supertype; BLOCK_INACCESSIBLE updates the flag for that level's fields. Per field: fields excluded in both directions are skipped; for records a non-static field gets its accessor method (made accessible unless blocked) and a @SerializedName on the accessor without one on the field throws JsonIOException; static record fields are excluded from deserialization; non-record fields are made accessible unless blocked. Generic field types are resolved against the enclosing TypeToken. Each field's names come from getFieldNames; deserialization registers every name (primary + alternates) and throws the duplicate-field exception on collision; serialization registers only the primary name, likewise failing on collision. The loop advances by resolving the generic superclass and continues with its raw type.

<a id="u-d7cfdfc44369"></a>
### `ReflectiveTypeAdapterFactory.getFieldNames`

`@SuppressWarnings("MixedMutabilityReturnType") private List<String> getFieldNames(Fie…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L85-L107][f2]

Computes a field's JSON names: with @SerializedName, the annotation value plus its alternates; otherwise the FieldNamingStrategy's translated name plus its alternateNames.

The first element is the primary serialization name; with no alternates a single-element list is returned.

<a id="u-bc24316c33e8"></a>
### `ReflectiveTypeAdapterFactory.includeField`

`private boolean includeField(Field f, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L80-L82][f2]

Returns whether a field participates in the given direction: true unless the configured Excluder excludes it for that serialize/deserialize mode.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldNamingStrategy.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java
