# Generic type reflection

**Capability.** Resolves, represents, compares, and adapts generic Java types, arrays, and TypeToken assignability.

Use for generic type handling and array adapters. Units show GsonTypes resolution, TypeToken assignability, and ArrayTypeAdapter read/write.

**Depends on.**

- [Reflective adapter support](reflective-adapter-support.md) · graph-only · 2 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Enum runtime adapter selection](enum-runtime-adapter-selection.md) · graph-confirmed · 1 edge(s)
- [Gson serialization facade](gson-serialization-facade.md) · graph-only · 9 edge(s)
- [Gson builder configuration](gson-builder-configuration.md) · graph-only · 4 edge(s)
- [Reflective adapter support](reflective-adapter-support.md) · graph-only · 4 edge(s)
- [Map type adapter factory](map-type-adapter-factory.md) · graph-only · 3 edge(s)
- [Gson annotation adapter support](gson-annotation-adapter-support.md) · graph-only · 2 edge(s)
- [Object construction adapters](object-construction-adapters.md) · graph-only · 2 edge(s)

Parent: [Type resolution and enums](type-resolution-and-enums.md)

## Units (27)

<a id="u-de62a2795c43"></a>
### `ArrayTypeAdapter.java-arraytypeadapter-class-and-constructor`

`class ArrayTypeAdapter<E> extends TypeAdapter<Object>` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L34-L37][f1]

ArrayTypeAdapter is a TypeAdapter for array values that delegates each element to a component adapter wrapped for runtime type selection.

The constructor stores the component class and wraps the supplied component adapter in a runtime-type wrapper using the Gson context, so element serialization can choose a more specific adapter at runtime.

<a id="u-e2c75fd90836"></a>
### `GsonTypes.java-collection-map-and-array-type-extraction`

`public static Type getArrayComponentType(Type array)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L300-L304][f2]

Extracts array component, collection element, and map key/value types from a context type.

Array extraction returns the generic component for GenericArrayType; otherwise it casts to Class and calls getComponentType, so a non-array Class returns null while a non-Class non-GenericArrayType input throws ClassCastException. Collection extraction resolves the Collection supertype and returns its first actual argument, or Object.class when not parameterized. Map extraction special-cases Properties as String/String, otherwise resolves the Map supertype and returns its actual arguments, or Object/Object when not parameterized.

<a id="u-5fb3878bae68"></a>
### `GsonTypes.java-generic-array-type-implementation`

`class GenericArrayTypeImpl implements GenericArrayType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L585-L586][f2]

Immutable GenericArrayType implementation that canonicalizes and stores its component type.

The constructor requires a non-null component. Equality delegates to structural type equality when the other object is a GenericArrayType. Hash code is the component hash, and string form appends [] to the component string.

<a id="u-f8c081be497c"></a>
### `GsonTypes.java-gsontypes-class`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L48-L56][f2]

Static utility class for reflective Type handling with a private constructor that throws UnsupportedOperationException.

It provides factories and inspectors for parameterized, generic-array, and wildcard types, canonicalization, equality, raw-type extraction, supertype resolution, and nested immutable Type implementations.

<a id="u-54d7a217697b"></a>
### `GsonTypes.java-parameterized-type-implementation`

`class ParameterizedTypeImpl implements ParameterizedType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L512-L513][f2]

Immutable ParameterizedType implementation that canonicalizes owner, raw type, and arguments and validates them.

The constructor requires a raw type, rejects a missing owner when the raw type requires one, canonicalizes owner and raw type, clones arguments, and rejects null or primitive arguments. Actual arguments are returned as a clone; raw and owner types are returned directly. Equality delegates to structural type equality when the other object is a ParameterizedType. Hash code combines argument-array hash, raw-type hash, and owner hash or zero. String form is the raw type alone when there are no arguments, otherwise raw<arg0, arg1, ...>.

<a id="u-8f19f7f9da95"></a>
### `GsonTypes.java-supertype-resolution`

`private static Type getGenericSupertype(Type context, Class<?> rawType, Class<?> supe…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L237-L269][f2]

Finds the generic supertype path from a raw class to a target supertype and resolves it in context.

