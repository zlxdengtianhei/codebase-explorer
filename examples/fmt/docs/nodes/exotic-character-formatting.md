# Exotic character formatting

**Capability.** Format and format_to entry points for character types beyond char and wchar_t, including locale-aware variants.

Support for exotic character types (e.g. char16_t/char32_t): string-returning format, iterator-based format_to, and their locale-aware counterparts. Everything funnels through buffered-context vformat calls.

Parent: [Wide character formatting](wide-character-formatting.md)

## Units (7)

<a id="u-d178a8535105"></a>
### `include/fmt/xchar.h:format (3)`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L200-L207][f1]

Formats with an exotic (non-char, non-wchar_t) character format string, deducing Char via format_string_char_t, and returns std::basic_string<Char> via vformat with a buffered context.

<a id="u-2b6b83b6d480"></a>
### `include/fmt/xchar.h:format (4)`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L219-L226][f1]

Locale-aware format for exotic character types: builds format args for a buffered context and delegates to the locale-taking vformat.

<a id="u-ede40b663f33"></a>
### `include/fmt/xchar.h:format_to (2)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L239-L247][f1]

format_to for exotic character types other than wchar_t: converts the format string to a view, builds buffered-context args, and delegates to vformat_to.

<a id="u-f872eacd5360"></a>
### `include/fmt/xchar.h:format_to (3)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L261-L269][f1]

Locale-aware format_to for exotic chars, delegating to the locale-taking vformat_to with converted format string and buffered-context args; enabled via a bool template parameter and std::enable_if.

<a id="u-3d812594b50c"></a>
### `include/fmt/xchar.h:vformat (2)`

`template <typename Char, FMT_ENABLE_IF(!std::is_same<Char, char>::value)> auto vforma…` · [include/fmt/xchar.h:L178-L185][f1]

Formats a non-char format string with buffered-context args into a memory buffer via detail::vformat_to and returns the result as std::basic_string<Char>.

<a id="u-3188ee0608a4"></a>
### `include/fmt/xchar.h:vformat (3)`

`template <typename S, typename Char = detail::format_string_char_t<S>, FMT_ENABLE_IF(…` · [include/fmt/xchar.h:L209-L217][f1]

Locale-aware vformat for exotic character types: formats into a memory buffer via detail::vformat_to with the locale_ref and returns a std::basic_string<Char>.

<a id="u-f8d71482a4f6"></a>
### `include/fmt/xchar.h:vformat_to (3)`

`template <typename S, typename OutputIt, typename... Args, typename Char = detail::fo…` · [include/fmt/xchar.h:L249-L259][f1]

Locale-aware vformat_to into an output iterator for exotic chars: buffers via detail::get_buffer, formats with the locale through the buffer overload of vformat_to, and returns the converted iterator.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
