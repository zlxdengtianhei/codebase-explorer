# Number and Object Adapters

**Capability.** Implements adapters for java.lang.Number via an injected ToNumberStrategy and for statically-typed Object values.

Come here to see how untyped JSON values become Java Numbers or generic Objects. The Number adapter delegates the concrete numeric type choice to a strategy; the Object adapter dispatches on runtime class for serialization.

**Depends on.**

- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Gson Configuration Assembly](gson-configuration-assembly.md) · graph-confirmed · 2 edge(s)

Parent: [Built-in Adapter Implementations](built-in-adapter-implementations.md)

## Units (3)

<a id="u-48c53b5a61ab"></a>
### `NumberTypeAdapter.java-numbertypeadapter-class-and-factories`

`class NumberTypeAdapter extends TypeAdapter<Number>` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L32-L34][f1]

TypeAdapter for java.lang.Number that converts JSON numbers according to an injected ToNumberStrategy.

The class is private-constructed; newFactory(strategy) builds a factory whose create returns the single shared adapter when the requested raw type is exactly Number.class, else null. getFactory(strategy) returns a cached LAZILY_PARSED_NUMBER_FACTORY when the strategy is ToNumberPolicy.LAZILY_PARSED_NUMBER (Gson's default), otherwise builds a fresh factory — so callers get a shared instance for the default policy only.

uses: [ToNumberPolicy.LAZILY_PARSED_NUMBER](../../catalog.json.gz)

<a id="u-ee6fafc57c86"></a>
### `NumberTypeAdapter.java-numbertypeadapter-read-write`

`public static TypeAdapterFactory getFactory(ToNumberStrategy toNumberStrategy)` · [gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java:L54-L60][f1]

read peeks the token: NULL consumes it and returns null; NUMBER or STRING delegates to toNumberStrategy.readNumber(in), so the concrete Number subclass (e.g. LazilyParsedNumber vs Double) depends on the strategy; any other token throws JsonSyntaxException naming the token and the reader path.

write simply calls out.value(value), passing null through to the writer.

calls: [ToNumberStrategy.readNumber](../../catalog.json.gz)

<a id="u-5918ab461bc5"></a>
### `ObjectTypeAdapter.java-objecttypeadapter-class-and-factories`

`class ObjectTypeAdapter extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java:L40-L42][f2]

TypeAdapter for statically-typed Object values: deserialization yields primitives, List, or Map; serialization uses the runtime class.

newFactory(strategy) returns a factory whose create matches only raw type Object.class, producing a fresh ObjectTypeAdapter per call with the Gson instance and the number strategy. getFactory(strategy) returns the cached DOUBLE_FACTORY for ToNumberPolicy.DOUBLE (Gson's default) and otherwise a new factory. The adapter holds the Gson instance (for write delegation) and the strategy (for number terminals).

uses: [ToNumberPolicy.DOUBLE](../../catalog.json.gz)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/NumberTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ObjectTypeAdapter.java
