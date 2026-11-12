# Wide Format and Print Forwarding

**Capability.** Forwards wchar_t format, format_to, print, and vprint operations to buffered formatting and wide output streams.

This module contains wchar_t forwarding overloads. It routes format, format_to, print, and vprint calls to buffered or stream-based wide output.

Parent: [Wide and Exotic Character Paths](wide-and-exotic-character-paths.md)

## Units (10)

<a id="u-b46162e99872"></a>
### `include/fmt/xchar.h:format`

`template <typename... T> inline auto format(text_style ts, wformat_string<T...> fmt, …` · [include/fmt/xchar.h:L348-L352][f1]

This text-style format overload forwards the style, stored format string, and wchar_t format arguments to vformat.

<a id="u-c25121bdc76a"></a>
### `include/fmt/xchar.h:format (2)`

`template <typename... T> auto format(wformat_string<T...> fmt, T&&... args) -> std::w…` · [include/fmt/xchar.h:L187-L190][f1]

This wchar_t format overload calls vformat with the stored format string and wchar_t format arguments, returning std::wstring.

<a id="u-9c0c1fe55c7c"></a>
### `include/fmt/xchar.h:format_to`

`template <typename OutputIt, typename... T> auto format_to(OutputIt out, wformat_stri…` · [include/fmt/xchar.h:L192-L196][f1]

This wchar_t format_to overload calls vformat_to with the stored format string and wchar_t format arguments, returning the output iterator.

<a id="u-1b65b660dd90"></a>
### `include/fmt/xchar.h:format_to_n`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/xchar.h:L283-L288][f1]

This wchar_t format_to_n overload is enabled for a wchar_t output iterator; it forwards to vformat_to_n with the stored format string and wchar_t format arguments.

<a id="u-d73413ffe7dc"></a>
### `include/fmt/xchar.h:print`

`template <typename... T> void print(std::FILE* f, wformat_string<T...> fmt, T&&... args)` · [include/fmt/xchar.h:L323-L326][f1]

This wchar_t print overload forwards the stored format string and wchar_t format arguments to the FILE-based vprint.

<a id="u-38d1ffcc855b"></a>
### `include/fmt/xchar.h:print (2)`

`template <typename... T> void print(wformat_string<T...> fmt, T&&... args)` · [include/fmt/xchar.h:L328-L330][f1]

This wchar_t print overload forwards the stored format string and wchar_t format arguments to the stdout vprint.

<a id="u-d2da72672a19"></a>
### `include/fmt/xchar.h:print (3)`

`template <typename... T> void print(std::wostream& os, wformat_string<T...> fmt, T&&.…` · [include/fmt/xchar.h:L360-L364][f1]

This wchar_t print overload forwards the stored format string and wchar_t format arguments to the wide-stream vprint.

<a id="u-5d145e6cc2ac"></a>
### `include/fmt/xchar.h:vprint`

`inline void vprint(std::FILE* f, wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L311-L317][f1]

This function formats a wchar_t string into a memory buffer, appends a null terminator, and writes it to the FILE with fputws.

If fputws returns -1, it throws a system_error carrying errno and 'cannot write to file'.

<a id="u-624a4d961e2d"></a>
### `include/fmt/xchar.h:vprint (2)`

`inline void vprint(wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L319-L321][f1]

This overload writes a wchar_t formatted string to stdout by forwarding to the FILE-based vprint.

<a id="u-5737a2b91886"></a>
### `include/fmt/xchar.h:vprint (3)`

`inline void vprint(std::wostream& os, wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L354-L358][f1]

This function formats a wchar_t string into a memory buffer and writes the buffer to the wide output stream.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
