# Reflection and record support

**Capability.** Provides reflection utilities: accessible-object handling, member descriptions, and a JVM-version-agnostic record introspection API.

Come here for making reflective members accessible with descriptive errors, and for record support that compiles without java.lang.Record. It includes the record adapter used by the reflective factory and impossible-failure exception builders.

**Depends on.**

- [Reflective type adapter factory](reflective-type-adapter-factory.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Reflective type adapter factory](reflective-type-adapter-factory.md) · graph-confirmed · 13 edge(s) · The reflective factory uses reflection utilities and record introspection to bind fields.
- [Instance construction utilities](instance-construction-utilities.md) · graph-only · 4 edge(s)
- [Exclusion Strategies and Builder](exclusion-strategies-and-builder.md) · graph-only · 2 edge(s)

Parent: [Field Binding and Introspection](field-binding-and-introspection.md)

## Units (12)

<a id="u-6905d7ff54a2"></a>
### `ReflectionHelper.java-accessible-object-descriptions`

`public static String getAccessibleObjectDescription( AccessibleObject object, boolean…` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L89-L113][f1]

Produce short human-readable descriptions of reflective members.

getAccessibleObjectDescription dispatches on runtime type: Field yields "field '<declaringClass#name>'" via fieldToString, Method yields "method '<class>#<name>(simple param types)>'", Constructor yields "constructor '<class>(simple param types)>'" via constructorToString, anything else falls back to "<unknown AccessibleObject> " plus toString. appendExecutableParameters writes the parenthesized parameter list with simple class names (uses Method/Constructor casts because Executable is unavailable on old Android). If requested, a leading lowercase letter is uppercased. fieldToString and constructorToString are also public for direct use in error messages elsewhere.

<a id="u-e5fc8649e0aa"></a>
### `ReflectionHelper.java-class-modifier-queries`

`public static boolean isStatic(Class<?> clazz)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L151-L153][f1]

isStatic reports whether a class has the static modifier.

isAnonymousOrNonStaticLocal returns true only for non-static classes that are anonymous or local — i.e. inner classes that cannot be instantiated via a no-arg constructor.

<a id="u-05fbf2c28569"></a>
### `ReflectionHelper.java-record-facade`

`public static boolean isRecord(Class<?> raw)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L182-L184][f1]

Thin static delegates to the RECORD_HELPER instance chosen at class initialization: isRecord, getRecordComponentNames, getAccessor (record accessor Method matching a field name), and getCanonicalRecordConstructor.

Behavior therefore depends on whether the JVM supports records: on a supporting JVM they reflect through the record APIs; otherwise isRecord is always false and the other three throw UnsupportedOperationException.

<a id="u-ff3dfa925ade"></a>
### `ReflectionHelper.java-recordhelper-abstraction`

`class RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L223-L224][f1]

Private abstract base class defining the record-introspection surface (isRecord, component names, canonical constructor, accessor lookup) so the rest of the code can be compiled without java.lang.Record.

Concrete subclasses implement it for record-supporting and non-supporting JVMs.

<a id="u-4264d463db1c"></a>
### `ReflectionHelper.java-recordnotsupportedhelper`

`class RecordNotSupportedHelper extends RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L300-L302][f1]

Fallback record helper for JVMs without record support.

isRecord always returns false; the other three methods throw UnsupportedOperationException with a message stating records are unsupported and the method should not have been called — callers are expected to gate on isRecord first.

<a id="u-46002c75bb3e"></a>
### `ReflectionHelper.java-recordsupportedhelper`

`class RecordSupportedHelper extends RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L233-L234][f1]

Implementation of the record helper for JVMs where the record reflection APIs exist.

Its constructor looks up Class.isRecord, Class.getRecordComponents, and RecordComponent.getName/getType by reflection; any NoSuchMethodException/ClassNotFoundException propagates and triggers the fallback in the enclosing static initializer. isRecord invokes Class.isRecord. getRecordComponentNames returns each component's name in declaration order. getCanonicalRecordConstructor collects component types and calls getDeclaredConstructor (not getConstructor, since the implicit canonical constructor has the record's visibility). getAccessor returns raw.getMethod(field.getName()), relying on the record component accessor having the same name as the field. Every ReflectiveOperationException in these methods is converted by createExceptionForRecordReflectionException into a RuntimeException.

<a id="u-2a7be649f2ab"></a>
### `ReflectionHelper.java-reflectionhelper-class`

`class ReflectionHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L28-L30][f1]

