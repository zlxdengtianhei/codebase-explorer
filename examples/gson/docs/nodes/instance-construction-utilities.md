# Instance construction utilities

**Capability.** Produces object constructors for deserialization, from user InstanceCreators through no-args reflection to JDK Unsafe allocation, plus collection adapters.

This module decides how new instances are created during deserialization: the ConstructorConstructor strategy chain, special collection/map constructors, and the UnsafeAllocator fallback. It also contains the Collection TypeAdapterFactory and a null-rejecting list wrapper.

**Depends on.**

- [Reflection access filtering](reflection-access-filtering.md) · graph-confirmed · 2 edge(s) · Instance construction consults access filters to decide whether reflective instantiation is permitted.
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-only · 4 edge(s)
- [Reflection and record support](reflection-and-record-support.md) · graph-only · 4 edge(s)
- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Annotations and Module Declaration](annotations-and-module-declaration.md) · graph-only · 1 edge(s)

Parent: [Instance Creation and Access Control](instance-creation-and-access-control.md)

## Units (18)

<a id="u-0242bf44f46f"></a>
### `CollectionTypeAdapterFactory.java-collection-adapter`

`class Adapter<E> extends TypeAdapter<Collection<E>>` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L64-L65][f1]

Inner TypeAdapter that reads and writes homogeneous collections.

read returns null on a JSON null token; otherwise it constructs the collection via the injected ObjectConstructor (so the concrete Collection implementation comes from ConstructorConstructor, not hardcoded), then reads elements in a beginArray/hasNext loop with the element adapter, adding each, and ends the array. write emits nullValue for a null collection, else beginArray, each element through the (runtime-type-wrapping) element adapter, endArray. IOExceptions from reader/writer propagate; a constructor that fails would surface as whatever its construct() throws.

calls: [ObjectConstructor](../../catalog.json.gz)

<a id="u-8a5f211d80d7"></a>
### `CollectionTypeAdapterFactory.java-collectiontypeadapterfactory`

`class CollectionTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L34-L35][f1]

TypeAdapterFactory adapting Collection subtypes; create returns null if the requested raw type is not assignable to Collection.

Otherwise it resolves the element type via GsonTypes.getCollectionElementType, obtains the element adapter from Gson and wraps it in a TypeAdapterRuntimeTypeWrapper (so serialization can use runtime subtypes), and obtains a collection constructor from the injected ConstructorConstructor with allowUnsafe=false — deliberately refusing Unsafe-based construction because half-initialized collections could throw confusing exceptions on Collection methods. It returns an Adapter binding the wrapped element adapter and the constructor. The class holds only the ConstructorConstructor as state.

calls: [ConstructorConstructor.get](../../catalog.json.gz), [GsonTypes.getCollectionElementType](../../catalog.json.gz), [Gson.getAdapter](../../catalog.json.gz)

<a id="u-b616c0d60e92"></a>
### `ConstructorConstructor.java-constructor-lookup-entrypoints`

`public <T> ObjectConstructor<T> get(TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L92-L94][f2]

Select an ObjectConstructor for a type by trying strategies in fixed order: exact-type InstanceCreator, raw-type InstanceCreator, special JDK collection constructor, no-args default constructor (gated by ReflectionAccessFilterHelper.getFilterResult), default Collection/Map implementation, then fallbacks.

If the raw type is an interface or abstract class it returns a ThrowingObjectConstructor with checkInstantiable's message. If unsafe is disallowed by the caller (allowUnsafe=false) or the filter result is not ALLOW, it returns a ThrowingObjectConstructor whose message names the applicable remedy; otherwise it falls back to newUnsafeAllocator. The one-arg overload always permits Unsafe. Note the filter is consulted even when an InstanceCreator exists only indirectly: instance creators and special constructors bypass the filter entirely.

<a id="u-72c65d385325"></a>
### `ConstructorConstructor.java-constructorconstructor-and-instantiability-check`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L57-L66][f2]

Factory that produces ObjectConstructor instances for requested types, configured with user InstanceCreators, a JDK-Unsafe flag, and reflection access filters.

