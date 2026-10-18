# ReflectiveTypeAdapterFactory

**Capability.** Builds field-level adapters: create dispatches on record vs regular class, getBoundFields walks the hierarchy collecting non-excluded fields, createBoundField wires each field (including @JsonAdapter overrides and accessibility checks), and dedicated Adapter bases handle field-reflective classes and canonical-constructor records.

Read this subtree to understand exactly which fields are serialized, under which JSON names, and in what order. The BoundField/FieldsData structures and duplicate-name diagnostics explain error reporting and name conflicts.

**Depends on.**

- [@JsonAdapter Annotation Handling](r2-jsonadapter-annotation-factory.md) · graph-confirmed · 1 edge(s) · createBoundField resolves @JsonAdapter-annotated fields through JsonAdapterAnnotationTypeAdapterFactory.getTypeAdapter.
- [Object Construction Strategy](r2-object-construction.md) · graph-confirmed · 1 edge(s) · ReflectiveTypeAdapterFactory obtains ObjectConstructors from ConstructorConstructor to instantiate target objects.
- [Exclusion and Reflection Policy](r1-reflection-policy.md) · graph-only · 26 edge(s) · Reflective binding resolves field names, exclusion, and accessibility via the Excluder and reflection policy contracts.
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 10 edge(s)

Parent: [Reflection-Based Object Binding](r2-reflective-binding.md)

## Units (14)

<a id="u-8440716539c2"></a>
### `reflectiveTypeAdapterFactory-class-header`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L60-L67][f1]

Declares ReflectiveTypeAdapterFactory and its five collaborators injected by the constructor: ConstructorConstructor for instance creation, FieldNamingStrategy for name translation, Excluder for field filtering, JsonAdapterAnnotationTypeAdapterFactory for @JsonAdapter handling, and the list of ReflectionAccessFilter.

The folded includeField simply negates excluder.excludeField(f, serialize), so a field is included for serialization or deserialization whenever the excluder does not exclude it.

<a id="u-356c3ac5fb58"></a>
### `reflectiveTypeAdapterFactory-create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L109-L124][f1]

Implements TypeAdapterFactory.create, deciding what adapter to build for a type.

If the raw type is not assignable from Object (a primitive) it returns null. If ReflectionHelper.isAnonymousOrNonStaticLocal(raw) is true, it returns an adapter that skips values on read (returning null) and writes null on write, intentionally ignoring the actual data for backward compatibility; its toString identifies it as AnonymousOrNonStaticLocalClassAdapter. Otherwise it evaluates the reflection filters: BLOCK_ALL throws JsonIOException instructing the user to register an adapter; BLOCK_INACCESSIBLE sets blockInaccessible, deferring per-member access checks. For records it returns a RecordAdapter using the record's bound fields; for all other classes it fetches an ObjectConstructor via constructorConstructor.get(type, true) and returns a FieldReflectionAdapter.

