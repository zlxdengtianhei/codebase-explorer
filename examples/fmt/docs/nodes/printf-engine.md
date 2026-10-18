# printf Engine & API

**Capability.** basic_printf_context, the printf_arg_formatter implementing C output semantics per type, the core vprintf loop, and printf/fprintf/sprintf wrappers over it.

The wrappers pack make_printf_args and delegate to vfprintf/vsprintf, which run detail::vprintf; the arg formatter produces the actual bytes.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-confirmed · 6 edge(s)
- [printf Spec Parsing](printf-spec.md) · model-inferred · 0 edge(s)
- [printf Arg Visitors](printf-support.md) · model-inferred · 0 edge(s)

Parent: [printf Compatibility](printf-h.md)

## Units (10)

<a id="u-6e00c8bae8bf"></a>
### `printf.h-basic-printf-context`

`class basic_printf_context` · [include/fmt/printf.h:L18-L32][f1]

Defines basic_printf_context, the formatting context used by the printf-style engine for char and wchar_t.

It stores a basic_appender<Char> output sink and a basic_format_args bundle; arg(id) looks up a positional argument from that bundle, out() returns the sink, advance_to is a no-op (printf walks the buffer implicitly), and locale() returns an empty locale_ref so locale-specific formatting is disabled. A static_assert rejects character types other than char and wchar_t. The enum builtin_types = 1 signals the builtin-type-only mode of the engine. References to arguments are retained, so callers must keep them alive.

uses: [basic_appender][f2], [basic_format_args][f2]

<a id="u-22b5e784b152"></a>
### `printf.h-printf-arg-formatter`

`void write_null_pointer(bool is_string = false)` · [include/fmt/printf.h:L239-L243][f1]

printf_arg_formatter<Char> extends arg_formatter<Char> to implement C printf output semantics for each visited argument type, writing into the appender using the supplied format_specs.

Helper write_null_pointer emits "(nil)" or "(null)" (for string types) with presentation type cleared; write delegates to detail::write with the formatter's locale; write_zero_with_zero_precision implements the C rule that a zero value with precision 0 prints no digits, only sign and padding. The integral operator() handles the char case specially when T is Char: if the presentation type is neither none nor chr it re-dispatches as int; otherwise it strips sign, alt flag and '0' fill (fill becomes space, alignment forced right when none or numeric) before writing the character. Non-char integrals with value 0 and precision 0 use the zero-with-zero-precision path, else plain write. Floating points write directly. Null char/wchar_t pointers emit the null placeholder, choosing "(null)" when the spec type is not pointer; string_views and non-null pointers write normally. A dynamic handle argument is formatted via handle.format with a fresh empty parse_context and the stored printf context, so custom formatters can participate. monostate writes through the generic write.

