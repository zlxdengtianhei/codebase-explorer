# Builder and Naming Configuration

**Capability.** Accumulates mutable configuration (custom adapters, naming policy, number strategy) and freezes it into an ordered, immutable factory list for a Gson instance.

Use GsonBuilder's fluent setters to register per-type or hierarchy adapters and to pick a FieldNamingPolicy or ToNumberStrategy; createFactories then assembles the pipeline. newImmutableList is the shared helper producing the unmodifiable factory list.

**Depends on.**

- [Date and Time Adapters](r2-date-time-adapters.md) · graph-confirmed · 7 edge(s) · GsonBuilder.addDateTypeAdapters installs DefaultDateTypeAdapter factories during configuration.
- [Public Contracts and Annotations](r2-public-api.md) · model-inferred · 0 edge(s)
- [Primitive and Utility Type Adapters](r2-primitive-adapters.md) · graph-only · 9 edge(s)
- [Exclusion and Reflection Policy](r1-reflection-policy.md) · graph-only · 7 edge(s)
- [Built-in Type Adapters](r1-builtin-adapters.md) · graph-only · 2 edge(s)
- [Tree-Style Serializer Bridge](r1-tree-adapter-bridge.md) · graph-only · 2 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · model-inferred · 0 edge(s)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-only · 4 edge(s)

Parent: [Gson JSON Library](r2-gson.md)

## Units (11)

<a id="u-01c61f219079"></a>
### `GsonBuilder`

`class GsonBuilder` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L93-L158][f1]

Configures and builds immutable Gson instances: it holds mutable configuration state and fluent setters, then assembles a factory pipeline in create().

**Notes.**

- field: Defaults are captured in private DEFAULT_* constants: html escaping on, nulls omitted, compact formatting, strictness null (legacy mode), Unsafe allowed, identity field naming, DOUBLE object-to-number and LAZILY_PARSED_NUMBER number-to-number strategies.
- contract: Two static prebuilt instances exist: a shared DEFAULT builder and DEFAULT_TYPE_ADAPTER_FACTORIES built from it; these back the default Gson() constructor and must not be mutated.

**Uncertainties.**

- Field defaults are observable only via constants; runtime use of DEFAULT/DEFAULT_TYPE_ADAPTER_FACTORIES by Gson is not visible in this file.

<a id="u-c0ca1cb1828c"></a>
### `gson/src/main/java/com/google/gson/GsonBuilder.java:GsonBuilder (35)`

`GsonBuilder(Gson gson)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L166-L187][f1]

Builds a GsonBuilder that copies the full configuration of an existing Gson instance so the instance can be reconfigured and rebuilt.

uses: [gson/src/main/java/com/google/gson/Gson.java:Gson (35)](r1-facade-api.md#u-b738e22e796c)

**Uncertainties.**

- Whether the copied configuration fully reproduces the original Gson depends on Gson-internal fields (builderFactories, builderHierarchyFactories) not visible here.

<a id="u-fb292afb648f"></a>
### `GsonBuilder.registerTypeAdapter`

`@CanIgnoreReturnValue public GsonBuilder registerTypeAdapter(Type type, Object typeAd…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L739-L771][f1]

Registers a custom adapter for exactly one type, dispatching by the interfaces the adapter object implements.

It first requires non-null type and adapter, then rejects adapters implementing none of JsonSerializer, JsonDeserializer, InstanceCreator, TypeAdapter with IllegalArgumentException. Registration for Object.class is rejected via hasNonOverridableAdapter (JsonElement is deliberately not protected for backward compatibility). An InstanceCreator goes into instanceCreators keyed by type; serializers/deserializers add a TreeTypeAdapter factory with raw-type matching to factories; a TypeAdapter adds a TypeAdapters.newFactory. An object implementing several interfaces registers multiple factories. Returns this.

**Notes.**

- contract: JsonSerializer/JsonDeserializer registrations are null-safe: nulls bypass the adapter; TypeAdapter handles nulls itself.

