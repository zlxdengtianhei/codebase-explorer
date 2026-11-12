# JsonElement tree base

**Capability.** Defines the abstract JSON tree element contract, subtype predicates/casts, and tree writing adapter.

Use for shared JsonElement behavior and tree serialization. Units show abstract root, unsupported base methods, subtype checks, and JsonElement writer.

**Depends on.**

- [Ordered JSON array](ordered-json-array.md) · graph-confirmed · 1 edge(s)
- [JSON primitive values](json-primitive-values.md) · graph-only · 2 edge(s)
- [Ordered JSON object map](ordered-json-object-map.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Map type adapter factory](map-type-adapter-factory.md) · graph-confirmed · 5 edge(s)
- [Ordered JSON array](ordered-json-array.md) · graph-confirmed · 1 edge(s)
- [Stream serialization helpers](stream-serialization-helpers.md) · graph-confirmed · 1 edge(s)
- [Gson builder configuration](gson-builder-configuration.md) · graph-only · 1 edge(s)
- [JSON writer formatting](json-writer-formatting.md) · graph-only · 1 edge(s)

Parent: [JSON element tree components](json-element-tree-components.md)

## Units (6)

<a id="u-f1d4d0260b25"></a>
### `JsonElement.java-jsonelement-class`

`class JsonElement` · [gson/src/main/java/com/google/gson/JsonElement.java:L96-L102][f1]

Abstract root of the JSON tree; concrete subclasses represent objects, arrays, primitives, and null.

It provides type predicates, checked casts, and default conversion methods that subclasses override, and it serializes to JSON through toString. Custom subclassing is deprecated; the public constructor exists only for backward compatibility.

<a id="u-9fbf8fc3f346"></a>
### `JsonElement.java-jsonelement-primitive-conversions`

`public boolean getAsBoolean()` · [gson/src/main/java/com/google/gson/JsonElement.java:L223-L225][f1]

The base implementations all throw UnsupportedOperationException using the runtime class's simple name.

Subclasses override these methods to provide actual conversions; the base class performs no parsing or fallback.

<a id="u-881adfafe2ed"></a>
### `JsonElement.java-jsonelement-type-checks`

`public boolean isJsonArray()` · [gson/src/main/java/com/google/gson/JsonElement.java:L118-L120][f1]

Each predicate returns true when this element is an instance of the corresponding subclass (JsonArray, JsonObject, JsonPrimitive, or JsonNull), and false otherwise.

They do not mutate state.

<a id="u-9b8ca9eef133"></a>
### `JsonElement.java-jsonelement-typed-casts`

`public JsonObject getAsJsonObject()` · [gson/src/main/java/com/google/gson/JsonElement.java:L159-L164][f1]

Each method returns this element cast to the requested subtype when the matching type predicate succeeds.

Otherwise it throws IllegalStateException with a message naming the expected JSON type and including this element's string form. No conversion is performed.

<a id="u-dbfeb1240183"></a>
### `JsonElement.deepCopy`

`public abstract JsonElement deepCopy();` · [gson/src/main/java/com/google/gson/JsonElement.java:L111-L111][f1]

Abstract contract requiring subclasses to return a deep copy of the element.

Immutable elements such as primitives and nulls are documented as not copied.

<a id="u-abc7bd1c85bd"></a>
### `JsonElementTypeAdapter.write`

`@Override public void write(JsonWriter out, JsonElement value) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java:L138-L170][f2]

Writes a JsonElement tree to a JsonWriter.

- null or JsonNull: writes nullValue.
- primitive number: writes getAsNumber.
- primitive boolean: writes getAsBoolean.
- other primitive: writes getAsString.
- array: begins an array, recursively writes each element, and ends the array.
- object: begins an object, writes each member name and recursively writes its value, and ends the object.
- other JsonElement subclass: throws IllegalArgumentException naming its class.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/JsonElement.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/JsonElementTypeAdapter.java
