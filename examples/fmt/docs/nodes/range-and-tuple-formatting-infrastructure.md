# Range and Tuple Formatting Infrastructure

**Capability.** Provides range/tuple detection, formatter selection, join views, and tuple formatting helpers used by fmt range formatting.

Consult this module for ranges.h infrastructure that classifies tuple-like and container-adaptor types and builds formatters. It includes join views, tuple formatter storage, index expansion helpers, and public tuple traits.

**Depends on.**

- [Format Spec Parser](format-spec-parser.md) · graph-only · 1 edge(s)

Parent: [Range and Tuple Formatting](range-and-tuple-formatting.md)

## Units (16)

<a id="u-c39686bbda4c"></a>
### `ranges.h-conjunction`

`template <typename...> struct conjunction : std::true_type` · [include/fmt/ranges.h:L390-L390][f1]

Metafunction conjunction: empty pack is true, a single predicate inherits that predicate, and a multi-predicate pack inherits the first false predicate or the conjunction of the rest when the first is true.

<a id="u-4f44d76e38a9"></a>
### `ranges.h-empty-spec-parser`

`template <typename Char> struct parse_empty_specs` · [include/fmt/ranges.h:L265-L266][f1]

Functor that parses a formatter with the current parse context and then enables debug formatting on that formatter.

It is used to initialize element formatters with empty specs.

<a id="u-89dc7d768c69"></a>
### `ranges.h-integer-sequence-selection`

`template <typename T, T... N> using integer_sequence = std::integer_sequence<T, N...>;` · [include/fmt/ranges.h:L142-L143][f1]

Selects std::integer_sequence/index_sequence/make_index_sequence when the library feature macro is present or FMT_MSC_VERSION is at least 1900.

Otherwise it provides a fallback integer_sequence with value_type and size(), plus recursive make_integer_sequence that stops at N=0 and make_index_sequence over size_t.

<a id="u-8456e032cf90"></a>
### `ranges.h-join-overloads`

`auto join(It begin, Sentinel end, string_view sep) -> join_view<It, Sentinel>` · [include/fmt/ranges.h:L850-L852][f1]

join overloads build views without formatting.

The iterator/sentinel overload returns a join_view with moved begin, end, and separator. The range overload is enabled for non-tuple-like ranges and returns a join_view over range_begin/range_end. The tuple overload is enabled for tuple-like types and returns a tuple_join_view holding a reference to the tuple and the separator. The initializer_list overload is deprecated and returns a join_view over const pointers by calling the iterator overload with std::begin/end.

<a id="u-4531374685aa"></a>
### `ranges.h-join-view-formatter`

`template <typename It, typename Sentinel, typename Char> struct formatter<join_view<I…` · [include/fmt/ranges.h:L681-L699][f1]

Formatter for join_view.

parse delegates to the element formatter. format walks the iterator range: if empty it returns the current output; otherwise it formats the first element, then for each remaining element copies the separator and formats the element. The view type is const when the iterator is copy-constructible, otherwise non-const; the element type comes from iter_value_t when ranges are available, otherwise iterator_traits.

<a id="u-fe31a22c9a58"></a>
### `ranges.h-map-and-set-detection`

`class is_map` · [include/fmt/ranges.h:L35-L42][f1]

Detects map-like and set-like types by probing nested mapped_type and key_type.

A type is a map when mapped_type is detectable; it is a set when key_type is detectable and it is not a map. Detection is SFINAE-based and does not inspect runtime values.

<a id="u-cd4541f4f53a"></a>
### `ranges.h-range-formatter-helper-aliases`

`namespace detail` · [include/fmt/ranges.h:L376-L377][f1]

range_formatter_type selects a formatter for the cvref-stripped element type.

maybe_const_range chooses const R when const begin/end is available, otherwise R. is_formattable_delayed checks formattability of the cvref-stripped element type of that selected range.

<a id="u-19d367ebafce"></a>
### `ranges.h-tuple-element-formatter`

