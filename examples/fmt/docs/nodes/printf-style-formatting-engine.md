# Printf-Style Formatting Engine

**Capability.** Implements printf-style parsing, argument conversion, context storage, and output through vfprintf, vsprintf, or memory buffers.

Consult this module for printf.h support that parses format strings and converts arguments for printf length, width, and precision modifiers. It includes printf contexts, visitors, formatter core, and FILE/string output helpers.

**Depends on.**

- [Compiled Formatting Engine](compiled-formatting-engine.md) · graph-confirmed · 13 edge(s) · printf-style-formatting-engine depends on compiled-formatting-engine for formatting output.
- [Format Spec Parser](format-spec-parser.md) · graph-only · 13 edge(s)

Parent: [fmt Formatting Library](fmt-formatting-library.md)

## Units (23)

<a id="u-e998dc5b36e1"></a>
### `printf.h-arg-converter`

`class arg_converter` · [include/fmt/printf.h:L120-L128][f1]

This visitor mutates a format argument to a requested target type for printf length modifiers.

bool converts only when the type specifier is not 's'. Integral values treat 'd' and 'i' as signed; the target is T unless T is void, in which case the original U is used. If the target is no larger than int, signed values become int and unsigned values become unsigned after make_unsigned_or_bool on the target; otherwise signed values become long long and unsigned values use make_unsigned_or_bool on U. Non-integral values are left unchanged.

<a id="u-ac55553926cc"></a>
### `printf.h-c-string-extractor`

`template <typename T> auto operator()(T) -> const Char*` · [include/fmt/printf.h:L190-L190][f1]

This visitor returns a C string pointer only for a matching const character pointer argument; every other argument type yields null.

<a id="u-48de9e8f2997"></a>
### `printf.h-char-converter`

`class char_converter` · [include/fmt/printf.h:L171-L176][f1]

This visitor converts integral format arguments to the context's character type and stores the result back in the argument.

Non-integral arguments are left unchanged.

<a id="u-38995e874d1b"></a>
### `printf.h-find-helpers`

`template <bool IS_CONSTEXPR, typename T, typename Ptr = const T*> FMT_CONSTEXPR auto …` · [include/fmt/printf.h:L53-L59][f1]

These helpers search a range for a value and return the result through an out pointer.

The generic version scans linearly, leaves out at last when absent, and returns whether found. The char specialization uses memchr, sets out to the match or null, and returns out != null.

<a id="u-14dabab5542c"></a>
### `printf.h-fprintf-overloads`

`template <typename... T> inline auto fprintf(std::FILE* f, string_view fmt, const T&.…` · [include/fmt/printf.h:L643-L646][f1]

The char overload forwards to vfprintf with printf arguments and returns its int result.

The wchar_t overload is deprecated and forwards to vfprintf with wchar_t printf arguments. Both accept const argument references.

<a id="u-da5b677740cd"></a>
### `printf.h-int-fit-checkers`

`template <bool IS_SIGNED> struct int_checker` · [include/fmt/printf.h:L71-L72][f1]

These visitors decide whether an integer value fits in int.

The unsigned primary compares the value with max int and always accepts bool. The signed specialization requires the value to be at least int min and at most int max, and always accepts int.

<a id="u-a687ff2ba0d9"></a>
### `printf.h-printf-argument-formatter`

`class printf_arg_formatter : public arg_formatter<Char>` · [include/fmt/printf.h:L231-L239][f1]

This formatter writes one printf argument using the parsed specs and the printf context.

Null pointers are written as '(null)' for string-like types and '(nil)' for pointer types; a null void pointer always uses '(nil)'. A zero integer with precision zero writes only the sign and padding. Integral values that are not the character type use that zero-precision rule, otherwise normal write; character-typed values with a non-none, non-chr presentation recurse as int, while other character values clear sign and alternate form, force space fill, and right-align unless already left. Floating values and string views use normal write. A handle formats through an empty parse context and the stored printf context. monostate uses normal write.

