# Generic Type Reflection

**Capability.** Provides TypeToken and GsonTypes utilities for capturing, canonicalizing, and resolving generic Java types, plus array adapters.

This module is the reflection backbone for matching types to adapters. It contains canonical Type implementations, type-variable resolution against supertypes, deprecated assignability checks, and the JSON-array-to-Java-array adapter.

**Depends on.**

- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-confirmed · 2 edge(s)
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-confirmed · 2 edge(s)
- [Built-in JDK Type Adapters](built-in-jdk-type-adapters.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Gson Entry Point and Streaming](gson-entry-point-and-streaming.md) · graph-confirmed · 5 edge(s) · The Gson facade resolves generic types via TypeToken and GsonTypes utilities to look up adapters.
- [Public API and Tree Bridge](public-api-and-tree-bridge.md) · graph-confirmed · 1 edge(s)
- [Reflective type adapter factory](reflective-type-adapter-factory.md) · graph-only · 2 edge(s)

Parent: [Core Gson Contracts and Facade](core-gson-contracts-and-facade.md)

## Units (29)

<a id="u-83c822d9dd3d"></a>
### `ArrayTypeAdapter.java-arraytypeadapter-factory-and-class`

`class ArrayTypeAdapter<E> extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L34-L37][f1]

Factory producing adapters for array and generic-array types, and the adapter class that converts between JSON arrays and Java arrays.

The factory's create returns null unless the type is a GenericArrayType or a Class that isArray; otherwise it resolves the component type, obtains its adapter from Gson, and constructs an ArrayTypeAdapter with the component's raw class. The adapter constructor wraps the component adapter in a TypeAdapterRuntimeTypeWrapper so serialization can pick a runtime subtype adapter; it also stores the component class. read returns null on JSON null; otherwise it collects elements via the component adapter into an ArrayList, then copies them into a new array: primitive component types are filled element-by-element with Array.set, other types use list.toArray over a newInstance array. write emits nullValue for a null array, else beginArray, each element via the wrapped component adapter, endArray.

calls: [GsonTypes.getArrayComponentType](../../catalog.json), [Gson.getAdapter](../../catalog.json); uses: [TypeAdapterRuntimeTypeWrapper](../../catalog.json)

<a id="u-6e6c3dd8fb5d"></a>
### `GsonTypes.java-element-and-key-value-type-extraction`

`public static Type getArrayComponentType(Type array)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L300-L304][f2]

Extract component types from composite types.

getArrayComponentType returns the generic component for GenericArrayType or the Class component type otherwise (ClassCastException if not an array). getCollectionElementType resolves the Collection supertype and returns its first type argument, or Object.class if not parameterized. getMapKeyAndValueTypes special-cases Properties (declared Hashtable<Object,Object>) to return {String,String}, then resolves the Map supertype and returns its two type arguments, or {Object,Object} if not parameterized. All supertype-based paths can throw IllegalArgumentException from getSupertype when the raw type is not the expected subtype.

<a id="u-3641838158cb"></a>
### `GsonTypes.java-genericarraytypeimpl`

`class GenericArrayTypeImpl implements GenericArrayType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L585-L586][f2]

Immutable GenericArrayType holding a canonicalized, non-null component type.

getGenericComponentType returns it directly; equals delegates to GsonTypes.equals against any GenericArrayType; hashCode is the component's hashCode; toString appends '[]' to the component's string form.

<a id="u-e0471bb48423"></a>
### `GsonTypes.java-parameterizedtypeimpl`

`class ParameterizedTypeImpl implements ParameterizedType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L512-L513][f2]

Immutable ParameterizedType implementation used as Gson's canonical form.

The constructor requires a non-null raw type, throws IllegalArgumentException when no owner is given but requiresOwnerType says one is needed, canonicalizes owner, raw type, and each argument, requires non-null arguments, and rejects primitives. getActualTypeArguments returns a defensive clone; getRawType/getOwnerType are plain accessors. equals delegates to GsonTypes.equals against any ParameterizedType; hashCode combines arguments, raw type, and owner (0 when null). toString renders 'Raw<Arg1, Arg2>' or just the raw type when no arguments.

<a id="u-0d2128d3b217"></a>
### `GsonTypes.java-type-construction-factories`

