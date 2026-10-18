# Runtime Generic Type Model

**Capability.** Captures and manipulates generic Types despite erasure: TypeToken captures T from anonymous subclasses; GsonTypes builds, canonicalizes, resolves, and structurally compares parameterized, array, wildcard, and type-variable types, backed by immutable Type implementations.

Consult this subtree for generic type identity: what type an adapter is for, how type variables resolve against a context, and how supertype/collection/map element types are derived.

**Depends on.**

- [Internal Utilities and Data Structures](r2-infrastructure.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Built-in Type Adapters](r1-builtin-adapters.md) · graph-confirmed · 8 edge(s)
- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 11 edge(s) · fromJson/toJson/getAdapter resolve user-supplied generic types via TypeToken and GsonTypes.
- [Exclusion and Reflection Policy](r1-reflection-policy.md) · graph-confirmed · 1 edge(s)
- [ReflectiveTypeAdapterFactory](r2-reflective-type-adapter-factory.md) · graph-only · 10 edge(s)
- [Collection, Map, and Tree Adapters](r2-collection-map-adapters.md) · graph-only · 9 edge(s)
- [Tree-Style Serializer Bridge](r1-tree-adapter-bridge.md) · graph-only · 8 edge(s)
- [@JsonAdapter Annotation Handling](r2-jsonadapter-annotation-factory.md) · graph-only · 5 edge(s)
- [Primitive and Utility Type Adapters](r2-primitive-adapters.md) · graph-only · 5 edge(s)
- [Date and Time Adapters](r2-date-time-adapters.md) · graph-only · 4 edge(s)
- [Builder and Naming Configuration](r2-configuration.md) · graph-only · 2 edge(s)
- [Object Construction Strategy](r2-object-construction.md) · graph-only · 2 edge(s)
- [TypeAdapter Framework](r1-adapter-framework.md) · graph-only · 1 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (19)

<a id="u-55a9c25d6eea"></a>
### `type-token-class`

`class TypeToken<T>` · [gson/src/main/java/com/google/gson/reflect/TypeToken.java:L54-L72][f1]

Represents a generic type T at runtime by capturing the type argument of an anonymous subclass despite erasure.

The protected no-arg constructor reads getClass().getGenericSuperclass(): if it is a ParameterizedType with raw type TypeToken, it canonicalizes the first type argument via GsonTypes.canonicalize; if it is raw TypeToken it throws IllegalStateException (with a troubleshooting-guide link mentioning shrinkers dropping generic signatures); anything else (indirect subclass) also throws IllegalStateException. When capturing type variables is not disabled (system property gson.allowCapturingTypeVariables != "true"), verifyNoTypeVariable recursively rejects a type argument containing a TypeVariable — directly, inside generic arrays, parameterized owner/argument types, or wildcard bounds — with IllegalArgumentException, including the Eclipse/Java 11.0.18 case where the argument is null. The private TypeToken(Type) constructor canonicalizes a non-null type and derives rawType and hashCode; get(Type) and get(Class) use it, getParameterized builds a validated parameterized type, and getArray builds an array type. getParameterized requires a Class raw type, an exact count of type arguments, non-null arguments, rejection of raw types requiring an owner, and each argument satisfying the declared type-variable bounds (by raw assignability), throwing IllegalArgumentException on any violation; with zero arguments on a non-generic class it delegates to get(Class). isAssignableFrom(Type) is deprecated and may diverge from javac for wildcards: null returns false, equal types return true, Class targets use raw assignability, ParameterizedType and GenericArrayType targets use private recursive helpers that walk generic interfaces and superclasses with a type-variable substitution map; any other Type kind throws IllegalArgumentException from buildUnsupportedTypeException. equals delegates to GsonTypes.equals on the captured type, hashCode is cached, and toString uses GsonTypes.typeToString.

**Notes.**

- condition: Setting gson.allowCapturingTypeVariables=true skips the type-variable check, allowing otherwise rejected tokens.
- failure: IllegalStateException is thrown for raw or indirect TypeToken subclasses; IllegalArgumentException for captured type variables, null captured types, and invalid getParameterized inputs.

