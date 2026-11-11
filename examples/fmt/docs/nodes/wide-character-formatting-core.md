# Wide-character formatting core

**Capability.** Wide/exotic-character format, print, and vformat entry points plus locale-aware numeric output and compile-time format string wrappers.

The wchar_t analog of the main format API: format, print, println, format_to, and size computation for wide strings. It also provides the compile-checked wide format string type and named-argument support.

Parent: [Wide character formatting](wide-character-formatting.md)

## Units (16)

<a id="u-c91ec548f8ca"></a>
### `xchar.h-basic-fstring`

`template <typename Char, typename... T> struct basic_fstring` · [include/fmt/xchar.h:L79-L95][f1]

Compile-time-checked format string wrapper for wchar_t and exotic character types, storing a basic_string_view.

The string-convertible constructor is FMT_CONSTEVAL and, in constant evaluation, runs parse_format_string with a format_string_checker sized to the argument pack, so invalid format strings fail to compile. The compile_string constructor does the same check as a constexpr expression. A runtime_format_string constructor stores the string without checking. `get()` returns the view; the implicit conversion operator to the view is FMT_DEPRECATED. basic_format_string is an alias of this class, and wformat_string names its `t` member type.

<a id="u-d72ef4919f4c"></a>
### `xchar.h-format-string-char-trait`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/xchar.h:L23-L28][f1]

Type trait deducing the character type of a format string S.

The primary template has no `type`. The void_t specialization applies when to_string_view(S) is valid and yields char_t<S>; the compile_string specialization (for types deriving detail::compile_string) yields S::char_type. format_string_char_t is the alias for the result.

<a id="u-66afd754d8b0"></a>
### `xchar.h-println-wide-file`

`template <typename... T> void println(std::FILE* f, wformat_string<T...> fmt, T&&... …` · [include/fmt/xchar.h:L332-L335][f1]

Wide println: formats the arguments with fmt::format, then prints the result followed by a newline ("{}\n") to the given FILE* or to stdout.

<a id="u-1543a9ab5af2"></a>
### `include/fmt/xchar.h:vformat_to`

`template <typename Char> void vformat_to(buffer<Char>& buf, basic_string_view<Char> f…` · [include/fmt/xchar.h:L60-L68][f1]

Formats `fmt` with `args` into a buffer<Char> for non-char character types (static_assert rejects char) by running parse_format_string with a format_handler carrying the parse context, output appender, args, and optional locale_ref.

<a id="u-29b8e5ac1e06"></a>
### `include/fmt/xchar.h:write_loc`

`inline auto write_loc(basic_appender<wchar_t> out, loc_value value, const format_spec…` · [include/fmt/xchar.h:L46-L58][f1]

Locale-aware writer for wchar_t numeric output: when FMT_USE_LOCALE is on, it fetches the std::locale from the locale_ref, obtains its numpunct<wchar_t> facet, builds a thousands-separator string only if the facet's grouping is non-empty, and dispatches to loc_writer<wchar_t> returning its result.

With locale support compiled out it ignores all inputs and returns false (signaling the caller should fall back to non-localized writing).

<a id="u-74fdf36fafde"></a>
### `include/fmt/xchar.h:arg`

`template <typename T> auto arg(const wchar_t* name, const T& arg) -> named_arg<T, wch…` · [include/fmt/xchar.h:L140-L143][f1]

Creates a named_arg<T, wchar_t> binding a wide-string name to a value for use in format strings.

<a id="u-c6b9884589de"></a>
### `include/fmt/xchar.h:formatted_size`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L301-L309][f1]

Computes the formatted size in code units for exotic-char format strings by formatting into a detail::counting_buffer and returning its count.

<a id="u-a27e9d38377d"></a>
### `include/fmt/xchar.h:operator""_a`

`inline auto operator""_a(const wchar_t* s, size_t) -> detail::udl_arg<wchar_t>` · [include/fmt/xchar.h:L134-L136][f1]

User-defined literal `_a` producing a named-argument wrapper (detail::udl_arg<wchar_t>) for a wide string, enabling `name_a = value` style; only defined when non-type template args are unavailable.

<a id="u-d2da72672a19"></a>
### `include/fmt/xchar.h:print (3)`

`template <typename... T> void print(std::wostream& os, wformat_string<T...> fmt, T&&.…` · [include/fmt/xchar.h:L360-L364][f1]

Wide print to a std::wostream: builds buffered wchar_t context args from the compile-checked format string and delegates to the wostream vprint.

<a id="u-382fe888321f"></a>
### `include/fmt/xchar.h:println (3)`

`template <typename... T> void println(std::wostream& os, wformat_string<T...> fmt, T&…` · [include/fmt/xchar.h:L366-L369][f1]

Wide println to a std::wostream: formats the arguments with fmt::format, then prints the result plus newline to the stream via the wostream print.

<a id="u-a216619ae5e5"></a>
### `runtime`

`inline auto runtime(wstring_view s) -> runtime_format_string<wchar_t>` · [include/fmt/xchar.h:L122-L124][f1]

Wraps a wchar_t string view in a runtime_format_string<wchar_t>, opting out of compile-time format checking.

<a id="u-64e113389e95"></a>
### `include/fmt/xchar.h:vformat_to (2)`

`template <typename OutputIt, typename S, typename Char = detail::format_string_char_t…` · [include/fmt/xchar.h:L228-L237][f1]

Formats an exotic-char format string into an output iterator by obtaining a buffer via detail::get_buffer, running detail::vformat_to, and returning detail::get_iterator's result; enabled when OutputIt is an output iterator for the deduced exotic Char.

<a id="u-7a64503e6cbc"></a>
### `include/fmt/xchar.h:vformat_to_n`

`template <typename OutputIt, typename Char, typename... Args, FMT_ENABLE_IF(detail::i…` · [include/fmt/xchar.h:L271-L281][f1]

Bounded formatting into an output iterator: wraps it in an iterator_buffer with fixed_buffer_traits limiting output to n characters, formats via detail::vformat_to, and returns a format_to_n_result with the advanced iterator and count.

<a id="u-5d145e6cc2ac"></a>
### `include/fmt/xchar.h:vprint`

`inline void vprint(std::FILE* f, wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L311-L317][f1]

Wide vprint to a FILE*: formats into a wmemory_buffer, appends a terminating L'\0', and writes with std::fputws; if fputws returns -1 it throws system_error(errno, "cannot write to file").

<a id="u-624a4d961e2d"></a>
### `include/fmt/xchar.h:vprint (2)`

`inline void vprint(wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L319-L321][f1]

Wide vprint to stdout: delegates to the FILE* overload with stdout.

<a id="u-5737a2b91886"></a>
### `include/fmt/xchar.h:vprint (3)`

`inline void vprint(std::wostream& os, wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L354-L358][f1]

Wide vprint to a std::wostream: formats into a memory buffer via detail::vformat_to and flushes it to the stream with detail::write_buffer.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
