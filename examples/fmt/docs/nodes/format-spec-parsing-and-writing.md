# Format Spec Parsing and Writing

**Capability.** Parses format specifications and writes builtin values with padding, signs, prefixes, escaping, and floating-point presentation.

Use this module for the main parser and writer paths for standard format specs. It covers string, integer, floating-point, padding, sign, and named-argument handling.

**Depends on.**

- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-confirmed · 5 edge(s)
- [Format Spec Parser](format-spec-parser.md) · graph-only · 9 edge(s)
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 3 edge(s)
- [Compile-Time Format Checking](compile-time-format-checking.md) · graph-only · 1 edge(s)

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (24)

<a id="u-52f92331f19b"></a>
### `format.h-argument-visitors`

`void operator()(typename basic_format_arg<context>::handle h)` · [include/fmt/format.h:L3953-L3958][f1]

The default visitor reports a missing argument for monostate and writes builtin values.

The spec visitor writes builtin values with specs and locale. The dynamic-spec visitor returns an unsigned value for integers, mapping negatives to all ones, and reports an error for non-integers. The dynamic-spec handler resolves an index or name, reports missing arguments, rejects values above the integer maximum, and stores the result.

<a id="u-ac44050f5e99"></a>
### `format.h-bytes-formatter`

`FMT_CONSTEXPR auto parse(parse_context<>& ctx) -> const char*` · [include/fmt/format.h:L4341-L4344][f1]

The parser reads string format specs.

The formatter resolves dynamic width and precision, then writes the byte view with string padding.

<a id="u-700686dc8de3"></a>
### `format.h-escaping-and-character-writing`

`template <size_t width, typename Char, typename OutputIt> auto write_codepoint(Output…` · [include/fmt/format.h:L2026-L2034][f1]

These helpers write escaped text and characters.

The code-point writer emits a backslash, a prefix, and fixed-width hex digits. The escape writer maps newline, carriage return, tab, quote, apostrophe, and backslash specially; other values use hex, Unicode, or per-byte escapes when out of range. The string writer wraps in double quotes and copies or escapes segments. The character writer wraps in single quotes and escapes when needed except for a double quote. The character formatter optionally uses debug escaping and then applies padding.

<a id="u-9ecb7c23dc89"></a>
### `format.h-finite-checks`

`template <typename T, FMT_ENABLE_IF(is_floating_point<T>::value&& has_isfinite<T>::va…` · [include/fmt/format.h:L2889-L2896][f1]

The first overload uses the standard finite check outside constant evaluation and otherwise compares against infinities and NaN.

The fallback overload always uses the comparison form for types without a standard finite check.

<a id="u-bef74423df47"></a>
### `format.h-format-handler-fields`

`FMT_CONSTEXPR auto on_arg_id(basic_string_view<Char> id) -> int` · [include/fmt/format.h:L4057-L4062][f1]

The named-argument handler checks the name and resolves it, reporting an error when absent.

The format-spec handler reports a missing argument, lets custom types format themselves, otherwise parses specs, resolves dynamic width and precision, and visits the argument with the spec writer.

<a id="u-8a02ee65dc6a"></a>
### `format.h-grouped-integer-formatter`

`FMT_CONSTEXPR auto parse(parse_context<>& ctx) -> const char*` · [include/fmt/format.h:L4380-L4383][f1]

The parser reads integer format specs.

The formatter resolves dynamic width and precision, builds a sign/prefix argument, and writes the integer with a fixed comma grouping pattern.

<a id="u-8f57128e6ef7"></a>
### `format.h-integer-writing`

`template <typename Char, typename OutputIt, typename T> FMT_CONSTEXPR FMT_INLINE auto…` · [include/fmt/format.h:L2329-L2391][f1]

The main writer formats an integer argument into a stack buffer according to presentation type, adding alternate prefixes and handling character presentation separately.

It has a fast path when width and precision are absent, otherwise computes size and zero padding and right-pads. The no-inline wrapper calls the main writer.

<a id="u-f1c31e2d1801"></a>
### `format.h-nested-format-specs`