`template <typename FormatContext> struct format_tuple_element` · [include/fmt/ranges.h:L272-L275][f1]

Formats one tuple element into the context.

Before every element after the first it copies the separator to the output and advances the context; then it formats the value and increments the element index.

<a id="u-b008f48d5e8c"></a>
### `ranges.h-tuple-formattability-detection`

`class is_tuple_formattable_` · [include/fmt/ranges.h:L167-L171][f1]

Primary trait is false.

The tuple-like specialization builds an index sequence and checks every tuple element's formattability; value is true only if all element checks succeed. The all_true helper is used to collapse the boolean pack.

<a id="u-07f38570e014"></a>
### `ranges.h-tuple-formatter`

`template <typename Tuple, typename Char> struct formatter< Tuple, Char, // format_as …` · [include/fmt/ranges.h:L300-L322][f1]

Formatter specialization for tuple-like, formattable types that do not have format_as.

It stores one formatter per element, default separator ', ', default brackets '()', and nested specs. parse first parses nested specs with ':', then consumes 'n' to clear brackets and separator; any remaining character other than '}' is an invalid-format error. It then parses empty specs for every element, enabling debug formatting on them. format delegates to nested specs write. write_body copies the opening bracket, formats elements with the separator between them, and copies the closing bracket. set_separator and set_brackets replace the stored delimiters.

**Uncertainties.**

- nested_format_specs parse/write behavior is not defined in this file.

<a id="u-dface0cd5ea8"></a>
### `ranges.h-tuple-formatter-result-helper`

`namespace tuple` · [include/fmt/ranges.h:L218-L219][f1]

Defines a tuple of formatters for the cvref-stripped element types and declares a helper that builds that result type from get<Is> expressions.

The helper is a declaration only in this file.

<a id="u-9d77c8564594"></a>
### `ranges.h-tuple-iteration-helpers`

`template <typename Tuple, typename F, size_t... Is> FMT_CONSTEXPR void for_each(index…` · [include/fmt/ranges.h:L190-L196][f1]

for_each expands over tuple indices and calls the function with get<Is>(tuple); for_each2 calls it with get<Is> from two tuples.

Both derive the index sequence from the first tuple after removing cvref, and use an initializer-list expansion so calls occur in index order.

<a id="u-fcda8e6b2252"></a>
### `ranges.h-tuple-join-view-formatter`

`template <typename Tuple, typename Char> struct formatter<tuple_join_view<Tuple, Char…` · [include/fmt/ranges.h:L739-L742][f1]

Formatter for tuple_join_view when the tuple is tuple-like.

parse calls do_parse with the tuple size; format calls do_format with the tuple size. The base do_parse returns the current parse position. The recursive do_parse only parses element specs when FMT_TUPLE_JOIN_SPECIFIERS is enabled (default 0); when enabled it parses the element at tuple_size-N, recursively parses the rest, and reports an error if the resulting positions differ. The base do_format returns the current output. The recursive do_format formats the element at tuple_size-N, then if more than one element remains copies the separator, advances the context, and recurses with N-1; it starts at tuple index 0 and proceeds forward while the recursion count decreases, with no trailing separator.

<a id="u-6b69d585fe2c"></a>
### `is_tuple_like_`

`class is_tuple_like_` · [include/fmt/ranges.h:L123-L131][f1]

Detects tuple-like types by checking whether std::tuple_size is valid for the cv-unqualified type.

The check is SFINAE-based and does not require tuple_element.

<a id="u-e437c653d19d"></a>
### `ranges.h module code (L287–L299)`

`module_region` · [include/fmt/ranges.h:L287-L299][f1]

Public tuple traits.

is_tuple_like is true only for detail tuple-like types that are not ranges; is_tuple_formattable delegates directly to the detail formattability trait.

<a id="u-18a8d33bed1d"></a>
### `is_container_adaptor`

`struct is_container_adaptor` · [include/fmt/ranges.h:L816-L824][f1]

Detects container adaptors by probing a nested container_type.

The check is SFINAE-based and does not require the adaptor to be a range.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h