The generic-supertype search returns the context when the target equals the raw type, searches interfaces first when the target is an interface, then walks superclasses until Object, and returns the target when it cannot resolve further. The supertype resolver replaces a wildcard context with its first upper bound, throws IllegalArgumentException when the target is not assignable from the raw context type, and otherwise resolves the found generic supertype.

<a id="u-a344bbf12282"></a>
### `GsonTypes.java-type-construction-and-canonicalization`

`public static ParameterizedType newParameterizedTypeWithOwner( Type ownerType, Class<…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L56-L59][f2]

Creates and normalizes reflective Type instances into Gson's immutable implementations.

Parameterized types and generic arrays are wrapped in their implementation classes. A subtype wildcard reuses a wildcard bound's upper bounds or wraps a single bound, with no lower bounds. A supertype wildcard reuses a wildcard bound's lower bounds or wraps a single bound, with Object as the upper bound. Canonicalization converts Class arrays, ParameterizedType, GenericArrayType, and WildcardType into the corresponding implementations; unsupported types and null are returned unchanged, so null returns null.

<a id="u-ecee77c9bf84"></a>
### `GsonTypes.java-type-equality`

`private static boolean equal(Object a, Object b)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L166-L168][f2]

Implements structural equality for reflective types, with identity short-circuit and type-specific comparisons.

Identity, including both null, returns true. Classes use Class.equals. ParameterizedType requires another ParameterizedType and compares owner, raw type, and actual arguments. GenericArrayType requires another GenericArrayType and recursively compares components. WildcardType requires another WildcardType and compares upper and lower bound arrays. TypeVariable requires another TypeVariable and compares generic declaration and name. Unsupported types return false.

<a id="u-0f9e2ea84374"></a>
### `GsonTypes.java-type-utility-class`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L43-L44][f2]

Utility class for reflective type operations; its private constructor always throws UnsupportedOperationException to prevent instantiation.

<a id="u-4ec82e9ed008"></a>
### `GsonTypes.java-type-validation-helpers`

`static void checkNotPrimitive(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L490-L494][f2]

Provides small validation predicates for primitive types and owner-type requirements.

Primitive Class inputs throw IllegalArgumentException. Owner type is required only when the raw type is a non-static class with a declaring class; other inputs return false.

<a id="u-52e1c610f8fc"></a>
### `GsonTypes.java-type-variable-resolution`

`public static Type resolve(Type context, Class<?> contextRawType, Type toResolve)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L343-L346][f2]

Resolves type variables and nested type structures against a context, tracking visited variables to avoid infinite recursion.

The public entrypoint starts with an empty visited map. The private loop handles TypeVariable by returning a prior result or the original on a cycle, inserting a placeholder, resolving the variable, and stopping if unchanged. Class arrays and GenericArrayType resolve their component and rebuild only when it changes. ParameterizedType resolves owner and each argument, cloning arguments on first change and rebuilding only when owner or arguments change. WildcardType resolves a single lower bound or single upper bound and rebuilds only when changed. Other types stop unchanged. The first resolving variable is updated with the final result. Variable resolution uses the declaring class, generic supertype, and type-parameter index; a missing index throws NoSuchElementException. Declarations that are not classes return null.

<a id="u-1f2098069dde"></a>
### `GsonTypes.java-wildcard-type-implementation`

`class WildcardTypeImpl implements WildcardType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L620-L621][f2]

Immutable WildcardType implementation supporting at most one upper bound and at most one lower bound.

The constructor rejects more than one lower bound, rejects anything other than exactly one upper bound, and when a lower bound exists requires it non-null and non-primitive with Object as the upper bound. Without a lower bound it requires a non-null, non-primitive upper bound. Upper bounds are returned as a new single-element array; lower bounds are returned as a single-element array or the shared empty array. Equality delegates to structural type equality when the other object is a WildcardType. String form is ? super X, ?, or ? extends X.

<a id="u-e41480345cdf"></a>
### `TypeToken.java-assignability-checks`

`@Deprecated public boolean isAssignableFrom(Class<?> cls)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L175-L178][f3]

Checks whether this token's type can be assigned from another type.

The Class overload delegates to the Type overload; the TypeToken overload delegates to the other token's type. The Type overload returns false for null input, true for an exactly equal type, and then branches on this token's type: Class uses raw-type assignability; ParameterizedType runs the recursive parameterized check with a fresh map; GenericArrayType requires raw-type assignability and runs the generic-array check; any other type throws IllegalArgumentException built from the unsupported-type helper.

