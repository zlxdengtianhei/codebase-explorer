# Text styling and colors

**Capability.** ANSI color/emphasis styling: text_style, RGB/terminal color types, escape sequence generation, and styled print/format functions.

Terminal styling support: color types, the packed text_style, ANSI escape construction, and the print/format/println family that applies styles. styled_arg lets a style apply to a single argument.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 3 edge(s)

Parent: [Wide text and styling](wide-text-and-styling.md)

## Units (13)

<a id="u-2e21e82482f3"></a>
### `color.h-ansi-color-escape`

`template <typename Char> struct ansi_color_escape` · [include/fmt/color.h:L366-L367][f1]

Builds a short ANSI escape sequence into a fixed Char buffer, usable as a const Char* or via begin()/end().

The color constructor branches on is_terminal_color(): for terminal colors it emits ESC '[' plus the two-digit code (with a leading '1' and modulo reduction for codes >= 100) and 'm', adding 10 to the code when the escape string indicates a background (compared against "\x1b[48;2;"); for RGB colors it copies the 7-character escape prefix, then writes r, g, b as three-digit zero-padded decimal values with ';' separators and a final 'm' via to_esc, setting size to 19. The emphasis constructor maps each of the eight emphasis bits to its SGR code (1,2,3,4,5,7,8,9), emits ESC '[' followed by each active code and ';', then overwrites the last ';' with 'm'; with no emphasis set this still writes ESC '[' 'm' since size is at least 2 after the prefix. The buffer is zero-initialized and large enough for the worst case; all paths are constexpr and cannot fail.

<a id="u-8105ebf8414c"></a>
### `color.h-color-type-bit-packed-color`

`struct color_type` · [include/fmt/color.h:L210-L211][f1]

A detail variant packing an RGB color, a terminal color, or no color into one uint32_t.

The color overload sets the 24-bit value with discriminator bit 24; the rgb overload reuses the color overload after packing the bytes; the terminal_color overload stores the code with bits 24-25 set (value 3<<24). is_terminal_color() tests bit 25; value() masks to the low 24 bits. The raw uint32_t constructor (used internally by text_style) stores the value verbatim, so a default-constructed color_type reads as unset. All operations are constexpr and cannot fail.

<a id="u-51e4800e1642"></a>
### `color.h-escape-factories-and-reset-color`

`template <typename Char> FMT_CONSTEXPR auto make_foreground_color(color_type foregrou…` · [include/fmt/color.h:L448-L452][f1]

make_foreground_color/make_background_color/make_emphasis wrap ansi_color_escape construction with the appropriate escape prefix ("\x1b[38;2;" / "\x1b[48;2;") or emphasis overload; reset_color appends the literal "\x1b[0m" to a buffer.

All are thin constexpr/inline forwarders with no failure paths.

<a id="u-844630be9a41"></a>
### `color.h-fg-bg-and-emphasis-or-helpers`

`FMT_CONSTEXPR inline auto fg(detail::color_type foreground) noexcept -> text_style` · [include/fmt/color.h:L348-L351][f1]

fg packs a color_type's raw value into the foreground field of a text_style; bg shifts it into the background field (bit 27).

operator|(emphasis, emphasis) combines two emphasis masks by constructing a text_style from the left mask and ORing in the right one, yielding a style with only emphasis bits. All are constexpr and noexcept.

<a id="u-708bcef97002"></a>
### `color.h-formatter-for-styled-arg`

`template <typename T, typename Char> struct formatter<detail::styled_arg<T>, Char> : …` · [include/fmt/color.h:L619-L621][f1]

A formatter<styled_arg<T>, Char> inheriting formatter<T, Char> that writes the style's escape sequences (emphasis, foreground, background, each conditional on the style having it) to the context output, then delegates to the base formatter to format the wrapped value, and appends "\x1b[0m" only if any style component was present (tracked by has_style).

This styles a single argument rather than the whole output; base formatter errors propagate.

<a id="u-9c261facbcb1"></a>
### `color.h-rgb-color-struct`

`struct rgb` · [include/fmt/color.h:L192-L193][f1]

A plain red/green/blue byte triple constructible from three uint8_t components, from a packed uint32_t (r = bits 16-23, g = 8-15, b = 0-7), or from a color enum value with the same packing; the default constructor yields black (0,0,0).

