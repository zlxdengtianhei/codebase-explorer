# Enum, Number Policy, Runtime Dispatch

**Capability.** Implements enum adapters, number-deserialization strategies, and runtime-type-based serialization delegation for Object values.

Come here for reflective enum name mapping, ToNumberPolicy choices, and the adapter that picks serializers by runtime type. The module also contains the marker interface for adapters that serialize through a different delegate.

**Depends on.**

- [Adapter Abstractions and Dates](adapter-abstractions-and-dates.md) · graph-confirmed · 1 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Adapter Configuration and Policies](adapter-configuration-and-policies.md) · graph-confirmed · 1 edge(s)

Parent: [Type Adapter Framework](type-adapter-framework.md)

## Units (16)

<a id="u-0f392bfc0543"></a>
### `EnumTypeAdapter.java-enumtypeadapter-constructor-and-maps`

`class EnumTypeAdapter<T extends Enum<T>> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L50-L56][f1]

Reflectively builds three lookup maps for one enum class: nameToConstant and stringToConstant (String→constant) and constantToName (constant→serialized name).

It filters declared fields to enum constants by compacting the array in place, sizes the HashMaps with calculateHashMapCapacity (ceil(n/0.75), mirroring Java 19's HashMap.newHashMap) to avoid resizing, makes the fields accessible, and for each constant reads its value, name(), and toString(). A @SerializedName annotation overrides the serialized name and registers each alternate spelling in nameToConstant; toString() is always registered in stringToConstant. IllegalAccessException is converted to AssertionError on the assumption it cannot occur after setAccessible. HashMap (not EnumMap) is used deliberately to survive ProGuard/R8 obfuscation.

**Notes.**

- side_effect: Constructor mutates the fields array in place during filtering and calls setAccessible on the constant fields.

**Uncertainties.**

- Behavior when two constants share a @SerializedName value or alternate is not resolved here; later map entries overwrite earlier ones, but which constant wins depends on getDeclaredFields order.

<a id="u-488a3d6c3c86"></a>
### `EnumTypeAdapter.java-enumtypeadapter-factory`

`class EnumTypeAdapter<T extends Enum<T>> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L35-L38][f1]

Package-private factory that only handles enum types, excluding java.lang.Enum itself: create returns null when the raw type is not assignable to Enum or is exactly Enum.class.

If the raw type is not isEnum() (anonymous enum subclasses), it walks up to the superclass to get the real enum class, then builds an EnumTypeAdapter for it. The adapter construction performs the reflective scan described in the constructor unit, so factory failures there (AssertionError on IllegalAccessException) propagate to callers of create.

calls: [TypeToken.getRawType](../../catalog.json)

<a id="u-da7109b1f413"></a>
### `ObjectTypeAdapter.java-objecttypeadapter-nesting-terminal-helpers`

`class ObjectTypeAdapter extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L71-L77][f2]

tryBeginNesting consumes BEGIN_ARRAY/BEGIN_OBJECT and returns a new ArrayList or LinkedHashMap respectively, or null for other tokens.

readTerminal maps STRING→String, NUMBER→toNumberStrategy.readNumber(in) (so numbers become Double under the default policy), BOOLEAN→Boolean, NULL→null with the token consumed; any other token throws IllegalStateException("Unexpected token: ..."), reachable only with a reader in an invalid state.

calls: [ToNumberStrategy.readNumber](../../catalog.json)

<a id="u-32e175f2ca0e"></a>
### `SerializationDelegatingTypeAdapter.java-serializationdelegatingtypeadapter`

`class SerializationDelegatingTypeAdapter<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java:L22-L27][f3]

Abstract marker extending TypeAdapter for adapters that may serialize through a different adapter than themselves.

It declares the single abstract method getSerializationDelegate(), which returns the adapter to use for serialization — possibly this, possibly another adapter, which may itself be another SerializationDelegatingTypeAdapter. It adds no behavior; subclasses define the delegation.

<a id="u-096210813d42"></a>
### `ToNumberPolicy.java-long-or-double-policy`

`@Override public Number readNumber(JsonReader in) throws IOException, JsonParseException` · [gson/src/main/java/com/google/gson/ToNumberPolicy.java:L70-L82][f4]

Policy that reads a JSON number as Long when parseable as such, otherwise as Double.

It takes the raw string: if it contains '.', it goes straight to parseAsDouble; otherwise it tries Long.parseLong and falls back to parseAsDouble on NumberFormatException. parseAsDouble uses Double.valueOf; if the result is infinite or NaN and the reader is not lenient, it throws MalformedJsonException (JSON forbids these), and if the string is not parseable at all it throws JsonParseException with the reader's previous path.

<a id="u-3a2f35513b80"></a>
### `ToNumberPolicy.java-simple-tonumberpolicy-constants`

`@Override public Double readNumber(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/ToNumberPolicy.java:L43-L46][f4]

Enum constants implementing ToNumberStrategy for number deserialization.

DOUBLE reads via JsonReader.nextDouble(); LAZILY_PARSED_NUMBER wraps the raw string in a LazilyParsedNumber (default for numbers as Number); BIG_DECIMAL parses the string with NumberLimits.parseBigDecimal, converting NumberFormatException to JsonParseException including the reader's previous path.

<a id="u-a79129b42799"></a>
### `TypeAdapterRuntimeTypeWrapper.java-typeadapterruntimetypewrapper`

`class TypeAdapterRuntimeTypeWrapper<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L28-L29][f5]