<a id="u-2cd16b83845a"></a>
### `TypeToken.java-assignability-internals`

`private static boolean isAssignableFrom(Type from, GenericArrayType to)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L222-L241][f3]

Implements recursive assignability for generic arrays and parameterized types.

The generic-array helper only recurses when the target component is a ParameterizedType; it derives the source component from a GenericArrayType or by stripping array dimensions from a Class, then runs the parameterized check with a fresh map, and otherwise returns true so other checks decide. The parameterized helper returns false for null source, true for exact equality, and only when the source is a ParameterizedType builds a type-variable map from the source's actual arguments (resolving TypeVariable arguments through the existing map) and runs typeEquals; if that does not match, or the source is not parameterized, it recurses into generic interfaces and then the generic superclass with copied maps. typeEquals requires equal raw types and each actual argument to match under the map. matches accepts exact equality or a source TypeVariable whose name maps to the target. The exception builder formats an IllegalArgumentException listing expected classes and the actual token class and string.

<a id="u-eb3778085b7a"></a>
### `TypeToken.java-assignability-overload-declarations`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L168-L175][f3]

These deprecated overloads declare assignability checks from a class, a type, or another token.

The class and token overloads delegate to the type overload. The type overload returns false for a null source and true for an equal type; otherwise it dispatches on this token's type: a class uses raw assignability, a parameterized type uses recursive type-variable mapping, and a generic array checks raw assignability plus its component. For parameterized targets, the helper only builds the type-variable map when the source is also parameterized; otherwise it skips direct type equality and recurses into interfaces and superclass. Unsupported target kinds throw IllegalArgumentException.

<a id="u-a80c4c2b4a96"></a>
### `TypeToken.java-simple-type-token-factories`

`public static TypeToken<?> get(Type type)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L355-L357][f3]

Creates tokens for a supplied Type, Class, or array component.

get(Type) and get(Class) both go through the private constructor, which canonicalizes the type and rejects null with NullPointerException. getArray wraps GsonTypes.arrayOf(componentType); null component behavior depends on that helper and is not shown here.

<a id="u-9f6babd9613e"></a>
### `TypeToken.java-type-argument-capture-validation`

`private static boolean isCapturingTypeVariablesForbidden()` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L87-L89][f3]

Validates the type argument captured by an anonymous TypeToken subclass.

isCapturingTypeVariablesForbidden returns true unless the system property 'gson.allowCapturingTypeVariables' equals 'true'. getTypeTokenTypeArgument inspects the generic superclass: if it is a ParameterizedType whose raw type is TypeToken, it canonicalizes the first actual type argument and, when capture is forbidden, verifies no type variable; if the superclass is raw TypeToken it throws IllegalStateException; any other superclass shape throws IllegalStateException for not being a direct subclass. verifyNoTypeVariable recursively rejects TypeVariable with IllegalArgumentException naming the variable and declaration, recurses through GenericArrayType components, ParameterizedType owner and arguments, and WildcardType lower and upper bounds, and rejects a null type with IllegalArgumentException about a compiler/runtime bug.

<a id="u-77f46893f151"></a>
### `TypeToken.java-typetoken-class-and-constructors`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L54-L55][f3]

Represents a generic type and captures it through an anonymous subclass.

The protected constructor derives the type argument from the generic superclass, computes the raw type, and caches the type hash; the private constructor canonicalizes a supplied non-null type and computes the same fields. Both constructors rely on GsonTypes for raw-type resolution.

<a id="u-18bc7793111b"></a>
### `TypeToken.java-typetoken-value-semantics`

`@Override public final int hashCode()` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L339-L342][f3]

equals compares only TypeToken instances using GsonTypes.equals on the canonical types.

hashCode returns the cached hash of the canonical type. toString delegates to GsonTypes.typeToString.

<a id="u-6ec82906ebea"></a>
### `GsonTypes.getRawType`

