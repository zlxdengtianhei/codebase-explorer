# gson: code map

Gson is a Java JSON library that provides serialization and deserialization through configuration, tree, streaming, reflection, and adapter APIs. Core configuration and adapters build configured Gson instances and default adapters; the tree model represents JSON in memory; streaming and tree reading parse tokens and JsonElement trees; serialization facade and writing expose conversion and output. Object binding, type resolution and enums, annotations, public utilities and dates, and Java time/SQL adapters divide the remaining binding, type, annotation, utility, and temporal work.

## Modules

- [**Core configuration and adapters**](nodes/core-configuration-and-adapters.md) — Configures Gson instances and supplies default adapters for common Java types. (98 units; `TypeAdapters.java`, `GsonBuilder.java`, `TypeAdapter.java`)
  - [**Gson setup and defaults**](nodes/gson-setup-and-defaults.md) — Builds configured Gson instances and provides default serialization adapters. (52 units; `GsonBuilder.java`, `ObjectTypeAdapter.java`, `DefaultDateTypeAdapter.java`)
    - [**Gson builder configuration**](nodes/gson-builder-configuration.md) — Accumulates Gson settings and registers custom tree/type adapters, producing configured Gson instances. (27 units; `GsonBuilder.java`, `TreeTypeAdapter.java`, `TypeAdapters.java`)
    - [**Core Gson default adapters**](nodes/core-gson-default-adapters.md) — Provides Gson entry point and default adapters for dates, numbers, Object values, and serialization delegation. (25 units; `GsonBuilder.java`, `ObjectTypeAdapter.java`, `DefaultDateTypeAdapter.java`)
  - [**Built-in Java type adapters**](nodes/built-in-java-type-adapters.md) — Provides foundational TypeAdapter implementations for Java scalars, atomics, conversion helpers, and strict floating-point values. (46 units; `TypeAdapters.java`, `TypeAdapter.java`)
    - [**Basic Java type adapters**](nodes/basic-java-type-adapters.md) — Defines TypeAdapter factories and adapters for common Java scalar, string, URL, UUID, and calendar types. (25 units; `TypeAdapters.java`)
    - [**Null-safe atomic adapters**](nodes/null-safe-atomic-adapters.md) — Wraps atomic, BitSet, Class, and Currency adapters to tolerate JSON null values. (10 units; `TypeAdapters.java`, `TypeAdapter.java`)
    - [**TypeAdapter conversion base**](nodes/typeadapter-conversion-base.md) — Defines abstract TypeAdapter conversion and convenience methods for writers, readers, strings, and trees. (8 units; `TypeAdapter.java`, `TypeAdapters.java`)
    - [**Strict floating-point adapters**](nodes/strict-floating-point-adapters.md) — Implements Double and Float adapters with strict validation rejecting NaN and infinite JSON values. (3 units; `TypeAdapters.java`)
- [**JSON tree model**](nodes/json-tree-model.md) — Represents and manipulates JSON as an in-memory tree of objects, arrays, primitives, and elements. (79 units; `LinkedTreeMap.java`, `JsonArray.java`, `JsonElement.java`)
  - [**JSON element tree components**](nodes/json-element-tree-components.md) — Implements JSON tree elements, array and map adapters, and stream helpers for tree serialization. (33 units; `JsonArray.java`, `JsonElement.java`, `MapTypeAdapterFactory.java`)
    - [**Ordered JSON array**](nodes/ordered-json-array.md) — Implements ordered JsonArray storage, access, mutation, equality, copying, and single-element conversions. (12 units; `JsonArray.java`)
    - [**Map type adapter factory**](nodes/map-type-adapter-factory.md) — Creates and operates TypeAdapters for Java Map types, including key adaptation and complex-key handling. (7 units; `MapTypeAdapterFactory.java`)
    - [**JsonElement tree base**](nodes/jsonelement-tree-base.md) — Defines the abstract JSON tree element contract, subtype predicates/casts, and tree writing adapter. (6 units; `JsonElement.java`, `JsonElementTypeAdapter.java`)
    - [**JsonElement tree adapter**](nodes/jsonelement-tree-adapter.md) — Reads and writes JsonElement trees through a singleton TypeAdapter, including nested arrays and objects. (4 units; `JsonElementTypeAdapter.java`)
    - [**Stream serialization helpers**](nodes/stream-serialization-helpers.md) — Provides stream adapters and helpers for serializing JsonElement trees and adapting readers/writers. (4 units; `Streams.java`, `JsonElement.java`, `JsonReaderInternalAccess.java`)
  - [**Primitive values and utilities**](nodes/primitive-values-and-utilities.md) — Supports JSON primitives and shared internal Java helpers used by tree-model code. (26 units; `JsonPrimitive.java`, `LazilyParsedNumber.java`, `Primitives.java`)
    - [**Internal Java utilities**](nodes/internal-java-utilities.md) — Groups internal helpers for Java version detection, lazy numbers, non-null lists, number limits, and date formats. (14 units; `LazilyParsedNumber.java`, `JavaVersion.java`, `PreJava9DateFormatProvider.java`)
    - [**JSON primitive values**](nodes/json-primitive-values.md) — Implements JsonPrimitive storage/conversion/equality and static primitive-wrapper identity utilities. (12 units; `JsonPrimitive.java`, `Primitives.java`)
  - [**Ordered JSON object map**](nodes/ordered-json-object-map.md) — Implements ordered JsonObject members and the insertion-ordered AVL-backed LinkedTreeMap used for storage. (20 units; `LinkedTreeMap.java`, `JsonObject.java`)
