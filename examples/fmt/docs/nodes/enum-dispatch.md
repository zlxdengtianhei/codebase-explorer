# Enum Formatter Dispatch

**Capability.** Compile-time annotation detection (is_annotated) and use_identifiers/use_underlying predicates selecting between the identifier-name formatter and the underlying-value formatter.

Read to see how annotation types steer formatter selection; the two formatter specializations are the public entry points for enum formatting.

**Depends on.**

- [Enumerator Identifier Lookup](enum-lookup.md) · model-inferred · 0 edge(s)

Parent: [Enum Formatting](enum-h.md)

## Units (5)

<a id="u-1df930fe79a2"></a>
### `is_annotated`

`template <typename A, typename U> consteval auto is_annotated() -> bool` · [include/fmt/enum.h:L66-L68][f1]

Reports at compile time whether a type carries an annotation of a given type.

It delegates to std::meta::annotations_of_with_type and returns true only when the resulting annotation list is non-empty; consteval evaluation makes the result a compile-time constant.

uses: [use_underlying](enum-dispatch.md#u-0a34bd303952), [use_identifiers](enum-dispatch.md#u-ad740c79a87d)

<a id="u-ad740c79a87d"></a>
### `use_identifiers`

`template <typename T, typename U = remove_cvref_t<T>> consteval auto use_identifiers(…` · [include/fmt/enum.h:L71-L78][f1]

Compile-time predicate deciding identifier-based enum formatting.

After stripping cv/ref qualifiers via its default U, it returns is_annotated<as_identifiers_t, U>() when U is an enum, and false for non-enum types, so such instantiations are valid and select no formatter specialization.

calls: [is_annotated](enum-dispatch.md#u-1df930fe79a2)

<a id="u-0a34bd303952"></a>
### `use_underlying`

`template <typename T, typename U = remove_cvref_t<T>> consteval auto use_underlying()…` · [include/fmt/enum.h:L81-L94][f1]

Compile-time predicate deciding underlying-value enum formatting.

For enums it first static_asserts that as_underlying and as_identifiers are not both applied, giving a clear diagnostic instead of an ambiguous formatter specialization; it then returns whether as_underlying is present. Non-enum types yield false.

**Notes.**

- failure: Applying both as_underlying and as_identifiers to the same enum is a compile-time error via static_assert.

calls: [is_annotated](enum-dispatch.md#u-1df930fe79a2)

<a id="u-ff31f16576d6"></a>
### `enum-h-formatter-as-identifiers`

`template <typename E> struct formatter<E, char, enable_if_t<detail::use_identifiers<E…` · [include/fmt/enum.h:L223-L229][f1]

Formats enums annotated with fmt::as_identifiers as enumerator names, selected by the enable_if on detail::use_identifiers.

parse delegates to an embedded formatter<string_view>, so accepted format specs are string specs. On format, it looks up the name via detail::identifier_of; a non-empty identifier is formatted directly as a string_view. An unmatched value falls back to the underlying value written in decimal into a memory_buffer via detail::write, with unary plus applying integral promotion so char and bool underlying types print as numbers rather than as a character or true/false; the buffer is then formatted through the same string_view impl_, so string presentation specs still apply to the fallback text.

calls: [identifier_of](enum-lookup.md#u-1a9d33300db0)

<a id="u-6c70fcba1656"></a>
### `enum-h-formatter-as-underlying`

`template <typename E, typename Char> struct formatter<E, Char, enable_if_t<detail::us…` · [include/fmt/enum.h:L248-L251][f1]

Formats enums annotated with fmt::as_underlying as their underlying value, selected by the enable_if on detail::use_underlying.

It derives from detail::underlying_formatter<E, Char> (formatter mapped to E's underlying type) so parse and spec handling come from the base. format_as converts a value via underlying(value) and is noexcept; format forwards that underlying value to base::format, so integer presentation specs like width and hex apply to the numeric value.

contract: [use_underlying](enum-dispatch.md#u-0a34bd303952)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/enum.h