`FMT_CONSTEXPR auto parse(const Char* begin, const Char* end, parse_context<Char>& ctx…` · [include/fmt/format.h:L4122-L4131][f1]

The basic parser reads optional alignment and width, including dynamic width.

The separator overload stops before a separator character. The writer resolves dynamic width; with zero width it writes the body directly, otherwise it writes the body into a temporary buffer and writes that buffer with the outer specs.

<a id="u-d030596f3e53"></a>
### `format.h-nested-formatter`

`template <typename FormatContext> auto write_arg(FormatContext& ctx, nested_view<U> v…` · [include/fmt/format.h:L4409-L4413][f1]

The nested-view writer formats the pointed-to value with the stored formatter; the generic writer uses the normal value writer.

The body writer applies the variadic arguments in order and returns the output. Parsing first reads outer nested specs, advances the context, then parses the inner formatter. Writing delegates to the nested specs writer.

<a id="u-1fc4881d3c88"></a>
### `format.h-padded-writing`

`template <typename Char, align default_align = align::left, typename OutputIt, typena…` · [include/fmt/format.h:L1933-L1952][f1]

These functions write a value with width padding.

They compute padding from requested width versus display width, split it left and right according to alignment and the default alignment, reserve space, fill, invoke the writer, fill again, and return the base iterator. The shorter overload uses the size as the display width.

<a id="u-5630b4c90898"></a>
### `format.h-significand-writing`

`template <typename Char, typename OutputIt> constexpr auto write_significand(OutputIt…` · [include/fmt/format.h:L2643-L2647][f1]

These overloads write a decimal significand in several forms.

Basic forms copy characters or format an integer. The exponent form appends trailing zeros and applies grouping when present. The integral-size forms insert a decimal point at the requested position, using a direct buffer or an output iterator. The grouped form writes the integral part through grouping and copies the fractional part.

<a id="u-eca20a83a44c"></a>
### `format.h-string-and-integer-write-overloads`

`template <typename Char, typename OutputIt, FMT_ENABLE_IF(std::is_same<Char, char>::v…` · [include/fmt/format.h:L2506-L2515][f1]

The non-narrow string overload truncates by precision, optionally counts debug-escaped size, and pads.

The locale overload ignores the locale and forwards. The C-string overload writes a pointer when pointer presentation is requested, reports an error for null, and otherwise writes a string view. The no-spec integer overload computes absolute value and sign, counts digits, uses direct pointer output when possible, and otherwise writes the sign and decimal digits.

<a id="u-d11c6739150e"></a>
### `format.h-value-write-overloads`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_fast_float<T…` · [include/fmt/format.h:L3785-L3849][f1]

These overloads dispatch values to formatting.

The floating overload handles localization, sign, non-finite values, numeric alignment, shortest Dragonbox output, hexfloat, and fixed/exponential precision rules. The fast-float no-spec overload writes shortest fixed or exponential form directly. The non-fast float overload forwards to the spec overload. The monostate overload asserts. The string-view overload copies. The string-view-convertible overload forwards. The enum overload writes the underlying value. The bool overload writes true/false unless an integer or string presentation is requested. The character overload reserves and writes one character. The C-string overload reports null and otherwise writes a string view. The void-pointer overload writes a pointer.

<a id="u-ab8ef9a9cc81"></a>
### `format.h-write-dispatch`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_integral<T>:…` · [include/fmt/format.h:L2401-L2414][f1]

The integral overload first tries localized writing, then builds a sign/prefix argument and calls the integer writer, using the no-inline path for appenders.

The character overload checks character specs and either writes a character or writes the unsigned integer value. The narrow-string overload handles debug escaping, precision and width limits, display width, a bounded output iterator, and final padding.

<a id="u-86decb0e5906"></a>
### `display_width_of`

`FMT_CONSTEXPR inline auto display_width_of(uint32_t cp) noexcept -> size_t` · [include/fmt/format.h:L836-L850][f1]

This function returns the display width of a code point.

Values below the first wide range are width one; otherwise it binary-searches the sorted wide ranges and returns two on a hit, one on a miss. It is noexcept.

<a id="u-fa90bc1ea1ab"></a>
### `write_bytes`

