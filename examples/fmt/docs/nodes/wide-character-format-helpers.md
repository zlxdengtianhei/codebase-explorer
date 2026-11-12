# Wide Character Format Helpers

**Capability.** Provides wchar_t and exotic-character format-string wrappers, argument stores, named arguments, and bounded formatting helpers.

Use this module for wide-character formatting support. The units describe wchar_t format strings, argument stores, named arguments, and bounded output.

Parent: [Wide and Exotic Character Paths](wide-and-exotic-character-paths.md)

## Units (14)

<a id="u-c91ec548f8ca"></a>
### `xchar.h-basic-fstring`

`template <typename Char, typename... T> struct basic_fstring` · [include/fmt/xchar.h:L79-L95][f1]

This compile-time format string wrapper stores a string view and computes checker and argument-pack types from the argument list.

Construction from a string-view-convertible value stores it and, when consteval is enabled, parses it with the checker; construction from a compile string with the same character type stores its value and parses it at compile time; construction from a runtime format string stores its view. It also provides a deprecated string-view conversion and a get accessor.

<a id="u-37a99de3f461"></a>
### `xchar.h-wchar-join-overloads`

`template <typename It, typename Sentinel, typename S, typename Char = typename declty…` · [include/fmt/xchar.h:L145-L151][f1]

These overloads build join views for wide or exotic character separators.

The iterator overload returns a join view over the iterator range and is enabled when the deduced character is not char. The range overload returns a join view over begin/end and is enabled when the deduced character is not char and the range is not tuple-like. The initializer_list overload is deprecated, has no such enable_if, is always available for wchar_t, and delegates to the iterator overload. The tuple overload returns a tuple join view and is enabled when the deduced character is not char and the tuple is tuple-like.

<a id="u-29b8e5ac1e06"></a>
### `include/fmt/xchar.h:write_loc`

`inline auto write_loc(basic_appender<wchar_t> out, loc_value value, const format_spec…` · [include/fmt/xchar.h:L46-L58][f1]

This locale writer formats a localized value for wchar_t output when locale support is enabled.

It obtains the std::locale, its wchar_t numpunct facet, and grouping; a nonempty grouping produces a one-character thousands separator, then the value is visited with a locale writer. When locale support is disabled it ignores its inputs and returns false.

<a id="u-74fdf36fafde"></a>
### `include/fmt/xchar.h:arg`

`template <typename T> auto arg(const wchar_t* name, const T& arg) -> named_arg<T, wch…` · [include/fmt/xchar.h:L140-L143][f1]

This helper builds a named wchar_t argument from a name and value.

<a id="u-c6b9884589de"></a>
### `include/fmt/xchar.h:formatted_size`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L301-L309][f1]

This function is enabled for exotic character types; it formats into a counting buffer and returns the counted output size.

<a id="u-a27e9d38377d"></a>
### `include/fmt/xchar.h:operator""_a`

`inline auto operator""_a(const wchar_t* s, size_t) -> detail::udl_arg<wchar_t>` · [include/fmt/xchar.h:L134-L136][f1]

This literal operator builds a named wchar_t argument from a null-terminated name; it is compiled only when non-type template arguments are unavailable.

<a id="u-9babc9f02b27"></a>
### `make_wformat_args`

`template <typename... T> constexpr auto make_wformat_args(T&... args) -> decltype(fmt…` · [include/fmt/xchar.h:L126-L130][f1]

This helper builds a wchar_t format argument store by forwarding to make_format_args with the wchar_t buffered context.

<a id="u-0f2076553706"></a>
### `include/fmt/xchar.h:println`

`template <typename... T> void println(std::FILE* f, wformat_string<T...> fmt, T&&... …` · [include/fmt/xchar.h:L332-L335][f1]

This wchar_t println overload formats the arguments first, then prints the formatted result followed by a newline to the FILE.

<a id="u-ff816b6a5acd"></a>
### `include/fmt/xchar.h:println (2)`

`template <typename... T> void println(wformat_string<T...> fmt, T&&... args)` · [include/fmt/xchar.h:L337-L339][f1]

This wchar_t println overload formats the arguments first, then prints the formatted result followed by a newline to stdout.

<a id="u-382fe888321f"></a>
### `include/fmt/xchar.h:println (3)`

`template <typename... T> void println(std::wostream& os, wformat_string<T...> fmt, T&…` · [include/fmt/xchar.h:L366-L369][f1]

This wchar_t println overload formats the arguments first, then prints the formatted result followed by a newline to the wide output stream.

<a id="u-a216619ae5e5"></a>
### `runtime`

`inline auto runtime(wstring_view s) -> runtime_format_string<wchar_t>` · [include/fmt/xchar.h:L122-L124][f1]

This helper wraps a wstring view in a runtime format string for wchar_t.

<a id="u-cfba6dbb5108"></a>
### `to_wstring`

`template <typename T> inline auto to_wstring(const T& value) -> std::wstring` · [include/fmt/xchar.h:L372-L374][f1]

This function converts a value to std::wstring using the default wchar_t format '{}'.

<a id="u-90bfb1dc242c"></a>
### `include/fmt/xchar.h:vformat`

`inline auto vformat(text_style ts, wstring_view fmt, wformat_args args) -> std::wstring` · [include/fmt/xchar.h:L341-L346][f1]

This text-style vformat overload formats a wchar_t string with the given style into a memory buffer and returns the buffer contents as std::wstring.

<a id="u-7a64503e6cbc"></a>
### `include/fmt/xchar.h:vformat_to_n`

`template <typename OutputIt, typename Char, typename... Args, FMT_ENABLE_IF(detail::i…` · [include/fmt/xchar.h:L271-L281][f1]

This bounded formatter is enabled for an output iterator and exotic character type; it uses a fixed-buffer iterator buffer limited to n, formats into it, and returns the output iterator and written count.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