Static utility facade for reflection operations: accessibility, human-readable descriptions of reflective members, class-modifier queries, and a JVM-version-agnostic record API.

A static initializer tries to construct RecordSupportedHelper and falls back to RecordNotSupportedHelper on any ReflectiveOperationException, so record queries never fail merely because the JVM lacks records. Private constructor; all members are static.

<a id="u-27f31a253cc9"></a>
### `ReflectionHelper.java-unexpected-reflection-exceptions`

`public static RuntimeException createExceptionForUnexpectedIllegalAccess( IllegalAcce…` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L199-L207][f1]

Both methods build and throw a RuntimeException for reflection failures considered impossible at their call sites.

createExceptionForUnexpectedIllegalAccess (public) wraps an IllegalAccessException, noting that ReflectionAccessFilter features need Java >= 9 and asking non-filter users to report the bug; it embeds GsonBuildConfig.VERSION. createExceptionForRecordReflectionException (private) wraps a ReflectiveOperationException hit while reflecting on records after support was established, explaining the same.

<a id="u-d28a2f217ddb"></a>
### `ReflectiveTypeAdapterFactory.java-recordadapter`

`class RecordAdapter<T> extends Adapter<T, Object[]>` · [gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java:L592-L593][f2]

Adapter for Java records: the accumulator is a clone of constructorArgsDefaults, an argument array pre-filled with non-null defaults for primitive parameters (PRIMITIVE_DEFAULTS maps each primitive class to its zero value; reference parameters stay null).

The constructor captures the canonical record constructor (access-checked when blocked, else made accessible) and maps component names to argument indices. readField looks up the field's index by its Java name and throws IllegalStateException if a field has no matching record component (unexpected, since components should mirror fields), then delegates to readIntoArray which rejects null for primitive components. finalize invokes the constructor with the accumulated args: IllegalAccessException becomes the unexpected-illegal-access exception; InstantiationException or IllegalArgumentException becomes a RuntimeException naming the constructor and args; InvocationTargetException becomes a RuntimeException wrapping the constructor's own failure cause.

<a id="u-cc8b54b1e7ab"></a>
### `ReflectionHelper.getInaccessibleTroubleshootingSuffix`

`private static String getInaccessibleTroubleshootingSuffix(Exception e)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L46-L57][f1]

Builds a troubleshooting-URL suffix for accessibility failures.

Returns "" unless the exception's class name is exactly java.lang.reflect.InaccessibleObjectException (compared by name for Java 8 compatibility); then it picks the more specific guide ID when the exception message mentions 'to module com.google.gson', and appends 'See <url>' from TroubleshootingGuide.createUrl.

<a id="u-0ee683fe15a7"></a>
### `ReflectionHelper.makeAccessible`

`public static void makeAccessible(AccessibleObject object) throws JsonIOException` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L66-L79][f1]

Makes an AccessibleObject accessible or throws a descriptive JsonIOException.

Calls setAccessible(true); on any Exception it builds a message from getAccessibleObjectDescription, advises increasing visibility or writing a custom TypeAdapter, appends the troubleshooting suffix when the cause is an InaccessibleObjectException, and rethrows with the original as cause.

<a id="u-5492494e6fb9"></a>
### `ReflectionHelper.tryMakeAccessible`

`public static String tryMakeAccessible(Constructor<?> constructor)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L166-L179][f1]

Attempts constructor.setAccessible(true), returning null on success or a non-null error message on failure.

The message names the constructor via constructorToString, suggests an InstanceCreator or custom TypeAdapter, includes the caught exception's message, and appends the InaccessibleObjectException troubleshooting suffix when applicable. Never throws; callers decide how to use the message.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java