checkInstantiable returns null for instantiable classes; for interfaces it returns a message telling the user to register an InstanceCreator or TypeAdapter, and for abstract classes a message mentioning R8 configuration plus a troubleshooting URL, since R8 may strip default constructors and mark classes abstract.

<a id="u-0d89fbdde2ae"></a>
### `ConstructorConstructor.java-default-collection-and-map-implementations`

`private static <T> ObjectConstructor<T> newDefaultImplementationConstructor( Class<? …` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L288-L313][f2]

Provides constructors for common Collection and Map interface types that have public no-args constructors, deliberately after the no-args check so future JDK-internal constructors are not matched.

Dispatches on assignability: Collection goes to newCollectionConstructor, Map to newMapConstructor, otherwise null. newCollectionConstructor picks the first assignable implementation in order ArrayList, LinkedHashSet, TreeSet, ArrayDeque; newMapConstructor picks LinkedHashMap, TreeMap, ConcurrentHashMap, ConcurrentSkipListMap; each returns null when nothing matches, letting the caller try other means.

<a id="u-ef0870fe9651"></a>
### `ConstructorConstructor.java-instancecreatorconstructor`

`class InstanceCreatorConstructor<T> implements ObjectConstructor<T>` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L428-L429][f2]

ObjectConstructor delegating to a user-supplied InstanceCreator, passing the stored Type through to createInstance at construct time; the creator was matched by exact or raw type during lookup.

<a id="u-a5c373d68646"></a>
### `ConstructorConstructor.java-throwingobjectconstructor`

`class ThrowingObjectConstructor<T> implements ObjectConstructor<T>` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L411-L412][f2]

ObjectConstructor that always throws a JsonIOException built from a fixed message on each construct() call, deliberately creating a fresh exception each time to avoid retaining a long stack trace.

Returning this instead of null preserves backward compatibility and supports types that are serialized but never deserialized.

<a id="u-02c308ad1d1f"></a>
### `NonNullElementWrapperList.java-nonnullelementwrapperlist`

`class NonNullElementWrapperList<E> extends AbstractList<E> implements RandomAccess` · [gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java:L34-L36][f3]

List wrapper around an ArrayList that rejects null elements on insertion while delegating everything else, and overrides many AbstractList defaults purely for efficiency.

The constructor requires a non-null ArrayList (explicit type chosen to guarantee RandomAccess). set and add(int,E) route the element through nonNull, which throws NullPointerException with message "Element must be non-null" for null; this is the only null-enforcement point, so nulls already present in the delegate or entering via the constructor are not detected. All other methods—get, size, remove(int), remove(Object), clear, removeAll, retainAll, removeIf, contains, indexOf, lastIndexOf, both toArray overloads, sort, spliterator, equals, hashCode—delegate directly to the backing list; per the class doc, check-only methods like contains accept null arguments without throwing.

<a id="u-ce15003a3304"></a>
### `ObjectConstructor.java-objectconstructor`

`public interface ObjectConstructor<T>` · [gson/src/main/java/com/google/gson/internal/ObjectConstructor.java:L27-L30][f4]

Generic factory interface whose construct() returns a new default instance of T, used to create objects for population during deserialization.

The interface imposes no exception contract; behavior of implementations is outside this source.

<a id="u-1da05c5a2028"></a>
### `UnsafeAllocator.java-unsafeallocator-abstraction`

`class UnsafeAllocator` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L30-L31][f5]

Abstract base declaring newInstance(Class) which allocates an object without invoking any constructor and may throw Exception.

assertInstantiable is a safeguard reusing ConstructorConstructor.checkInstantiable; if the class is an interface or abstract it throws AssertionError, because using Unsafe on such classes could crash some JVMs. The static INSTANCE is built once by create().

<a id="u-7eae49037e99"></a>
### `UnsafeAllocator.java-unsafeallocator-platform-selection`

`public static final UnsafeAllocator INSTANCE = create();` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L46-L46][f5]

create() probes allocation strategies in order, each in a try/catch that swallows any Exception and moves on.

