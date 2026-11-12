# ANSI Color Style Formatting

**Capability.** Builds ANSI color escapes and formats, prints, and wraps styled text with foreground, background, and emphasis.

This module implements styled text and ANSI color output. It includes color packing, escape construction, styled arguments, and print/format forwarding.

**Depends on.**

- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 3 edge(s)
- [Format Spec Parser](format-spec-parser.md) · graph-only · 1 edge(s)

Parent: [Character and Style Formatting](character-and-style-formatting.md)

## Units (20)

<a id="u-2e21e82482f3"></a>
### `color.h-ansi-color-escape`

`template <typename Char> struct ansi_color_escape` · [include/fmt/color.h:L366-L367][f1]

ansi_color_escape builds an ANSI escape sequence in a fixed Char buffer.

The color constructor: if the color_type is terminal, it writes ESC [, then the decimal terminal code (background adds 10) as two or three digits, then m; otherwise it copies the seven-character prefix, writes the RGB channels as three-digit decimal fields with delimiters, and sets size to 19. The emphasis constructor maps bold/faint/italic/underline/blink/reverse/conceal/strikethrough to codes 1,2,3,4,5,7,8,9, writes ESC [, appends each present code followed by ';', then replaces the final ';' with 'm'; with no emphasis bits it writes ESC then overwrites the '[' with 'm', yielding ESC 'm' with size 2. Conversion and begin return the buffer; end returns buffer+size. to_esc writes a three-digit decimal and delimiter; has_emphasis tests a bitmask.

<a id="u-f31594561564"></a>
### `color.h-color-type`

`struct color_type` · [include/fmt/color.h:L210-L211][f1]

color_type is a bit-packed color value.

Default value_ is 0. Constructing from color sets the low 24 bits and sets bit 24; constructing from rgb converts to color and delegates; constructing from terminal_color sets the low bits and sets bits 24-25 to 3. The uint32_t constructor is public and stores the raw value. is_terminal_color tests bit 25; value returns the low 24 bits.

<a id="u-5f036583e4f2"></a>
### `color.h-escape-factories`

`template <typename Char> FMT_CONSTEXPR auto make_foreground_color(color_type foregrou…` · [include/fmt/color.h:L448-L452][f1]

make_foreground_color and make_background_color construct ansi_color_escape with the RGB prefixes for foreground and background.

make_emphasis constructs ansi_color_escape from an emphasis value. reset_color appends the literal ESC [0m to a buffer.

<a id="u-48c8eadf75eb"></a>
### `color.h-rgb`

`struct rgb` · [include/fmt/color.h:L192-L193][f1]

rgb is a plain three-byte color value.

The default constructor zeroes all channels; the three-argument constructor stores the given channels; the uint32_t constructor extracts red from bits 16-23, green from 8-15, and blue from 0-7; the color constructor delegates through the same extraction after converting the enum to uint32_t. No range validation is performed.

<a id="u-8e8058d409fb"></a>
### `color.h-style-builders`

`FMT_CONSTEXPR inline auto fg(detail::color_type foreground) noexcept -> text_style` · [include/fmt/color.h:L348-L351][f1]

fg builds a text_style from a color_type's low value; bg shifts the background value left 27; operator|(emphasis, emphasis) constructs a text_style from the left emphasis and ORs the right emphasis into it.

<a id="u-61d833cd70d2"></a>
### `color.h-styled-arg-formatter`

`template <typename T, typename Char> struct formatter<detail::styled_arg<T>, Char> : …` · [include/fmt/color.h:L619-L621][f1]

formatter<detail::styled_arg<T>, Char> inherits formatter<T, Char> and overrides format to write style escapes around the underlying value.

It writes emphasis, foreground, and background escapes when present, tracks has_style, formats the value through the base formatter, and appends reset ESC [0m if any style was written.

<a id="u-011ad6efc10c"></a>
### `color.h-styled-formatting-into-buffer`

`struct styled_arg : view` · [include/fmt/color.h:L471-L476][f1]

styled_arg holds a const T& value and a text_style.

detail::vformat_to(buffer, text_style, fmt, args) appends the emphasis escape if present, then the foreground escape if present, then the background escape if present, formats the arguments into the buffer, and appends reset color if the style is not the default text_style.

<a id="u-a88c6652b8c6"></a>
### `color.h-text-style-accessors`

`FMT_CONSTEXPR auto has_foreground() const noexcept -> bool` · [include/fmt/color.h:L313-L315][f1]

has_foreground tests bit 24; has_background tests bit 51; has_emphasis tests whether style_ shifted right 54 is nonzero.

get_foreground asserts has_foreground and returns the low 26 bits; get_background asserts has_background and returns bits 27-52; get_emphasis asserts has_emphasis and returns style_ shifted right 54 cast to emphasis. Failed assertions go through FMT_ASSERT.

<a id="u-bf1b67b10af5"></a>
### `color.h-text-style-construction-and-combination`

`class text_style` · [include/fmt/color.h:L236-L290][f1]

text_style packs foreground, background, and emphasis into a 64-bit style_.

The emphasis constructor shifts the emphasis bits to bit 54. operator|= adds the two packed styles to detect conflicting terminal/RGB discriminators via overflow bits 26 and 53; if either is set it calls report_error("can't OR a terminal color"), otherwise it ORs and returns *this. operator| copies the left operand and applies |=. Equality compares style_; inequality negates equality. The private uint64_t constructor stores a raw style and is used by friends fg and bg.

<a id="u-cd69c718e653"></a>
### `color.h-vprint`

`template <typename T> struct styled_arg : view { const T& value; text_style style; FM…` · [include/fmt/color.h:L471-L471][f1]

vprint formats a styled string into a memory_buffer via detail::vformat_to, then prints the buffer contents to the FILE using the format string "{}".

<a id="u-0e86a613d41b"></a>
### `include/fmt/color.h:format`

`template <typename... T> inline auto format(text_style ts, format_string<T...> fmt, T…` · [include/fmt/color.h:L586-L590][f1]

format(text_style, format_string, args...) forwards to vformat with fmt.str and vargs.

<a id="u-5919ceab157a"></a>
### `format_to`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/color.h:L612-L617][f1]

format_to(OutputIt, text_style, format_string, args...) forwards to vformat_to with fmt.str and vargs.

<a id="u-0818e14957b6"></a>
### `print`

`template <typename... T> void print(FILE* f, text_style ts, format_string<T...> fmt, …` · [include/fmt/color.h:L512-L515][f1]

print(FILE*, text_style, format_string, args...) forwards to vprint with the format string's str and a vargs pack.

<a id="u-1ecc91f855ad"></a>
### `include/fmt/color.h:print`

`template <typename... T> void print(text_style ts, format_string<T...> fmt, T&&... args)` · [include/fmt/color.h:L526-L529][f1]

print(text_style, format_string, args...) forwards to the FILE* overload with stdout.

<a id="u-b006dc0a0755"></a>
### `println`

`template <typename... T> void println(FILE* f, text_style ts, format_string<T...> fmt…` · [include/fmt/color.h:L548-L551][f1]

println(FILE*, text_style, format_string, args...) forwards to vprintln with fmt.str and vargs.

<a id="u-3c18c284024a"></a>
### `include/fmt/color.h:println`

`template <typename... T> void println(text_style ts, format_string<T...> fmt, T&&... …` · [include/fmt/color.h:L562-L565][f1]

println(text_style, format_string, args...) forwards to the FILE* overload with stdout.

<a id="u-1d44db6148de"></a>
### `styled`

`template <typename T> FMT_CONSTEXPR auto styled(const T& value, text_style ts) -> det…` · [include/fmt/color.h:L664-L668][f1]

styled returns a detail::styled_arg<remove_cvref_t<T>> holding the value reference and the given text_style.

<a id="u-425c753c3798"></a>
### `vformat`

`inline auto vformat(text_style ts, string_view fmt, format_args args) -> std::string` · [include/fmt/color.h:L567-L572][f1]

vformat formats a styled string into a memory_buffer via detail::vformat_to and returns fmt::to_string(buf).

<a id="u-d965f1cf0777"></a>
### `vformat_to`

`template <typename OutputIt, FMT_ENABLE_IF(detail::is_output_iterator<OutputIt, char>…` · [include/fmt/color.h:L593-L600][f1]

vformat_to(OutputIt, text_style, string_view, format_args) obtains a char buffer from the output iterator, calls detail::vformat_to, and returns the iterator derived from the buffer.

<a id="u-91907b55c510"></a>
### `vprintln`

`inline void vprintln(FILE* f, text_style ts, string_view fmt, format_args args)` · [include/fmt/color.h:L531-L537][f1]

vprintln formats a styled string into a memory_buffer, appends a newline, then prints the buffer to the FILE using "{}".

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/color.h
