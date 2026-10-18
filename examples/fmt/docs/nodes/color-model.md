# Style Model

**Capability.** Packed text_style and color_type representation (bit-packed RGB/terminal color plus emphasis), rgb value type, the pre-rendered ANSI escape buffer, and style constructors fg/bg/operator|.

Understand this before touching styling internals: one uint64_t packs both colors and emphasis, and the escape buffer is filled from it.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Styled Formatting API](color-format-api.md) · graph-confirmed · 6 edge(s)

Parent: [Terminal Color & Styling](color-h.md)

## Units (7)

<a id="u-f31594561564"></a>
### `color.h-color-type`

`namespace detail` · [include/fmt/color.h:L206-L209][f1]

Bit-packed variant of unset, RGB, or terminal color used inside text_style.

A color packs its 24-bit RGB value with bit 24 set; an rgb decomposes to r/g/b bytes and forwards through the color constructor; a terminal_color packs its code with bits 24-25 set (3 << 24). is_terminal_color tests bit 25; value() masks to the low 24 bits, so for terminal colors it yields the SGR code. The default and uint32_t constructors store the raw packed word (default 0, meaning unset).

<a id="u-48c8eadf75eb"></a>
### `color.h-rgb`

`struct rgb` · [include/fmt/color.h:L192-L193][f1]

Value type holding 8-bit red, green, and blue components.

The default constructor yields black (0,0,0); constructors take three uint8_t components, a 32-bit hex value (split by shifting 16 and 8), or a color enumerator converted the same way. All constructors are constexpr; conversion truncates any bits above 0xFF per channel.

<a id="u-fcba1e5ed7b9"></a>
### `color.h-text-style`

`class text_style` · [include/fmt/color.h:L236-L290][f1]

Style combining a foreground color, a background color, and emphasis flags, all packed into one uint64_t: foreground in bits 0-25 (24-bit value plus 2-bit discriminator), bit 26 reserved as an overflow bit, background likewise in bits 27-53, emphasis bits 54-61.

The public constructor takes only emphasis. operator|= ORs the words but first checks for a terminal/other color conflict by adding the packed values: if either foreground or background combines a terminal discriminator (11) with any color discriminator (11 or 01), the sum's overflow bit (26 or 53) is set and report_error throws; otherwise the OR proceeds. operator| composes styles, ==/!= compare raw words, has_foreground/has_background/has_emphasis test the discriminator or emphasis bits, and get_foreground/get_background/get_emphasis each FMT_ASSERT the corresponding has_ predicate (failing via assert_fail) before extracting the masked value. The private uint64_t constructor is used by the fg/bg friends.

raises: [report_error](core-errors.md#u-4fe75221d1d1), [assert_fail](core-errors.md#u-51c7265a0ebb); uses: [color.h-color-type](color-model.md#u-f31594561564)

**Uncertainties.**

- Exact exception type thrown by report_error is defined in format-inl.h, not supplied here.

<a id="u-2e21e82482f3"></a>
### `color.h-ansi-color-escape`

`template <typename Char> struct ansi_color_escape` · [include/fmt/color.h:L366-L367][f1]

Stack buffer holding a ready-made ANSI escape sequence for one color or emphasis.

The color constructor branches on is_terminal_color: for terminal colors it writes ESC [ then the decimal SGR code (adding 10 for backgrounds, detected by comparing esc to "\x1b[48;2;", emitting a leading '1' when the value reaches 100) and 'm'; otherwise it copies the 7-byte template prefix ("\x1b[38;2;" or "\x1b[48;2;"), then writes r, g, b as three zero-padded 3-digit numbers via to_esc separated by ';' and terminated by 'm', totaling 19 characters. The emphasis constructor maps each set emphasis bit to its SGR parameter (bold 1, faint 2, italic 3, underline 4, blink 5, reverse 7, conceal 8, strikethrough 9), writes ESC [ then each active code followed by ';', and overwrites the final ';' with 'm'. Conversion to const Char* and begin/end expose the buffer; end uses the recorded size. If no emphasis is set the buffer is just "\x1b[" plus a terminal 'm' written at position size-1.

**Uncertainties.**

- Terminal-color code assumed below 200: the >=100 branch emits at most one leading '1', and to_esc assumes 8-bit components (max 3 digits); values outside these ranges are not representable via color_type's 24-bit mask anyway.

<a id="u-d20976e15844"></a>
### `fg`

`FMT_CONSTEXPR inline auto fg(detail::color_type foreground) noexcept -> text_style` · [include/fmt/color.h:L348-L351][f1]

Creates a text style carrying only the given foreground color by privately constructing a text_style from the color_type's packed word (bits 0-25).

uses: [color.h-text-style](color-model.md#u-fcba1e5ed7b9)

<a id="u-ab444d1b30e0"></a>
### `bg`

`FMT_CONSTEXPR inline auto bg(detail::color_type background) noexcept -> text_style` · [include/fmt/color.h:L354-L357][f1]

Creates a text style carrying only the given background color by shifting the color_type's packed word left 27 into the background field of text_style.

uses: [color.h-text-style](color-model.md#u-fcba1e5ed7b9)

<a id="u-01f6fb561f3c"></a>
### `operator|`

`FMT_CONSTEXPR inline auto operator|(emphasis lhs, emphasis rhs) noexcept -> text_style` · [include/fmt/color.h:L359-L362][f1]

Combines two emphasis flags into a text_style by wrapping the left operand in text_style and applying operator|=, inheriting the terminal-color conflict check (irrelevant for pure emphasis) and OR semantics.

calls: [color.h-text-style](color-model.md#u-fcba1e5ed7b9)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/color.h