# Reflective adapter support

**Capability.** Builds reflection-based adapters and applies field naming, exclusion, accessibility, and reflection filters.

Use for reflective serialization/deserialization internals and access policy. Units show field naming, reflection filters, reflective adapter factory, and reflection helpers.

**Depends on.**

- [Serialization exclusion policy](serialization-exclusion-policy.md) · graph-confirmed · 1 edge(s)
- [Generic type reflection](generic-type-reflection.md) · graph-only · 4 edge(s)

**Depended on by.**

- [Serialization exclusion policy](serialization-exclusion-policy.md) · graph-confirmed · 2 edge(s)
- [Object construction adapters](object-construction-adapters.md) · graph-only · 7 edge(s)
- [Generic type reflection](generic-type-reflection.md) · graph-only · 2 edge(s)
- [Null-safe atomic adapters](null-safe-atomic-adapters.md) · graph-only · 2 edge(s)
- [JSON token scanning](json-token-scanning.md) · graph-only · 1 edge(s)
- [JSON value consumption](json-value-consumption.md) · graph-only · 1 edge(s)

Parent: [Reflection and exclusion rules](reflection-and-exclusion-rules.md)

## Units (27)

<a id="u-7fe72caa66d3"></a>
### `FieldNamingStrategy.java-fieldnamingstrategy-methods`

`String translateName(Field f);` · [gson/src/main/java/com/google/gson/FieldNamingStrategy.java:L43-L43][f1]

Defines the naming contract used by reflective adapters: translateName maps a reflected field to its JSON name, and alternateNames supplies extra deserialization names.

The default alternateNames returns an empty immutable list; implementations may override either method. No state is held.

<a id="u-dfd134f0087a"></a>
### `ReflectionAccessFilter.java-built-in-reflection-access-filters`

`@Override public FilterResult check(Class<?> rawClass)` · [gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:L114-L119][f2]

These singleton filters classify a class and return a FilterResult.

BLOCK_INACCESSIBLE_JAVA returns BLOCK_INACCESSIBLE for Java types and INDECISIVE otherwise; BLOCK_ALL_JAVA returns BLOCK_ALL for Java types and INDECISIVE otherwise; BLOCK_ALL_ANDROID returns BLOCK_ALL for Android types and INDECISIVE otherwise; BLOCK_ALL_PLATFORM returns BLOCK_ALL for any platform type and INDECISIVE otherwise. Each toString returns the exact string ReflectionAccessFilter# plus its constant name, such as ReflectionAccessFilter#BLOCK_INACCESSIBLE_JAVA. Classification is delegated to ReflectionAccessFilterHelper.

**Uncertainties.**

- Exact class sets for Java, Android, and platform classification are delegated to ReflectionAccessFilterHelper and are not proven here.

<a id="u-18b8ba610042"></a>
### `ReflectionAccessFilterHelper.java-filter-result-and-access-checking`

`public static FilterResult getFilterResult( List<ReflectionAccessFilter> reflectionFi…` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L64-L73][f3]

Applies reflection-access filters and checks accessibility.

Filter result returns the first non-INDECISIVE filter result, or ALLOW when the list is empty or all are indecisive. Accessibility delegates to a singleton checker. On Java 9+ the checker reflectively invokes AccessibleObject.canAccess(Object); invocation failures are wrapped in RuntimeException. If that method is unavailable or the runtime is older, the fallback assumes access is allowed.

<a id="u-d775ff2f00aa"></a>
### `ReflectionAccessFilterHelper.java-platform-type-detection`

`class ReflectionAccessFilterHelper` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L26-L27][f3]

Platform type classification by class name.

Java types start with java. or javax.; Android types start with android. or androidx. or are Java types; any-platform types are Android/Java or start with kotlin., kotlinx., or scala.

<a id="u-6f4ef34f3c2f"></a>
### `ReflectionHelper.java-accessibility-and-reflection-descriptions`

