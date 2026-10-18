# Exclusion and Reflection Policy

**Capability.** Decides what Gson may reflect on and serialize: the ExclusionStrategy contract and its Excluder implementation (version, modifier, Expose, inner/anonymous-class rules), the FieldNamingStrategy contract, ReflectionAccessFilter with its platform-detection helper, and the low-level reflection helpers (accessibility, member descriptions, record support, constructor-less instantiation).

Use this subtree to understand which fields/classes are omitted, how member names are derived, and how reflection access is filtered or performed across JVM versions.

**Depends on.**

- [Gson Facade and Conversion API](r1-facade-api.md) · graph-confirmed · 1 edge(s) · Excluder.create delegates to Gson.getDelegateAdapter when wiring into the factory chain.
- [Runtime Generic Type Model](r1-type-model.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [ReflectiveTypeAdapterFactory](r2-reflective-type-adapter-factory.md) · graph-only · 26 edge(s) · Reflective binding resolves field names, exclusion, and accessibility via the Excluder and reflection policy contracts.
- [Builder and Naming Configuration](r2-configuration.md) · graph-only · 7 edge(s)
- [Object Construction Strategy](r2-object-construction.md) · graph-only · 6 edge(s)

Parent: [Gson JSON Binding Library](r1-gson-root.md)

## Units (26)

<a id="u-9e4317139aec"></a>
### `exclusionstrategy-java`

`boolean shouldSkipField(FieldAttributes f);` · [gson/src/main/java/com/google/gson/ExclusionStrategy.java:L102-L102][f1]

Defines a serialization/deserialization exclusion policy implemented as a two-method interface.

Implementations decide per field and per class whether Gson should skip them: shouldSkipField receives a FieldAttributes wrapper and returns true to ignore that field; shouldSkipClass receives a Class and returns true to ignore the whole class. The Javadoc shows typical strategies (exclude by class type or annotation) and registration via GsonBuilder methods for global, deserialization-only, or serialization-only exclusion. Graph evidence shows Gson's internal Excluder invokes both callbacks, so returning true suppresses output or input for the tested member.

uses: [fieldattributes-java](r2-public-api.md#u-72f87f0ef005), [Excluder.excludeClass](r1-reflection-policy.md#u-5e55a6a62a63), [excluder.java-exclusion-predicates](r1-reflection-policy.md#u-cd0a9969382b)

<a id="u-cd33229a9c3f"></a>
### `Excluder`

`class Excluder implements TypeAdapterFactory, Cloneable` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L49-L60][f2]

Configurable selector deciding which Gson fields and types to omit, operating as a TypeAdapterFactory and Cloneable builder.

Holds configuration state: version cutoff (default IGNORE_VERSIONS = -1.0), excluded modifier mask (default TRANSIENT|STATIC), serializeInnerClasses (default true), requireExpose (default false), and per-direction ExclusionStrategy lists (default empty). A shared DEFAULT instance exists with these defaults. Mutators in the fluent-builder group produce modified clones; exclusion decisions live in the predicate group and excludeClass; adapter creation lives in create.

group: [excluder.java-fluent-builders](r1-reflection-policy.md#u-c804607c3278), [excluder.java-exclusion-predicates](r1-reflection-policy.md#u-cd0a9969382b), [Excluder.create](r1-reflection-policy.md#u-fd6e9952f274)

<a id="u-c804607c3278"></a>
### `excluder.java-fluent-builders`

`@Override protected Excluder clone()` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L60-L67][f2]

Fluent configuration methods that each copy the Excluder via clone() and change exactly one aspect of the copy, leaving the receiver untouched.

withVersion sets the version cutoff; withModifiers ORs all given modifier bits into a fresh mask starting from 0; disableInnerClassSerialization sets serializeInnerClasses to false; excludeFieldsWithoutExposeAnnotation sets requireExpose to true; withExclusionStrategy appends the strategy to a fresh copy of the serialization list when serialization is true and to the deserialization list when deserialization is true (both flags may be set, neither may be). clone() delegates to super.clone() and wraps the impossible CloneNotSupportedException in an AssertionError; this cannot fire because Excluder implements Cloneable.

<a id="u-cd0a9969382b"></a>
### `excluder.java-exclusion-predicates`

`private boolean isExcludedByModifier(Field field)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L167-L169][f2]

Predicate helpers backing excludeField and excludeClass.

isExcludedByModifier returns true when the configured modifier mask intersects the field's modifiers. isExcludedByVersion applies only when a version is configured (version != IGNORE_VERSIONS) and the field's Since/Until do not form a valid range. isExcludedByExposeAnnotation applies only when requireExpose is set: a missing @Expose excludes, and a present annotation excludes when the flag for the current direction (serialize()/deserialize()) is false. isExcludedByStrategy uses the direction's strategy list; an empty list returns false immediately, otherwise it wraps the field in a FieldAttributes and returns true on the first strategy whose shouldSkipField is true. isInnerClass is true for non-static member classes. isValidVersion is isValidSince AND isValidUntil: a present @Since requires version >= its value; a present @Until requires version < its value; absent annotations are always valid.

<a id="u-fd6e9952f274"></a>
### `Excluder.create`

`@Override public <T> TypeAdapter<T> create(Gson gson, TypeToken<T> type)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L110-L128][f2]