`public static ParameterizedType newParameterizedTypeWithOwner( Type ownerType, Class<…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L56-L59][f2]

Factory methods producing Gson's internal Type implementations.

newParameterizedTypeWithOwner wraps owner, raw type, and arguments in ParameterizedTypeImpl; arrayOf wraps a component type in GenericArrayTypeImpl. subtypeOf returns a wildcard with the given bound as upper bound (reusing an existing wildcard's upper bounds if bound is itself a WildcardType); supertypeOf returns a wildcard with Object as upper bound and the given bound (or an existing wildcard's lower bounds) as lower bound.

<a id="u-ecee77c9bf84"></a>
### `GsonTypes.java-type-equality`

`private static boolean equal(Object a, Object b)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L166-L168][f2]

Structural equality for Types beyond what Class.equals provides.

Fast path: identical references (also covers both null). Classes delegate to equals. ParameterizedTypes compare owner (via Objects.equals), raw type, and type arguments element-wise with recursive equals; GenericArrayTypes compare canonicalized component types recursively; WildcardTypes compare upper and lower bound arrays; TypeVariables compare generic declaration and name. Mixed kinds are unequal, and unsupported types fall back to false. The private equal helper is Objects.equals.

<a id="u-4ec82e9ed008"></a>
### `GsonTypes.java-type-validation-helpers`

`static void checkNotPrimitive(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L490-L494][f2]

checkNotPrimitive throws IllegalArgumentException('Primitive type is not allowed') when the Type is a primitive Class; used by the Impl constructors.

requiresOwnerType returns true only for a non-static Class that has a declaring class, i.e. inner classes whose parameterized types need an owner; false for anything else.

<a id="u-52e1c610f8fc"></a>
### `GsonTypes.java-type-variable-resolution`

`public static Type resolve(Type context, Class<?> contextRawType, Type toResolve)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L343-L346][f2]

Resolves a Type against a context, substituting type variables with their bindings from the context's supertypes.

The public overload starts with a fresh visited-map; the core loop handles: TypeVariable (lookup previously resolved value, returning the original if the placeholder Void.TYPE marks unresolvable recursion; otherwise record a placeholder, resolve via resolveTypeVariable, and loop if it changed), array Classes and GenericArrayTypes (resolve component, rebuild via arrayOf only if changed), ParameterizedTypes (resolve owner and each argument, cloning the array lazily and rebuilding only if something changed), and WildcardTypes (resolve the single lower or upper bound and rebuild with supertypeOf/subtypeOf if changed). Everything else returns unchanged. After the loop the initially resolving variable is updated with the final result, so chained resolutions converge; the visited map prevents infinite recursion on self-referential variables.

<a id="u-9b4dfe2a26ff"></a>
### `GsonTypes.java-type-variable-resolution-helpers`

`private static Type resolveTypeVariable( Type context, Class<?> contextRawType, TypeV…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L454-L470][f2]

resolveTypeVariable finds the class declaring a variable (returning the variable unchanged if declared by a non-class GenericDeclaration), locates the generic form of that declaring class via getGenericSupertype, and returns the corresponding actual type argument by index; if the declaration is not parameterized the variable is returned unchanged.

indexOf linearly searches for the variable and throws NoSuchElementException if absent. declaringClassOf returns the declaring Class or null.

<a id="u-146e7e631aed"></a>
### `GsonTypes.java-wildcardtypeimpl`

`class WildcardTypeImpl implements WildcardType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L620-L621][f2]

Immutable WildcardType supporting at most one upper and one lower bound, matching what current Java allows.

The constructor throws IllegalArgumentException for more than one lower bound, for any count of upper bounds other than exactly one, and when a lower bound is present unless the upper bound is Object; bounds must be non-null, non-primitive, and are canonicalized. getUpperBounds always returns a single-element array; getLowerBounds returns the bound or an empty array. equals delegates to GsonTypes.equals; hashCode mirrors Arrays.hashCode of both bound arrays. toString prints '? super X', '?' when the upper bound is Object, or '? extends X'.

<a id="u-8970bd2f1322"></a>
### `TypeToken.java-deprecated-isassignablefrom-entry-points`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L168-L175][f3]

These class regions contain the deprecated public assignability entry points: one accepts a Class and delegates to the Type overload; the other accepts a TypeToken and delegates with its underlying Type.

Both inherit the documented caveat that wildcard handling may diverge from javac, and a null TypeToken argument would produce a NullPointerException when getType is called.

<a id="u-e73becefaa82"></a>
### `TypeToken.java-typetoken-assignability-internals`

