# Null-safe atomic adapters

**Capability.** Wraps atomic, BitSet, Class, and Currency adapters to tolerate JSON null values.

Use when inspecting null-safe adapter wrappers for atomic and related JDK types. Units show NullSafeTypeAdapter and null-safe Atomic/BitSet/Class/Currency adapters.

**Depends on.**

- [Reflective adapter support](reflective-adapter-support.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Java time and SQL adapters](java-time-and-sql-adapters.md) · graph-only · 4 edge(s)
- [Core Gson default adapters](core-gson-default-adapters.md) · graph-only · 2 edge(s)
- [Gson annotation adapter support](gson-annotation-adapter-support.md) · graph-only · 1 edge(s)

Parent: [Built-in Java type adapters](built-in-java-type-adapters.md)

## Units (10)

<a id="u-460b95ad335d"></a>
### `TypeAdapter.java-nullsafetypeadapter`

`class NullSafeTypeAdapter extends TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L299-L300][f1]

Inner wrapper that makes an adapter null-tolerant.

write emits nullValue when the value is null, otherwise delegates to the outer adapter's write. read consumes a NULL token and returns null when peek is NULL, otherwise delegates to the outer adapter's read. toString returns NullSafeTypeAdapter[ plus the outer adapter's toString plus ].

<a id="u-ec5ed92f2839"></a>
### `TypeAdapter.java-typeadapter-7`

`class TypeAdapter<T>` · [gson/src/main/java/com/google/gson/TypeAdapter.java:L249-L292][f1]

Returns this if it is already a NullSafeTypeAdapter; otherwise returns a new NullSafeTypeAdapter wrapping this adapter.

The wrapper handles nulls before delegating.

<a id="u-9a14a26277d8"></a>
### `TypeAdapters.java-atomicboolean-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L323-L327][f2]

Null-safe AtomicBoolean adapter.

Reading wraps nextBoolean in a new AtomicBoolean; writing emits the current boolean value.

<a id="u-b198ef94b541"></a>
### `TypeAdapters.java-atomicinteger-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L288-L292][f2]

Null-safe AtomicInteger adapter.

Reading wraps nextInt in a new AtomicInteger and converts NumberFormatException to JsonSyntaxException. Writing emits the current integer value.

<a id="u-bd7375142952"></a>
### `TypeAdapters.java-atomicintegerarray-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L338-L342][f2]

Null-safe AtomicIntegerArray adapter.

Reading consumes an array, converts each nextInt failure to JsonSyntaxException, then builds an AtomicIntegerArray. Writing emits an array of current integer values.

<a id="u-d22db0bf65fe"></a>
### `TypeAdapters.java-atomiclong-adapter-factory`

`public static TypeAdapter<AtomicLong> atomicLongAdapter(TypeAdapter<Number> longAdapter)` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L309-L312][f2]

Builds a null-safe AtomicLong adapter from a required non-null numeric adapter.

Reading delegates to the numeric adapter and wraps its longValue in AtomicLong; writing delegates the current long value to the numeric adapter.

<a id="u-c5fb1bdf5442"></a>
### `TypeAdapters.java-atomiclongarray-adapter-factory`

`public static TypeAdapter<AtomicLongArray> atomicLongArrayAdapter( TypeAdapter<Number…` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L375-L379][f2]

Builds a null-safe AtomicLongArray adapter from a required non-null numeric adapter.

Reading consumes an array through the delegate; a null element throws JsonSyntaxException, otherwise longValue is stored. Writing emits each current long through the delegate.

<a id="u-154865415faa"></a>
### `TypeAdapters.java-bitset-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L90-L94][f2]

Null-safe BitSet adapter.

Reading expects an array; each element is handled by token:
- NUMBER or STRING: nextInt; 0 clears, 1 sets, other values throw JsonSyntaxException; a non-integer string lets NumberFormatException propagate unwrapped.
- BOOLEAN: nextBoolean sets or clears.
- other token: throws JsonSyntaxException.
Writing emits an array of 0/1 for the bitset length.

<a id="u-21a172d880ed"></a>
### `TypeAdapters.java-class-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L66-L71][f2]

Null-safe adapter for java.lang.Class that rejects non-null values.

Writing throws UnsupportedOperationException naming the class and a troubleshooting URL; reading throws UnsupportedOperationException with a troubleshooting URL. Null is handled by the null-safe wrapper.

<a id="u-cec7e942cbae"></a>
### `TypeAdapters.java-currency-adapter`

`class TypeAdapters` · [gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java:L824-L828][f2]

Null-safe Currency adapter.

Reading parses nextString with Currency.getInstance and converts IllegalArgumentException to JsonSyntaxException with input and path. Writing emits the currency code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/TypeAdapter.java
[f2]: https://github.com/google/gson/blob/e2292f9c9f2e07a4791827e8eea34aa7d80545d6/gson/src/main/java/com/google/gson/internal/bind/TypeAdapters.java