All constructors are constexpr with no failure paths.

<a id="u-54845fbdcd0f"></a>
### `color.h-styled-arg-and-styled-vformat-to`

`struct styled_arg : view` · [include/fmt/color.h:L471-L476][f1]

styled_arg is a view-like pair of a const reference to a value and a text_style; detail::vformat_to writes a styled string into a buffer<Char> by conditionally appending emphasis, foreground, and background escape sequences (in that order, each only if the style has that component), then delegating to the plain vformat_to overload for the actual formatting, and finally appending a reset sequence if the style differs from a default text_style.

Escape output precedes the formatted text, so the style applies to the whole result; exceptions from the inner vformat_to propagate unchanged.

<a id="u-2b5e4fc5bf21"></a>
### `color.h-styled-format-family`

`inline auto vformat(text_style ts, string_view fmt, format_args args) -> std::string` · [include/fmt/color.h:L567-L572][f1]

vformat styles into a memory_buffer via detail::vformat_to and converts it to a std::string with fmt::to_string; the variadic format builds args from the pack and calls vformat.

Formatting errors propagate.

<a id="u-d9ec9a83d1c6"></a>
### `color.h-styled-format-to-family`

`template <typename OutputIt, FMT_ENABLE_IF(detail::is_output_iterator<OutputIt, char>…` · [include/fmt/color.h:L593-L600][f1]

vformat_to obtains a buffer over the output iterator via detail::get_buffer<char>, runs detail::vformat_to into it, and returns the iterator past the written range via detail::get_iterator; the variadic format_to forwards with packed args.

Enabled only for output iterators of char.

<a id="u-b1f7c61caa13"></a>
### `color.h-styled-print-family`

`template <typename T> struct styled_arg : view { const T& value; text_style style; FM…` · [include/fmt/color.h:L471-L471][f1]

vprint formats into a memory_buffer via detail::vformat_to and writes the result to the FILE* with print(f, "{}", view) so the buffer content is emitted verbatim without reinterpreting escape codes; the variadic print overloads build format_args from the pack and forward to vprint, the no-file overload targeting stdout.

Errors from the underlying print propagate.

<a id="u-8c675c0794b7"></a>
### `color.h-styled-println-family`

`inline void vprintln(FILE* f, text_style ts, string_view fmt, format_args args)` · [include/fmt/color.h:L531-L537][f1]

Like the print family but appends a '\n' to the memory_buffer before writing it to the FILE* (so the newline is outside any reset sequence); the variadic println overloads forward to vprintln, the no-file overload targeting stdout.

<a id="u-fcba1e5ed7b9"></a>
### `color.h-text-style`

`class text_style` · [include/fmt/color.h:L236-L290][f1]

A packed 64-bit text style holding foreground color (bits 0-25), background color (bits 27-52), and emphasis (bits 54-61), each color with a 2-bit discriminator (00 unset, 01 RGB, 11 terminal).

The public emphasis constructor shifts the emphasis mask into the emphasis field; the private raw-uint64_t constructor is used only by fg/bg. operator|= first adds the two packed styles and checks overflow bits 26 and 53: if either side of a color pair mixes a terminal color with any color, report_error("can't OR a terminal color") is raised (constexpr-friendly, non-returning); otherwise the styles are ORed in place. operator| delegates to |=; ==/!= compare the packed values. has_foreground/has_background test the low discriminator bit of each field; has_emphasis checks any nonzero emphasis bits. get_foreground/get_background extract the 26-bit color field and get_emphasis the top bits; each FMT_ASSERTs its has_* precondition, so calling a getter on a style lacking that component triggers an assertion failure (behavior depends on the assert configuration).

<a id="u-1d44db6148de"></a>
### `styled`

`template <typename T> FMT_CONSTEXPR auto styled(const T& value, text_style ts) -> det…` · [include/fmt/color.h:L664-L668][f1]

Returns a detail::styled_arg holding a reference to the given value (with cv/ref stripped for the type parameter) and the given text_style, so the styled_arg formatter applies ANSI styling to just that argument inside a larger format call.

constexpr; the value is stored by reference, so the argument must outlive the formatting call.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/color.h
