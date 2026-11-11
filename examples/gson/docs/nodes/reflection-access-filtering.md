# Reflection access filtering

**Capability.** Defines and evaluates filters that decide whether Gson may use reflection on a given class during (de)serialization.

Readers controlling whether reflective access is permitted should consult this module: the ReflectionAccessFilter interface, its standard filter constants, and the internal helper applying them. Outcomes allow, defer, or block with guidance to write custom adapters.

**Depended on by.**

- [Instance construction utilities](instance-construction-utilities.md) · graph-confirmed · 2 edge(s) · Instance construction consults access filters to decide whether reflective instantiation is permitted.
- [Reflective type adapter factory](reflective-type-adapter-factory.md) · graph-only · 3 edge(s)

Parent: [Instance Creation and Access Control](instance-creation-and-access-control.md)

## Units (5)

<a id="u-061eeacbb15d"></a>
### `ReflectionAccessFilter.java-built-in-filters`

`@Override public FilterResult check(Class<?> rawClass)` · [gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:L114-L119][f1]

Four anonymous ReflectionAccessFilter constants.

BLOCK_INACCESSIBLE_JAVA returns BLOCK_INACCESSIBLE for Java types (per ReflectionAccessFilterHelper.isJavaType), else INDECISIVE. BLOCK_ALL_JAVA returns BLOCK_ALL for Java types, else INDECISIVE. BLOCK_ALL_ANDROID returns BLOCK_ALL for Android types, else INDECISIVE. BLOCK_ALL_PLATFORM returns BLOCK_ALL for any platform type, else INDECISIVE. Each overrides toString with a stable descriptive name. The exact class sets covered by the helper predicates are outside this file.

<a id="u-b9a545b6f5d6"></a>
### `ReflectionAccessFilterHelper.java-accesschecker`

`class AccessChecker` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L81-L82][f2]

Version-strategy holder chosen once in a static initializer.

On Java 9+ it reflectively looks up AccessibleObject.canAccess(Object) and installs an anonymous checker that invokes it, wrapping any invocation exception in RuntimeException("Failed invoking canAccess"); if the method is missing (NoSuchMethodException) it falls through. Otherwise it installs a checker that always returns true, assuming access since it cannot be determined.

<a id="u-50ab4cb695c8"></a>
### `ReflectionAccessFilterHelper.java-reflectionaccessfilterhelper`

`class ReflectionAccessFilterHelper` · [gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java:L26-L27][f2]

Internal helper for ReflectionAccessFilter.

Platform detection by class-name prefix: isJavaType matches java./javax.; isAndroidType matches android./androidx. or any Java type; isAnyPlatformType adds kotlin., kotlinx., scala. getFilterResult applies filters in order and returns the first non-INDECISIVE result, defaulting to ALLOW when the list is empty or all are indecisive. canAccess delegates to the AccessChecker singleton.

<a id="u-45a11205c184"></a>
### `FilterResult`

`enum FilterResult` · [gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:L51-L90][f1]

Enum of filter outcomes: ALLOW permits Gson to attempt reflection (Java runtime may still deny); INDECISIVE defers to the next registered filter, acting like ALLOW when none remains; BLOCK_INACCESSIBLE blocks access only when a member would have to be made accessible, unaffected by command-line or module opens (Java 9+ only, limited on older versions); BLOCK_ALL blocks all reflection for the class, requiring other means such as a TypeAdapter.

<a id="u-807e9949c5d3"></a>
### `gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:ReflectionAccessFilter.check (4)`

`FilterResult check(Class<?> rawClass);` · [gson/src/main/java/com/google/gson/ReflectionAccessFilter.java:L227-L227][f1]

The single abstract method of the interface: given a class, returns a FilterResult indicating whether reflection-based (de)serialization may proceed; implementations decide between allowing, deferring, or blocking, and a blocking result causes Gson to throw rather than skip, unlike an ExclusionStrategy.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/ReflectionAccessFilter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/ReflectionAccessFilterHelper.java