TypeAdapterFactory entry point: decides whether a type is fully/partially excluded and returns an adapter or null.

It evaluates excludeClass(rawType, true) and excludeClass(rawType, false). If neither direction is excluded it returns null, letting later factories handle the type. Otherwise it returns an anonymous adapter: read skips the incoming value and returns null when skipDeserialize; write emits a JSON null and returns when skipSerialize; in the non-excluded direction both delegate. The delegate is obtained lazily and cached in a volatile field via gson.getDelegateAdapter(Excluder.this, type), because obtaining it may fail and Gson promises thread safety; a race may assign the field multiple times but the last assignment wins.

**Uncertainties.**

- Behavior of gson.getDelegateAdapter for an already-registered Excluder is defined in Gson.java, outside this batch.

<a id="u-5e55a6a62a63"></a>
### `Excluder.excludeClass`

`public boolean excludeClass(Class<?> clazz, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L199-L234][f2]

Decides whether a whole class is omitted for the given direction, checking in order: version mismatch of the class's own Since/Until annotations (same range rules as fields); inner-class exclusion when serializeInnerClasses is false and the class is a non-static member class; and, only for deserialization, exclusion of anonymous and non-static local classes that are not enum subclasses, via ReflectionHelper.isAnonymousOrNonStaticLocal — serialization deliberately allows these because a custom adapter may exist, while deserialization cannot be made reliable since adapters like the collection adapter may create instances via Unsafe.

Finally each strategy of the direction's list is consulted via shouldSkipClass, returning true on the first hit; otherwise false.

**Uncertainties.**

- ReflectionHelper.isAnonymousOrNonStaticLocal's exact detection criteria are outside this batch.

<a id="u-e8afb68b3259"></a>
### `Excluder.excludeField`

`public boolean excludeField(Field field, boolean serialize)` · [gson/src/main/java/com/google/gson/internal/Excluder.java:L158-L165][f2]

Decides whether a single field is omitted for the given direction (serialize true/false) as a short-circuiting OR of: a configured modifier bit set on the field, a version mismatch on its Since/Until annotations, the field being synthetic, failing the Expose requirement, the field's declared type being an excluded class, or a per-direction ExclusionStrategy skipping it.

Order matters only for cost, since any true wins; the result feeds reflective field inclusion in ReflectiveTypeAdapterFactory.

<a id="u-1d2a847ffab9"></a>
### `fieldnamingstrategy-interface`

`public interface FieldNamingStrategy` · [gson/src/main/java/com/google/gson/FieldNamingStrategy.java:L34-L43][f3]

Defines the Gson field-naming contract that translates Java reflection Field objects into JSON member names.

The abstract translateName(Field) must be implemented by strategies; ReflectiveTypeAdapterFactory calls it when serializing fields. The default alternateNames(Field) returns an empty list, meaning no extra deserialization aliases unless overridden; the same factory consults it for @SerializedName.alternate-like behavior. Implementations are user-supplied, so no exception behavior can be asserted here.

**Notes.**

- contract: alternateNames returns Collections.emptyList() by default, so strategies that do not override it contribute no deserialization aliases.

uses: [ReflectiveTypeAdapterFactory.getFieldNames](r2-reflective-type-adapter-factory.md#u-d7cfdfc44369)

**Uncertainties.**

- The exact JSON-name semantics of translateName (e.g., null handling or empty results) depend on implementations not present in this file.

<a id="u-717924398e61"></a>
### `reflectionaccessfilter-interface-and-helpers`

`public interface ReflectionAccessFilter` · [gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:L45-L51][f4]

Defines a filter interface deciding whether Gson may use reflection for a class, plus its result type and four ready-made filters.

FilterResult has four outcomes: ALLOW permits reflection (Java's own access checks still apply); INDECISIVE defers to the next registered filter and acts like ALLOW if none remains; BLOCK_INACCESSIBLE blocks only when a member is not accessible by default and would need setAccessible — it deliberately ignores command-line --add-opens and module 'opens' directives and only works on Java 9+ (behaving closer to ALLOW on older versions); BLOCK_ALL forbids reflection entirely, forcing a TypeAdapter or similar. Unlike an ExclusionStrategy, a disallowing filter causes an exception rather than skipping. The four constants delegate to ReflectionAccessFilterHelper: BLOCK_INACCESSIBLE_JAVA returns BLOCK_INACCESSIBLE for classes the helper classifies as java/javax types and INDECISIVE otherwise; BLOCK_ALL_JAVA returns BLOCK_ALL for java/javax types; BLOCK_ALL_ANDROID uses isAndroidType (android/androidx plus java/javax) for BLOCK_ALL; BLOCK_ALL_PLATFORM uses isAnyPlatformType (java, android, and other language platforms like kotlin) for BLOCK_ALL. Each anonymous filter's toString names itself, e.g. ReflectionAccessFilter#BLOCK_ALL_JAVA. The coverage sets may expand without notice.

**Notes.**

- contract: Registered via GsonBuilder.addReflectionAccessFilter; filters are consulted in registration order until one is decisive.
- failure: A filter returning BLOCK_INACCESSIBLE or BLOCK_ALL causes Gson to throw rather than silently skip, which is the key difference from ExclusionStrategy.

calls: [ReflectionAccessFilterHelper.isJavaType](r1-reflection-policy.md#u-21e2b04f26ae), [ReflectionAccessFilterHelper.isAndroidType](r1-reflection-policy.md#u-c55520342054), [ReflectionAccessFilterHelper](r1-reflection-policy.md#u-55b6301124d4)

**Uncertainties.**

- Exact platform-class detection rules are inside ReflectionAccessFilterHelper and cannot be confirmed from this file.
- BLOCK_INACCESSIBLE's pre-Java-9 degradation is documented but its precise behavior there is not implemented in this file.

<a id="u-55b6301124d4"></a>
### `ReflectionAccessFilterHelper`

`class ReflectionAccessFilterHelper` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L26-L27][f5]

Static helper for ReflectionAccessFilter offering platform-type detection and filter evaluation.

isJavaType matches class names starting with "java." or "javax."; isAndroidType additionally matches "android." and "androidx." (and includes Java types); isAnyPlatformType extends that with "kotlin.", "kotlinx.", and "scala." prefixes. Detection is by class-name prefix only, modeled on Moshi's platform-type check. canAccess is covered by the AccessChecker unit; getFilterResult has its own unit. Private constructor prevents instantiation.

**Uncertainties.**

- Prefix matching means classes like 'javax.servlet...' count as Java types even when provided by an app server.

<a id="u-8f899af6c7fc"></a>
### `AccessChecker`

`class AccessChecker` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L81-L93][f5]

Version-adapted access check selected once in a static initializer.

On Java 9+ it reflectively looks up AccessibleObject.canAccess(Object); if found, its checker invokes that method reflectively and returns the boolean, wrapping any invocation failure in RuntimeException("Failed invoking canAccess"). A NoSuchMethodException is ignored, falling through to the fallback checker that unconditionally returns true because accessibility cannot be determined. On pre-9 runtimes only the fallback is installed. The chosen instance is stored in the static final INSTANCE used by canAccess.

**Uncertainties.**

- JavaVersion.isJava9OrLater is defined outside this batch.

<a id="u-862d5415c1c9"></a>
### `ReflectionAccessFilterHelper.canAccess`

`@SuppressWarnings("InvalidLink") // suppress Error Prone warning about link to Java 9…` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L76-L79][f5]