First sun.misc.Unsafe: reflectively reads the static theUnsafe field and binds allocateInstance. Second, post-gingerbread Dalvik: ObjectStreamClass.getConstructorId(Object.class) plus ObjectStreamClass.newInstance(Class, int). Third, pre-gingerbread Dalvik: ObjectInputStream.newInstance(Class, Class) with Object.class as constructor class. Each successful strategy returns an anonymous allocator whose newInstance first calls assertInstantiable and then reflectively invokes the platform method, propagating reflective failures as Exception. If all probes fail, the fallback allocator's newInstance throws UnsupportedOperationException stating that Unsafe is enabled but unusable and suggesting a runtime configuration fix.

<a id="u-f01c8b37d51e"></a>
### `InstanceCreator.createInstance`

`T createInstance(Type type);` · [gson/src/main/java/com/google/gson/InstanceCreator.java:L92-L92][f6]

Callback interface for constructing instances of types lacking a no-args constructor during deserialization; implementors return a newly created object of type T for the given Type, whose fields Gson will then overwrite with deserialized values.

Implementations must return a fresh instance, never a shared one, and are registered via GsonBuilder.registerTypeAdapter; ConstructorConstructor invokes them.

<a id="u-634e58111d7f"></a>
### `gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L400-L411][f2]

Class header for the ConstructorConstructor region containing newUnsafeAllocator and toString; the class itself is documented elsewhere, and these members have their own units.

<a id="u-5168f8be5011"></a>
### `gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:ConstructorConstructor (5)`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L94-L103][f2]

Class header declaring ConstructorConstructor, which produces ObjectConstructor instances for requested types using registered InstanceCreators, reflection filters, and optional JDK Unsafe.

<a id="u-4fd103a8db29"></a>
### `ConstructorConstructor.newDefaultConstructor`

`private static <T> ObjectConstructor<T> newDefaultConstructor( Class<? super T> rawTy…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L217-L285][f2]

Returns a constructor invoking the declared no-args constructor of rawType, or null/throwing variants.

Returns null if the class is abstract or has no declared no-args constructor. Accessibility: allowed if the filter result is ALLOW, or the constructor is accessible and (for BLOCK_ALL) public; otherwise returns a ThrowingObjectConstructor explaining the access restriction. When the filter allows, ReflectionHelper.tryMakeAccessible is attempted and its failure message becomes a ThrowingObjectConstructor. The returned lambda calls constructor.newInstance(), wrapping InstantiationException and InvocationTargetException (with its cause) in RuntimeException naming the constructor, and converting IllegalAccessException via ReflectionHelper.createExceptionForUnexpectedIllegalAccess.

<a id="u-c5a0a0dd1a6f"></a>
### `ConstructorConstructor.newSpecialCollectionConstructor`

`private static <T> ObjectConstructor<T> newSpecialCollectionConstructor( Type type, C…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L177-L215][f2]

Builds constructors for EnumSet subtypes and exactly EnumMap, which lack usable public no-args constructors.

For EnumSet it returns a lambda that, at construct time, requires the type to be a ParameterizedType whose first argument is a Class, then calls EnumSet.noneOf; otherwise it throws JsonIOException('Invalid EnumSet type: ...'). EnumMap is matched by exact class (not subtypes, since their constructor parameters may differ) and behaves analogously with new EnumMap. Returns null for all other types.

<a id="u-90054f28a20a"></a>
### `ConstructorConstructor.newUnsafeAllocator`

`private <T> ObjectConstructor<T> newUnsafeAllocator(Class<? super T> rawType)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L361-L395][f2]

Last-resort constructor using JDK Unsafe.

If useJdkUnsafe is true, returns a lambda calling UnsafeAllocator.INSTANCE.newInstance(rawType), wrapping any Exception in a RuntimeException suggesting an InstanceCreator, TypeAdapter, or no-args constructor. If false, returns a ThrowingObjectConstructor whose message explains Unsafe is disabled; when the class has zero declared constructors (an R8 artifact) the message is extended with advice to keep the no-args constructor in the R8 configuration.

<a id="u-6dd3d63a9e7a"></a>
### `gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:UnsafeAllocator`

`class UnsafeAllocator` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L31-L38][f5]

Class header for the UnsafeAllocator region containing the static INSTANCE field and the create() factory that selects an allocation strategy; those members have their own units.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ObjectConstructor.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/InstanceCreator.java