`private static String getInaccessibleTroubleshootingSuffix(Exception e)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L46-L57][f4]

Provides accessibility attempts and compact descriptions for reflected members.

makeAccessible calls setAccessible(true) and, on any Exception, throws JsonIOException with a description, guidance, and a troubleshooting suffix, preserving the cause. tryMakeAccessible does the same but returns null on success and an error message on failure instead of throwing. The troubleshooting suffix is non-empty only when the exception class name is exactly java.lang.reflect.InaccessibleObjectException; it selects the module-specific troubleshooting id when the message contains 'to module com.google.gson', otherwise the generic id, and returns an empty string for other exceptions. Descriptions render fields as declaring#name, methods as declaring#name(simple parameter types), constructors as declaring(simple parameter types), and unknown objects with a fallback prefix; the optional uppercase flag only changes a lowercase first character. The parameter-list helper appends parentheses and comma-space-separated simple type names.

<a id="u-e5fc8649e0aa"></a>
### `ReflectionHelper.java-class-modifier-queries`

`public static boolean isStatic(Class<?> clazz)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L151-L153][f4]

isStatic reports whether the class modifiers include static.

isAnonymousOrNonStaticLocal reports true only when the class is not static and is either anonymous or local; it does not inspect constructors or instantiation ability.

<a id="u-4ddc3838f672"></a>
### `ReflectionHelper.java-record-reflection-dispatch`

`public static boolean isRecord(Class<?> raw)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L182-L184][f4]

These public record queries delegate to the helper selected at class initialization.

On a JVM without record support, isRecord returns false while component-name, accessor, and canonical-constructor queries throw UnsupportedOperationException. On a supported JVM they delegate to the record-supported helper's reflective implementations.

<a id="u-8ab3e2736162"></a>
### `ReflectionHelper.java-record-supported-helper`

`class RecordSupportedHelper extends RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L233-L234][f4]

This helper is used when record reflection is available.

Its constructor reflectively looks up Class.isRecord, Class.getRecordComponents, and RecordComponent.getName/getType; any lookup failure throws ReflectiveOperationException, which the outer static initializer catches to select the unsupported helper. Each operation invokes the cached methods and wraps any ReflectiveOperationException in the record-reflection RuntimeException. Component names are read in order. The canonical constructor is obtained with getDeclaredConstructor using the component types, so non-public record constructors are reachable. The accessor is the public method whose name equals the field name.

<a id="u-df8fe7780a3b"></a>
### `ReflectionHelper.java-record-unsupported-helper`

`class RecordNotSupportedHelper extends RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L300-L302][f4]

This helper is used when record reflection is unavailable.

isRecord always returns false. The component-name, canonical-constructor, and accessor operations always throw UnsupportedOperationException with a message that records are not supported on this JVM.

<a id="u-ff3dfa925ade"></a>
### `ReflectionHelper.java-recordhelper-abstraction`

`class RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L223-L224][f4]

This private abstract inner class defines the record-reflection contract for testing, naming, constructing, and accessing records.

It supplies no implementation; the two concrete helpers provide supported and unsupported behavior.

<a id="u-e316f2e6868c"></a>
### `ReflectionHelper.java-reflection-exception-wrapping`

`public static RuntimeException createExceptionForUnexpectedIllegalAccess( IllegalAcce…` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L199-L207][f4]

Both methods always throw RuntimeException rather than returning normally.

The illegal-access wrapper includes the Gson version and a message about ReflectionAccessFilter requiring Java 9 or newer, with the original exception as cause. The record-reflection wrapper includes the Gson version and a message that record reflection failed unexpectedly after record support was established, with the original exception as cause.

<a id="u-2a7be649f2ab"></a>
### `ReflectionHelper.java-reflectionhelper-class`