calls: [GsonTypes.canonicalize](r1-type-model.md#u-39eea521af00), [GsonTypes.getRawType](r1-type-model.md#u-6ec82906ebea), [GsonTypes.newParameterizedTypeWithOwner](r1-type-model.md#u-7cd8a211ba3f), [GsonTypes](r1-type-model.md#u-f248f331b1a0), [GsonTypes.arrayOf](r1-type-model.md#u-f8ccc55d7f2c), [GsonTypes.equals](r1-type-model.md#u-5cef2f4f8255), [TroubleshootingGuide](r2-infrastructure.md#u-9bcd073a2728)

**Uncertainties.**

- Exact semantics of GsonTypes.canonicalize, equals, and typeToString are outside this file; their effects are taken from the call graph only.
- The recursive isAssignableFrom(Type, ParameterizedType, Map) walks the full class hierarchy and may recurse through Object's superclass (null), whose handling is not visible in this source.

<a id="u-f248f331b1a0"></a>
### `GsonTypes`

`class GsonTypes` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L43-L46][f2]

Static toolkit for working with reflection Types: building parameterized, array, and wildcard types, canonicalizing them into this package's implementations, extracting raw types and element types, resolving type variables against a context, and structural equality of types.

Instantiation is blocked with UnsupportedOperationException. Simple helpers folded here: typeToString returns the class name for Class types and toString otherwise; equal delegates to Objects.equals; checkNotPrimitive throws IllegalArgumentException for primitive Class types; requiresOwnerType reports true exactly for non-static classes with a declaring class; getArrayComponentType returns the generic component for GenericArrayType and the Class component otherwise.

uses: [gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes.resolve](r1-type-model.md#u-b5e70ef0ee63)

<a id="u-f8ccc55d7f2c"></a>
### `GsonTypes.arrayOf`

`public static GenericArrayType arrayOf(Type componentType)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L66-L68][f2]

Factory creating a GenericArrayTypeImpl whose component is the given type.

<a id="u-39eea521af00"></a>
### `GsonTypes.canonicalize`

`public static Type canonicalize(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L104-L126][f2]

Replaces reflection Type objects with this package's equal-valued implementations.

Class arrays become GenericArrayTypeImpl (component canonicalized recursively); ParameterizedType becomes ParameterizedTypeImpl with the original owner, raw class, and arguments; GenericArrayType becomes GenericArrayTypeImpl; WildcardType becomes WildcardTypeImpl with the same bounds. Any other Type implementation is returned unchanged.

<a id="u-5cef2f4f8255"></a>
### `GsonTypes.equals`

`public static boolean equals(Type a, Type b)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L171-L226][f2]

Structural equality of two Types beyond Object.equals.

Reference equality short-circuits true (including both null). Class uses its own equals. ParameterizedType compares owner, raw type, and type arguments; GenericArrayType compares component types recursively; WildcardType compares upper and lower bound arrays; TypeVariable compares generic declaration and name. Mismatched kinds, including an unsupported kind of a, yield false; b being null or another kind yields false in every branch.

<a id="u-c821854d018d"></a>
### `GsonTypes.getCollectionElementType`

`public static Type getCollectionElementType(Type context, Class<?> contextRawType)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L311-L318][f2]

Resolves the element type of a Collection type via getSupertype against Collection.class; if the resulting collection type is a ParameterizedType its first type argument is returned, otherwise Object.class.

<a id="u-aaf3d61fa3b3"></a>
### `GsonTypes.getGenericSupertype`

`private static Type getGenericSupertype(Type context, Class<?> rawType, Class<?> supe…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L237-L269][f2]

Finds the generic (parameterized) form of supertype as seen from context/rawType.

If supertype equals rawType, context itself is returned. For interface supertypes, rawType's interfaces are searched in order: a direct match returns the corresponding generic interface, otherwise recursion continues through assignable interfaces. For class supertypes, the superclass chain is walked up to Object, returning generic superclasses at matches or recursing deeper. If nothing resolves, supertype itself is returned unchanged.

<a id="u-936f504373bc"></a>
### `GsonTypes.getMapKeyAndValueTypes`

`public static Type[] getMapKeyAndValueTypes(Type context, Class<?> contextRawType)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L324-L341][f2]

