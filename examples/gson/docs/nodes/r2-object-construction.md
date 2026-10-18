# Object Construction Strategy

**Capability.** Selects, in strict priority order, how to instantiate a requested type: registered InstanceCreator, special collections (EnumSet/EnumMap), no-args constructor, JDK default implementations for Collection/Map interfaces, or a last-resort Unsafe allocation, with instantiability diagnostics.

Consult ConstructorConstructor.get to understand which constructor wins for a type and why. All adapter factories obtain their ObjectConstructors here, so changes to this priority order affect every binding path.

**Depends on.**

- [Public Contracts and Annotations](r2-public-api.md) · graph-confirmed · 1 edge(s) · ConstructorConstructor delegates instance creation to user-registered InstanceCreator implementations.
- [Exclusion and Reflection Policy](r1-reflection-policy.md) · graph-only · 6 edge(s)
- [Runtime Generic Type Model](r1-type-model.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Built-in Type Adapter Factories](r2-default-adapters.md) · graph-confirmed · 2 edge(s) · Collection, map, and @JsonAdapter factories create their container instances through ConstructorConstructor.get.
- [ReflectiveTypeAdapterFactory](r2-reflective-type-adapter-factory.md) · graph-confirmed · 1 edge(s) · ReflectiveTypeAdapterFactory obtains ObjectConstructors from ConstructorConstructor to instantiate target objects.
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) · graph-only · 2 edge(s)

Parent: [Gson JSON Library](r2-gson.md)

## Units (12)

<a id="u-7b2651c48b48"></a>
### `ConstructorConstructor`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L45-L50][f1]

Chooses and caches-free construction strategy for requested types, returning an ObjectConstructor selected among registered InstanceCreators, special collections, no-args constructors, JDK default implementations, or Unsafe.

The strategy inputs are fixed at construction time: the instanceCreators map, the useJdkUnsafe flag, and reflectionFilters; toString prints only instanceCreators. All lookup precedence and fallback logic lives in the two get methods; helper factories and the nested ThrowingObjectConstructor and InstanceCreatorConstructor supply the returned strategies.

