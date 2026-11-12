# Exotic Character Formatting

**Capability.** Implements format, vformat, and format_to paths for character types other than char and wchar_t.

Come here for formatting with exotic character types. The units describe buffered contexts, format-string conversion, and vformat/format_to forwarding.

Parent: [Wide and Exotic Character Paths](wide-and-exotic-character-paths.md)

## Units (10)

<a id="u-1543a9ab5af2"></a>
### `include/fmt/xchar.h:vformat_to`

`template <typename Char> void vformat_to(buffer<Char>& buf, basic_string_view<Char> f…` · [include/fmt/xchar.h:L60-L68][f1]

This internal formatter requires a non-char character type, creates an appender over the buffer, and parses the format string with a format handler carrying the parse context, output, arguments, and locale.

<a id="u-d178a8535105"></a>
### `include/fmt/xchar.h:format (3)`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L200-L207][f1]

This format overload is enabled when the deduced character is neither char nor wchar_t; it converts the format to a string view and formats arguments through a buffered context for that character type, returning a basic string.

<a id="u-2b6b83b6d480"></a>
### `include/fmt/xchar.h:format (4)`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L219-L226][f1]

This locale-aware format overload is enabled for exotic character types; it forwards to vformat with the locale, converted format string, and buffered-context arguments.

<a id="u-ede40b663f33"></a>
### `include/fmt/xchar.h:format_to (2)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L239-L247][f1]

This format_to overload is enabled for an output iterator and a character type that is neither char nor wchar_t; it forwards to vformat_to with converted format string and buffered-context arguments.

<a id="u-f872eacd5360"></a>
### `include/fmt/xchar.h:format_to (3)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L261-L269][f1]

This locale-aware format_to overload is enabled when the output iterator and exotic character type conditions hold; it forwards to vformat_to with the locale, converted format string, and buffered-context arguments.

<a id="u-e74f538e8e08"></a>
### `include/fmt/xchar.h:format_to_n (2)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L290-L299][f1]

This format_to_n overload is enabled for an output iterator and a character type that is neither char nor wchar_t; it forwards to vformat_to_n with a basic string view of the format and buffered-context arguments.

<a id="u-3d812594b50c"></a>
### `include/fmt/xchar.h:vformat (2)`

`template <typename Char, FMT_ENABLE_IF(!std::is_same<Char, char>::value)> auto vforma…` · [include/fmt/xchar.h:L178-L185][f1]

This vformat overload is enabled for non-char character types; it formats into a memory buffer and returns the buffer contents as a basic string.

<a id="u-3188ee0608a4"></a>
### `include/fmt/xchar.h:vformat (3)`

`template <typename S, typename Char = detail::format_string_char_t<S>, FMT_ENABLE_IF(…` · [include/fmt/xchar.h:L209-L217][f1]

This locale-aware vformat overload is enabled for exotic character types; it formats into a memory buffer with the locale and returns a basic string.

<a id="u-64e113389e95"></a>
### `include/fmt/xchar.h:vformat_to (2)`

`template <typename OutputIt, typename S, typename Char = detail::format_string_char_t…` · [include/fmt/xchar.h:L228-L237][f1]

This vformat_to overload is enabled for an output iterator and exotic character type; it obtains a buffer for the iterator, formats into it, and returns the iterator advanced by the buffer.

<a id="u-f8d71482a4f6"></a>
### `include/fmt/xchar.h:vformat_to (3)`

`template <typename S, typename OutputIt, typename... Args, typename Char = detail::fo…` · [include/fmt/xchar.h:L249-L259][f1]

This locale-aware vformat_to overload is enabled for an output iterator and exotic character type; it obtains a buffer, formats with the locale, and returns the iterator advanced by the buffer.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