Returns the key and value types of a Map type as a two-element array.

Special case: any contextRawType assignable from Properties returns {String, String}, working around Properties extending Hashtable<Object, Object> instead of Hashtable<String, String>. Otherwise the Map supertype is resolved; if it is a ParameterizedType its actual type arguments are returned, else {Object, Object}.

<a id="u-6ec82906ebea"></a>
### `GsonTypes.getRawType`

`public static Class<?> getRawType(Type type)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L128-L164][f2]

Extracts the erased Class behind a Type.

Class returns itself; ParameterizedType returns its raw type cast to Class; GenericArrayType builds a zero-length array of the component's raw type and takes its class; TypeVariable returns Object.class (bounds intentionally ignored); WildcardType recurses into its single upper bound (guarded by an assert). Any other type, including null, throws IllegalArgumentException naming the offending class.

**Uncertainties.**

- The cast of ParameterizedType.getRawType() to Class relies on well-formed reflection types; a hostile implementation could throw ClassCastException.

<a id="u-b7c5c031e1d1"></a>
### `GsonTypes.getSupertype`

`private static Type getSupertype(Type context, Class<?> contextRawType, Class<?> supe…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L278-L293][f2]

Returns the resolved generic form of supertype for a context type.

A WildcardType context is replaced by its single upper bound first. If contextRawType is not a subtype of supertype, IllegalArgumentException is thrown; otherwise the generic supertype found by getGenericSupertype is resolved against the context via resolve.

calls: [GsonTypes.getGenericSupertype](r1-type-model.md#u-aaf3d61fa3b3), [gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes.resolve](r1-type-model.md#u-b5e70ef0ee63)

<a id="u-7cd8a211ba3f"></a>
### `GsonTypes.newParameterizedTypeWithOwner`

`public static ParameterizedType newParameterizedTypeWithOwner( Type ownerType, Class<…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L56-L59][f2]

Factory creating a ParameterizedTypeImpl from an owner type, raw class, and type arguments; validation and canonicalization happen inside the impl constructor.

<a id="u-3db3c53c9136"></a>
### `GsonTypes.resolve`

`public static Type resolve(Type context, Class<?> contextRawType, Type toResolve)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L343-L346][f2]

Public three-argument resolve entry point; starts resolution with a fresh map tracking in-progress type variables to prevent infinite recursion.

<a id="u-b5e70ef0ee63"></a>
### `gson/src/main/java/com/google/gson/internal/GsonTypes.java:GsonTypes.resolve`

`private static Type resolve( Type context, Class<?> contextRawType, Type toResolve, M…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L348-L452][f2]

Resolves type variables in toResolve against a context, looping to avoid object creation.

TypeVariable: a previously resolved variable is returned directly (a Void.TYPE placeholder means an unresolved cycle, so the variable itself is returned); a new variable is marked in-progress, then substituted via resolveTypeVariable, breaking if it does not reduce. Arrays and generic arrays: the component is resolved recursively and a new array type is built only if it changed. ParameterizedType: owner and each argument are resolved, cloning the argument array lazily on first change, and a new ParameterizedTypeImpl is built only when owner or arguments changed. WildcardType: a single lower bound resolves via supertypeOf, a single upper bound via subtypeOf, each only when changed; otherwise the original is returned. Any other kind breaks immediately. Finally, the in-progress entry for the first resolving variable is updated with the final result.

calls: [GsonTypes.resolveTypeVariable](r1-type-model.md#u-58cabc81f38b), [GsonTypes.resolve](r1-type-model.md#u-3db3c53c9136)

**Uncertainties.**

- WildcardType handling only resolves bounds when exactly one bound is present; multi-bound wildcards are returned unchanged.

<a id="u-58cabc81f38b"></a>
### `GsonTypes.resolveTypeVariable`

`private static Type resolveTypeVariable( Type context, Class<?> contextRawType, TypeV…` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L454-L470][f2]

Substitutes a TypeVariable using the context.

If the variable was not declared by a class, it is returned unchanged. Otherwise the generic supertype of its declaring class is located; if that is a ParameterizedType, the actual type argument at the variable's parameter index is returned, else the variable itself. An out-of-range index cannot occur because indexOf throws NoSuchElementException before indexing.

calls: [GsonTypes.getGenericSupertype](r1-type-model.md#u-aaf3d61fa3b3)

<a id="u-4a44782267b4"></a>
### `GsonTypes.subtypeOf`

`public static WildcardType subtypeOf(Type bound)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L76-L84][f2]

