# Object construction adapters

**Capability.** Selects object constructors and implements collection adapters for deserialization and serialization.

Use for instance creation and collection adapter behavior. Units show ConstructorConstructor strategies, Unsafe allocation, InstanceCreator, and collection read/write.

**Depends on.**

- [Reflection and exclusion rules](reflection-and-exclusion-rules.md) · graph-confirmed · 7 edge(s)
- [Reflective adapter support](reflective-adapter-support.md) · graph-only · 7 edge(s)
- [Generic type reflection](generic-type-reflection.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Reflection and exclusion rules](reflection-and-exclusion-rules.md) · graph-confirmed · 1 edge(s)
- [Gson annotation adapter support](gson-annotation-adapter-support.md) · graph-only · 1 edge(s)

Parent: [Object binding adapters](object-binding-adapters.md)

## Units (22)

<a id="u-d04516e48b09"></a>
### `CollectionTypeAdapterFactory.java-collectiontypeadapterfactory-adapter-class-and-constructor`

`class Adapter<E> extends TypeAdapter<Collection<E>>` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L64-L65][f1]

The nested Adapter is a TypeAdapter for a concrete collection type, holding the element adapter and the object constructor used to create empty collections.

Its constructor only stores those two collaborators; read and write are separate.

<a id="u-41bb48ac8640"></a>
### `CollectionTypeAdapterFactory.java-collectiontypeadapterfactory-class-and-constructor`

`class CollectionTypeAdapterFactory implements TypeAdapterFactory` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L34-L35][f1]

CollectionTypeAdapterFactory is a TypeAdapterFactory for Collection types that stores a ConstructorConstructor used to instantiate collections during deserialization.

The constructor only retains that collaborator; adapter creation is handled separately.

<a id="u-b616c0d60e92"></a>
### `ConstructorConstructor.java-constructor-lookup-entrypoints`

