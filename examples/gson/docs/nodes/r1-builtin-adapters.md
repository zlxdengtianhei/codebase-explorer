# Built-in Type Adapters

**Capability.** Concrete adapters for common Java kinds: arrays, enums, Number/Object with pluggable ToNumberStrategy, plus the strategy hook itself; each adapter is created by a factory that claims matching types.

Use this subtree to see how specific Java types map to JSON; number shaping in Object/Number deserialization is controlled by ToNumberStrategy implementations.

**Children.**

- [java.time Adapters](r1-java-time-adapters.md) `r1-java-time-adapters` · 9 unit(s)

**Depends on.**

- [TypeAdapter Framework](r1-adapter-framework.md) · graph-confirmed · 4 edge(s) · Built-in adapters compose through TypeAdapter.nullSafe and the runtime-type wrapper of the framework.
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 9 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-confirmed · 8 edge(s)

**Depended on by.**

- [java.time Adapters](r1-java-time-adapters.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-java-time-adapters ` → ` r1-builtin-adapters `)
- [Builder and Naming Configuration](r2-configuration.md) · graph-only · 2 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (25)

<a id="u-bd31bdfb1fd0"></a>
### `arraytypeadapter.java-class`

`class ArrayTypeAdapter<E> extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L34-L37][f1]

ArrayTypeAdapter is a final TypeAdapter<Object> converting between Java arrays (primitive or Object arrays) and JSON arrays.

Its public FACTORY field claims array-shaped TypeTokens and builds one instance per component type; instances dispatch element I/O through a TypeAdapterRuntimeTypeWrapper so runtime element types are honored. The componentType and componentTypeAdapter fields set by the constructor drive both read and write behavior.

group: [ArrayTypeAdapter.create](r1-builtin-adapters.md#u-07041a2aec40)

<a id="u-22938dcdcd45"></a>
### `gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:ArrayTypeAdapter (3)`

`public ArrayTypeAdapter( Gson context, TypeAdapter<E> componentTypeAdapter, Class<E> …` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L58-L63][f1]

Builds the adapter by wrapping the supplied component adapter in a TypeAdapterRuntimeTypeWrapper bound to this Gson context and the component class, so element reads and writes dispatch to an adapter matching the element's runtime type.

It also stores the component class, which read() and write() use for reflective array creation and access. No argument validation occurs.

uses: [ArrayTypeAdapter.create](r1-builtin-adapters.md#u-07041a2aec40)

<a id="u-07041a2aec40"></a>
### `ArrayTypeAdapter.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L37-L52][f1]

Creates the adapter for array-shaped types, returning null for anything else so other factories can claim the type.

It accepts a type that is a GenericArrayType or a Class with isArray() true; otherwise it returns null. For accepted types it extracts the component type via GsonTypes.getArrayComponentType, resolves a component adapter with gson.getAdapter(TypeToken.get(componentType)), and constructs an ArrayTypeAdapter with GsonTypes.getRawType(componentType) as the runtime component class, returned via an unchecked cast.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613), [GsonTypes](r1-type-model.md#u-f248f331b1a0), [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:ArrayTypeAdapter (3)](r1-builtin-adapters.md#u-22938dcdcd45)

**Uncertainties.**

- Behavior of GsonTypes.getArrayComponentType for malformed generic array types is not visible here.

<a id="u-e54aa525f0d8"></a>
### `ArrayTypeAdapter.read`

`@Override public Object read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L65-L95][f1]

Reads a JSON array into a Java array.

A peeked NULL token is consumed with nextNull() and null is returned. Otherwise it collects elements into an ArrayList, delegating each element to componentTypeAdapter.read(in) between beginArray() and endArray(), then materializes the array: when the component type is primitive it builds the array with Array.newInstance and copies element by element via Array.set; otherwise it creates an E[] and returns list.toArray(array). An empty JSON array yields a zero-length array. IOExceptions propagate; an Array.set failure on a mismatched boxed value is not caught.

**Notes.**

- side_effect: Consumes the reader through the whole array, including the endArray token.

uses: [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:ArrayTypeAdapter (3)](r1-builtin-adapters.md#u-22938dcdcd45)

**Uncertainties.**

- Failure behavior of the TypeAdapterRuntimeTypeWrapper on runtime element-type mismatches is outside this file.

<a id="u-d7de852306f0"></a>
### `ArrayTypeAdapter.write`

`@Override public void write(JsonWriter out, Object array) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L97-L111][f1]

Writes a Java array as a JSON array.

A null array is written as a JSON null and the method returns. Otherwise it opens an array, iterates indices 0..Array.getLength(array)-1, casts each Array.get result to the component type, and delegates each element to componentTypeAdapter.write(out, value), then closes the array. Primitive arrays are handled uniformly via reflective Array.get/getLength; exceptions from the component adapter propagate.