calls: [TreeTypeAdapter.newFactoryWithMatchRawType](r1-tree-adapter-bridge.md#u-ac1820337c5b), [typeadapters-factory-helpers](r2-primitive-adapters.md#u-434284f4fe08), [type-token-class](r1-type-model.md#u-55a9c25d6eea)

**Uncertainties.**

- Duplicate registration for the same type is added to the list without removing earlier entries; which factory wins depends on factory-chain ordering in Gson, not visible here.

<a id="u-52a0d7037a42"></a>
### `GsonBuilder.registerTypeHierarchyAdapter`

`@CanIgnoreReturnValue public GsonBuilder registerTypeHierarchyAdapter(Class<?> baseTy…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L818-L841][f1]

Registers an adapter applying to an inheritance hierarchy rooted at baseType.

Requires non-null arguments; throws IllegalArgumentException when the adapter implements none of JsonSerializer, JsonDeserializer, TypeAdapter (unlike registerTypeAdapter, InstanceCreator is not accepted here, so passing one falls into the rejection branch). Serializers/deserializers add a TreeTypeAdapter type-hierarchy factory to hierarchyFactories; TypeAdapter instances add a TypeAdapters.newTypeHierarchyFactory to factories, so an adapter may be registered in both lists if it implements both. Returns this.

calls: [TreeTypeAdapter.newTypeHierarchyFactory](r1-tree-adapter-bridge.md#u-48ebb4829b63), [typeadapters-factory-helpers](r2-primitive-adapters.md#u-434284f4fe08)

**Uncertainties.**

- Precedence between hierarchy and specific-type adapters at runtime depends on Gson's factory chain, not shown here.

<a id="u-f54ca5b55863"></a>
### `GsonBuilder.createFactories`

`List<TypeAdapterFactory> createFactories( ConstructorConstructor constructorConstruct…` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L926-L1003][f1]

Assembles the ordered, unmodifiable factory list a Gson instance uses, from this builder's current state.

Order is fixed: non-overridable built-ins (JSON element, ObjectTypeAdapter with the configured objectToNumberStrategy), then the excluder so it precedes user types, then user-registered factories (reversed, see addUserDefinedAdapters), then optional date adapters, then built-in primitive/platform adapters. Long adapters come from longSerializationPolicy.typeAdapter(); double/float adapters switch between strict and permissive variants based on serializeSpecialFloatingPointValues (doubleAdapter/floatAdapter). If TypeAdapters.javaTimeTypeAdapterFactory() returns null (java.time absent) it is skipped. Composite adapters (collection, map with complexMapKeySerialization, @JsonAdapter annotation factory, enum) come next, and ReflectiveTypeAdapterFactory is last, receiving the field naming policy, excluder, and reflectionFilters converted via newImmutableList. Returns Collections.unmodifiableList after trimToSize.

**Notes.**

- side_effect: Reads builder state only; does not mutate this builder, so createFactories can be called repeatedly.

calls: [LongSerializationPolicy](r1-facade-api.md#u-f02f3acb5dbc), [NumberTypeAdapter.getFactory](r1-builtin-adapters.md#u-3b04a756297b), [ObjectTypeAdapter.getFactory](r1-builtin-adapters.md#u-6d223f0cde9f), [TypeAdapters.javaTimeTypeAdapterFactory](r2-date-time-adapters.md#u-f9f1ea7218e2), [typeadapters-integer-like](r2-primitive-adapters.md#u-3e7ac8874b8d); uses: [DateType](r2-date-time-adapters.md#u-af642623c40a)

**Uncertainties.**

- Exact runtime resolution order of overlapping factories is defined by Gson's factory chain, not by this list alone.

<a id="u-7f60251665e6"></a>
### `GsonBuilder.addDateTypeAdapters`

`private void addDateTypeAdapters(List<TypeAdapterFactory> factories)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L1043-L1076][f1]

Appends date adapters to the factory list only when a custom date format is configured; otherwise adds nothing.

If datePattern is non-null and non-blank after trim, it creates a Date adapter from the pattern, plus sql.Timestamp and sql.Date adapters when the java.sql module is present. Else if either dateStyle or timeStyle differs from DateFormat.DEFAULT, it creates the same three adapters from the style pair. In the remaining default case it returns without adding. SQL adapters are added only when SqlTypesSupport.SUPPORTS_SQL_TYPES is true; null sql factory references are never added in that case because they are always assigned first.

calls: [DateType](r2-date-time-adapters.md#u-af642623c40a)

**Uncertainties.**

- A whitespace-only pattern is silently treated as unset (falls through to style/default branch); whether that is intended is not stated in the source.

<a id="u-8784c7046129"></a>
### `GsonBuilder.newImmutableList`

`static <E> List<E> newImmutableList(Collection<E> collection)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L1005-L1018][f1]

Copies a collection into a fixed, unmodifiable list with three cases: empty collection yields the shared emptyList; a single-element collection yields a singletonList, taking element 0 for Lists or iterator().next() otherwise; otherwise wraps Arrays.asList(collection.toArray()) in unmodifiableList with an unchecked cast.

Returns the new list; the input is not modified.

**Uncertainties.**

- The unchecked cast assumes toArray produces Object[] assignable to E[], which holds for typical collections but is not verified here.

<a id="u-75c42d6c7df8"></a>
### `fieldnamingpolicy-field-naming-policy`

`public enum FieldNamingPolicy implements FieldNamingStrategy` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L31-L35][f2]

Enumerates Gson's standard field-naming conventions, each translating a Java field name to its JSON name.

IDENTITY returns the field name unchanged. UPPER_CAMEL_CASE capitalizes the first letter. UPPER_CAMEL_CASE_WITH_SPACES first inserts a space before each uppercase character, then capitalizes the first letter. UPPER_CASE_WITH_UNDERSCORES inserts an underscore before each uppercase character and uppercases everything (so acronyms split: aURL becomes A_U_R_L); leading underscores are preserved untouched. LOWER_CASE_WITH_UNDERSCORES, LOWER_CASE_WITH_DASHES, and LOWER_CASE_WITH_DOTS do the same insertion and then lowercase with the respective separator. Non-letter leading characters and existing separators pass through unchanged. All seven constants implement FieldNamingStrategy.translateName(Field) by delegating to the shared helpers separateCamelCase and upperCaseFirstLetter; locale-sensitive case changes use Locale.ENGLISH, so the result is locale-independent.

**Notes.**

- contract: Used with GsonBuilder.setFieldNamingStrategy; each constant's translateName is the per-Field entry point.
- field: separateCamelCase inserts the separator only before an uppercase character when the output built so far is non-empty, so the first character never gains a leading separator.

calls: [FieldNamingPolicy.separateCamelCase](r2-configuration.md#u-f62cb9a19af0), [FieldNamingPolicy.upperCaseFirstLetter](r2-configuration.md#u-e1b81b3e2980)

**Uncertainties.**

- Behavior for characters above the basic uppercase set follows Character.isUpperCase and Character.toUpperCase; results for locale-special letters are not defined here beyond use of Locale.ENGLISH.

<a id="u-f62cb9a19af0"></a>
### `FieldNamingPolicy.separateCamelCase`

`static String separateCamelCase(String name, char separator)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L179-L189][f2]

Inserts the given separator before every uppercase character of the camel-case name, except before the first character.

It copies each character into a StringBuilder; when Character.isUpperCase is true and the builder is non-empty, the separator is appended first. Existing characters (including leading underscores) are copied verbatim; aURL therefore becomes a_U_R_L. Returns the joined string; empty input yields an empty string.

<a id="u-e1b81b3e2980"></a>
### `FieldNamingPolicy.upperCaseFirstLetter`

`static String upperCaseFirstLetter(String s)` · [gson/src/main/java/com/google/gson/FieldNamingPolicy.java:L192-L212][f2]

Uppercases the first letter of the string, leaving any leading non-letter prefix intact.

It scans for the first character for which Character.isLetter is true: if that character is already uppercase the original string is returned; otherwise it is uppercased and spliced back in (one substring when at index 0, otherwise prefix + uppercased + suffix). If the string contains no letters at all, the original string is returned unchanged.

<a id="u-996841e54d4d"></a>
### `tonumberpolicy-java`

`@Override public Double readNumber(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/ToNumberPolicy.java:L43-L46][f3]

Enum of number-reading strategies used when Gson deserializes numbers as Object or Number; each constant implements ToNumberStrategy.readNumber.

DOUBLE calls in.nextDouble(), returning a Double and propagating reader exceptions (lenient-mode infinities/NaN allowed by the reader's own rules). LAZILY_PARSED_NUMBER wraps in.nextString() in a LazilyParsedNumber, deferring numeric parsing. LONG_OR_DOUBLE reads the token as a String: if it contains a '.', or Long.parseLong fails with NumberFormatException, it parses as Double via the private parseAsDouble helper; that helper converts infinite or NaN results into MalformedJsonException when the reader is not lenient (message includes the value and previous path), and any unparseable text becomes JsonParseException. Otherwise the Long value is returned. BIG_DECIMAL reads the string and returns NumberLimits.parseBigDecimal(value), converting NumberFormatException to JsonParseException with the value and previous path in the message. All strategies propagate IOException from the reader unchanged.

**Notes.**

- failure: LONG_OR_DOUBLE falls back to Double parsing when Long.parseLong fails, so '12345678901234567890' becomes a Double rather than failing.

**Uncertainties.**

- Additional checks performed by NumberLimits.parseBigDecimal (e.g. magnitude limits) are not visible in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldNamingPolicy.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ToNumberPolicy.java