uses: [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get](r2-object-construction.md#u-2b1d12b84c2c), [instancecreator-java](r2-public-api.md#u-f5d6aed7d6b2)

<a id="u-8f68b29ba616"></a>
### `ConstructorConstructor.checkInstantiable`

`static String checkInstantiable(Class<?> c)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L66-L89][f1]

Returns null if a class could in principle be allocated without a constructor, else a ready-to-use diagnostic message.

For an interface it returns a message advising an InstanceCreator or TypeAdapter. For an abstract class it returns a message mentioning R8 configuration plus a troubleshooting URL, because R8 optimizations can strip default constructors and mark classes abstract; per the inline comments this message is shown for all abstract classes, not only R8-processed ones. Any other class returns null.

**Notes.**

- contract: null return means instantiable; a non-null return is a complete exception message.

calls: [TroubleshootingGuide](r2-infrastructure.md#u-9bcd073a2728)

<a id="u-32e35d33a79d"></a>
### `ConstructorConstructor.get`

`public <T> ObjectConstructor<T> get(TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L92-L94][f1]

One-argument overload delegating to the two-argument get with allowUnsafe=true, so callers of this entry point permit the JDK-Unsafe fallback unless the instance-wide useJdkUnsafe flag disables it.

calls: [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get](r2-object-construction.md#u-2b1d12b84c2c)

<a id="u-2b1d12b84c2c"></a>
### `gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor.get`

`public <T> ObjectConstructor<T> get(TypeToken<T> typeToken, boolean allowUnsafe)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L103-L171][f1]

Resolves the construction strategy for a type in strict priority order, returning the first match.

(1) An InstanceCreator registered under the exact Type wins; then one registered under the raw Class. (2) A special EnumSet/EnumMap constructor is tried before no-args constructors, to avoid matching internal JDK constructors added in future versions. (3) A FilterResult is computed for the raw type via ReflectionAccessFilterHelper.getFilterResult, then a no-args-constructor constructor is attempted. (4) Default Collection/Map implementations are tried. (5) If checkInstantiable reports an interface or abstract class, a ThrowingObjectConstructor with that message is returned. (6) If allowUnsafe is false, a ThrowingObjectConstructor with a registration hint is returned. (7) If the filter result is not ALLOW, Unsafe counts as reflection and a ThrowingObjectConstructor explaining the filter restriction is returned. (8) Otherwise an Unsafe-based constructor is returned. Failures are deferred to construct() time; requesting a constructor almost never throws.

calls: [ReflectionAccessFilterHelper.getFilterResult](r1-reflection-policy.md#u-fb4c4e1a4f55), [ConstructorConstructor.newSpecialCollectionConstructor](r2-object-construction.md#u-c5a0a0dd1a6f), [ConstructorConstructor.newDefaultConstructor](r2-object-construction.md#u-4fd103a8db29), [ConstructorConstructor.newDefaultImplementationConstructor](r2-object-construction.md#u-64bce5de2b7e), [ConstructorConstructor.checkInstantiable](r2-object-construction.md#u-8f68b29ba616), [ConstructorConstructor.newUnsafeAllocator](r2-object-construction.md#u-90054f28a20a)

<a id="u-8cef222ae248"></a>
### `ConstructorConstructor.newCollectionConstructor`

`private static ObjectConstructor<? extends Collection<?>> newCollectionConstructor( C…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L315-L337][f1]

Picks a concrete Collection implementation whose no-args constructor the raw type can accept, in order ArrayList, LinkedHashSet, TreeSet, ArrayDeque; the first class the raw type is assignable from wins.

Returns null when none fits.

<a id="u-4fd103a8db29"></a>
### `ConstructorConstructor.newDefaultConstructor`

`private static <T> ObjectConstructor<T> newDefaultConstructor( Class<? super T> rawTy…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L217-L285][f1]

Wraps the no-args constructor of a concrete class.

Abstract classes return null immediately; a missing declared no-args constructor (NoSuchMethodException) also returns null. Accessibility is judged by filterResult: ALLOW always passes; otherwise the constructor must already be accessible, and for BLOCK_ALL it must additionally be public. If the filter forbids access, a ThrowingObjectConstructor with an explanatory message is returned. When ALLOW, ReflectionHelper.tryMakeAccessible is attempted and any message it returns becomes a ThrowingObjectConstructor. The successful wrapper calls constructor.newInstance(); InvocationTargetException is rethrown as RuntimeException carrying the constructor string and the cause; InstantiationException (deemed impossible after the abstract check) becomes a wrapping RuntimeException; IllegalAccessException is turned into an exception via ReflectionHelper.createExceptionForUnexpectedIllegalAccess.

calls: [ReflectionAccessFilterHelper.canAccess](r1-reflection-policy.md#u-862d5415c1c9), [ReflectionHelper.tryMakeAccessible](r1-reflection-policy.md#u-5492494e6fb9), [reflectionhelper-tostring-helpers](r1-reflection-policy.md#u-b5a5fd80dd89), [reflectionhelper-record-exception-factories](r1-reflection-policy.md#u-2a0f9c033ddd)

**Uncertainties.**

- Whether tryMakeAccessible can still fail for a constructor judged accessible under ALLOW is decided inside ReflectionHelper, outside this source.

<a id="u-64bce5de2b7e"></a>
### `ConstructorConstructor.newDefaultImplementationConstructor`

`private static <T> ObjectConstructor<T> newDefaultImplementationConstructor( Class<? …` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L288-L313][f1]

Provides constructors for common interface types by dispatching on the raw type: if it is assignable from Collection, the result of newCollectionConstructor is returned; else if assignable from Map, newMapConstructor; otherwise null.

Per the comment, only classes with public no-args constructors may be matched here, so special factory-built types such as EnumSet must be handled earlier by newSpecialCollectionConstructor.

calls: [ConstructorConstructor.newCollectionConstructor](r2-object-construction.md#u-8cef222ae248), [ConstructorConstructor.newMapConstructor](r2-object-construction.md#u-47e7e403f026)

<a id="u-47e7e403f026"></a>
### `ConstructorConstructor.newMapConstructor`

`private static ObjectConstructor<? extends Map<?, Object>> newMapConstructor(Class<?>…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L339-L359][f1]

Picks a concrete Map implementation whose no-args constructor the raw type can accept, in order LinkedHashMap, TreeMap, ConcurrentHashMap, ConcurrentSkipListMap; the first assignable match wins.

Returns null when none fits.

<a id="u-c5a0a0dd1a6f"></a>
### `ConstructorConstructor.newSpecialCollectionConstructor`

`private static <T> ObjectConstructor<T> newSpecialCollectionConstructor( Type type, C…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L177-L215][f1]

Builds constructors for EnumSet and EnumMap, which lack usable public no-args constructors.

For any EnumSet-assignable raw type, the returned constructor requires the type to be a ParameterizedType whose first argument is a Class, and yields EnumSet.noneOf(that class); otherwise construct() throws JsonIOException('Invalid EnumSet type'). EnumMap is handled only for the exact raw type (not subtypes, whose type parameters may have different meanings), with the same parameterization requirement, yielding new EnumMap(elementClass) or throwing JsonIOException. Returns null for all other types.

**Notes.**

- failure: The JsonIOException is thrown lazily inside construct(), not when the constructor is requested.

<a id="u-90054f28a20a"></a>
### `ConstructorConstructor.newUnsafeAllocator`

`private <T> ObjectConstructor<T> newUnsafeAllocator(Class<? super T> rawType)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L361-L395][f1]

Last-resort construction via JDK Unsafe.

If useJdkUnsafe is enabled, the returned constructor calls UnsafeAllocator.INSTANCE.newInstance(rawType) and wraps any Exception in a RuntimeException suggesting an InstanceCreator, TypeAdapter, or no-args constructor. If Unsafe is disabled, a ThrowingObjectConstructor carries a message saying Unsafe is disabled; additionally, when the class has zero declared constructors, an R8-specific hint about keeping the no-args constructor is appended.

calls: [UnsafeAllocator](r1-reflection-policy.md#u-ef1c93c904c0)

<a id="u-0776c7c04887"></a>
### `constructorconstructor-java-instance-creator-constructor`

`InstanceCreatorConstructor(InstanceCreator<T> instanceCreator, Type type)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L432-L435][f1]

ObjectConstructor backed by a user-registered InstanceCreator: construct() simply delegates to instanceCreator.createInstance(type), where type is the exact Type originally requested (which may differ from the key under which the creator was registered when a raw-type match was used).

Failure behavior is whatever the InstanceCreator itself does; nothing is caught or wrapped here. Members folded: constructor stores creator and type; construct performs the delegation.

calls: [instancecreator-java](r2-public-api.md#u-f5d6aed7d6b2)

<a id="u-2f547d61cbfb"></a>
### `constructorconstructor-java-throwing-object-constructor`

`ThrowingObjectConstructor(String exceptionMessage)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L414-L416][f1]

ObjectConstructor that always fails: construct() throws a new JsonIOException carrying the stored message.

The exception is created on every call to avoid retaining a long stack trace from construction time. Per the Javadoc, this preserves backward compatibility versus returning null (which would make callers pick another creation path) and supports serialize-only types whose runtime class is inaccessible. Members folded: the constructor stores the message; construct implements the throwing behavior.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java