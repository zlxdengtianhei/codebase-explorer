# Wide convenience formatting API

**Capability.** User-facing wide-string format, format_to, print, styled format, and to_string wrappers built on compile-checked wformat_string.

Thin public wrappers that make wide formatting ergonomic: format, format_to, print, styled formatting, and converting any value to std::wstring. All delegate to the wide core with compile-time checked format strings.

Parent: [Wide character formatting](wide-character-formatting.md)

## Units (8)

<a id="u-f5d4c38c3044"></a>
### `xchar.h-format-to-n`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/xchar.h:L283-L288][f1]

Bounded format_to for wide and exotic format strings: the wchar_t overload uses a compile-checked wformat_string with make_wformat_args; the exotic overload converts the format string to a view and builds buffered-context args.

Both delegate to vformat_to_n.

<a id="u-9bc0ca2bd06c"></a>
### `xchar.h-print-wide`

`template <typename... T> void print(std::FILE* f, wformat_string<T...> fmt, T&&... args)` · [include/fmt/xchar.h:L323-L326][f1]

Wide print: formats a compile-checked wformat_string with wide args and writes either to the given FILE* or to stdout via vprint.

<a id="u-b46162e99872"></a>
### `include/fmt/xchar.h:format`

`template <typename... T> inline auto format(text_style ts, wformat_string<T...> fmt, …` · [include/fmt/xchar.h:L348-L352][f1]

Wide text-style format: applies a text_style to a compile-checked wformat_string with wide args, delegating to the text-style vformat.

<a id="u-c25121bdc76a"></a>
### `include/fmt/xchar.h:format (2)`

`template <typename... T> auto format(wformat_string<T...> fmt, T&&... args) -> std::w…` · [include/fmt/xchar.h:L187-L190][f1]

Wide-string format: takes a compile-checked wformat_string, builds wide format args, and returns the formatted std::wstring via vformat.

<a id="u-9c0c1fe55c7c"></a>
### `include/fmt/xchar.h:format_to`

`template <typename OutputIt, typename... T> auto format_to(OutputIt out, wformat_stri…` · [include/fmt/xchar.h:L192-L196][f1]

Wide-string format_to: formats a compile-checked wformat_string with wide args into the output iterator, returning the iterator.

<a id="u-9babc9f02b27"></a>
### `make_wformat_args`

`template <typename... T> constexpr auto make_wformat_args(T&... args) -> decltype(fmt…` · [include/fmt/xchar.h:L126-L130][f1]

Builds a format_arg_store for wformat_context from the arguments via fmt::make_format_args, mirroring make_format_args for wchar_t.

<a id="u-cfba6dbb5108"></a>
### `to_wstring`

`template <typename T> inline auto to_wstring(const T& value) -> std::wstring` · [include/fmt/xchar.h:L372-L374][f1]

Converts any value to std::wstring using its default format by formatting with the compile-time wide string L"{}".

<a id="u-90bfb1dc242c"></a>
### `include/fmt/xchar.h:vformat`

`inline auto vformat(text_style ts, wstring_view fmt, wformat_args args) -> std::wstring` · [include/fmt/xchar.h:L341-L346][f1]

Wide text-style vformat: formats with a text_style, wide format string, and wide args into a wmemory_buffer via detail::vformat_to, returning a std::wstring.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