TypeAdapter that delegates reads unchanged but chooses the serialization adapter based on the value's runtime type; it stores the Gson context, the declared-type delegate adapter, and the declared Type.

<a id="u-8f072830d6e7"></a>
### `TypeAdapterRuntimeTypeWrapper.java-typeadapterruntimetypewrapper-2`

`class TypeAdapterRuntimeTypeWrapper<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L78-L85][f5]

Reports whether an adapter is (or ultimately delegates to, through SerializationDelegatingTypeAdapter chains) a ReflectiveTypeAdapterFactory.Adapter; the unwinding loop stops when a delegating adapter returns itself.

<a id="u-4009961af4ef"></a>
### `TypeAdapterRuntimeTypeWrapper.java-typeadapterruntimetypewrapper-3`

`class TypeAdapterRuntimeTypeWrapper<T> extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L100-L103][f5]

Returns the type to use for adapter selection: the declared type for a null value; for a wildcard, the decision uses its upper bound but a parameterized bound keeps the declared type (runtime class would lose type arguments); if the effective declared type is a Class or TypeVariable it returns value.getClass() (the more specific runtime class); otherwise (e.g. parameterized types) it returns the declared type unchanged.

<a id="u-d277fc846eb5"></a>
### `ToNumberStrategy.readNumber`

`Number readNumber(JsonReader in) throws IOException;` · [gson/src/main/java/com/google/gson/ToNumberStrategy.java:L69-L69][f6]

Strategy interface controlling how numbers are deserialized for Object and Number targets when the concrete numeric type is unknown, used by GsonBuilder's object/number-to-number strategy settings.

readNumber(JsonReader) must consume a single value from the reader and never return null; it may throw IOException. The class Javadoc notes the default policies (Double for Object, lazily parsed numbers for Number) can lose precision, and points to LONG_OR_DOUBLE or BIG_DECIMAL policies to avoid it.

<a id="u-68637a954b9c"></a>
### `EnumTypeAdapter.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L113-L123][f1]

Deserializes a JSON string to an enum constant.

A JSON null yields null (token consumed). Otherwise it looks the string up first in nameToConstant (covering constant names, @SerializedName values, and alternates); if absent, it falls back to stringToConstant (constant toString() values); an unknown string returns null rather than throwing.

<a id="u-1e88a24ca68f"></a>
### `EnumTypeAdapter.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java:L125-L128][f1]

Serializes an enum constant by writing its registered name (constant name or @SerializedName value) via out.value; a null value writes a JSON null.

Constants missing from constantToName would write null, though in practice every constant is registered by the constructor.

<a id="u-d55b0d86a0c2"></a>
### `ObjectTypeAdapter.read`

`@Override public Object read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L108-L167][f2]

Reads any JSON value into plain Java objects: Strings, Booleans, strategy-chosen Numbers, null, ArrayList for arrays, and LinkedHashMap for objects (preserving member order).

A top-level terminal is returned directly via readTerminal. For containers it uses an explicit Deque loop: while hasNext, a Map reads the member name (Lists skip it), the child comes from tryBeginNesting or readTerminal, is appended to the current List or put into the current Map, and nesting pushes the current container and descends. On exhausting a level it ends the array/object, then returns the root or pops the enclosing container. Reader IOExceptions propagate; the only thrown exception is readTerminal's IllegalStateException on invalid reader state.

<a id="u-b459182808db"></a>
### `ObjectTypeAdapter.write`

`@Override public void write(JsonWriter out, Object value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L169-L185][f2]

Serializes an Object by looking up an adapter for its runtime class via gson.getAdapter and delegating.

A null value writes nullValue. If the resolved adapter is itself an ObjectTypeAdapter (no more specific type exists), it writes an empty JSON object (beginObject/endObject) rather than failing — an Object with no fields serializes as {}. Otherwise the delegate adapter writes the value, so actual runtime types (String, Number, collections, beans) serialize with their specific adapters. getAdapter failures and delegate IOExceptions propagate.

calls: [Gson.getAdapter](../../catalog.json)

<a id="u-1c46fb4e1917"></a>
### `TypeAdapterRuntimeTypeWrapper.read`

`@Override public T read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L39-L42][f5]

Read is a pure pass-through to the delegate adapter; runtime-type logic applies only to writing.

<a id="u-283e3401a504"></a>
### `TypeAdapterRuntimeTypeWrapper.write`

`@Override public void write(JsonWriter out, T value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java:L44-L78][f5]

Chooses the write adapter by preference: adapter registered for the runtime type, then the declared-type delegate, then the reflective adapter for the runtime type, then the reflective adapter for the declared type.

Concretely: if getRuntimeTypeIfMoreSpecific returns a different type, it fetches the runtime-type adapter; if that adapter is not a ReflectiveTypeAdapterFactory.Adapter the user registered it, so it wins; otherwise if the delegate is not itself reflective (per isReflective) the user's declared-type adapter wins; otherwise the runtime-type reflective adapter is used. If the runtime type equals the declared type the delegate writes directly.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/EnumTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/SerializationDelegatingTypeAdapter.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ToNumberPolicy.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapterRuntimeTypeWrapper.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ToNumberStrategy.java
