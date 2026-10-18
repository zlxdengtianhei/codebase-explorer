# Styled Formatting API

**Capability.** Core styled vformat_to (escape, formatted text, conditional reset), the styled_arg formatter, and public format/format_to/print/println/styled overloads built on it.

Call the public overloads; they all funnel through detail::vformat_to and the styled_arg formatter which wraps values with the style's ANSI escapes.

**Depends on.**

- [Style Model](color-model.md) · graph-confirmed · 6 edge(s)

Parent: [Terminal Color & Styling](color-h.md)

## Units (11)

<a id="u-4a5972dc6d05"></a>
### `color.h-styled-arg-vformat-to`

`template <typename T> struct styled_arg : view { const T& value; text_style style; FM…` · [include/fmt/color.h:L471-L471][f1]

Core styled formatting.

styled_arg is a view holding a const T& plus a text_style. detail::vformat_to(buf, ts, fmt, args) writes, in order, the emphasis escape if ts.has_emphasis(), the foreground escape if ts.has_foreground(), and the background escape if ts.has_background(), then performs the ordinary vformat_to of the format string and arguments, and finally appends the "\x1b[0m" reset when ts differs from a default text_style. Unset style parts are skipped, so a default style produces plain formatted output with no escapes.

calls: [color.h-ansi-color-escape](color-model.md#u-2e21e82482f3)

<a id="u-7b9c9464c4ab"></a>
### `include/fmt/color.h:format (2)`

`template <typename FormatContext> FMT_CONSTEXPR auto format(const detail::styled_arg<…` · [include/fmt/color.h:L621-L651][f1]

Formatter that wraps a styled_arg's value with ANSI escapes.

It derives from formatter<T, Char> and reuses the base's parse. During formatting it writes, via detail::copy into ctx.out(), the emphasis escape if present, then foreground, then background, tracking has_style; then delegates the value itself to formatter<T, Char>::format(arg.value, ctx); finally, if any style was emitted, appends the "\x1b[0m" reset. A default text_style yields exactly the base formatter's output with no escape bytes.

calls: [color.h-ansi-color-escape](color-model.md#u-2e21e82482f3); uses: [color.h-styled-arg-vformat-to](color-format-api.md#u-4a5972dc6d05)

<a id="u-1d44db6148de"></a>
### `styled`

`template <typename T> FMT_CONSTEXPR auto styled(const T& value, text_style ts) -> det…` · [include/fmt/color.h:L664-L668][f1]

Wraps a value with a text_style for use as a formatting argument: returns detail::styled_arg<remove_cvref_t<T>>{value, ts}, holding the argument by reference, later rendered by the styled_arg formatter.

contract: [include/fmt/color.h:format (2)](color-format-api.md#u-7b9c9464c4ab)

<a id="u-425c753c3798"></a>
### `vformat`

`inline auto vformat(text_style ts, string_view fmt, format_args args) -> std::string` · [include/fmt/color.h:L567-L572][f1]

Type-erased styled formatting to a string: renders into a memory_buffer with detail::vformat_to (escapes, formatted text, conditional reset) and returns the buffer contents via fmt::to_string.

calls: [color.h-styled-arg-vformat-to](color-format-api.md#u-4a5972dc6d05)

<a id="u-d965f1cf0777"></a>
### `vformat_to`

`template <typename OutputIt, FMT_ENABLE_IF(detail::is_output_iterator<OutputIt, char>…` · [include/fmt/color.h:L593-L600][f1]

Type-erased styled formatting through an output iterator: obtains a detail buffer wrapping `out`, runs detail::vformat_to into it (escapes, formatted text, conditional reset), and returns detail::get_iterator(buf, out) as the past-the-end iterator.

Constrained to output iterators of char.

calls: [color.h-styled-arg-vformat-to](color-format-api.md#u-4a5972dc6d05)

<a id="u-0e86a613d41b"></a>
### `include/fmt/color.h:format`

`template <typename... T> inline auto format(text_style ts, format_string<T...> fmt, T…` · [include/fmt/color.h:L586-L590][f1]

Typed styled formatting to a string: forwards fmt.str and packed vargs to the type-erased vformat overload and returns its std::string.

calls: [vformat](color-format-api.md#u-425c753c3798)

<a id="u-5919ceab157a"></a>
### `format_to`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/color.h:L612-L617][f1]

Typed styled formatting to an output iterator: forwards to the type-erased vformat_to with fmt.str and packed vargs and returns its iterator result.

calls: [vformat_to](color-format-api.md#u-d965f1cf0777)

<a id="u-0818e14957b6"></a>
### `print`

`template <typename... T> void print(FILE* f, text_style ts, format_string<T...> fmt, …` · [include/fmt/color.h:L512-L515][f1]

Formats with a text style and prints to the given FILE.

It renders into a memory_buffer via detail::vformat_to (escapes, formatted text, conditional reset) and prints the buffer contents as a string_view with print(f, FMT_STRING("{}"), ...).

calls: [color.h-styled-arg-vformat-to](color-format-api.md#u-4a5972dc6d05)

<a id="u-1ecc91f855ad"></a>
### `include/fmt/color.h:print`

`template <typename... T> void print(text_style ts, format_string<T...> fmt, T&&... args)` · [include/fmt/color.h:L526-L529][f1]

Styled print to stdout: forwards to the FILE overload with stdout and the forwarded arguments.

calls: [print](color-format-api.md#u-0818e14957b6)

<a id="u-3c18c284024a"></a>
### `include/fmt/color.h:println`

`template <typename... T> void println(text_style ts, format_string<T...> fmt, T&&... …` · [include/fmt/color.h:L562-L565][f1]

Styled println to stdout: forwards to the FILE overload of println with stdout and the forwarded arguments.

calls: [vprintln](color-format-api.md#u-91907b55c510)

<a id="u-91907b55c510"></a>
### `vprintln`

`inline void vprintln(FILE* f, text_style ts, string_view fmt, format_args args)` · [include/fmt/color.h:L531-L537][f1]

Styled vformat into a memory_buffer, appends a '\n' after the (possibly reset-terminated) output, and prints the whole buffer to the given FILE via print.

calls: [color.h-styled-arg-vformat-to](color-format-api.md#u-4a5972dc6d05)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/color.h