Delegates to the version-specific AccessChecker.INSTANCE, mirroring AccessibleObject.canAccess(Object) from Java 9+.

On runtimes without that API the checker's fallback reports everything as accessible, so callers must not rely on it for access enforcement pre-9.

<a id="u-fb4c4e1a4f55"></a>
### `ReflectionAccessFilterHelper.getFilterResult`

`public static FilterResult getFilterResult( List<ReflectionAccessFilter> reflectionFi…` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L64-L73][f5]

Applies the given filters in list order, returning the first FilterResult other than INDECISIVE.

If the list is empty or every filter returns INDECISIVE, it returns FilterResult.ALLOW, so absence of a decisive filter means reflective access is permitted. Filter implementations come from ReflectionAccessFilter.check outside this batch.

**Uncertainties.**

- Semantics of each FilterResult value are defined in ReflectionAccessFilter, outside this batch.

<a id="u-c55520342054"></a>
### `ReflectionAccessFilterHelper.isAndroidType`

`public static boolean isAndroidType(Class<?> c)` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L41-L43][f5]

Public entry converting the Class to its name for the string overload, which returns true for names starting with "android." or "androidx." and otherwise falls back to isJavaType, so all java./javax.

classes count as Android platform types too.

<a id="u-21e2b04f26ae"></a>
### `ReflectionAccessFilterHelper.isJavaType`

