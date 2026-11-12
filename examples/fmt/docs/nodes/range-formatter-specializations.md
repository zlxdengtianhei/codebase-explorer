# Range Formatter Specializations

**Capability.** Selects and provides range formatter specializations for disabled, map-like, string, debug-string, and sequence ranges.

Come here for ranges.h formatter classes chosen by range kind and element formattability. It includes classification and specializations for container adaptors, maps, strings, and general sequences.

**Depends on.**

- [Format Spec Parser](format-spec-parser.md) · graph-only · 4 edge(s)

Parent: [Range and Tuple Formatting](range-and-tuple-formatting.md)

## Units (6)

<a id="u-d56fdc31117e"></a>
### `ranges.h-container-adaptor-formatter`

`template <typename T, typename Char> struct formatter< T, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L826-L834][f1]

Formatter for container adaptors whose range kind is disabled.

It inherits the formatter for the all view over the adaptor's container_type. format defines a local getter derived from the adaptor to access the protected container member through a pointer-to-member, wraps that container in the all view, and delegates to the base formatter.

<a id="u-d713dc2df609"></a>
### `ranges.h-map-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L569-L587][f1]

Formatter for map-like ranges whose element is formattable.

It stores formatters for the map element (key/value pair) and a no-delimiters flag. parse, when input remains, parses nested specs with ':', consumes 'n' to set no_delimiters, and rejects any remaining character other than '}' unless it is ':', which is consumed. It then parses empty specs for every element formatter. format delegates to nested specs write. write_body copies '{' unless no_delimiters, iterates entries with ', ' between them, formats each entry's two parts with ': ' between them, and copies '}' unless no_delimiters.

**Uncertainties.**

- nested_format_specs parse/write behavior is not defined in this file.

<a id="u-21602bbee644"></a>
### `ranges.h-range-format-kind`

`template <typename T> struct range_format_kind_ : std::integral_constant<range_format…` · [include/fmt/ranges.h:L252-L259][f1]

Classifies a range as disabled, map, set, or sequence.

The detail trait returns disabled when the dereferenced element type is the same as the range type, otherwise map if mapped_type exists, set if key_type exists and it is not a map, and sequence otherwise. The public trait applies that classification only when the type is a range; otherwise it is disabled. The constant alias exposes a range_format value as a type.

<a id="u-770daeac9f71"></a>
### `ranges.h-range-formatter`

`FMT_EXPORT template <typename T, typename Char, typename Enable = void> struct range_…` · [include/fmt/ranges.h:L396-L415][f1]

Formatter for a range element type that is already cvref-stripped and formattable.

It stores an underlying element formatter, default separator ', ', default brackets '[]', a debug flag, and nested specs. parse enables debug on the underlying formatter, parses nested specs with ':', and then handles specifiers: 'n' clears brackets; '?' sets debug, clears brackets, requires a following 's', and then behaves like 's'; 's' is valid only when the element type is Char, sets quotes and empty separator unless already debug, consumes 's', and returns immediately without parsing following specs. After the switch, a remaining character other than '}' must be ':'; otherwise it is an invalid-format error, and ':' disables debug on the underlying formatter before parsing it. write_body uses debug-string writing when the debug flag is set; otherwise it copies the opening bracket, formats each element with the separator between elements, and copies the closing bracket. The debug-string overload for Char builds a buffer and writes it as a debug string; the non-Char overload returns the output unchanged. format delegates to nested specs write, and underlying exposes the element formatter.

**Uncertainties.**

- nested_format_specs parse/write behavior is not defined in this file.

<a id="u-a4aa8232cfa1"></a>
### `ranges.h-sequence-and-set-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L532-L549][f1]

Formatter for ranges whose kind is not disabled, map, string, or debug_string, and whose element is formattable.

It wraps a range_formatter over the cvref-stripped element type of the possibly-const range. The constructor changes brackets to '{}' when the range kind is set. parse and format delegate to the wrapped range formatter.

<a id="u-ab163421d7c9"></a>
### `ranges.h-string-range-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<range_for…` · [include/fmt/ranges.h:L636-L654][f1]

Formatter for ranges classified as string or debug_string.

It chooses std_string_view when constructible from the range begin/end, otherwise basic_string. parse delegates to the underlying string formatter and, for debug_string kind, enables debug format. format constructs the chosen string type from the range begin/end and delegates to the underlying formatter.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h
