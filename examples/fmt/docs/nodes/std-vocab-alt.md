# Vocabulary Alternative Formatters

**Capability.** Formats optional/expected/unexpected/variant-style wrappers, using write_escaped_alternative to render each alternative with escaping or a debug-enabled underlying formatter, gated by variant/alternative traits.

Use for optional-like and variant-like types; alternatives containing strings or chars are escaped, others delegate to their element formatter.

Parent: [std Type Formatters](std-h.md)

## Units (6)

<a id="u-f9d5bbb8699e"></a>
### `std-h-optional-formatter`

`template <typename T, typename Char> struct formatter<std::optional<T>, Char, std::en…` · [include/fmt/std.h:L370-L382][f1]

Formats std::optional<T> as 'optional(value)' or 'none', enabled only when T is formattable.

parse enables the underlying formatter's debug format via maybe_set_debug_format(underlying_, true) then delegates to its parse, so the value's own spec syntax is accepted. format writes the 'none' literal for an empty optional; otherwise it writes 'optional(', advances the context, formats *opt through underlying_, and appends ')'.

<a id="u-31f08b7b1bee"></a>
### `std-h-expected-formatter`

`template <typename T, typename E, typename Char> struct formatter<std::expected<T, E>…` · [include/fmt/std.h:L402-L407][f1]

Formats std::expected<T, E>, enabled when E is formattable and T is void or formattable.

parse accepts no specs (returns ctx.begin(), so any spec characters are an error downstream). format writes 'expected(' and, when T is not void, the contained value via write_escaped_alternative; on the error path it writes 'unexpected(' and the error via write_escaped_alternative. Either way it closes with ')' and returns the iterator.

calls: [write_escaped_alternative](std-vocab-alt.md#u-7dfa11f868a1)

<a id="u-37128a975a0b"></a>
### `std-h-unexpected-formatter`

`template <typename E, typename Char> struct formatter<std::unexpected<E>, Char, std::…` · [include/fmt/std.h:L429-L432][f1]

Formats std::unexpected<E> as 'unexpected(error)' with the error rendered by write_escaped_alternative (escaped string/char or debug-enabled underlying formatter).

parse accepts no specs. Always appends the closing ')'.

calls: [write_escaped_alternative](std-vocab-alt.md#u-7dfa11f868a1)

<a id="u-265141506f1f"></a>
### `std-h-variant-formatters`

`template <typename Char> struct formatter<std::monostate, Char>` · [include/fmt/std.h:L476-L477][f1]

Formats std::monostate as the literal 'monostate' (parse accepts no specs).

The variant formatter, enabled when the variant is variant-like and all alternatives formattable, writes 'variant(', visits the active alternative formatting it through write_escaped_alternative, and closes with ')'. If visiting throws std::bad_variant_access (a valueless-by-exception variant), the FMT_CATCH handler writes 'valueless by exception' instead of propagating, then the ')' is still appended.

**Notes.**

- failure: Only std::bad_variant_access is caught; other exceptions from alternative formatters propagate.

calls: [write_escaped_alternative](std-vocab-alt.md#u-7dfa11f868a1)

<a id="u-5652e9f5f220"></a>
### `std-h-variant-traits`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/std.h:L148-L152][f1]

Compile-time traits gating variant formatting.

detail::is_variant_like_ is false for all types except specializations of std::variant, which yield true; the public is_variant_like forwards to it. is_variant_formattable<Variant, Char> checks via a private check(std::index_sequence<Is...>) that every variant_alternative_t is formattable in Char, exposing the conjunction's value; it compiles only under FMT_CPP_LIB_VARIANT.

<a id="u-7dfa11f868a1"></a>
### `write_escaped_alternative`

`template <typename Char, typename OutputIt, typename T, typename FormatContext> FMT_C…` · [include/fmt/std.h:L137-L148][f1]

Formats one alternative of an expected/variant with escaping, chosen by type at compile time.

If T has a to-string-view conversion it writes an escaped string via write_escaped_string; if T is exactly Char it writes an escaped character; otherwise it constructs formatter<std::remove_cv_t<T>, Char>, enables its debug format via maybe_set_debug_format(underlying, true), advances the context to out, and returns underlying.format(v, ctx). Compiled only when __cpp_lib_expected or FMT_CPP_LIB_VARIANT is defined.

uses: [std-h-expected-formatter](std-vocab-alt.md#u-31f08b7b1bee), [std-h-variant-formatters](std-vocab-alt.md#u-265141506f1f)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h