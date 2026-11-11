# Printf implementation

**Capability.** Legacy printf-style formatting: argument conversion visitors, spec parsing, the core engine, and print/sprintf entry points.

A complete printf implementation layered on fmt's argument model: flag/width/precision parsing, integer length-modifier conversion, and the engine that walks the format string. Also hosts the shared throw_format_error helper.

**Depended on by.**

- [Core formatting implementation](core-formatting-implementation.md) · graph-confirmed · 12 edge(s)
- [Format argument infrastructure](format-argument-infrastructure.md) · graph-confirmed · 19 edge(s) · The argument infrastructure supplies the argument model and error reporting that the printf engine consumes.
- [Ranges and tuples formatting](ranges-and-tuples-formatting.md) · graph-confirmed · 5 edge(s) · Range and tuple formatting shares the printf module's error reporting helper.
- [Wide text and styling](wide-text-and-styling.md) · graph-confirmed · 1 edge(s)
- [Spec parsing and printf mapping](spec-parsing-and-printf-mapping.md) · graph-only · 13 edge(s)
- [Formatting driver and contexts](formatting-driver-and-contexts.md) · graph-only · 4 edge(s)
- [Core argument and buffer base](core-argument-and-buffer-base.md) · graph-only · 3 edge(s)
- [Locale and dynamic specs](locale-and-dynamic-specs.md) · graph-only · 3 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 3 edge(s)
- [Argument storage and checking](argument-storage-and-checking.md) · graph-only · 2 edge(s)
- [Character and pointer writers](character-and-pointer-writers.md) · graph-only · 1 edge(s)
- [Float presentation writers](float-presentation-writers.md) · graph-only · 1 edge(s)

Parent: [fmt formatting library](fmt-formatting-library.md)

## Units (24)

<a id="u-e998dc5b36e1"></a>
### `printf.h-arg-converter`

`class arg_converter` · [include/fmt/printf.h:L120-L128][f1]

Argument visitor that rewrites an integer argument in place to the printf length-modifier target type T (or, when T is void, to int/unsigned or long long/unsigned depending on the type specifier).