`public static Class<?> getRawType(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L128-L164][f2]

Maps a reflective Type to its raw Class, throwing IllegalArgumentException for unsupported or null inputs.

Classes return themselves; ParameterizedType raw types are cast to Class; GenericArrayType recursively resolves its component and creates an array class; TypeVariable returns Object.class; WildcardType resolves the first upper bound. The final branch throws with the input and its class name, using "null" when the input is null.

<a id="u-0a4d27fa54cb"></a>
### `GsonTypes.typeToString`

`public static String typeToString(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L228-L230][f2]

Renders a type as a string, using Class.getName for classes and toString otherwise.

<a id="u-07041a2aec40"></a>
### `ArrayTypeAdapter.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> typeToken)` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L37-L52][f1]

The array factory creates an array adapter only when the requested type is a generic array or a class that is an array; otherwise it returns null.

It derives the component type, obtains the component adapter from Gson, and constructs the adapter with the component raw class.

<a id="u-e54aa525f0d8"></a>
### `ArrayTypeAdapter.read`

`@Override public Object read(JsonReader in) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L65-L95][f1]

Reads a JSON array into a Java array, returning null for JSON null and delegating each element to the component adapter.

It first collects elements into an ArrayList, then builds the result array.
- JSON null: consumes nextNull and returns null.
- primitive component: creates a primitive array and assigns each collected element via Array.set.
- non-primitive component: creates an object array and copies the list via toArray.
The source does not perform explicit unboxing, so null or incompatible primitive elements fail according to Array.set rather than an explicit unboxing step.

**Uncertainties.**

- The source does not explicitly unbox primitive elements; null or incompatible values fail according to Array.set.

<a id="u-d7de852306f0"></a>
### `ArrayTypeAdapter.write`

`@Override public void write(JsonWriter out, Object array) throws IOException` · [gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java:L97-L111][f1]

Writes a Java array as a JSON array, emitting JSON null for a null array and delegating each element to the component adapter.

It iterates by index using Array.getLength and Array.get, then closes the JSON array.

<a id="u-a73b5b493602"></a>
### `gson/src/main/java/com/google/gson/reflect/TypeToken.java:TypeToken (10)`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L362-L385][f3]

This declaration documents construction of a parameterized type token from a raw class and type arguments.

- Null raw type, null argument array, or null individual argument: NullPointerException from Objects.requireNonNull.
- Raw type not a Class: IllegalArgumentException.
- Argument count mismatch: IllegalArgumentException.
- Zero arguments: returns get(rawClass) before the owner-type check.
- Positive arguments and raw type requires an owner: IllegalArgumentException.
- Any argument whose raw type does not satisfy a declared bound: IllegalArgumentException.
- Otherwise: returns a token for the parameterized type with no owner.

<a id="u-501080edcdf7"></a>
### `gson/src/main/java/com/google/gson/reflect/TypeToken.java:TypeToken (13)`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L89-L95][f3]

This declaration documents extraction of the type argument from a direct anonymous TypeToken subclass.

It canonicalizes the superclass type argument and, unless the system property gson.allowCapturingTypeVariables is exactly 'true', recursively rejects captured type variables. A raw TypeToken superclass or an indirect subclass causes IllegalStateException; a captured type variable or a null type argument causes IllegalArgumentException.

<a id="u-ae4ec614c7f7"></a>
### `TypeToken.getParameterized`

`public static TypeToken<?> getParameterized(Type rawType, Type... typeArguments)` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L385-L444][f3]

Builds a parameterized token from a raw class and type arguments, validating the shape before construction.

rawType and the typeArguments array are required non-null via Objects.requireNonNull, so nulls throw NullPointerException. rawType must be a Class or IllegalArgumentException is thrown. The actual argument count must equal the raw class's type-parameter count or IllegalArgumentException is thrown. If the count is zero (only possible for a non-generic class after the count check), it returns get(rawClass) before the owner-type check. Otherwise, if GsonTypes.requiresOwnerType(rawType) is true it throws IllegalArgumentException about needing an owner type. Each individual type argument is required non-null via Objects.requireNonNull, so a null element throws NullPointerException; each argument's raw type must satisfy every bound of the corresponding type variable or IllegalArgumentException is thrown. On success it returns a token for GsonTypes.newParameterizedTypeWithOwner(null, rawClass, typeArguments).

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ArrayTypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/GsonTypes.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/reflect/TypeToken.java