- [**Streaming and tree reading**](nodes/streaming-and-tree-reading.md) — Reads JSON from streams and JsonElement trees with token navigation and validation. (68 units; `JsonReader.java`, `JsonTreeReader.java`)
  - [**Streaming JSON reader internals**](nodes/streaming-json-reader-internals.md) — Implements low-level streaming JSON reading, token scanning, scalar consumption, and structure navigation. (44 units; `JsonReader.java`)
    - [**Streaming JSON reader core**](nodes/streaming-json-reader-core.md) — Implements streaming JSON reader state, token queries, nesting limits, paths, and diagnostics. (14 units; `JsonReader.java`)
    - [**JSON token scanning**](nodes/json-token-scanning.md) — Scans JSON input for tokens, literals, numbers, comments, escapes, and malformed-input errors. (12 units; `JsonReader.java`)
    - [**JSON value consumption**](nodes/json-value-consumption.md) — Consumes JSON scalar values, property names, strings, and unquoted values with strict validation. (12 units; `JsonReader.java`)
    - [**JSON structure navigation**](nodes/json-structure-navigation.md) — Consumes array/object structure tokens and skips nested values while maintaining reader scopes. (6 units; `JsonReader.java`)
  - [**JsonElement tree reader**](nodes/jsonelement-tree-reader.md) — Implements JsonReader over JsonElement trees, including token navigation, paths, skipping, and validation. (24 units; `JsonTreeReader.java`)
- [**Serialization facade and writing**](nodes/serialization-facade-and-writing.md) — Exposes Gson serialization and deserialization entry points and implements streaming JSON writing and formatting. (55 units; `Gson.java`, `JsonWriter.java`, `JsonTreeWriter.java`)
  - [**JSON writer formatting**](nodes/json-writer-formatting.md) — Implements streaming JSON writing, tree writing, formatting styles, escaping, and writer state handling. (28 units; `JsonWriter.java`, `JsonTreeWriter.java`, `FormattingStyle.java`)
  - [**Gson serialization facade**](nodes/gson-serialization-facade.md) — Provides Gson serialization/deserialization entry points, adapter lookup, reader/writer creation, and configuration round-tripping. (27 units; `Gson.java`, `JsonReader.java`, `JsonWriter.java`)
