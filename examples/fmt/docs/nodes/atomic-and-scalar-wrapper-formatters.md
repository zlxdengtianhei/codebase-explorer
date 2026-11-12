# Atomic and Scalar Wrapper Formatters

**Capability.** Formats atomic, bit-reference, bitset, byte, reference_wrapper, and small _BitInt values by delegating to underlying formatters.

Come here for std.h formatter specializations that adapt atomic and scalar wrapper types. They load or cast values and delegate to bool, unsigned, long long, or referenced-type formatters.

Parent: [Standard Library Formatters](standard-library-formatters.md)

## Units (8)

<a id="u-ea826370cbab"></a>
### `std.h-atomic-flag-formatter`

`template <typename Char> struct formatter<std::atomic_flag, Char> : formatter<bool, C…` · [include/fmt/std.h:L752-L754][f1]

Formats std::atomic_flag by calling test() and delegating the resulting bool to the bool formatter.

<a id="u-5618b86d4fdf"></a>
### `std.h-atomic-formatter`

`template <typename T, typename Char> struct formatter<std::atomic<T>, Char, enable_if…` · [include/fmt/std.h:L740-L744][f1]

Formats std::atomic<T> when T is formattable by loading the atomic value and delegating to the T formatter.

<a id="u-b30d09c073a8"></a>
### `std.h-bit-reference-formatter`

`template <typename BitRef, typename Char> struct formatter<BitRef, Char, enable_if_t<…` · [include/fmt/std.h:L715-L719][f1]

Formats bit-reference-like types by delegating to the bool formatter.

Detection normally requires convertible-to-bool, nothrow-assignable-from-bool, and a flip() member, but a libc++ specialization forces the trait true for std::__bit_const_reference<C>, so this formatter can be enabled without those conditions.

<a id="u-577c5905932d"></a>
### `std.h-bitset-formatter`

`template <size_t N, typename Char> struct formatter<std::bitset<N>, Char> : nested_fo…` · [include/fmt/std.h:L353-L357][f1]

Formats a std::bitset by converting it to a string of the requested character type, wrapping that string in a view, and delegating to the inherited nested formatter for width/alignment handling.

<a id="u-8d9310ce4bd2"></a>
### `std.h-byte-formatter`

`template <typename Char> struct formatter<std::byte, Char> : formatter<unsigned, Char>` · [include/fmt/std.h:L727-L729][f1]

Formats std::byte by casting to unsigned char and delegating to the unsigned formatter.

<a id="u-6fbf3199c82a"></a>
### `std.h-reference-wrapper-formatter`

`template <typename T, typename Char> struct formatter<std::reference_wrapper<T>, Char…` · [include/fmt/std.h:L829-L837][f1]

Formats std::reference_wrapper by delegating to the formatter for the referenced type.

It is enabled only when the referenced type is formattable and has no format_as or format_as member, avoiding implicit conversion through reference_wrapper.

<a id="u-27490a69354a"></a>
### `std.h-signed-bitint-formatter`

`template <int N, typename Char> struct formatter<detail::bitint<N>, Char> : formatter…` · [include/fmt/std.h:L688-L691][f1]

Formats signed _BitInt values up to 64 bits by casting to long long and delegating to the long long formatter.

A static assertion rejects widths above 64.

<a id="u-d36ca143e928"></a>
### `std.h-unsigned-bitint-formatter`

`template <int N, typename Char> struct formatter<detail::ubitint<N>, Char> : formatte…` · [include/fmt/std.h:L700-L703][f1]

Formats unsigned _BitInt values up to 64 bits by casting to unsigned long long and delegating to that formatter.

A static assertion rejects widths above 64.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