`public static boolean isJavaType(Class<?> c)` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L33-L35][f5]

Public entry that converts the Class to its name and delegates to the private string overload, which returns true for names starting with "java." or "javax." and false otherwise; non-Class Types are not involved since the input is already a Class.

<a id="u-580064b5eb25"></a>
### `ReflectionHelper`

`class ReflectionHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L28-L44][f6]

Internal reflection helpers for Gson: accessibility handling, human-readable member descriptions, class modifiers checks, and record support.

A static initializer selects a RECORD_HELPER implementation once: RecordSupportedHelper is constructed reflectively, and if that throws ReflectiveOperationException (records unsupported) RecordNotSupportedHelper is used instead. The public record methods delegate to whichever implementation was chosen.

uses: [reflectionhelper-record-abstraction](r1-reflection-policy.md#u-0864658a6e4a)

<a id="u-54a5fb178011"></a>
### `reflectionhelper-classifier-helpers`

`public static boolean isStatic(Class<?> clazz)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L151-L153][f6]

Class modifier checks.

isStatic reports Modifier.isStatic of the class modifiers. isAnonymousOrNonStaticLocal is true only when the class is not static and is either anonymous or a local class; static nested or ordinary member classes do not match.

<a id="u-0864658a6e4a"></a>
### `reflectionhelper-record-abstraction`

