# Internal Java utilities

**Capability.** Groups internal helpers for Java version detection, lazy numbers, non-null lists, number limits, and date formats.

Use for low-level internal utility behavior. Units show Java version caching, LazilyParsedNumber, non-null list wrapper, number limits, and pre-Java-9 date formats.

**Depended on by.**

- [JSON primitive values](json-primitive-values.md) · graph-confirmed · 2 edge(s)
- [Basic Java type adapters](basic-java-type-adapters.md) · graph-only · 2 edge(s)

Parent: [Primitive values and utilities](primitive-values-and-utilities.md)

## Units (14)

<a id="u-876445e8cdc2"></a>
### `JavaVersion.java-java-version-accessors`

`class JavaVersion` · [gson/src/main/java/com/google/gson/internal/JavaVersion.java:L75-L82][f1]

These declarations expose the cached major Java version and a Java 9-or-later predicate.

The cached value is computed once during class initialization; the first accessor returns that integer, and the second returns true exactly when it is at least 9. Parsing failure in the initializer falls back to 6, so both accessors reflect that fallback. No per-call parsing or system-property read occurs.

<a id="u-0b16931f5518"></a>
### `JavaVersion.java-java-version-parsing`

`private static int determineMajorJavaVersion()` · [gson/src/main/java/com/google/gson/internal/JavaVersion.java:L28-L31][f1]

Reads java.version and derives a major version with fallbacks.

determineMajorJavaVersion passes the system property to parseMajorJavaVersion. parseMajorJavaVersion first tries dotted parsing; if that returns -1 it tries leading-integer extraction; if both fail it returns 6 as the minimum supported default. parseDotted splits on '.' or '_' with a limit of three, parses the first part, and for legacy 1.x returns the second part when present; any NumberFormatException yields -1. extractBeginningInt collects leading digits until the first non-digit and parses them; an empty or non-numeric prefix yields -1. A null version string is not caught and would fail during split.

<a id="u-ffda8fe9d95d"></a>
### `JavaVersion.java-javaversion-class-and-accessors`

`class JavaVersion` · [gson/src/main/java/com/google/gson/internal/JavaVersion.java:L20-L26][f1]

Caches the JVM major version once at class initialization and exposes it through simple accessors.

The cached value is produced by reading the java.version system property and parsing it; getMajorJavaVersion returns that cached integer, isJava9OrLater returns whether it is at least 9, and the private constructor prevents instantiation.

<a id="u-791ddda39cfd"></a>
### `LazilyParsedNumber.java-lazilyparsednumber-class-and-constructor`

`class LazilyParsedNumber extends Number implements Comparable<LazilyParsedNumber>` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L28-L30][f2]

Holds a number as its original string and converts only when a numeric view is requested.

The constructor stores the supplied string without a null check, despite the parameter documentation saying it must not be null.

<a id="u-dc6ea1cb665f"></a>
### `LazilyParsedNumber.java-numeric-conversions`

`private BigDecimal asBigDecimal()` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L39-L41][f2]

Converts the stored string to primitive numeric values, with fallback paths that can still fail.

asBigDecimal delegates to NumberLimits.parseBigDecimal, so it can throw NumberFormatException for strings longer than 10,000 characters or with absolute scale at least 10,000. intValue first tries Integer.parseInt; on failure it tries Long.parseLong and casts the result to int; if that also fails it calls asBigDecimal().intValue(), which may throw the same limit or syntax NumberFormatException. longValue tries Long.parseLong and on failure calls asBigDecimal().longValue(), which may throw. floatValue and doubleValue use Float.parseFloat and Double.parseDouble directly.

<a id="u-dbb6224b3f68"></a>
### `LazilyParsedNumber.java-serialization-behavior`

`private Object writeReplace()` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L84-L86][f2]

writeReplace returns a BigDecimal produced by asBigDecimal, so serialization can throw NumberFormatException for invalid or over-limit strings instead of always substituting a value.

readObject always throws InvalidObjectException to prevent direct deserialization of this class.

<a id="u-f53d0cb30b08"></a>
### `LazilyParsedNumber.java-value-semantics`

`@Override public String toString()` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L75-L78][f2]

toString returns the original string.

compareTo compares the stored strings lexicographically, so it is not a numeric comparison. hashCode uses the string hash. equals returns true for the same instance or another LazilyParsedNumber with an equal stored string, and false for any other type.

