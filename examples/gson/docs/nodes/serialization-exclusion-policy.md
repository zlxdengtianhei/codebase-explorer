# Serialization exclusion policy

**Capability.** Configures and applies exclusion strategies for fields and classes during serialization and deserialization.

Use when controlling which fields/classes Gson skips. Units show ExclusionStrategy callback, builder mutation, and Excluder field/class decisions.

**Depends on.**

- [Reflective adapter support](reflective-adapter-support.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Reflective adapter support](reflective-adapter-support.md) · graph-confirmed · 1 edge(s)

Parent: [Reflection and exclusion rules](reflection-and-exclusion-rules.md)

## Units (6)

<a id="u-5a965779dfcf"></a>
### `Excluder.java-class-exclusion-and-version-checks`

`public boolean excludeClass(Class<?> clazz, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L199-L234][f1]

Decides class exclusion and validates version annotations.

Version checking is skipped when the policy ignores versions; otherwise a class is excluded when its since/until annotations are invalid. Inner classes are excluded when inner-class serialization is disabled. For deserialization only, anonymous and non-static local classes are excluded unless they are enums. Any direction-specific strategy can also exclude the class. Since passes when the policy version is at least the annotation value; until passes when it is strictly less; absent annotations pass.

<a id="u-b21f5814d906"></a>
### `Excluder.java-configuration-and-cloning`

`class Excluder implements TypeAdapterFactory, Cloneable` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L49-L50][f1]

This configurable exclusion policy clones itself for each setting and decides which fields and classes are omitted.

Defaults ignore version checks, exclude transient/static fields, serialize inner classes, do not require expose annotations, and have empty strategy lists. Each with-style method clones and returns a new policy; modifier configuration replaces the mask with the OR of supplied bits, and strategy configuration appends to the selected serialization/deserialization list.

<a id="u-88bb999338ee"></a>
### `Excluder.java-exclusion-adapter`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L110-L128][f1]

Creates a type adapter only when at least one direction excludes the raw class; otherwise returns null.

The adapter lazily obtains a delegate through the enclosing factory and caches it in a volatile field. On read, if deserialization is excluded it skips the value and returns null; otherwise it delegates. On write, if serialization is excluded it writes null; otherwise it delegates.

<a id="u-751cf8a7f437"></a>
### `Excluder.java-field-exclusion`

`public boolean excludeField(Field field, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L158-L165][f1]

Decides field exclusion by short-circuit OR over modifier, version, synthetic, expose, declaring class, and strategy checks.

A field is excluded if any configured modifier bit is set; if version checking is enabled and its version annotations are invalid; if synthetic; if expose is required and the annotation is missing or the direction flag is false; if its type is excluded for that direction; or if any strategy for that direction says skip.

<a id="u-569a3dd65df7"></a>
### `ExclusionStrategy.java-exclusionstrategy`

`boolean shouldSkipField(FieldAttributes f);` · [gson/src/main/java/com/google/gson/ExclusionStrategy.java:L102-L102][f2]

Callback interface letting users decide whether a field or class is skipped during serialization or deserialization; implementors return true from shouldSkipField(FieldAttributes) or shouldSkipClass(Class<?>) to exclude the given target.

Gson's Excluder consults these methods when applying exclusion strategies registered on GsonBuilder.

<a id="u-397de774e5ee"></a>
### `GsonBuilder.java-exclusion-and-version-configuration`

`@CanIgnoreReturnValue public GsonBuilder setVersion(double version)` · [gson/src/main/java/com/google/gson/GsonBuilder.java:L204-L211][f3]

These methods mutate the builder's Excluder and return this.

- setVersion: NaN or negative throws IllegalArgumentException; otherwise replaces excluder with withVersion result.
- excludeFieldsWithModifiers: null array throws NPE; otherwise replaces excluder with withModifiers result.
- excludeFieldsWithoutExposeAnnotation: replaces excluder with excludeFieldsWithoutExposeAnnotation result.
- disableInnerClassSerialization: replaces excluder with disableInnerClassSerialization result.
- setExclusionStrategies: null array throws NPE; each strategy is added with withExclusionStrategy(strategy, true, true); null elements are not checked here.
- addSerializationExclusionStrategy: null strategy throws NPE; adds with withExclusionStrategy(strategy, true, false).
- addDeserializationExclusionStrategy: null strategy throws NPE; adds with withExclusionStrategy(strategy, false, true).
Strategies accumulate; existing strategies are not replaced.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Excluder.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ExclusionStrategy.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/GsonBuilder.java