uses: [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:ArrayTypeAdapter (3)](r1-builtin-adapters.md#u-22938dcdcd45)

<a id="u-d26e843c3261"></a>
### `enumtypeadapter.java-class`

`class EnumTypeAdapter<T extends Enum<T>> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L35-L38][f2]

EnumTypeAdapter is a package-private TypeAdapter for concrete enum classes (explicitly not java.lang.Enum).

It maps between JSON strings and enum constants using reflection over declared fields so obfuscated classes still work, honoring @SerializedName values and alternates for reading and annotated names for writing. Its static FACTORY field performs the type matching done by create(), skipping java.lang.Enum and unwrapping anonymous subclasses.

group: [EnumTypeAdapter.create](r1-builtin-adapters.md#u-37911ed505c0)

<a id="u-a9a86bd7f55e"></a>
### `gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:EnumTypeAdapter (4)`

`private EnumTypeAdapter(Class<T> classOfT)` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L64-L111][f2]

Builds the enum name-to-constant mappings by reflection over the enum class's declared fields.

It filters the field array in place to enum-constant fields (counting into constantCount), trims with Arrays.copyOf — every enum type is expected to have at least one non-constant field, the implicit $VALUES array — then makes the fields accessible and reads each constant via constantField.get(null). For each constant it records nameToConstant[constant.name()], stringToConstant[constant.toString()], and constantToName[constant]; when the field carries @SerializedName, name becomes the annotation value, each alternate() is additionally registered in nameToConstant, and constantToName maps to the annotated name. All three maps are plain HashMaps sized by calculateHashMapCapacity; EnumMap is deliberately avoided because it breaks under ProGuard/R8. IllegalAccessException is impossible after setAccessible, so it is rethrown as AssertionError.

**Notes.**

- failure: IllegalAccessException is converted to AssertionError, never propagated as IOException.
- condition: If two constants share the same annotated name, the later field's mapping overwrites the earlier in the HashMaps; behavior for duplicate names is not otherwise guarded.

**Uncertainties.**

- Reflection on obfuscated classes could still fail in ways not represented here (e.g. SecurityException from setAccessible); only IllegalAccessException is handled.

<a id="u-f0570c85fc93"></a>
### `EnumTypeAdapter.calculateHashMapCapacity`

`private static int calculateHashMapCapacity(int numMappings)` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L56-L58][f2]

Computes a HashMap capacity sized for the expected number of mappings, mirroring Java 19's HashMap.newHashMap: it returns ceil(numMappings / 0.75F) so the map will not resize at the default load factor.

<a id="u-37911ed505c0"></a>
### `EnumTypeAdapter.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L38-L50][f2]

Creates the enum adapter for enum types, returning null when the raw type is not assignable to Enum or is exactly Enum.class (so java.lang.Enum itself is never adapted).