<a id="u-b419075a6d55"></a>
### `NonNullElementWrapperList.java-non-null-insertion`

`private E nonNull(E element)` · [gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java:L53-L58][f3]

nonNull throws NullPointerException with message 'Element must be non-null' when given null.

set and add call nonNull before delegating, so they reject null elements; set returns the previous element from the delegate and add inserts at the requested index.

<a id="u-5e13c8895b91"></a>
### `NonNullElementWrapperList.java-nonnullelementwrapperlist-class-and-constructor`

`class NonNullElementWrapperList<E> extends AbstractList<E> implements RandomAccess` · [gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java:L34-L36][f3]

Wraps an ArrayList and prevents insertion of null elements while implementing RandomAccess.

The constructor requires a non-null delegate via Objects.requireNonNull. Most read and bulk operations delegate directly to the wrapped list, including get, size, remove, clear, removeAll, retainAll, removeIf, contains, indexOf, lastIndexOf, toArray, sort, spliterator, equals, and hashCode.

<a id="u-c546b13cd45a"></a>
### `NumberLimits.java-numberlimits`

`class NumberLimits` · [gson/src/main/java/com/google/gson/internal/NumberLimits.java:L10-L11][f4]

Enforces limits on number strings parsed from JSON.

checkNumberStringLength throws NumberFormatException when the string length exceeds 10,000, including a truncated prefix in the message. parseBigDecimal checks length, constructs a BigDecimal, then throws NumberFormatException when the absolute scale is at least 10,000; otherwise returns the decimal. parseBigInteger checks length and returns a BigInteger. Syntax errors from BigDecimal or BigInteger propagate as NumberFormatException.

<a id="u-6a7724ab5af0"></a>
### `PreJava9DateFormatProvider.java-prejava9dateformatprovider`

`class PreJava9DateFormatProvider` · [gson/src/main/java/com/google/gson/internal/PreJava9DateFormatProvider.java:L23-L24][f5]

Provides US-locale date-time formats matching Java 8 defaults.

getUsDateTimeFormat combines a date pattern and a time pattern with a space and returns a SimpleDateFormat for Locale.US. Date styles map as: SHORT M/d/yy; MEDIUM MMM d, yyyy; LONG MMMM d, yyyy; FULL EEEE, MMMM d, yyyy. Time styles map as: SHORT h:mm a; MEDIUM h:mm:ss a; LONG and FULL h:mm:ss a z. An unknown date or time style throws IllegalArgumentException.

<a id="u-041cf0c4e000"></a>
### `gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:LazilyParsedNumber (2)`

`class LazilyParsedNumber extends Number implements Comparable<LazilyParsedNumber>` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L92-L100][f2]

This declaration documents lexicographical ordering of the stored numeric string, not numeric ordering.

Comparison uses the raw string values, so values such as '10' and '2' order by text. Equality and hash code are also string-based; numeric comparison requires converting both sides to BigDecimal.

<a id="u-3b2717f7e4a6"></a>
### `gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:LazilyParsedNumber (4)`

`class LazilyParsedNumber extends Number implements Comparable<LazilyParsedNumber>` · [gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java:L78-L84][f2]

This declaration documents serialization replacement for the lazily parsed number.

It replaces the instance with a BigDecimal produced through the same bounded parser used by numeric conversion. That parser can throw NumberFormatException for invalid strings, strings longer than 10,000 characters, or absolute scale at least 10,000; the replacement is not a safe fallback for such values. Direct deserialization is rejected separately with InvalidObjectException.

<a id="u-cf949721357e"></a>
### `gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java:NonNullElementWrapperList.remove`

`@SuppressWarnings("UngroupedOverloads") // this is intentionally ungrouped, see comme…` · [gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java:L82-L86][f3]

This override delegates removal by value directly to the wrapped list and returns whether an element was removed.

It performs no non-null validation, so a null argument is passed through; because the wrapper normally prevents null insertion, null usually matches nothing unless the underlying list was mutated externally. The side effect is removal of the first matching element from the delegate.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/JavaVersion.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/LazilyParsedNumber.java
[f3]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/NonNullElementWrapperList.java
[f4]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/NumberLimits.java
[f5]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/PreJava9DateFormatProvider.java