bool arguments are converted like integers unless the specifier is 's'. For target types no larger than int, values are cast to int when the specifier is 'd'/'i' and to unsigned otherwise, routing through make_unsigned_or_bool to silence warnings. Larger targets cast to long long when signed, or to the unsigned counterpart of the *source* type U when unsigned (deliberately not replicating glibc's sign-extension UB). Non-integral arguments are left untouched.

<a id="u-6e00c8bae8bf"></a>
### `printf.h-basic-printf-context`

`basic_printf_context(basic_appender<Char> out, basic_format_args<basic_printf_context…` · [include/fmt/printf.h:L36-L38][f1]

Context object for printf-style formatting that holds an output appender and a store of format arguments, restricted to char or wchar_t.

`out()` returns the stored appender; `advance_to` is a no-op (the appender already tracks position); `locale()` returns a default locale_ref (printf formatting is locale-independent here); `arg(id)` fetches argument `id` from the stored args, returning a disengaged arg if absent. The constructor stores references, so callers must keep arguments alive for the context's lifetime.

<a id="u-48de9e8f2997"></a>
### `printf.h-char-converter`

`class char_converter` · [include/fmt/printf.h:L171-L176][f1]

Argument visitor used for the 'c' specifier on integral arguments: it rewrites the stored argument to the context's char type via static_cast.

Non-integral arguments are left unchanged.

<a id="u-bb71d2232875"></a>
### `printf.h-find`

`template <bool IS_CONSTEXPR, typename T, typename Ptr = const T*> FMT_CONSTEXPR auto …` · [include/fmt/printf.h:L53-L59][f1]

Linear search for `value` in [first, last), reporting the hit position through the `out` reference parameter (a workaround for gcc bug 77539) and returning whether it was found.

The generic constexpr version scans element by element. The char specialization delegates to memchr and returns true only when the result is non-null; on failure the caller sees out == nullptr, which vprintf relies on.

<a id="u-d92efab7e256"></a>
### `printf.h-fprintf`

`template <typename... T> inline auto fprintf(std::FILE* f, string_view fmt, const T&.…` · [include/fmt/printf.h:L643-L646][f1]

Printf-formats to a FILE*: the char overload takes string_view; the wchar_t overload is FMT_DEPRECATED.

Both build printf args and delegate to vfprintf.

<a id="u-002edf2eb327"></a>
### `printf.h-get-cstring`

`template <typename Char> struct get_cstring` · [include/fmt/printf.h:L189-L190][f1]

Argument visitor returning the argument as a const Char* when it is exactly a C string, and nullptr for every other type; vprintf uses it to apply a precision limit to %s arguments.

<a id="u-b8f55385065e"></a>
### `printf.h-int-checker`

`template <bool IS_SIGNED> struct int_checker` · [include/fmt/printf.h:L71-L72][f1]

Compile-time-selected helpers that test whether a value fits in int without signed/unsigned comparison warnings.

The unsigned specialization compares against to_unsigned(max_value<int>()) and always accepts bool. The signed specialization checks both numeric_limits<int>::min() and max, and always accepts int itself.

<a id="u-986df532695c"></a>
### `printf.h-is-zero-int`

`struct is_zero_int` · [include/fmt/printf.h:L102-L103][f1]

Argument visitor returning true only for integral arguments equal to zero; every non-integral argument yields false.

vprintf uses it to strip the '#' flag for zero values as C requires.

<a id="u-d15cd413ad55"></a>
### `printf.h-make-unsigned-or-bool`

`template <typename T> struct make_unsigned_or_bool : std::make_unsigned<T>` · [include/fmt/printf.h:L114-L114][f1]

Type trait identical to std::make_unsigned except that bool maps to bool instead of an unsigned type, so arg_converter can cast through it without changing bool.

<a id="u-22b5e784b152"></a>
### `printf.h-printf-arg-formatter`

`class printf_arg_formatter : public arg_formatter<Char>` · [include/fmt/printf.h:L231-L239][f1]

Argument visitor, derived from arg_formatter<Char>, that writes one printf argument to the output using parsed specs and the printf context.

Null C-string and pointer arguments are rendered as "(null)"/"(nil)" via write_null_pointer with the presentation type cleared (string vs pointer text chosen by the requested type). Integral values that are not the char type are written normally, except that a zero value with precision 0 emits only the sign and padding (write_zero_with_zero_precision). Char-typed values: if a non-character type is requested they are re-dispatched as int; otherwise sign, alt and '0' fill are cleared, fill is forced to ' ', none/numeric alignment becomes right, and the char is written. Floating-point, string_view, and non-null C strings/pointers are written through detail::write with the specs. monostate is written as-is. User-defined handles are formatted by invoking handle.format with an empty parse context and this printf context.

<a id="u-7f0bcc9dff76"></a>
### `printf.h-printf-precision-handler`

`struct printf_precision_handler` · [include/fmt/printf.h:L86-L87][f1]

Argument visitor that converts a `*` precision argument to int.

Integral values are range-checked via int_checker and negated to -1 if negative (a negative precision means "omit the value" downstream); values exceeding int trigger report_error("number is too big"). Non-integral arguments trigger report_error("precision is not integer").

<a id="u-e5beb3a861bb"></a>
### `printf.h-printf-width-handler`

`class printf_width_handler` · [include/fmt/printf.h:L196-L201][f1]

Argument visitor validating a `*` width.

Integral values are widened; a negative value sets left alignment in the specs and uses the negated magnitude. Widths exceeding max int trigger report_error("number is too big"); non-integral arguments trigger report_error("width is not integer").

<a id="u-aa2cdcd69454"></a>
### `printf.h-sprintf`

`template <typename... T> inline auto sprintf(string_view fmt, const T&... args) -> st…` · [include/fmt/printf.h:L614-L617][f1]

Returns the printf-formatted result as a string: the char overload takes string_view and non-const argument references; the wchar_t overload is FMT_DEPRECATED and uses make_printf_args<wchar_t>.

Both delegate to vsprintf.

<a id="u-4fe75221d1d1"></a>
### `report_error`

`FMT_FUNC void report_error(const char* message)` · [include/fmt/format-inl.h:L157-L165][f2]

Throws format_error with the given message; on MSVC/NVCC a volatile-true guard suppresses unreachable-code warnings without changing behavior.

<a id="u-3cf8434d7cf5"></a>
### `include/fmt/printf.h:FMT_BEGIN_EXPORT`

`class basic_printf_context` · [include/fmt/printf.h:L18-L32][f1]

Class template providing the formatting context for the legacy printf implementation, parameterized on char type (only char and wchar_t allowed, enforced by static_assert).

It stores an output appender and a format-args store; the constructor copies both, so argument references must outlive the context. It exposes the stored appender via out(), a no-op advance_to(), a default-constructed locale_ref from locale(), and argument lookup by zero-based id via arg(), which delegates to the stored args store and returns an empty basic_format_arg when the id is out of range. The enum sets builtin_types = 1.

group: [printf.h-basic-printf-context](printf-implementation.md#u-6e00c8bae8bf)

**Uncertainties.**

- Behavior of args_.get for invalid ids is defined in format.h, not visible here; the empty-arg fallback is inferred from usage in vprintf.

<a id="u-ea90dc0f4b07"></a>
### `convert_arg`

`template <typename T, typename Context, typename Char> void convert_arg(basic_format_…` · [include/fmt/printf.h:L165-L168][f1]

Visits `arg` with an arg_converter parameterized on target type T and type specifier, converting integer arguments in place for printf length modifiers; non-integral arguments pass through unchanged.

<a id="u-03e69617b787"></a>
### `make_arg_formatter`

`template <typename Char> auto make_arg_formatter(basic_appender<Char> iter, format_sp…` · [include/fmt/printf.h:L224-L228][f1]

Constructs an arg_formatter<Char> from an iterator, specs, and a default locale_ref; exists only to work around an XL compiler bug initializing printf_arg_formatter's base class.

<a id="u-ecb96ed933b2"></a>
### `parse_flags`

`template <typename Char> void parse_flags(format_specs& specs, const Char*& it, const…` · [include/fmt/printf.h:L323-L337][f1]

Parses a run of printf flag characters starting at `it`, setting specs accordingly: '-' sets left align, '+' sets plus sign, '0' sets '0' fill, ' ' sets space sign only if plus isn't already set, '#' sets the alt flag.

Any other character stops the loop without consuming it.

<a id="u-d385bf5e5f30"></a>
### `parse_header`

`template <typename Char, typename GetArg> auto parse_header(const Char*& it, const Ch…` · [include/fmt/printf.h:L339-L389][f1]

Parses the part of a printf conversion before precision: optional positional argument index (`N$`), flags, and width, returning the argument index or -1 for "next argument".

A leading digit run is parse_nonnegative_int; if followed by '$' it is the argument index (an overflow value -1 becomes max int). Otherwise, a leading '0' sets '0' fill, and a nonzero parsed width is stored and the function returns immediately (flags already handled); a -1 overflow triggers report_error("number is too big"). Otherwise flags are parsed, then width: digits are parsed (overflow errors), '*' consumes the next argument (or a positional `*N$` form via get_arg and printf_width_handler; a malformed positional like `*1x` triggers report_error("invalid format specifier")). Empty input returns -1 immediately.

<a id="u-0f7d73d0497e"></a>
### `vprintf`

`template <typename Char, typename Context> void vprintf(buffer<Char>& buf, basic_stri…` · [include/fmt/printf.h:L415-L576][f1]

Core printf engine: walks the format string, copying literal text and processing each '%' conversion into the buffer.

`%%` emits one '%'. For each conversion it parses header (index/flags/width), precision (digits, `*`, or positional `.*N$`; bare '.' gives precision 0), fetches the argument via a lambda that assigns the next automatic index or validates a positional one and reports "argument not found" for missing args. It then applies C rules: precision with integral args drops '0' fill; precision with a cstring argument truncates at the precision or an embedded NUL (via get_cstring and std::find); '0' fill becomes numeric alignment for arithmetic non-left-aligned args, else fill reverts to ' '. Length modifiers hh/h/l/ll/j/z/t convert the argument via convert_arg to the corresponding type ('L' is accepted but ignored). Integral args normalize 'i'/'u' to 'd' and 'c' converts via char_converter. The type character is mapped by parse_printf_presentation_type; none → report_error("invalid format specifier"); uppercase sets the upper flag. For alt-format zero integral values the '#' flag is cleared, and '#o' with precision 0 gets precision 1. Finally the argument is written by printf_arg_formatter. Truncated conversions (end of string after '%' or before a type) report "invalid format string".

<a id="u-bf4f7e99c4c5"></a>
### `make_printf_args`

`template <typename Char = char, typename... T> inline auto make_printf_args(T&... arg…` · [include/fmt/printf.h:L587-L591][f1]

Builds a format_arg_store of printf-context references to the arguments via fmt::make_format_args, with Char defaulting to char; the result converts implicitly to printf_args/wprintf_args.

<a id="u-cc734f4a924e"></a>
### `printf`

`template <typename... T> inline auto printf(string_view fmt, const T&... args) -> int` · [include/fmt/printf.h:L661-L664][f1]

Printf-formats to stdout: builds printf args from the arguments and delegates to vfprintf(stdout, ...), returning the written count or -1.

<a id="u-203c87bdd0ec"></a>
### `vfprintf`

`template <typename Char> auto vfprintf(std::FILE* f, basic_string_view<Char> fmt, typ…` · [include/fmt/printf.h:L624-L633][f1]

Formats into a memory buffer via detail::vprintf, then writes it to the FILE with fwrite of sizeof(Char) units.

Returns the number of units written as int, or -1 if the fwrite short-counts.

<a id="u-c0e15e26f744"></a>
### `vsprintf`

`template <typename Char> inline auto vsprintf(basic_string_view<Char> fmt, typename v…` · [include/fmt/printf.h:L597-L604][f1]

Formats into a basic_memory_buffer via detail::vprintf and returns the contents as a std::basic_string<Char>.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/printf.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