For an anonymous enum subclass (rawType.isEnum() false) it reassigns rawType to its superclass to reach the actual enum class. It then constructs an EnumTypeAdapter for that class and returns it via an unchecked cast.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea), [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:EnumTypeAdapter (4)](r1-builtin-adapters.md#u-a9a86bd7f55e)

<a id="u-68637a954b9c"></a>
### `EnumTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L113-L123][f2]

Reads one enum constant from JSON.

A peeked NULL is consumed with nextNull() and null is returned. Otherwise it reads the token as a string and looks it up first in nameToConstant (declared names and @SerializedName values/alternates); if that misses, it falls back to stringToConstant (toString() values). If neither map contains the key, the method returns null rather than throwing.

uses: [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:EnumTypeAdapter (4)](r1-builtin-adapters.md#u-a9a86bd7f55e)

<a id="u-1e88a24ca68f"></a>
### `EnumTypeAdapter.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L125-L128][f2]

Writes an enum value as its serialized name: null is written as a JSON null; otherwise the name looked up in constantToName is written via out.value.

A value absent from the map (possible only if the value did not come from the reflected constants) would write null.

uses: [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:EnumTypeAdapter (4)](r1-builtin-adapters.md#u-a9a86bd7f55e)

<a id="u-0e5aca721a5d"></a>
### `numbertypeadapter.java-class`

`class NumberTypeAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L32-L39][f3]

NumberTypeAdapter is a final TypeAdapter<Number> that reads JSON numbers into the Number type chosen by a configurable ToNumberStrategy and writes Number values directly.

The private LAZILY_PARSED_NUMBER_FACTORY field caches the default-policy factory; the private constructor just stores the strategy, and the private newFactory() helper builds the type-checking factory wrapper whose create() is covered by its own unit.

group: [NumberTypeAdapter.newFactory](r1-builtin-adapters.md#u-b0062a5a11fc)

<a id="u-3b04a756297b"></a>
### `NumberTypeAdapter.getFactory`

`public static TypeAdapterFactory getFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L54-L60][f3]

Returns a factory for the given number strategy.

When the strategy is exactly ToNumberPolicy.LAZILY_PARSED_NUMBER it returns the shared LAZILY_PARSED_NUMBER_FACTORY singleton; any other strategy gets a freshly created factory. This reuse avoids constructing a new adapter object for Gson's default policy.

calls: [NumberTypeAdapter.newFactory](r1-builtin-adapters.md#u-b0062a5a11fc)

<a id="u-b0062a5a11fc"></a>
### `NumberTypeAdapter.newFactory`

`private static TypeAdapterFactory newFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L43-L46][f3]

Builds a TypeAdapterFactory around a new NumberTypeAdapter for the given strategy.

Its create() returns the adapter only when the requested raw type is exactly Number.class, and null otherwise, so the factory never claims primitive numeric types or subclasses of Number.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-d893742943b8"></a>
### `NumberTypeAdapter.read`

`@Override public Number read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L62-L76][f3]

Reads one JSON number.

It peeks the token: NULL is consumed with nextNull() and null is returned; NUMBER or STRING delegates to toNumberStrategy.readNumber(in), so the concrete Number type (Double, LazilyParsedNumber, or a custom strategy's choice) is decided by the configured strategy; any other token throws JsonSyntaxException("Expecting number, got: " + jsonToken + "; at path " + in.getPath()), including the reader's path in the message.

**Notes.**

- failure: Non-numeric tokens raise JsonSyntaxException; strategy-specific parse failures propagate from readNumber.

calls: [ToNumberStrategy.readNumber](r1-builtin-adapters.md#u-d277fc846eb5)

**Uncertainties.**

- Whether readNumber consumes exactly one token depends on the strategy implementation.

<a id="u-570ba702e39d"></a>
### `NumberTypeAdapter.write`

`@Override public void write(JsonWriter out, Number value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L78-L81][f3]

Writes the Number via out.value(value); formatting and null handling (whether a null value writes a JSON null or throws) are determined by JsonWriter, not this class.

uses: [JsonWriter.nullValue](r2-streaming.md#u-09865727958f)

**Uncertainties.**

- JsonWriter.value(Number) behavior for a null argument is outside this file.

<a id="u-51f20af24d0c"></a>
### `objecttypeadapter.java-class`

`class ObjectTypeAdapter extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L40-L47][f4]

ObjectTypeAdapter adapts statically-typed Object values: deserialization produces ArrayList/LinkedHashMap trees with numbers shaped by a configurable ToNumberStrategy (Double by default); serialization dispatches on the value's runtime class.

The DOUBLE_FACTORY field caches the default-policy factory; the private constructor stores the Gson context and strategy; the private newFactory() helper's create() has its own unit.

group: [ObjectTypeAdapter.read](r1-builtin-adapters.md#u-d55b0d86a0c2)

<a id="u-6d223f0cde9f"></a>
### `ObjectTypeAdapter.getFactory`

`public static TypeAdapterFactory getFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L65-L71][f4]

Returns a factory for the given number strategy: the shared DOUBLE_FACTORY singleton when the strategy is exactly ToNumberPolicy.DOUBLE (Gson's default), otherwise a freshly created factory.

This keeps the default path allocation-free.

calls: [ObjectTypeAdapter.newFactory](r1-builtin-adapters.md#u-ea84a53752ea)

<a id="u-ea84a53752ea"></a>
### `ObjectTypeAdapter.newFactory`

`private static TypeAdapterFactory newFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L52-L54][f4]

Builds a TypeAdapterFactory for the given number strategy.

Its create() returns a new ObjectTypeAdapter bound to the supplied Gson and strategy when the requested raw type is exactly Object.class, and null otherwise, so the factory claims only statically-typed Object targets.

calls: [type-token-class](r1-type-model.md#u-55a9c25d6eea)

<a id="u-d55b0d86a0c2"></a>
### `ObjectTypeAdapter.read`

`@Override public Object read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L108-L167][f4]

Reads an arbitrary JSON value into plain Java objects: arrays become ArrayLists and objects become LinkedHashMaps (member order preserved).

It peeks; a non-container token is read via readTerminal. For a container it runs an iterative loop with a Deque stack: for each has-next member it reads the member name when current is a Map, peeks the value, nests (pushing current and descending) or reads a terminal, then stores the value via List.add or Map.put(name, value); when the container is exhausted it calls endArray()/endObject() and pops the parent, returning the root when the stack empties. Null values inside containers are represented as Java null.

calls: [ObjectTypeAdapter.tryBeginNesting](r1-builtin-adapters.md#u-6d26339c247e), [ObjectTypeAdapter.readTerminal](r1-builtin-adapters.md#u-9650c867d4f1)

**Uncertainties.**

- Whether read can be invoked in a state where peek() returns NAME/END_DOCUMENT is guarded only by the IllegalStateException in readTerminal.

<a id="u-9650c867d4f1"></a>
### `ObjectTypeAdapter.readTerminal`

`private Object readTerminal(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L91-L106][f4]

Reads one non-nested JSON value into a plain Java object: STRING yields the String from nextString(); NUMBER delegates to toNumberStrategy.readNumber(in), so the numeric result type follows the configured policy (Double by default); BOOLEAN yields the primitive boolean; NULL consumes the null and returns null.

Any other token — an invalid reader state — throws IllegalStateException("Unexpected token: " + peeked).

**Notes.**

- failure: IllegalStateException, not JsonSyntaxException, signals an unexpected token.

calls: [ToNumberStrategy.readNumber](r1-builtin-adapters.md#u-d277fc846eb5)

<a id="u-6d26339c247e"></a>
### `ObjectTypeAdapter.tryBeginNesting`

`private Object tryBeginNesting(JsonReader in, JsonToken peeked) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L77-L88][f4]

Begins reading a nested container if the peeked token is one: BEGIN_ARRAY calls in.beginArray() and returns a new ArrayList; BEGIN_OBJECT calls in.beginObject() and returns a new LinkedHashMap (preserving member order); any other token returns null without consuming, signaling a terminal value.

uses: [JsonReader.beginArray](r1-streaming-json.md#u-599a8f46d311)

<a id="u-b459182808db"></a>
### `ObjectTypeAdapter.write`

`@Override public void write(JsonWriter out, Object value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L169-L185][f4]

Serializes a runtime Object by looking up the adapter for value's actual class via gson.getAdapter(value.getClass()).

A null value writes a JSON null. If the resolved adapter is itself an ObjectTypeAdapter — meaning the runtime type still resolves to Object and no more specific adapter exists — it writes an empty JSON object (beginObject immediately followed by endObject) rather than recursing infinitely; otherwise it delegates to the resolved adapter's write.

**Notes.**

- failure: gson.getAdapter for an unserializable runtime class throws per Gson's adapter lookup; no fallback exists here.

calls: [Gson.getAdapter](r1-facade-api.md#u-276006924613)

**Uncertainties.**

- The empty-object convention for ObjectTypeAdapter-resolved values is a designed fallback; whether callers rely on it is not visible here.

<a id="u-d277fc846eb5"></a>
### `ToNumberStrategy.readNumber`

`Number readNumber(JsonReader in) throws IOException;` · [gson/src/main/java/com/google/gson/ToNumberStrategy.java:L69-L69][f5]

Strategy hook deciding how JSON numbers are deserialized when the target concrete type is Object or Number.

An implementation reads exactly one value from the given JsonReader and returns it as a Number; the contract guarantees the value is never null. It declares IOException because reading the stream can fail. Graph evidence shows NumberTypeAdapter.read and ObjectTypeAdapter.readTerminal delegate to this method, so custom strategies (e.g. ToNumberPolicy.BIG_DECIMAL or LONG_OR_DOUBLE) replace the defaults of Double for Object and lazily parsed numbers for Number, avoiding precision loss on arbitrary-length numbers.

uses: [NumberTypeAdapter.read](r1-builtin-adapters.md#u-d893742943b8), [ObjectTypeAdapter.readTerminal](r1-builtin-adapters.md#u-9650c867d4f1)

**Uncertainties.**

- Whether implementations may leave the reader positioned at another token is not specified in this interface.

<a id="u-097d6707d29c"></a>
### `IgnoreJRERequirement`

`@Retention(RetentionPolicy.CLASS) @Target({ElementType.METHOD, ElementType.CONSTRUCTO…` · [gson/src/main/java/com/google/gson/internal/bind/IgnoreJRERequirement.java:L8-L11][f6]

Package-private marker annotation with CLASS retention used to flag members with JRE-version requirements.

Its target list permits METHOD, CONSTRUCTOR, TYPE, and FIELD, so it can annotate almost any declaration. Retention is CLASS, meaning it is recorded in the class file but not visible at runtime via reflection.

**Uncertainties.**

- No consumers of this annotation appear in the supplied source, so its exact build-time effect is unknown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ToNumberStrategy.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/IgnoreJRERequirement.java