<a id="u-2b2361d06c0c"></a>
### `printf.h-printf-context`

`basic_printf_context(basic_appender<Char> out, basic_format_args<basic_printf_context…` · [include/fmt/printf.h:L36-L38][f1]

The printf context stores an output appender and format arguments for char or wchar_t only, enforced by a static assertion.

The constructor stores both; out returns the appender; advance_to is a no-op; locale returns an empty locale reference. arg delegates to the stored argument store's get(id); this source does not establish any fallback for an absent id.

<a id="u-7f0bcc9dff76"></a>
### `printf.h-printf-precision-handler`

`struct printf_precision_handler` · [include/fmt/printf.h:L86-L87][f1]

This visitor converts a printf precision argument to int.

For integral values it first checks fit in int; if not, it calls report_error('number is too big'), then returns -1 for negative values and the cast value otherwise. For non-integral values it calls report_error('precision is not integer') and returns 0.

<a id="u-e5beb3a861bb"></a>
### `printf.h-printf-width-handler`

`class printf_width_handler` · [include/fmt/printf.h:L196-L201][f1]

This visitor converts a printf width argument to unsigned.

For integral values it casts to a wide unsigned type; a negative value sets left alignment and negates the width; a width above max int calls report_error('number is too big'); the resulting width is returned as unsigned. Non-integral values call report_error('width is not integer') and return 0.

<a id="u-badbac86032b"></a>
### `printf.h-sprintf-overloads`

`template <typename... T> inline auto sprintf(string_view fmt, const T&... args) -> st…` · [include/fmt/printf.h:L614-L617][f1]

The char overload formats through vsprintf using printf arguments and returns std::string.

The wchar_t overload is deprecated, uses wchar_t printf arguments, and returns std::wstring. Both accept const argument references.

<a id="u-871c3f296d90"></a>
### `printf.h-zero-integer-visitor`

`struct is_zero_int` · [include/fmt/printf.h:L102-L103][f1]

This visitor reports whether an argument is an integer zero.

Integral values compare equal to zero; non-integral values return false.

<a id="u-3cf8434d7cf5"></a>
### `include/fmt/printf.h:FMT_BEGIN_EXPORT`

`class basic_printf_context` · [include/fmt/printf.h:L18-L32][f1]

Defines the printf formatting context that holds an output appender and format-argument references for later printf-style formatting.

A compile-time assertion restricts the code-unit type to char or wchar_t, and the context declares builtin_types as 1; construction and member access are handled by separate members.

<a id="u-ea90dc0f4b07"></a>
### `convert_arg`

`template <typename T, typename Context, typename Char> void convert_arg(basic_format_…` · [include/fmt/printf.h:L165-L168][f1]

This function applies the argument converter to a format argument, mutating it according to the requested target type and the printf type character.

<a id="u-03e69617b787"></a>
### `make_arg_formatter`

`template <typename Char> auto make_arg_formatter(basic_appender<Char> iter, format_sp…` · [include/fmt/printf.h:L224-L228][f1]

This helper constructs an argument formatter from an output appender and format specs, using an empty locale reference; it exists as a compiler workaround.

<a id="u-ecb96ed933b2"></a>
### `parse_flags`

`template <typename Char> void parse_flags(format_specs& specs, const Char*& it, const…` · [include/fmt/printf.h:L323-L337][f1]

This parser consumes leading printf flags and updates format specs.

'-' sets left alignment, '+' sets plus sign, '0' sets zero fill, space sets space sign only when plus is not already set, and '#' sets alternate form; the first other character stops parsing.

<a id="u-d385bf5e5f30"></a>
### `parse_header`

`template <typename Char, typename GetArg> auto parse_header(const Char*& it, const Ch…` · [include/fmt/printf.h:L339-L389][f1]

This parser reads an optional positional argument index, flags, and width from a printf format string.