`class RecordHelper` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L223-L224][f6]

Record-reflection abstraction behind RECORD_HELPER.

RecordHelper is the abstract contract (isRecord, getRecordComponentNames, getCanonicalRecordConstructor, getAccessor). RecordSupportedHelper is chosen when its constructor can reflectively look up Class.isRecord, Class.getRecordComponents, and java.lang.reflect.RecordComponent's getName/getType; its isRecord invokes the reflective method, getRecordComponentNames maps each record component to its name, getCanonicalRecordConstructor reads each component's type and calls getDeclaredConstructor with those types (visibility may be non-public), and getAccessor calls raw.getMethod(field.getName()) relying on the JLS record naming convention. All ReflectiveOperationExceptions in these paths are rethrown by createExceptionForRecordReflectionException. RecordNotSupportedHelper, used on JVMs without records, returns false from isRecord and throws UnsupportedOperationException('Records are not supported on this JVM...') from the other three methods.

raises: [reflectionhelper-record-exception-factories](r1-reflection-policy.md#u-2a0f9c033ddd)

**Uncertainties.**

- Whether Class.isRecord invoked reflectively on a non-record class can itself fail is not provable here; if it did, it would surface via the unexpected-failure wrapper.

<a id="u-2a0f9c033ddd"></a>
### `reflectionhelper-record-exception-factories`

`public static RuntimeException createExceptionForUnexpectedIllegalAccess( IllegalAcce…` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L199-L207][f6]

Two factories for unexpected-failure RuntimeExceptions, both wrapping the original exception and embedding the Gson version from GsonBuildConfig.

createExceptionForUnexpectedIllegalAccess is used when an IllegalAccessException appears where Java 9+ module semantics were assumed, blaming ReflectionAccessFilter requiring Java >= 9. createExceptionForRecordReflectionException wraps ReflectiveOperationException thrown after records were already established as supported, labeling it unexpected behavior.

<a id="u-b5a5fd80dd89"></a>
### `reflectionhelper-tostring-helpers`

`public static String fieldToString(Field field)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L116-L118][f6]

String-representation helpers.

fieldToString returns 'declaringClassName#fieldName', omitting modifiers and the field type. constructorToString returns the declaring class name followed by '(simpleTypeName, ...)' of its parameters, e.g. 'java.lang.String(char[], int, int)'. appendExecutableParameters appends the parenthesized comma-separated simple parameter type names to a builder, taking parameter types from Method.getParameterTypes when the object is a Method and Constructor.getParameterTypes otherwise (the Executable type is avoided for old Android API levels).

<a id="u-a4b7fca6ffeb"></a>
### `ReflectionHelper.getAccessibleObjectDescription`

`public static String getAccessibleObjectDescription( AccessibleObject object, boolean…` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L89-L113][f6]

Produces a compact human-readable description of an AccessibleObject.

Fields are rendered via fieldToString; methods as 'declaringClass#name(paramSimpleNames)'; constructors via constructorToString; anything else falls back to '<unknown AccessibleObject> ' plus toString. When uppercaseFirstLetter is true and the first character is lowercase, it is uppercased. If the description is empty and uppercasing is requested, charAt(0) would throw StringIndexOutOfBoundsException.

calls: [reflectionhelper-tostring-helpers](r1-reflection-policy.md#u-b5a5fd80dd89)

**Uncertainties.**

- Whether the empty-description uppercase path is reachable depends on the fallback branches; the fallback always produces a non-empty prefix.

<a id="u-cc8b54b1e7ab"></a>
### `ReflectionHelper.getInaccessibleTroubleshootingSuffix`

`private static String getInaccessibleTroubleshootingSuffix(Exception e)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L46-L57][f6]

Builds a troubleshooting-guide URL suffix for accessibility failures.