`private static boolean isAssignableFrom(Type from, GenericArrayType to)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L222-L241][f3]

Recursive helpers implementing the deprecated assignability checks.

For a GenericArrayType target, if the component type is parameterized it unwraps the source (GenericArrayType component, or repeatedly strips array dimensions from a Class) and recurses into the parameterized check; otherwise it returns true, deferring to the raw check already performed by the caller. The parameterized check returns false on null source, true on exact equality, then builds a type-variable map from the source's actual arguments (resolving chains of TypeVariables through the map), returns true if typeEquals matches under that mapping, and otherwise recurses into each generic interface and finally the generic superclass, each with a copy of the map. typeEquals compares raw types and requires every argument pair to satisfy matches, which accepts exact equality or a source TypeVariable mapped by the map to the target. buildUnsupportedTypeException constructs the IllegalArgumentException listing expected type kinds and the actual token.

<a id="u-7b3f01d039f4"></a>
### `TypeToken.java-typetoken-construction-and-type-variable-capture`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L54-L55][f3]

Represents a generic type T at runtime, capturing the type argument from an anonymous subclass and rejecting captures of type variables.

The protected constructor calls getTypeTokenTypeArgument, which requires the runtime class's generic superclass to be a parameterized TypeToken: it canonicalizes the first actual type argument and, unless the system property `gson.allowCapturingTypeVariables` equals "true", runs verifyNoTypeVariable on it. That check throws IllegalArgumentException for a TypeVariable (naming it and its declaration), recurses into GenericArrayType component types, ParameterizedType owner and type arguments, and WildcardType lower/upper bounds, and also throws IllegalArgumentException if the argument is null (a known compiler/runtime bug case). If the superclass is the raw TypeToken class, it throws IllegalStateException hinting at missing generic signatures under shrinkers; any other superclass shape throws IllegalStateException demanding direct subclasses. The private constructor used by the static factories instead canonicalizes a caller-supplied non-null Type and derives the raw type from it via GsonTypes.getRawType; both constructors cache the type's hashCode.

<a id="u-1ff6ed1e228e"></a>
### `TypeToken.java-typetoken-deprecated-isassignablefrom-overloads`

`@Deprecated public boolean isAssignableFrom(Class<?> cls)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L175-L178][f3]

Deprecated public assignability checks, documented as possibly inconsistent with javac for wildcard types.

The Class and TypeToken overloads funnel into isAssignableFrom(Type). That method returns false for a null argument, true when the represented type equals `from`, and otherwise dispatches on the token's own type: a plain Class compares raw types with Class.isAssignableFrom; a ParameterizedType runs the recursive parameterized check with a fresh type-variable map; a GenericArrayType additionally requires raw assignability and then checks the component type; any other type shape throws the IllegalArgumentException built by the unsupported-type helper.

<a id="u-cb9bdbaed8b9"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L230-L237][f2]

Class header for the GsonTypes region containing typeToString, which renders a Class by name and other types via toString; the method itself has its own unit.

<a id="u-f4296ae726fa"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes (2)`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L269-L278][f2]

Class header for the GsonTypes region containing getSupertype, which resolves the generic form of a supertype; the method itself has its own unit.

<a id="u-1b496699d158"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes (6)`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L48-L56][f2]

Class header for GsonTypes, a final utility class of static reflection helpers for java.lang.reflect types; its private constructor throws UnsupportedOperationException to prevent instantiation.

<a id="u-d2823b9bf6e8"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes (8)`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L494-L503][f2]

Class header for the GsonTypes region containing checkNotPrimitive, which rejects primitive Class arguments with IllegalArgumentException; the method itself has its own unit.

<a id="u-c2e979ab2320"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes (9)`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L612-L620][f2]

Class header for the GsonTypes region containing WildcardTypeImpl, the internal WildcardType implementation; that class and its members have their own units.

<a id="u-f6b60c6b41b4"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes (12)`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L68-L76][f2]

Class header for the GsonTypes region containing arrayOf, which wraps a component type into a GenericArrayType; the method itself has its own unit.

<a id="u-91e02f4877a1"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes (13)`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L84-L90][f2]

Class header for the GsonTypes region containing subtypeOf, which builds a wildcard with the given upper bound(s); the method itself has its own unit.

<a id="u-39eea521af00"></a>
### `GsonTypes.canonicalize`

