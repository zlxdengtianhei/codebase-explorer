# printf Spec Parsing

**Capability.** Parses printf conversion headers (index, flags, width), maps conversion characters to presentation types, and converts width/precision arguments with error reporting.

Read to understand printf syntax handling; parse_header and the width/precision handlers report malformed specs via report_error.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-confirmed · 7 edge(s)

**Depended on by.**

- [printf Engine & API](printf-engine.md) · model-inferred · 0 edge(s)

Parent: [printf Compatibility](printf-h.md)

## Units (5)

<a id="u-ecb96ed933b2"></a>
### `parse_flags`

`template <typename Char> void parse_flags(format_specs& specs, const Char*& it, const…` · [include/fmt/printf.h:L323-L337][f1]

Consumes leading printf flag characters from [it, end), mutating specs, until a non-flag or end is reached.

'-' sets left alignment, '+' plus sign, '0' zero fill, ' ' sets space sign only when the sign is not already plus (plus wins), '#' enables the alternate form. Any other character stops the scan without consuming it; it is advanced past every accepted flag.

<a id="u-d385bf5e5f30"></a>
### `parse_header`

`template <typename Char, typename GetArg> auto parse_header(const Char*& it, const Ch…` · [include/fmt/printf.h:L339-L389][f1]

Parses the leading portion of a printf conversion: optional argument index, flags, and width, updating it past what it consumes and returning the positional argument index (-1 when absent).

If the first character is a digit it parses a nonnegative integer; if followed by '$' it is a 1-based argument index (overflowing input maps to max_value<int>()); otherwise a leading '0' sets zero fill and a nonzero parsed value is taken as the width and returned immediately (width overflow beyond int reports "number is too big"; a value of 0 falls through to flag parsing). After parse_flags it parses a width: digits are parsed with overflow reported as "number is too big"; '*' fetches the width from the next automatic argument via printf_width_handler, or from the positional argument named by '*N$' when digits follow (a digit sequence not followed by '$' reports "invalid format specifier"). Returns arg_index, which stays -1 unless a positional index was seen.

calls: [parse_flags](printf-spec.md#u-ecb96ed933b2); uses: [printf.h-printf-width-handler](printf-spec.md#u-e5beb3a861bb); raises: [report_error](core-errors.md#u-4fe75221d1d1)

**Uncertainties.**

- Behavior when parse_nonnegative_int leaves it at end mid-index (e.g. '%5' at end of string) depends on parse_nonnegative_int's own contract, defined outside this file.

<a id="u-1b44d7ac70be"></a>
### `parse_printf_presentation_type`

`inline auto parse_printf_presentation_type(char c, type t, bool& upper) -> presentati…` · [include/fmt/printf.h:L391-L413][f1]

Maps a printf conversion character to the library's presentation_type based on the argument's type category, setting upper=true for the uppercase variants (X, E, F, G, A).

Each of d, o, x/X yields dec/oct/hex only for integral-like types (signed, unsigned, bool, char); e/E, f/F, g/G, a/A yield exp/fixed/general/hexfloat only for floating types; c yields chr for integral types; s yields string for string/cstring; p yields pointer for pointer/cstring; unknown characters yield none. An unsupported combination returns pt::none, which callers treat as an invalid format specifier.

calls: [function::FMT_END_EXPORT.in::32584][f2]

<a id="u-e5beb3a861bb"></a>
### `printf.h-printf-width-handler`

`inline explicit printf_width_handler(format_specs& specs) : specs_(specs)` · [include/fmt/printf.h:L201-L201][f1]

printf_width_handler converts a width argument from a format arg into an unsigned field width stored semantics via return value, mutating the held format_specs for negative widths.

For integral values it widens the value to the matching unsigned type; if the value is negative it sets left alignment on specs_ and negates the width (the '-' flag via a dynamic negative width). Widths above INT_MAX trigger report_error("number is too big"). Non-integral values trigger report_error("width is not integer") and return 0 (unreachable if report_error throws).

raises: [report_error](core-errors.md#u-4fe75221d1d1)

<a id="u-7f0bcc9dff76"></a>
### `printf.h-printf-precision-handler`

`template <typename T, FMT_ENABLE_IF(!std::is_integral<T>::value)> auto operator()(T) …` · [include/fmt/printf.h:L94-L98][f1]

printf_precision_handler converts a width/precision argument visited from a format arg into an int.

For integral values it first validates the range with int_checker selected by the type's signedness and calls report_error("number is too big") if it does not fit in int; it then returns -1 for negative values (so a negative precision behaves as unspecified) or the value cast to int. For non-integral types it calls report_error("precision is not integer") and returns 0, which is unreachable because report_error throws per the engine's error convention.

calls: [printf.h-int-checker](printf-support.md#u-b8f55385065e); raises: [report_error](core-errors.md#u-4fe75221d1d1)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/printf.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h