# Range Formatters

**Capability.** Formatter specializations per classification: primary sequence/set range formatter, top-level sequence/set dispatch, map '{key: value}' output, copying string/debug_string output, tuple rendering, and container-adaptor reuse.

Each formatter handles one range_format_kind; they report malformed range specs via report_error and delegate element formatting to element formatters.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-confirmed · 5 edge(s)
- [Range Detection Traits](ranges-traits.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Join Formatting](ranges-join.md) · model-inferred · 0 edge(s)

Parent: [Range Formatting](ranges-h.md)

## Units (6)

<a id="u-772ed30c82e0"></a>
### `ranges-h-range-formatter`

`FMT_EXPORT template <typename T, typename Char, typename Enable = void> struct range_…` · [include/fmt/ranges.h:L396-L415][f1]

Primary sequence/set element formatter for a type T that is the same after cv-ref removal and is formattable.

Holds an underlying per-element formatter (debug format enabled on it by default), ", " separator, '[]' brackets, an is_debug flag, and nested specs. parse: with an empty spec it delegates straight to the underlying parse. Otherwise it parses nested specs, then switches on the next character: 'n' removes brackets; '?' sets is_debug and clears brackets, then falls through requiring the next character to be 's' or report_error fires; 's' (or '?s') requires T to be Char (same element/character type) or report_error fires, and when not in debug mode it sets quote-string brackets '""', an empty separator, and disables debug format on the underlying formatter, returning immediately. After the switch, a leftover character that is neither '}' nor ':' is report_error; a ':' is consumed and debug format on the underlying is disabled before delegating the remainder to the underlying parse. write_body: if is_debug, write_debug_string buffers all elements (valid only when T is Char) and writes them with the debug presentation type, i.e. as an escaped quoted string; the non-Char overload returns the output unchanged, so '?s' on non-character element types is guarded earlier by the 's'-case error. Otherwise it copies '[', formats each element via the underlying formatter separated by ", " (advancing ctx to the current out each iteration), and copies ']'. format delegates to specs_.write; set_separator/set_brackets/underlying are simple accessors or mutators.

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538), [report_error](core-errors.md#u-4fe75221d1d1)

**Uncertainties.**

- write<Char> with presentation_type::debug escaping is implemented in format.h and not verifiable here.

<a id="u-787480d81bb5"></a>
### `ranges-h-sequence-set-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L532-L549][f1]

Top-level formatter for ranges classified as sequence or set: enabled when range_format_kind excludes disabled, map, string, and debug_string and the element type is formattable (delayed check).

It wraps a range_formatter for the element's uncvrefed type and iterates detail::maybe_const_range (const R when the range has const begin/end). The constructor, at compile time, sets '{' '}' brackets when the kind is set, leaving the range_formatter's default '[]' for sequences. parse and format simply delegate to the wrapped range_formatter; the nonlocking alias marks the formatter non-blocking.

uses: [ranges-h-range-formatter](ranges-formatters.md#u-772ed30c82e0)

<a id="u-186be4dbf4f9"></a>
### `ranges-h-map-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L569-L587][f1]

Formats map-like ranges as '{' key: value, key: value '}'.

Holds per-element (pair) formatters built like the tuple formatter, a no_delimiters_ flag, and nested specs. parse: only when the spec is non-empty does it parse nested specs, set no_delimiters_ on 'n', and then require the next character to be '}' or ':' (report_error("invalid format specifier") otherwise) before advancing the context; afterward every pair-element formatter gets its empty specs parsed via parse_empty_specs. format delegates to specs_.write; write_body copies '{' unless no_delimiters_, then for each map entry applies format_tuple_element with a ": " separator inside each pair (formatting key then value), joins entries with ", ", and copies '}' unless no_delimiters_. So 'n' prints bare "k: v, k: v" without braces.

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538), [report_error](core-errors.md#u-4fe75221d1d1)

<a id="u-f68c6f47fdd9"></a>
### `ranges-h-string-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<range_for…` · [include/fmt/ranges.h:L636-L654][f1]

Formats ranges classified as string or debug_string by copying their contents into a contiguous string object first: string_type is std_string_view<Char> when constructible from the range's iterators, otherwise std::basic_string<Char> (so non-contiguous or proxy-iterator ranges fall back to a copying string).

parse delegates to the underlying string formatter's parse and, at compile time for the debug_string kind, additionally calls set_debug_format on it. format constructs a string_type from range_begin/range_end and formats it through the underlying formatter, so the output is an ordinary or escaped string, not a bracketed sequence.

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538)

**Uncertainties.**

- set_debug_format is declared in format.h; its exact effect is not verifiable here.

<a id="u-1195bab12a35"></a>
### `ranges-h-tuple-formatter`

`template <typename Tuple, typename Char> struct formatter< Tuple, Char, // format_as …` · [include/fmt/ranges.h:L300-L322][f1]

Formats tuple-like types as '(' e1, e2 ')' with per-element formatters from detail::tuple::get_formatters.

The enable_if uses conditional_t so that when the type has a format_as overload, is_tuple_formattable is never instantiated; the comment explains this avoids infinite recursion for self-referential tuple-like types. Defaults: separator ", ", brackets "()", nested format specs. parse parses nested element specs via specs_.parse with ':' delimiter; if the next character is 'n' it clears brackets and separator (tuple printed without delimiters); any leftover character other than '}' triggers report_error("invalid format specifier"); finally it parses empty specs into every element formatter. format delegates to specs_.write, whose write_body copies the opening bracket, then for_each2 with a format_tuple_element visitor (separator before elements after the first), then the closing bracket. set_separator/set_brackets override the defaults. The default constructor and the nested_format_specs friendship are trivial.

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538), [report_error](core-errors.md#u-4fe75221d1d1)

**Uncertainties.**

- specs_.write/nested_format_specs behavior lives in format.h and is not verifiable here.

<a id="u-310ee3d8e042"></a>
### `ranges-h-container-adaptor-formatter`

`namespace detail` · [include/fmt/ranges.h:L803-L803][f1]

Formats container adaptors (std::stack, std::queue, ...) by reusing the formatter of their underlying container.

is_container_adaptor detects U::container_type via SFINAE. detail::all wraps a const Container& and exposes const begin()/end(), giving a formattable range view. The formatter inherits formatter<all<typename T::container_type>>, so parse comes from that base unchanged (the adaptor itself is range_format::disabled, satisfying the enable_if). format defines a local getter struct deriving from T so that the expression v.*(&getter::c) accesses the adaptor's (possibly protected) container member through the derived class, wraps it in an all view, and delegates to the base formatter's format. The container is read through a reference, so the output reflects iteration order of the underlying container.

uses: [ranges-h-detection-traits](ranges-traits.md#u-c4ccbfc94538); inherits: [ranges-h-sequence-set-formatter](ranges-formatters.md#u-787480d81bb5)

**Uncertainties.**

- Exact base formatting (brackets, set vs sequence classification of the underlying container) depends on formatter<all<...>> resolution and is inferred, not observed here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h