`public <T> ObjectConstructor<T> get(TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L92-L94][f2]

Selects an ObjectConstructor for a requested type, preferring registered instance creators and then special/default/unsafe strategies.

The single-argument entrypoint delegates with Unsafe allowed. Exact-type and raw-type instance creators return before any reflection filter is computed, so those creators bypass the filter. A special EnumSet/EnumMap constructor is tried next, also before filter computation. Only then is the filter result obtained and passed to the no-args constructor lookup. If no no-args constructor is found, default Collection/Map implementations are tried before the instantiable check, so Collection/Map interfaces and abstract collection/map types can still succeed. If the type is non-instantiable, a throwing constructor is returned. If Unsafe is disallowed by the caller, a throwing constructor is returned. If the filter result is not ALLOW, a throwing constructor is returned. Otherwise an Unsafe allocator is returned.

<a id="u-348274cb92eb"></a>
### `ConstructorConstructor.java-constructor-registry`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L45-L46][f2]

Holds the instance-creator map, JDK-Unsafe flag, and reflection filters used to choose object constructors; the constructor stores these dependencies and toString exposes the creator map.

No validation or defensive copying is performed.

<a id="u-fea829b5853c"></a>
### `ConstructorConstructor.java-constructorconstructor-class`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L57-L66][f2]

Factory for ObjectConstructor instances configured with instance creators, a JDK-Unsafe flag, and reflection access filters.

It selects a construction strategy for a requested TypeToken, returning a constructor that delegates to an InstanceCreator, creates special or default collection/map implementations, invokes a no-args constructor, uses Unsafe, or throws a JsonIOException with a diagnostic message.

<a id="u-52fbcd1d8c31"></a>
### `ConstructorConstructor.java-instance-creator-constructor`

`class InstanceCreatorConstructor<T> implements ObjectConstructor<T>` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L428-L429][f2]

Adapts a registered InstanceCreator into an ObjectConstructor by storing the creator and requested type.

Construction delegates directly to the creator with the stored type; it does not catch or wrap exceptions.

<a id="u-e7638931c97e"></a>
### `ConstructorConstructor.java-throwing-object-constructor`

`class ConstructorConstructor` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L400-L411][f2]

Stores a failure message and throws a fresh JsonIOException on every construction attempt.

The constructor only stores the message; construct creates a new exception each time to avoid retaining a potentially long stack trace.

<a id="u-ce15003a3304"></a>
### `ObjectConstructor.java-objectconstructor`

`public interface ObjectConstructor<T>` · [gson/src/main/java/com/google/gson/internal/ObjectConstructor.java:L27-L30][f3]

Defines a factory contract for constructing a default instance of a class, typically for object navigation during deserialization.

construct returns a new instance; the interface itself imposes no null or exception behavior.

<a id="u-33c637fa670c"></a>
### `UnsafeAllocator.java-unsafe-allocation-strategy-fallback`

`private static UnsafeAllocator create()` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L48-L60][f4]

Builds the singleton allocator by trying reflective allocation strategies in order and falling back to an always-throwing allocator.

It first tries sun.misc.Unsafe via the theUnsafe field and allocateInstance. If any Exception occurs, it tries ObjectStreamClass getConstructorId and newInstance. If that fails, it tries ObjectInputStream newInstance. Each successful strategy returns an allocator whose newInstance first asserts instantiable and then invokes the reflective method; exceptions propagate. The final fallback throws UnsupportedOperationException with a configuration message.

**Uncertainties.**

- The runtime availability of the reflective Unsafe/ObjectStreamClass/ObjectInputStream members is not established by this source; the factory only shows that any Exception causes fallback to the next strategy.

<a id="u-b0011d4eea01"></a>
### `UnsafeAllocator.java-unsafe-allocator-base`

`class UnsafeAllocator` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L30-L31][f4]

Abstract allocator that creates instances without invoking constructors; subclasses implement the actual allocation strategy.

The abstract newInstance is the strategy hook. The instantiable assertion calls the constructor registry's instantiable check and throws AssertionError when that check returns a message. The singleton instance is initialized by the factory.

<a id="u-f01c8b37d51e"></a>
### `InstanceCreator.createInstance`

`T createInstance(Type type);` · [gson/src/main/java/com/google/gson/InstanceCreator.java:L92-L92][f5]

Callback interface for constructing instances of types lacking a no-args constructor during deserialization; implementors return a newly created object of type T for the given Type, whose fields Gson will then overwrite with deserialized values.

Implementations must return a fresh instance, never a shared one, and are registered via GsonBuilder.registerTypeAdapter; ConstructorConstructor invokes them.

<a id="u-8f68b29ba616"></a>
### `ConstructorConstructor.checkInstantiable`

`static String checkInstantiable(Class<?> c)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L66-L89][f2]

Returns null when a class is instantiable, otherwise an explanatory message for interfaces or abstract classes.

Interfaces get a message asking for an InstanceCreator or TypeAdapter; abstract classes get an R8-oriented message with a troubleshooting URL. It does not throw.

<a id="u-8cef222ae248"></a>
### `ConstructorConstructor.newCollectionConstructor`

`private static ObjectConstructor<? extends Collection<?>> newCollectionConstructor( C…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L315-L337][f2]

Chooses a concrete collection implementation assignable from the raw type, in fixed preference order.

It returns ArrayList, LinkedHashSet, TreeSet, or ArrayDeque constructors when the raw type is assignable from that implementation; otherwise it returns null.

<a id="u-4fd103a8db29"></a>
### `ConstructorConstructor.newDefaultConstructor`

`private static <T> ObjectConstructor<T> newDefaultConstructor( Class<? super T> rawTy…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L217-L285][f2]

Builds a no-args reflective constructor when the raw type is concrete and declares one, subject to reflection-filter access rules.

Abstract types and types without a declared no-args constructor return null. Access is allowed when the filter is ALLOW, or when the constructor is accessible and either the filter is not BLOCK_ALL or the constructor is public. If access is denied, a throwing constructor is returned. With ALLOW, it tries to make the constructor accessible and returns a throwing constructor if that fails. The returned constructor invokes newInstance; InstantiationException and InvocationTargetException become RuntimeException, and IllegalAccessException is converted by the reflection helper.

