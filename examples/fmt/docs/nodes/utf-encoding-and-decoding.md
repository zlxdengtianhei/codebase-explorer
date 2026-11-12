# UTF Encoding and Decoding

**Capability.** Converts and decodes UTF-8, UTF-16, and UTF-32 views, appends UTF-8 code points, and provides branchless decoding.

Use this module for UTF conversion and decoding helpers. The units describe view conversion, code-point iteration, UTF-8 appending, and branchless decoding.

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (5)

<a id="u-21040983a7fe"></a>
### `format.h-utf-conversion`

`explicit to_utf8(basic_string_view<WChar> s, to_utf8_error_policy policy = to_utf8_er…` · [include/fmt/format.h:L1569-L1577][f1]

The constructor requires two- or four-byte input units, converts the view, and throws a runtime error for invalid UTF-16 or UTF-32.

The member converter calls the static converter and appends a NUL on success, returning false on conversion failure. The static converter handles surrogate pairs for two-byte input; invalid surrogates abort, become the replacement character, or are encoded directly according to policy. It emits one- to four-byte UTF-8 and returns false for other invalid code points.

<a id="u-6e4ee9204cf4"></a>
### `for_each_codepoint`

`template <typename F> FMT_CONSTEXPR void for_each_codepoint(string_view s, F f)` · [include/fmt/format.h:L633-L666][f1]

This iterator decodes a UTF-8 string view code point by code point and invokes a callback with the code point and the corresponding byte view.

On decode error it passes an invalid code point and a one-byte view. It processes full four-byte blocks directly and copies the tail into a zero-padded buffer. The callback can stop iteration by returning false.

<a id="u-38641960dd2e"></a>
### `prefix_append`

`FMT_CONSTEXPR inline void prefix_append(unsigned& prefix, unsigned value)` · [include/fmt/format.h:L2191-L2194][f1]

This function appends a byte value to a packed prefix.

It shifts the new value after existing bytes and updates the high-byte length count.

<a id="u-8b6a03b334a0"></a>
### `to_utf8_3bytes`

`inline void to_utf8_3bytes(buffer<char>& buf, uint32_t cp)` · [include/fmt/format.h:L1556-L1560][f1]

This helper appends the three-byte UTF-8 encoding of a code point to a character buffer.

<a id="u-0d35ef34dca4"></a>
### `utf8_decode`

`FMT_CONSTEXPR inline auto utf8_decode(const char* s, uint32_t* c, int* e) -> const char*` · [include/fmt/format.h:L592-L627][f1]

This branchless UTF-8 decoder reads four bytes, writes the decoded code point and an error mask, and returns a pointer to the next character.

It requires at least three bytes of readable padding. Errors mark non-canonical encodings, surrogate halves, out-of-range values, and bad continuation bytes; the returned pointer always advances at least one byte.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