- [**Object binding adapters**](nodes/object-binding-adapters.md) — Builds adapters that construct and bind Java objects, including collections and reflective fields. (55 units; `ReflectiveTypeAdapterFactory.java`, `ConstructorConstructor.java`, `ReflectionHelper.java`)
  - [**Reflection and exclusion rules**](nodes/reflection-and-exclusion-rules.md) — Creates reflection-based adapters and applies field and class exclusion policies during binding. (33 units; `ReflectiveTypeAdapterFactory.java`, `ReflectionHelper.java`, `Excluder.java`)
    - [**Reflective adapter support**](nodes/reflective-adapter-support.md) — Builds reflection-based adapters and applies field naming, exclusion, accessibility, and reflection filters. (27 units; `ReflectiveTypeAdapterFactory.java`, `ReflectionHelper.java`, `ReflectionAccessFilterHelper.java`)
    - [**Serialization exclusion policy**](nodes/serialization-exclusion-policy.md) — Configures and applies exclusion strategies for fields and classes during serialization and deserialization. (6 units; `Excluder.java`, `GsonBuilder.java`, `ExclusionStrategy.java`)
  - [**Object construction adapters**](nodes/object-construction-adapters.md) — Selects object constructors and implements collection adapters for deserialization and serialization. (22 units; `ConstructorConstructor.java`, `UnsafeAllocator.java`, `CollectionTypeAdapterFactory.java`)
- [**Type resolution and enums**](nodes/type-resolution-and-enums.md) — Resolves generic Java types and selects runtime adapters for enums and type hierarchies. (36 units; `GsonTypes.java`, `TypeToken.java`, `EnumTypeAdapter.java`)
  - [**Generic type reflection**](nodes/generic-type-reflection.md) — Resolves, represents, compares, and adapts generic Java types, arrays, and TypeToken assignability. (27 units; `GsonTypes.java`, `TypeToken.java`, `ArrayTypeAdapter.java`)
  - [**Enum runtime adapter selection**](nodes/enum-runtime-adapter-selection.md) — Implements enum adapters and runtime type adapter selection for serialization. (9 units; `EnumTypeAdapter.java`, `TypeAdapterRuntimeTypeWrapper.java`)
- [**Public utilities and dates**](nodes/public-utilities-and-dates.md) — Provides public API helper types and ISO-8601 date formatting and parsing utilities. (25 units; `ISO8601Utils.java`, `FieldAttributes.java`, `JsonParser.java`)
  - [**Public API utility classes**](nodes/public-api-utility-classes.md) — Provides public API helpers and types for fields, naming, parsing, contexts, exceptions, strictness, and factories. (21 units; `FieldAttributes.java`, `JsonParser.java`, `JsonStreamParser.java`)
  - [**ISO-8601 date utility**](nodes/iso-8601-date-utility.md) — Formats and parses ISO-8601 dates with UTC defaults and ParsePosition-aware parsing. (4 units; `ISO8601Utils.java`)
- [**Gson annotation adapter support**](nodes/gson-annotation-adapter-support.md) — Defines Gson runtime annotations and resolves @JsonAdapter annotations into type adapter factories. (13 units; `JsonAdapterAnnotationTypeAdapterFactory.java`, `JsonAdapter.java`, `SerializedName.java`)
- [**Java time and SQL adapters**](nodes/java-time-and-sql-adapters.md) — Provides TypeAdapter factories and adapters for java.time and java.sql date/time values. (13 units; `JavaTimeTypeAdapters.java`, `SqlTypesSupport.java`, `SqlDateTypeAdapter.java`)

## Key flows

- **Tree reader navigation**: JsonTreeReader navigates container tokens and uses stack helpers to track traversal state. — `JsonTreeReader.java-container-navigation` → `JsonTreeReader.java-stack-helpers`
- **Tree writer array emission**: JsonTreeWriter value methods use put-and-peek and JsonArray add overloads to append array values. — `JsonTreeWriter.java-value-methods` → `JsonTreeWriter.java-put-and-peek` → `JsonArray.java-jsonarray-add-overloads`
- **Generic type canonicalization**: Parameterized type handling uses GsonTypes construction and canonicalization to represent generic types. — `GsonTypes.java-parameterized-type-implementation` → `GsonTypes.java-type-construction-and-canonicalization`
- **Quoted value skipping**: Recursive skipping delegates quoted values to skipQuotedValue and refills the reader buffer as needed. — `JsonReader.java-recursive-value-skipper` → `JsonReader.skipQuotedValue` → `JsonReader.java-buffer-refill`
- **Unquoted value skipping**: Recursive skipping delegates unquoted values to skipUnquotedValue and refills the reader buffer as needed. — `JsonReader.java-recursive-value-skipper` → `JsonReader.skipUnquotedValue` → `JsonReader.java-buffer-refill`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
