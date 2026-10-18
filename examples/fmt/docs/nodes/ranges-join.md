# Join Formatting

**Capability.** join/tuple_join factory overloads and their view formatters that render elements separated by a caller-supplied separator without enclosing brackets.

Call fmt::join to emit separated elements; the factories produce views formatted by the join-view and tuple-join formatters.

**Depends on.**

- [Range Formatters](ranges-formatters.md) · model-inferred · 0 edge(s)

Parent: [Range Formatting](ranges-h.md)

## Units (3)

<a id="u-03c63f3c29c1"></a>
### `ranges-h-join-functions`

`auto join(It begin, Sentinel end, string_view sep) -> join_view<It, Sentinel>` · [include/fmt/ranges.h:L850-L852][f1]

Public join factory overloads producing join or tuple_join views.

The first takes an iterator pair [begin, end) plus sep and returns a join_view (Char defaults to char). The second takes a non-tuple-like range (FMT_ENABLE_IF on !is_tuple_like) and builds a join_view from detail::range_begin/range_end, with the range parameter marked FMT_LIFETIMEBOUND; the file also enables a clang diagnostic error for -Wreturn-stack-address, so returning a view over a temporary range is intended to fail compilation. The third takes a tuple-like value (FMT_LIFETIMEBOUND, const reference stored in the view) and returns a tuple_join_view<Tuple, char>. The fourth, deprecated overload takes std::initializer_list<T> and forwards to the iterator-pair overload with std::begin/std::end. None of them copy elements.

uses: [ranges-h-join-view-formatter](ranges-join.md#u-b71d5531e486), [ranges-h-tuple-join-formatter](ranges-join.md#u-ede80bc97dea)

<a id="u-b71d5531e486"></a>
### `ranges-h-join-view-formatter`

`template <typename It, typename Sentinel, typename Char> struct formatter<join_view<I…` · [include/fmt/ranges.h:L681-L699][f1]

Formats an iterator range with a caller-supplied separator and no brackets.

join_view stores begin, end, and sep and derives from detail::view. The formatter's value_type comes from std::iter_value_t or iterator_traits; the stored view is a const reference when It is copy constructible, otherwise a by-value copy (so move-only iterators still work). parse delegates to the per-value formatter. format: an empty range returns ctx.out() unchanged; it formats the first element, then for each remaining element copies the separator, advances the context, and formats the element; it inserts nothing before the first or after the last. The nonlocking alias is declared.

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538)

<a id="u-ede80bc97dea"></a>
### `ranges-h-tuple-join-formatter`

`template <typename Tuple, typename Char> struct formatter<tuple_join_view<Tuple, Char…` · [include/fmt/ranges.h:L739-L742][f1]

Formats a tuple with a caller-supplied separator and no brackets.

tuple_join_view holds a const reference to the tuple plus sep, deriving from detail::view. Specifier support is experimental and gated by FMT_TUPLE_JOIN_SPECIFIERS (0 by default): parse forwards to do_parse, which returns ctx.begin() unchanged when the macro is off (both the N=0 base and the recursive case return the untouched begin), so no spec text is consumed; with the macro on it parses each element formatter's specs recursively and report_error("incompatible format specs for tuple elements") fires if the element parses disagree. format forwards to do_format, which recurses from N=tuple_size down: it formats element index tuple_size-N via the matching formatter, and after each element except the last copies sep and advances the context; the N=0 base returns ctx.out().

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538), [report_error](core-errors.md#u-4fe75221d1d1)

**Uncertainties.**

- The FMT_TUPLE_JOIN_SPECIFIERS=1 code path is compiled out by default, so its runtime behavior is not established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h