`class ReflectionHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L28-L30][f4]

This final utility class centralizes reflection accessibility, human-readable reflection descriptions, class-modifier checks, and record reflection dispatch.

Its static initializer tries to construct the record-supported helper; if that construction throws ReflectiveOperationException, it falls back to the record-not-supported helper. The selected helper is then used by the record query methods.

<a id="u-a2f2d3c85aba"></a>
### `ReflectiveTypeAdapterFactory.java-bound-field-contract`

`class BoundField` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L452-L454][f5]

Abstract per-field contract holding the serialized name, reflective field, and underlying field name.

Subclasses implement writing a value, reading into a record constructor argument array, and reading into an object field.

<a id="u-92dd12a1a168"></a>
### `ReflectiveTypeAdapterFactory.java-bound-field-creation`

`private BoundField createBoundField( Gson context, Field field, Method accessor, Stri…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L181-L236][f5]

Creates a BoundField for one field, choosing the field adapter from @JsonAdapter when present or from Gson otherwise.

For serialization without @JsonAdapter it wraps the adapter in TypeAdapterRuntimeTypeWrapper; with @JsonAdapter it uses the adapter directly. write checks accessibility when blocked, invokes the record accessor or reads the field, wraps accessor InvocationTargetException in JsonIOException, skips writing when the value is the source object to avoid recursion, then writes the serialized name and value. readIntoArray reads a value and throws JsonParseException if a primitive component receives null, otherwise stores it at the index. readIntoField reads a value; for non-null or non-primitive values it checks accessibility when blocked, otherwise throws JsonIOException for static final fields only when blocking is off, then sets the field. When blocking is on, a static final field is not caught by that branch and field.set may throw IllegalAccessException.

<a id="u-dd9606d9437e"></a>
### `ReflectiveTypeAdapterFactory.java-create-and-local-class-fallback`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L109-L124][f5]

create returns null for primitives.

For anonymous or non-static local classes it returns a fallback adapter that skips any input and returns null on read, writes null on write, and identifies itself as AnonymousOrNonStaticLocalClassAdapter. Otherwise it applies reflection filters: BLOCK_ALL throws JsonIOException; BLOCK_INACCESSIBLE sets blockInaccessible; records use RecordAdapter; other classes use FieldReflectionAdapter with a constructor and bound fields.

<a id="u-d9584255ff03"></a>
### `ReflectiveTypeAdapterFactory.java-field-collections`

`class FieldsData` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L312-L313][f5]

Immutable holder for the deserialized-field map and serialized-field list; EMPTY uses empty collections.

<a id="u-6a4a9d79d77c"></a>
### `ReflectiveTypeAdapterFactory.java-field-reflection-adapter`

`class FieldReflectionAdapter<T> extends Adapter<T, T>` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L567-L568][f5]

Adapter for ordinary classes.

It constructs the accumulator with the configured ObjectConstructor, reads each field by delegating to BoundField.readIntoField, and finalizes by returning the accumulator unchanged.

<a id="u-72e8e247f4d2"></a>
### `ReflectiveTypeAdapterFactory.java-record-adapter`

`class RecordAdapter<T> extends Adapter<T, Object[]>` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L592-L593][f5]

Adapter for records.

The constructor obtains the canonical record constructor, checks or makes it accessible, maps record component names to constructor argument indices, and builds a default argument array with primitive zero values and nulls for non-primitives. createAccumulator clones those defaults. readField looks up the component index by the backing field name; if absent it throws IllegalStateException, which the public read wraps as JsonSyntaxException, otherwise it reads into the array. finalize invokes the constructor: IllegalAccessException is wrapped via ReflectionHelper; InstantiationException or IllegalArgumentException becomes RuntimeException with constructor and args; InvocationTargetException becomes RuntimeException with the cause.

<a id="u-6dd704dcc835"></a>
### `ReflectiveTypeAdapterFactory.java-reflective-adapter-base`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L481-L498][f5]

Base TypeAdapter for reflective adapters.

write returns null for null, otherwise begins an object, writes each serialized bound field, wraps IllegalAccessException via ReflectionHelper, and ends the object. read returns null for JSON null, creates an accumulator, begins an object, skips unknown names, reads known fields into the accumulator, wraps IllegalStateException as JsonSyntaxException and IllegalAccessException via ReflectionHelper, ends the object, and returns finalize(accumulator). Subclasses supply accumulator creation, per-field reading, and finalization.