If the first character is a digit, it parses a nonnegative integer: a following '$' makes it the argument index (or max int when parsing failed), otherwise a leading '0' sets zero fill and a nonzero value becomes width and returns immediately, reporting 'number is too big' for a failed parse. It then parses flags and width: a digit width reports 'number is too big' on failed parse; '*' consumes a width argument, using a positional index when digits and '$' follow, otherwise the next argument, and reports 'invalid format specifier' for a digit sequence without '$'. It returns the argument index or -1.

<a id="u-1b44d7ac70be"></a>
### `parse_printf_presentation_type`

`inline auto parse_printf_presentation_type(char c, type t, bool& upper) -> presentati…` · [include/fmt/printf.h:L391-L413][f1]

This function maps a printf conversion character to a presentation type only when the argument type is in the allowed set.

d/o/x/X require an integral type and select dec/oct/hex; e/E, f/F, g/G, and a/A require a floating type and select exp/fixed/general/hexfloat; c requires integral and selects chr; s requires string or C-string and selects string; p requires pointer or C-string and selects pointer. Uppercase variants set the upper flag; any mismatch or unknown character yields none.

<a id="u-0f7d73d0497e"></a>
### `vprintf`

`template <typename Char, typename Context> void vprintf(buffer<Char>& buf, basic_stri…` · [include/fmt/printf.h:L415-L576][f1]

This is the core printf parser and formatter: it scans the format string, resolves arguments, applies printf flags, width, precision, length modifiers, and conversion types, then writes each argument through the printf formatter.

It writes literal text before each '%' and handles '%%' as a literal percent. A '%' at end reports 'invalid format string'. Argument lookup uses the next argument for negative indices and otherwise checks and decrements the index; a missing argument reports 'argument not found'. A parsed argument index of 0 is rejected with 'argument not found' before lookup.
- precision: a digit sequence sets precision, '*' uses a positional or next argument through the precision handler, and a missing value sets precision 0; a digit sequence after '*' without '$' reports 'invalid format specifier'.
- precision with integral argument: zero fill is replaced by space fill.
- precision with C string: the string is truncated at the first null within the precision or at the precision.
- zero fill: arithmetic arguments with non-left alignment become numeric alignment; other cases replace zero fill with space fill.
- length modifiers: h/hh, l/ll, j, z, t, and L select conversions or no conversion; the default path backs up and converts with void.
- type normalization: integral i and u become d; c converts the argument to the context character type.
- presentation type: none reports 'invalid format specifier'; uppercase sets the upper flag.
- alternate form with a zero integer: alternate form is cleared, and octal with precision zero gets precision one.
After the loop it writes the remaining literal text.

<a id="u-bf4f7e99c4c5"></a>
### `make_printf_args`

`template <typename Char = char, typename... T> inline auto make_printf_args(T&... arg…` · [include/fmt/printf.h:L587-L591][f1]

This helper builds a printf argument store for the requested character type by forwarding to make_format_args with the printf context.

<a id="u-cc734f4a924e"></a>
### `printf`

`template <typename... T> inline auto printf(string_view fmt, const T&... args) -> int` · [include/fmt/printf.h:L661-L664][f1]

This function formats through vfprintf to stdout using printf arguments and returns the resulting int status.

<a id="u-203c87bdd0ec"></a>
### `vfprintf`

`template <typename Char> auto vfprintf(std::FILE* f, basic_string_view<Char> fmt, typ…` · [include/fmt/printf.h:L624-L633][f1]

This function formats into a memory buffer, writes the buffer to the FILE with fwrite, and returns the element count as int.

If fwrite writes fewer elements than the buffer size, it returns -1; otherwise it returns the size cast to int.

<a id="u-c0e15e26f744"></a>
### `vsprintf`

`template <typename Char> inline auto vsprintf(basic_string_view<Char> fmt, typename v…` · [include/fmt/printf.h:L597-L604][f1]

This function formats into a memory buffer with the printf engine and returns the buffer contents as a basic string.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/printf.h