If the exception's class name equals 'java.lang.reflect.InaccessibleObjectException' (name comparison because the class is Java 9+), it picks the troubleshooting id 'reflection-inaccessible-to-module-gson' when the message contains 'to module com.google.gson', otherwise 'reflection-inaccessible', and returns a newline plus the guide URL. Any other exception yields an empty string.

calls: [TroubleshootingGuide](r2-infrastructure.md#u-9bcd073a2728)

<a id="u-0ee683fe15a7"></a>
### `ReflectionHelper.makeAccessible`

`public static void makeAccessible(AccessibleObject object) throws JsonIOException` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L66-L79][f6]

Calls setAccessible(true) on the given AccessibleObject; on success it returns normally.

If any exception occurs, it throws JsonIOException whose message includes the object description, advice to increase visibility or supply a custom TypeAdapter, and the troubleshooting suffix from getInaccessibleTroubleshootingSuffix, with the original exception as cause.

calls: [ReflectionHelper.getAccessibleObjectDescription](r1-reflection-policy.md#u-a4b7fca6ffeb), [ReflectionHelper.getInaccessibleTroubleshootingSuffix](r1-reflection-policy.md#u-cc8b54b1e7ab)

<a id="u-5492494e6fb9"></a>
### `ReflectionHelper.tryMakeAccessible`

`public static String tryMakeAccessible(Constructor<?> constructor)` · [gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java:L166-L179][f6]

Attempts constructor.setAccessible(true) without throwing.

Returns null on success; on any exception returns a message naming the constructor (via constructorToString), advising an InstanceCreator or TypeAdapter, followed by the underlying exception message and the troubleshooting suffix.

calls: [reflectionhelper-tostring-helpers](r1-reflection-policy.md#u-b5a5fd80dd89)

<a id="u-ef1c93c904c0"></a>
### `UnsafeAllocator`

`class UnsafeAllocator` · [gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java:L30-L31][f7]

Allocates objects without invoking constructors, choosing at class-load time among three mechanisms in order: sun.misc.Unsafe.allocateInstance, the Android post-Gingerbread ObjectStreamClass native pair getConstructorId/newInstance (constructor id captured once for Object.class), and the pre-Gingerbread ObjectInputStream.newInstance native method.

Each failing attempt is swallowed with 'Exception ignored' and the next is tried; if all fail, the fallback allocator's newInstance throws UnsupportedOperationException stating sun.misc.Unsafe could not be used. Every successful variant first calls assertInstantiable, which delegates to ConstructorConstructor.checkInstantiable and throws AssertionError for interfaces or abstract classes, as a safeguard because Unsafe allocation of such types can crash some JVMs. newInstance is abstract on the base class; INSTANCE is created eagerly by the private static create(). Members folded: abstract newInstance, assertInstantiable, INSTANCE, create, and all four anonymous newInstance implementations described above.

**Notes.**

- failure: Initialization failures of the reflection lookups are silently ignored by design; only newInstance-time failures surface.
- side_effect: The Android variants call setAccessible(true) on private native methods when INSTANCE is initialized.

calls: [ConstructorConstructor.checkInstantiable](r2-object-construction.md#u-8f68b29ba616)

**Uncertainties.**

- The getConstructorId/newInstance native calls could fail at allocation time in ways not caught here; only reflective lookup failures are handled at create() time.

<a id="u-5ccd0bddbe37"></a>
### `ObjectConstructor`

`public interface ObjectConstructor<T>` · [gson/src/main/java/com/google/gson/internal/ObjectConstructor.java:L27-L30][f8]

Generic factory interface whose single construct() method returns a new instance of T.

Its documented purpose is to produce default instances used for object navigation during JSON deserialization. Implementations decide how instances are created; this file defines no behavior beyond the contract.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ExclusionStrategy.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/Excluder.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/FieldNamingStrategy.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ReflectionAccessFilter.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java
[f6]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/reflect/ReflectionHelper.java
[f7]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/UnsafeAllocator.java
[f8]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ObjectConstructor.java