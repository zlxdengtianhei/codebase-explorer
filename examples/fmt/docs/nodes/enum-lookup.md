# Enumerator Identifier Lookup

**Capability.** Compile-time construction of dense or open-addressed identifier tables (sized from min enumerator and count) and runtime identifier_of lookup returning string_views.

Use to understand how enumerator names are stored and probed; make_identifier_table and make_identifier_map build the structures, identifier_of queries them.

**Depended on by.**

- [Enum Formatter Dispatch](enum-dispatch.md) · model-inferred · 0 edge(s)

Parent: [Enum Formatting](enum-h.md)

## Units (8)

<a id="u-1a9d33300db0"></a>
### `identifier_of`

`template <typename E> constexpr auto identifier_of(E value) -> std::string_view` · [include/fmt/enum.h:L202-L218][f1]

Runtime lookup of the identifier for an enum value, returning an empty string_view when unmatched.

Two strategies chosen at compile time: if identifier_table_size is nonzero, it indexes the dense table by the unsigned distance from the minimum; out-of-range indices wrap around and are rejected by the bounds check, yielding empty. Otherwise it probes the hash map from identifier_slot(value); a free slot terminates the search and returns its empty identifier, and a slot whose value matches returns its identifier. Unmatched values therefore return empty in both paths.

calls: [identifier_table_size](enum-lookup.md#u-b4f4ddcc0308), [min_enumerator](enum-lookup.md#u-8352ece6d1d7), [identifier_slot](enum-lookup.md#u-7089e6010b0c)

<a id="u-77f057aab253"></a>
### `identifier_map_size`

`template <typename E> consteval auto identifier_map_size() -> size_t` · [include/fmt/enum.h:L158-L162][f1]

Sizes the open-addressed hash table as the smallest power of two at least twice the enumerator count.

The load factor at or below 0.5 guarantees at least one free slot, which terminates linear probing during both construction and lookup.

<a id="u-7089e6010b0c"></a>
### `identifier_slot`

`template <typename E, size_t N = identifier_map_size<E>()> constexpr auto identifier_…` · [include/fmt/enum.h:L167-L174][f1]

Computes the initial probe index for an enum value in the identifier hash map.

It hashes the uint64_t-cast value with a splitmix-style mix (two xor-shift-right steps around a 64-bit odd multiply) and masks with N-1, since only the low bits index the power-of-two table. Bit mixing compensates for enumerator values that typically occupy few low bits.

<a id="u-b4f4ddcc0308"></a>
### `identifier_table_size`

`template <typename E> consteval auto identifier_table_size() -> size_t` · [include/fmt/enum.h:L123-L134][f1]

Chooses between a dense lookup table and a hash map for an enum's identifiers.

Returns 0 for an empty enum or when values are too sparse: it computes the maximum span (largest unsigned distance from the minimum) and accepts a table only when the enumerator count reaches at least 70% density (limit = size*10/7; comparing against the limit instead of incrementing span avoids overflow). Otherwise it returns span+1, the table length, with holes left as empty string views.

<a id="u-dcf85916bdf4"></a>
### `make_identifier_map`

`template <typename E, size_t N = identifier_map_size<E>()> consteval auto make_identi…` · [include/fmt/enum.h:L176-L193][f1]

Builds the compile-time open-addressed (value, identifier) table with linear probing.

For each enumerator it probes from identifier_slot(value), wrapping with (i+1)&(N-1). An occupied slot holding the same value stops insertion, so duplicate enumerator values keep the first name; an occupied slot holding a different value continues probing; an empty slot (empty identifier) receives the entry. Load factor at most 0.5 guarantees termination.

calls: [identifier_slot](enum-lookup.md#u-7089e6010b0c); uses: [identifier_map_size](enum-lookup.md#u-77f057aab253)

<a id="u-23661a3f1cb1"></a>
### `make_identifier_table`

`template <typename E, size_t N = identifier_table_size<E>()> consteval auto make_iden…` · [include/fmt/enum.h:L136-L148][f1]

Builds the compile-time array of enumerator identifiers indexed by distance from the smallest enumerator value.

Each slot starts as an empty string_view; an enumerator writes its identifier only if the slot is still empty, so for duplicate values the first enumerator's name wins. std::meta::identifier_of returns a view of static storage duration, so no copy is needed. N defaults to identifier_table_size<E>() and is 0 in the sparse case, leaving the table unused.

calls: [min_enumerator](enum-lookup.md#u-8352ece6d1d7), [to_uint64](enum-lookup.md#u-974e5371206e); uses: [identifier_table_size](enum-lookup.md#u-b4f4ddcc0308)

<a id="u-8352ece6d1d7"></a>
### `min_enumerator`

`template <typename E> consteval auto min_enumerator() -> E` · [include/fmt/enum.h:L109-L118][f1]

Computes the smallest enumerator value of an enum at compile time.

It iterates std::meta::enumerators_of, extracting each value and keeping the minimum; an enum with no enumerators returns E() instead of a minimum.

<a id="u-974e5371206e"></a>
### `to_uint64`

`template <typename E> constexpr auto to_uint64(E value) -> uint64_t` · [include/fmt/enum.h:L104-L106][f1]

Converts an enum value to uint64_t through its underlying type.

Negative values wrap modulo 2^64, so subtraction of two results yields the unsigned distance between the original values; table-index and span computations rely on this.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/enum.h