calls: [reflectionhelper-classifier-helpers](r1-reflection-policy.md#u-54a5fb178011), [ReflectionHelper](r1-reflection-policy.md#u-580064b5eb25), [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get](r2-object-construction.md#u-2b1d12b84c2c), [ReflectiveTypeAdapterFactory.getBoundFields](r2-reflective-type-adapter-factory.md#u-3c962fb8d736)

**Uncertainties.**

- ReflectionHelper.isRecord is expected to be false on JVMs without record support; that platform behavior is asserted by comments, not proven here.

<a id="u-39b1562a58b3"></a>
### `reflectiveTypeAdapterFactory-createBoundField`

`private BoundField createBoundField( Gson context, Field field, Method accessor, Stri…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L181-L236][f1]

Creates the BoundField wiring one class field to its JSON handling.

It first resolves the field's adapter: a @JsonAdapter annotation obtains an adapter from jsonAdapterFactory.getTypeAdapter (an unsafe cast trusting user configuration); otherwise the Gson-resolved adapter for the field type is used. For serialization, the adapter is wrapped in a TypeAdapterRuntimeTypeWrapper unless a @JsonAdapter adapter is present; for deserialization the plain adapter is used (assigned only to avoid null). The returned anonymous BoundField has three operations. write: when blockInaccessible is set, it performs the accessibility check once per field and caches a positive result in knownAccessible (deliberately not volatile; the check is idempotent so a re-done check is benign, and a negative result must never be cached); then it reads the value via the record accessor if present — wrapping InvocationTargetException as JsonIOException with the accessor description and cause — or via Field.get; if the field value is the same object as the source it returns without writing to avoid infinite recursion; otherwise it writes the member name and delegates to writeTypeAdapter. readIntoArray (records): reads the value and, if it is null for a primitive component, throws JsonParseException including the reader path; otherwise stores it at the target index. readIntoField: reads the value; if the value is non-null or the type is not primitive, it performs the same once-per-field accessibility check when blockInaccessible, throws JsonIOException for a static final field (which reflection cannot set even after setAccessible), and sets the field.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613), [JsonAdapterAnnotationTypeAdapterFactory.getTypeAdapter](r2-jsonadapter-annotation-factory.md#u-b06bd194e1b8), [ReflectiveTypeAdapterFactory.checkAccessible](r2-reflective-type-adapter-factory.md#u-9616a5e5f747); uses: [typeAdapterRuntimeTypeWrapper-constructor](r1-adapter-framework.md#u-868542f9339b)

**Uncertainties.**

- The comment notes the accessor-based access check in write may be redundant because the canonical constructor check should have failed first for records; the redundancy is not proven from this file.

<a id="u-218ec11bc27c"></a>
### `reflectiveTypeAdapterFactory-boundField`

`class BoundField` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L452-L461][f1]

Abstract container for one mapped field: serializedName (used only for serialization), the reflective Field, and fieldName derived from it.

It declares the three abstract operations — write (serialize the field value into the writer), readIntoArray (store a value at a constructor-argument index, used for records), and readIntoField (read a value and set the field reflectively) — whose concrete behavior is supplied by the anonymous subclass built in createBoundField.

<a id="u-adbf6059a099"></a>
### `reflectiveTypeAdapterFactory-fieldsData`

`class FieldsData` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L312-L320][f1]

Immutable holder for a type's bound fields: deserializedFields maps each JSON member name to its BoundField, and serializedFields lists fields in serialization order.

The static EMPTY constant holds empty collections and is returned for interfaces.

<a id="u-699ed7db7e76"></a>
### `reflectiveTypeAdapterFactory-adapter`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L481-L498][f1]

Public abstract base (public because external projects check it with instanceof) shared by FieldReflectionAdapter and RecordAdapter, parameterized by target type T and accumulator type A.

write returns early writing a JSON null for a null value, otherwise writes an object by invoking each serialized BoundField; an escaping IllegalAccessException is converted via ReflectionHelper.createExceptionForUnexpectedIllegalAccess. read consumes a JSON null to null; otherwise it creates an accumulator, iterates the object's members, looks each name up in deserializedFields — skipping unknown names — and dispatches known ones to readField. An IllegalStateException during parsing is rethrown as JsonSyntaxException; IllegalAccessException is converted through the same helper. After endObject it returns finalize(accumulator). Subclasses implement createAccumulator, readField, and finalize.

**Uncertainties.**

- The class comment describes finalize as converting the accumulator to T; the contract that readField leaves the reader positioned at the value is documented, not enforced here.

<a id="u-452984850f65"></a>
### `reflectiveTypeAdapterFactory-fieldReflectionAdapter`

`class FieldReflectionAdapter<T> extends Adapter<T, T>` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L567-L570][f1]

Concrete Adapter for regular classes where the accumulator is the instance itself.

createAccumulator constructs the target object via the injected ObjectConstructor (so fields are populated on a pre-constructed instance), readField delegates to BoundField.readIntoField, and finalize is the identity, returning the accumulator unchanged.

<a id="u-51c0a69b3ae0"></a>
### `reflectiveTypeAdapterFactory-recordAdapter`

`class RecordAdapter<T> extends Adapter<T, Object[]>` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L592-L602][f1]

Adapter for Java records where deserialization must go through the canonical constructor.

The constructor resolves the canonical constructor via ReflectionHelper.getCanonicalRecordConstructor, then either checks accessibility (blockInaccessible) or makes it accessible; it maps record component names to their constructor argument indices, and builds constructorArgsDefaults where each primitive parameter type maps to a zero value from the PRIMITIVE_DEFAULTS map (byte/short/int/long/float/double/char/boolean) and reference types stay null, guaranteeing non-null primitive constructor arguments. createAccumulator returns a clone of that defaults array so each read starts fresh. readField looks up the component index by the BoundField's field name; a missing index throws IllegalStateException with a detailed message explaining that record components and fields are expected to correspond — this is caught by the base read and rethrown as JsonSyntaxException. finalize invokes constructor.newInstance(accumulator); IllegalAccessException is converted via ReflectionHelper.createExceptionForUnexpectedIllegalAccess, InstantiationException and IllegalArgumentException become RuntimeException with the constructor string and arguments (comments deem these practically impossible), and InvocationTargetException becomes RuntimeException wrapping the target cause. primitiveDefaults is a static initializer building the primitive zero-value map.

**Uncertainties.**

- Component-to-index mapping assumes record component names equal the backing field names; the code itself only throws when they do not.

<a id="u-9616a5e5f747"></a>
### `ReflectiveTypeAdapterFactory.checkAccessible`

`private static <M extends AccessibleObject & Member> void checkAccessible( Object obj…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L168-L179][f1]

Verifies that the current reflection filters allow accessing the member.

It calls ReflectionAccessFilterHelper.canAccess, passing null as the instance for static members and the given object otherwise. On failure it throws JsonIOException containing the member's description and remediation guidance; on success it returns silently, allowing the caller to proceed.

<a id="u-54bcdf126a95"></a>
### `ReflectiveTypeAdapterFactory.createDuplicateFieldException`

`private static IllegalArgumentException createDuplicateFieldException( Class<?> decla…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L326-L339][f1]

Builds and throws an IllegalArgumentException for duplicate JSON field names, reporting the declaring class, the duplicated name, string descriptions of both conflicting fields via ReflectionHelper.fieldToString, and a TroubleshootingGuide URL.

It never returns normally.

<a id="u-3c962fb8d736"></a>
### `ReflectiveTypeAdapterFactory.getBoundFields`

`private FieldsData getBoundFields( Gson context, TypeToken<?> type, Class<?> raw, boo…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L341-L450][f1]

Walks the class hierarchy collecting BoundFields for every non-excluded field.

For an interface raw type it returns FieldsData.EMPTY immediately. It iterates from the raw type up to (excluding) Object; for inherited fields it re-evaluates the reflection filters on each declaring class, throwing JsonIOException on BLOCK_ALL and updating blockInaccessible on BLOCK_INACCESSIBLE. Per field: if includeField excludes it both ways it is skipped. For records, static fields are excluded from deserialization while non-static fields get an accessor via ReflectionHelper.getAccessor, made accessible unless blockInaccessible; a @SerializedName present on the accessor but not the field throws JsonIOException because the annotation is unsupported on accessors. Non-record fields, and record fields without an accessor, are made accessible via ReflectionHelper.makeAccessible when blockInaccessible is false. Field types are resolved against the declaring raw type (GsonTypes.resolve) and each field's name list comes from getFieldNames, with names.get(0) as the serialized name. Deserialization registration inserts the BoundField under every name, throwing createDuplicateFieldException if a name is already mapped; serialization registration inserts under the primary name only, likewise detecting duplicates. The loop advances through TypeToken.get(GsonTypes.resolve(...)) on the generic superclass and returns a FieldsData of the deserialization map plus the serialized list.

calls: [ReflectiveTypeAdapterFactory.createDuplicateFieldException](r2-reflective-type-adapter-factory.md#u-54bcdf126a95), [reflectiveTypeAdapterFactory-createBoundField](r2-reflective-type-adapter-factory.md#u-39b1562a58b3), [ReflectionAccessFilterHelper.getFilterResult](r1-reflection-policy.md#u-fb4c4e1a4f55), [type-token-class](r1-type-model.md#u-55a9c25d6eea)

**Uncertainties.**

- Whether fields declared in interfaces along the hierarchy are considered is bounded by the immediate interface check; only the class chain up to Object is walked.

<a id="u-d7cfdfc44369"></a>
### `ReflectiveTypeAdapterFactory.getFieldNames`

`@SuppressWarnings("MixedMutabilityReturnType") private List<String> getFieldNames(Fie…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L85-L107][f1]

Computes the JSON names under which a field is serialized and deserialized.

If the field has no @SerializedName, the primary name comes from fieldNamingPolicy.translateName and alternates from fieldNamingPolicy.alternateNames; otherwise the primary name is annotation.value() and alternates are annotation.alternate(). With no alternates it returns a singleton list; otherwise the primary name is first followed by all alternates, so index 0 always holds the default name.

<a id="u-51c16956ce83"></a>
### `gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:ReflectiveTypeAdapterFactory (2)`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L693-L694][f1]

Closing segment of the outer class; no behavior.

<a id="u-f7ff02c07f89"></a>
### `ReflectiveTypeAdapterFactory.java module code (L1–L59)`

`module_region` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L1-L59][f1]

License header and imports only.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java