uses: [printf.h-basic-printf-context](printf-engine.md#u-6e00c8bae8bf); inherits: [arg_formatter][f2]; calls: [make_arg_formatter](printf-engine.md#u-03e69617b787)

**Uncertainties.**

- Whether write_null_pointer's write_bytes applies the specs' width/fill exactly follows C padding rules cannot be confirmed from this file.
- The handle path passes an empty parse_context, so custom formatters calling parse-side APIs would fail; how they behave is not visible here.

<a id="u-03e69617b787"></a>
### `make_arg_formatter`

`template <typename Char> auto make_arg_formatter(basic_appender<Char> iter, format_sp…` · [include/fmt/printf.h:L224-L228][f1]

Constructs an arg_formatter<Char> from an appender and format specs with an empty locale_ref, returned by value.

It exists solely as a workaround for an XL compiler bug initializing printf_arg_formatter's base class; it adds no behavior.

<a id="u-0f7d73d0497e"></a>
### `vprintf`

`template <typename Char, typename Context> void vprintf(buffer<Char>& buf, basic_stri…` · [include/fmt/printf.h:L415-L576][f1]

Core printf engine: formats args into buf according to the printf-style format string.

It builds a basic_printf_context and a parse_context, with get_arg resolving positional indices (1-based '$' indices are decremented and checked) or advancing next_arg_id for automatic arguments; a missing argument reports "argument not found". The main loop scans for '%': text before it is written verbatim; '%%' writes a single '%'; a trailing '%' or a conversion at end-of-string reports "invalid format string". For each conversion it parses index/flags/width via parse_header (index 0 is rejected), then precision: '.N' literal (or 0 when '.' is followed by nothing non-numeric), '.*' from the next argument via printf_precision_handler, or '.*N$' positional; a bare '.' means precision 0. After fetching the argument, a precision >= 0 turns '0' fill into space for integral types; for cstring arguments precision truncates via get_cstring with std::find locating an embedded NUL within the precision window; zero fill becomes numeric alignment for arithmetic non-left-aligned values, otherwise it is dropped. Length modifiers h/hh, l/ll, j, z, t convert the argument through convert_arg to signed char, short, long, long long, intmax_t, size_t, or ptrdiff_t, with the following character as the specifier; 'L' is accepted and ignored; an unknown modifier is rewound and passed as the conversion character to convert_arg<void>. The final type character is normalized ('i'/'u' become 'd'; 'c' converts integrals to char via char_converter), translated by parse_printf_presentation_type — none means "invalid format specifier" — with uppercase flagged; for '#' on zero values the alt flag is cleared, and for '#o' with value and precision both zero precision becomes 1 to emit a single '0'. Finally the argument is rendered through printf_arg_formatter and the trailing literal text is flushed after the loop.

uses: [printf.h-basic-printf-context](printf-engine.md#u-6e00c8bae8bf), [printf.h-printf-arg-formatter](printf-engine.md#u-22b5e784b152); calls: [parse_header](printf-spec.md#u-d385bf5e5f30), [parse_printf_presentation_type](printf-spec.md#u-1b44d7ac70be), [convert_arg](printf-support.md#u-ea90dc0f4b07); raises: [report_error](core-errors.md#u-4fe75221d1d1)

**Uncertainties.**

- Error handling assumes report_error does not return (call sites use it as a control-flow exit such as 'if (!arg) report_error(...)'); its throw/abort behavior is defined in format-inl.h, not here.
- find<false, Char>'s on-failure out value (last vs nullptr, see that unit) is compensated by setting it = end, but the interaction relies on the specialization actually selected for every Char.

<a id="u-bf4f7e99c4c5"></a>
### `make_printf_args`

`template <typename Char = char, typename... T> inline auto make_printf_args(T&... arg…` · [include/fmt/printf.h:L587-L591][f1]

Builds a format-argument store for basic_printf_context<Char> from lvalue references to the supplied arguments, forwarding to fmt::make_format_args; the result converts implicitly to printf_args.

Arguments are held by reference, so they must outlive the returned store.

<a id="u-55f159de62f5"></a>
### `fprintf`

`template <typename... T> inline auto fprintf(std::FILE* f, string_view fmt, const T&.…` · [include/fmt/printf.h:L643-L646][f1]

fprintf wrapper for narrow strings: packs args with make_printf_args and returns vfprintf's byte/character count or -1.

The wide overload (FMT_DEPRECATED) forwards identically with make_printf_args<wchar_t>.

calls: [vfprintf](printf-engine.md#u-203c87bdd0ec)

<a id="u-203c87bdd0ec"></a>
### `vfprintf`

`template <typename Char> auto vfprintf(std::FILE* f, basic_string_view<Char> fmt, typ…` · [include/fmt/printf.h:L624-L633][f1]

Formats args into a memory buffer via detail::vprintf, then fwrites the Char elements to the given FILE*.

Returns the number of characters written on full success, or -1 when fwrite wrote fewer items than requested; partial writes are not retried.

calls: [vprintf](printf-engine.md#u-0f7d73d0497e)

<a id="u-cc734f4a924e"></a>
### `printf`

`template <typename... T> inline auto printf(string_view fmt, const T&... args) -> int` · [include/fmt/printf.h:L661-L664][f1]

printf wrapper writing to stdout: packs args with make_printf_args and returns vfprintf(stdout, ...), i.e. the character count or -1 on short fwrite.

calls: [vfprintf](printf-engine.md#u-203c87bdd0ec)

<a id="u-37964eccbe79"></a>
### `sprintf`

`template <typename... T> inline auto sprintf(string_view fmt, const T&... args) -> st…` · [include/fmt/printf.h:L614-L617][f1]

Narrow-string sprintf wrapper: packs its arguments with make_printf_args and delegates to vsprintf, returning the formatted std::string.

The wchar_t overload (marked FMT_DEPRECATED) does the same with make_printf_args<wchar_t> and returns std::wstring; new code should use the wide path via different APIs.

calls: [vsprintf](printf-engine.md#u-c0e15e26f744)

<a id="u-c0e15e26f744"></a>
### `vsprintf`

`template <typename Char> inline auto vsprintf(basic_string_view<Char> fmt, typename v…` · [include/fmt/printf.h:L597-L604][f1]

Formats args with the printf engine into a basic_memory_buffer<Char> via detail::vprintf and returns the result as std::basic_string<Char>.

Errors surface from vprintf (invalid format, missing argument) rather than here; no fallback exists.

calls: [vprintf](printf-engine.md#u-0f7d73d0497e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/printf.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h