`public static Type canonicalize(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L104-L126][f2]

Returns a functionally equal copy of a Type using Gson's own implementations: Classes are returned as-is unless arrays, which become GenericArrayTypeImpl of the canonicalized component; ParameterizedType, GenericArrayType, and WildcardType are rewrapped in the corresponding Impl classes (recursively canonicalizing nested parts via their constructors); any other Type is returned unchanged.

<a id="u-aaf3d61fa3b3"></a>
### `GsonTypes.getGenericSupertype`

`private static Type getGenericSupertype(Type context, Class<?> rawType, Class<?> supe…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L237-L269][f2]

Finds the generic form of supertype as seen from rawType.

If supertype equals rawType it returns the context type. If supertype is an interface, it scans rawType's interfaces, returning the matching generic interface or recursing through an assignable sub-interface. Otherwise, for non-interface rawType it walks the superclass chain, returning the generic superclass on a match or recursing through an assignable superclass, stopping at Object. If unresolvable it returns supertype itself.

<a id="u-6ec82906ebea"></a>
### `GsonTypes.getRawType`

`public static Class<?> getRawType(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L128-L164][f2]

Maps a Type to its raw Class.

Classes return themselves; ParameterizedType returns its raw type (cast to Class); GenericArrayType recursively computes the component's raw class and returns Array.newInstance(component, 0).getClass(); TypeVariable returns Object.class as a deliberately general bound; WildcardType asserts a single upper bound (per JLS) and recurses on it. Any other type, including null, throws IllegalArgumentException naming the offending type's class.

<a id="u-b7c5c031e1d1"></a>
### `GsonTypes.getSupertype`

`private static Type getSupertype(Type context, Class<?> contextRawType, Class<?> supe…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L278-L293][f2]

Returns the generic form of a supertype resolved against the context.

If context is a WildcardType it substitutes its single asserted upper bound, since wildcards are useless for supertype resolution. Throws IllegalArgumentException if supertype is not assignable from contextRawType. Otherwise resolves the result of getGenericSupertype against the context via resolve, substituting type variables.

<a id="u-e54aa525f0d8"></a>
### `ArrayTypeAdapter.read`

`@Override public Object read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L65-L95][f1]

Deserializes a JSON array into a Java array of the component type.

Returns null when the reader peeks NULL (consuming it via nextNull). Otherwise reads elements with the wrapped component adapter into an ArrayList, then builds the result array: for primitive component types it creates the array reflectively and sets each slot with Array.set (unboxing nulls would throw); for reference types it allocates an E[] and uses list.toArray. Malformed input (missing endArray, wrong tokens) propagates whatever IOException the reader raises.

calls: [JsonReader](../../catalog.json)

<a id="u-d7de852306f0"></a>
### `ArrayTypeAdapter.write`

`@Override public void write(JsonWriter out, Object array) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L97-L111][f1]

Serializes a Java array (of any component type, accessed reflectively) as a JSON array.

A null array writes nullValue and returns. Otherwise it writes beginArray, iterates Array.getLength/Array.get to fetch each element, delegates each to the wrapped component adapter (which may choose a runtime-type adapter), and ends with endArray. No exception handling; reader/writer IOExceptions propagate.

calls: [JsonWriter](../../catalog.json)

<a id="u-cdb0eca53d60"></a>
### `gson/src/main/java/com/google/gson/reflect/TypeToken.java:TypeToken (2)`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L206-L213][f3]

This class region holds the private helper checking assignability of a source type to a target GenericArrayType.

If the array's generic component type is parameterized, it unwraps the source (component of a GenericArrayType, or repeatedly strips array dimensions of a Class) and recursively checks against that ParameterizedType with a fresh variable map; otherwise it returns true, deferring the decision to the raw-type check performed by the caller.

<a id="u-a73b5b493602"></a>
### `gson/src/main/java/com/google/gson/reflect/TypeToken.java:TypeToken (10)`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L362-L385][f3]

This class region contains the public factory building a TypeToken for a parameterized raw type with runtime-supplied arguments.

It requires a non-null Class raw type and non-null argument array, rejects argument-count mismatch, delegates to the Class factory when no arguments are given, rejects raw types needing an owner, requires each argument non-null and satisfying every bound of the corresponding type variable, then constructs the token from a parameterized type with null owner. All failures surface as IllegalArgumentException or NullPointerException.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/GsonTypes.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/reflect/TypeToken.java