Builds a wildcard '?

extends bound'. If bound is itself a WildcardType, its upper bounds are reused; otherwise the single bound is used. Lower bounds are empty, yielding '?' when the bound is Object.

<a id="u-8edc1e5d98bb"></a>
### `GsonTypes.supertypeOf`

`public static WildcardType supertypeOf(Type bound)` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L90-L98][f2]

Builds a wildcard '?

super bound'. If bound is itself a WildcardType, its lower bounds are reused; otherwise the single bound is used. The upper bound is fixed to Object.class.

<a id="u-e6e72949c746"></a>
### `gson-internal-gsontypes-parameterized-type-impl`

`class ParameterizedTypeImpl implements ParameterizedType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L512-L519][f2]

Immutable ParameterizedType implementation.

The constructor requires a non-null raw type and rejects a null owner when requiresOwnerType says one is mandatory; owner, raw type, and each argument are canonicalized, and null or primitive arguments are rejected. Accessors return the stored values, with getActualTypeArguments returning a defensive clone. Equality delegates to GsonTypes.equals against any ParameterizedType; hashCode combines argument, raw, and owner hashes (null owner as zero). toString prints 'raw<arg0, arg1>' or just the raw type when there are no arguments. Members folded: constructor, accessors, equals, hashCodeOrZero, hashCode, toString.

calls: [GsonTypes.equals](r1-type-model.md#u-5cef2f4f8255), [GsonTypes](r1-type-model.md#u-f248f331b1a0)

<a id="u-d70593f0537c"></a>
### `gson-internal-gsontypes-generic-array-type-impl`

`class GenericArrayTypeImpl implements GenericArrayType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L585-L588][f2]

Immutable GenericArrayType implementation: the constructor requires a non-null component and canonicalizes it; getGenericComponentType returns it; equals delegates to GsonTypes.equals for any GenericArrayType; hashCode is the component's hash; toString appends '[]' to the component string.

Members folded: constructor, accessors, equals, hashCode, toString.

calls: [GsonTypes.equals](r1-type-model.md#u-5cef2f4f8255)

<a id="u-979af4db340b"></a>
### `gson-internal-gsontypes-wildcard-type-impl`

`class WildcardTypeImpl implements WildcardType` · [gson/src/main/java/com/google/gson/internal/GsonTypes.java:L620-L625][f2]

Immutable WildcardType supporting at most one lower and exactly one upper bound, matching the target Java version.

The constructor throws IllegalArgumentException for more than one lower bound or not exactly one upper bound; with a lower bound present, the upper bound must be Object.class, the lower bound must be non-null and non-primitive, and it is canonicalized while the upper bound stays Object.class. Without a lower bound, the canonicalized upper bound is stored and lower is null. getUpperBounds returns a one-element array; getLowerBounds returns a one-element array or the shared empty array. equals delegates to GsonTypes.equals; hashCode combines the bound hashes as documented; toString renders '? super x', '?', or '? extends x'. Members folded: constructor, accessors, equals, hashCode, toString.

calls: [GsonTypes.equals](r1-type-model.md#u-5cef2f4f8255)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/reflect/TypeToken.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/GsonTypes.java