`template <typename Char, align default_align = align::left, typename OutputIt> FMT_CO…` · [include/fmt/format.h:L1961-L1969][f1]

This function writes a byte string with padding, using the string size as both size and display width and the requested default alignment.

<a id="u-c383924cee91"></a>
### `FMT_BEGIN_EXPORT.size_padding.exp_upper`

`template <typename T> FMT_CONSTEVAL auto exp_upper() -> int` · [include/fmt/format.h:L2733-L2737][f1]

This function returns the exponent threshold for switching to exponential notation: the smaller of 16 and decimal digits plus one, or 16 when decimal digits is zero.

<a id="u-f50fdbcd05bb"></a>
### `FMT_BEGIN_EXPORT.size_padding.native_formatter`

`template <typename T, typename Char, type TYPE> template <typename FormatContext> FMT…` · [include/fmt/format.h:L4099-L4111][f1]

This formatter writes a value with its stored specs.

If the specs are not dynamic it writes directly; otherwise it copies the specs, resolves dynamic width and precision, and writes with the resolved specs and locale.

<a id="u-e50e61ba7bee"></a>
### `FMT_BEGIN_EXPORT.size_padding.parse_align`

`template <typename Char> FMT_CONSTEXPR auto parse_align(const Char* begin, const Char…` · [include/fmt/format.h:L2575-L2608][f1]

This parser reads an optional fill character and alignment marker.

It recognizes left, right, and center; a fill before the marker is stored unless it is a closing brace, while an opening brace reports an error. It returns the position after the parsed alignment.

<a id="u-85d7b25c1135"></a>
### `FMT_BEGIN_EXPORT.size_padding.signbit`

`template <typename T, FMT_ENABLE_IF(is_floating_point<T>::value)> FMT_INLINE FMT_CONS…` · [include/fmt/format.h:L2904-L2915][f1]

This function reports the sign bit.

In constant evaluation for IEC559 doubles it inspects the high bit of the bit pattern; otherwise it calls the standard sign-bit function on a double conversion.

<a id="u-029a024f8165"></a>
### `FMT_BEGIN_EXPORT.size_padding.write.bounded_output_iterator.operator=`

`FMT_CONSTEXPR auto operator=(char c) -> bounded_output_iterator&` · [include/fmt/format.h:L2499-L2505][f1]

This assignment writes a character only while the remaining bound is positive, then decrements the bound.

It always returns the iterator wrapper.

<a id="u-4a047e978d6a"></a>
### `FMT_BEGIN_EXPORT.size_padding.write`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_floating_poi…` · [include/fmt/format.h:L3713-L3783][f1]

write formats a floating-point value with the given specs and locale.

It first tries localized formatting via write_loc; if that handles the value it returns. It determines the sign from signbit and specs.sign, writes non-finite values with write_nonfinite, and handles numeric alignment by emitting the sign before padding. For hexfloat it writes the prefix and calls format_hexfloat. For exp presentation it increments precision (erroring if precision is max int) and sets alt when the original precision was nonzero; for fixed presentation it sets alt only when precision is nonzero; for the default presentation it changes precision 0 to 1. It then calls format_float and writes the resulting decimal with write_float.

<a id="u-fe480160173d"></a>
### `include/fmt/format.h:FMT_BEGIN_EXPORT.size_padding.write (19)`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_integral<T>:…` · [include/fmt/format.h:L2555-L2573][f1]

Writes a C string with format specs and locale.

If the presentation type is pointer, it formats the pointer value via write_ptr with the address bit-cast to uintptr_t and the specs. Otherwise, a null pointer reports the error "string pointer is null"; a non-null pointer is written as a basic_string_view with the same specs and an empty locale.

<a id="u-369dd3e271a1"></a>
### `FMT_BEGIN_EXPORT.size_padding.write_nonfinite`

`template <typename Char, typename OutputIt> FMT_CONSTEXPR20 auto write_nonfinite(Outp…` · [include/fmt/format.h:L2610-L2626][f1]

This function writes nan or inf, upper- or lower-case, with an optional sign.

Zero fill is replaced by space for non-finite values, and the result is right-padded.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