<a id="u-a1cf1166b931"></a>
### `ReflectiveTypeAdapterFactory.java-reflective-factory`

`class ReflectiveTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L60-L61][f5]

ReflectiveTypeAdapterFactory is a TypeAdapterFactory that builds reflection-based adapters for classes, coordinating constructor lookup, field naming and exclusion, @JsonAdapter handling, and reflection access filters.

<a id="u-9e16a71125f9"></a>
### `TroubleshootingGuide.java-troubleshooting-url-helper`

`class TroubleshootingGuide` · [gson/src/main/java/com/google/gson/internal/TroubleshootingGuide.java:L3-L4][f6]

Final utility class with a private constructor; createUrl builds a GitHub troubleshooting URL by appending the id to a fixed base.

It performs no validation or encoding.

<a id="u-807e9949c5d3"></a>
### `gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:ReflectionAccessFilter.check (4)`

`FilterResult check(Class<?> rawClass);` · [gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:L227-L227][f2]

Abstract filter contract: implementations receive a raw class and return ALLOW, INDECISIVE, BLOCK_INACCESSIBLE, or BLOCK_ALL.

This interface method has no default behavior; the result controls whether reflection access is permitted, deferred to the next filter, restricted to accessible members, or blocked entirely.

<a id="u-9616a5e5f747"></a>
### `ReflectiveTypeAdapterFactory.checkAccessible`

`private static <M extends AccessibleObject & Member> void checkAccessible( Object obj…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L168-L179][f5]

Checks whether a member is accessible under the reflection filters.

If not, throws JsonIOException with the member description and guidance to register a TypeAdapter, adjust the filter, or increase visibility.

<a id="u-54bcdf126a95"></a>
### `ReflectiveTypeAdapterFactory.createDuplicateFieldException`

`private static IllegalArgumentException createDuplicateFieldException( Class<?> decla…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L326-L339][f5]

Always throws IllegalArgumentException describing the declaring class, duplicate JSON name, both conflicting fields, and a troubleshooting URL.

<a id="u-3c962fb8d736"></a>
### `ReflectiveTypeAdapterFactory.getBoundFields`

`private FieldsData getBoundFields( Gson context, TypeToken<?> type, Class<?> raw, boo…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L341-L450][f5]

Collects bound fields across the class hierarchy.

Interfaces return empty data. For each class, inherited classes with fields are rechecked against reflection filters: BLOCK_ALL throws JsonIOException naming the supertype, and BLOCK_INACCESSIBLE updates blocking. Fields excluded in both directions are skipped. For records, static fields are not deserialized; non-static fields get an accessor, which is made accessible when blocking is off, and an @SerializedName on the accessor without one on the field throws JsonIOException. Non-record fields are made accessible when blocking is off. Each included field is resolved, named, and bound; duplicate deserialization names or duplicate serialization names throw IllegalArgumentException. The loop continues through superclasses and returns the collected maps/lists.

<a id="u-d7cfdfc44369"></a>
### `ReflectiveTypeAdapterFactory.getFieldNames`

`@SuppressWarnings("MixedMutabilityReturnType") private List<String> getFieldNames(Fie…` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L85-L107][f5]

Computes the primary JSON name and alternate names for a field.

With @SerializedName, the primary is the annotation value and alternates are its alternate list; otherwise the configured FieldNamingStrategy supplies both. Returns a singleton list when there are no alternates, otherwise a list with the primary first followed by alternates.

<a id="u-bc24316c33e8"></a>
### `ReflectiveTypeAdapterFactory.includeField`

`private boolean includeField(Field f, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L80-L82][f5]

Returns whether the field is included for the requested direction by delegating to the configured Excluder.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldNamingStrategy.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ReflectionAccessFilter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/TroubleshootingGuide.java