<a id="u-64bce5de2b7e"></a>
### `ConstructorConstructor.newDefaultImplementationConstructor`

`private static <T> ObjectConstructor<T> newDefaultImplementationConstructor( Class<? …` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L288-L313][f2]

Returns default collection or map implementations for Collection/Map raw types, or null when neither applies.

Collection-assignable types use the collection constructor lookup; Map-assignable types use the map constructor lookup. This can handle interfaces and abstract collection/map types before the instantiable check.

<a id="u-47e7e403f026"></a>
### `ConstructorConstructor.newMapConstructor`

`private static ObjectConstructor<? extends Map<?, Object>> newMapConstructor(Class<?>…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L339-L359][f2]

Chooses a concrete map implementation assignable from the raw type, in fixed preference order.

It returns LinkedHashMap, TreeMap, ConcurrentHashMap, or ConcurrentSkipListMap constructors when the raw type is assignable from that implementation; otherwise it returns null.

<a id="u-c5a0a0dd1a6f"></a>
### `ConstructorConstructor.newSpecialCollectionConstructor`

`private static <T> ObjectConstructor<T> newSpecialCollectionConstructor( Type type, C…` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L177-L215][f2]

Builds constructors for EnumSet and exact EnumMap types that lack usable public no-args constructors.

For EnumSet-assignable raw types, construction requires a ParameterizedType whose first actual argument is a Class; otherwise it throws JsonIOException. For raw type exactly EnumMap, construction has the same validation and creates an EnumMap for the element class; custom EnumMap subtypes are not handled here. Other raw types return null.

<a id="u-90054f28a20a"></a>
### `ConstructorConstructor.newUnsafeAllocator`

`private <T> ObjectConstructor<T> newUnsafeAllocator(Class<? super T> rawType)` · [gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java:L361-L395][f2]

Creates an Unsafe-based allocator when enabled, otherwise a throwing constructor with a diagnostic message.

When enabled, the returned constructor calls the singleton Unsafe allocator and wraps any Exception in RuntimeException. When disabled, the message explains how to fix the problem; if the raw type declares no constructors, it appends R8 advice. The disabled path returns a throwing constructor.

<a id="u-6dd3d63a9e7a"></a>
### `gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:UnsafeAllocator`

`class UnsafeAllocator` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L31-L38][f4]

Abstract allocator that creates instances without invoking constructors; subclasses implement newInstance.

The static INSTANCE is produced by a factory that tries JVM Unsafe, Dalvik ObjectStreamClass, ObjectInputStream, then a fallback that throws UnsupportedOperationException. The abstract contract throws Exception and concrete implementations guard against non-instantiable classes.

<a id="u-8a9a3c647475"></a>
### `CollectionTypeAdapterFactory.Adapter.read`

`@Override public Collection<E> read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L74-L89][f1]

Reads a JSON array into a collection, returning null for JSON null and otherwise constructing a collection before reading elements.

It calls the constructor, begins the array, reads each element through the element adapter and adds it, then ends the array and returns the collection. Exceptions from construction or element reading propagate.

<a id="u-2403ce181efc"></a>
### `CollectionTypeAdapterFactory.Adapter.write`

`@Override public void write(JsonWriter out, Collection<E> collection) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L91-L103][f1]

Writes a collection as a JSON array, emitting JSON null for a null collection and otherwise writing each element through the element adapter between beginArray and endArray.

<a id="u-42f8907567ac"></a>
### `CollectionTypeAdapterFactory.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java:L41-L62][f1]

Creates a collection adapter only when the raw type is assignable to Collection; otherwise returns null.

It resolves the element type, obtains and runtime-wraps the element adapter, and asks the ConstructorConstructor for an object constructor with Unsafe disabled so broken collection instances are not created. The resulting adapter is returned for the requested type.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/CollectionTypeAdapterFactory.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ConstructorConstructor.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ObjectConstructor.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/InstanceCreator.java
