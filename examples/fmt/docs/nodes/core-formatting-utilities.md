# Core formatting utilities

**Capability.** Provides the header's shared low-level helpers: allocators, compile-time strings, named-argument factories, bit/UTF-8 primitives, and string-like formatter specializations.

Readers needing the building blocks behind format.h—fixed_string, udl_arg, bit_cast, UTF-8 decoding, display width, and escape checks—should start here. It gathers the small detail utilities that the rest of the library instantiates.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (29)

<a id="u-890a07e43a07"></a>
### `format.h-a-literal`

`template <detail::fixed_string S> constexpr auto operator""_a()` · [include/fmt/format.h:L4460-L4463][f1]

operator""_a creates a named-argument factory: with nontype template args it returns a udl_arg bound to a compile-time fixed_string (enabling compile-time name checks); otherwise it returns a udl_arg carrying the runtime string pointer.

<a id="u-f351109141dd"></a>
### `format.h-allocator`

`FMT_CONSTEXPR20 auto allocate(size_t n) -> T*` · [include/fmt/format.h:L907-L914][f1]

A minimal malloc/free-based allocator that avoids the C++ runtime: allocate asserts n does not overflow size_t/sizeof(T) and delegates to detail::allocate (new T[n] under constant evaluation); deallocate frees (delete[] under constant evaluation).

All instances compare equal, so operator== is true and operator!= is false.

<a id="u-d34c87233a74"></a>
### `format.h-base-iterator`

`template <typename OutputIt, FMT_ENABLE_IF(is_back_insert_iterator<OutputIt>::value&&…` · [include/fmt/format.h:L517-L524][f1]

Converts a reserve pointer back to the output iterator: for back-insert iterators into contiguous containers the iterator itself is returned; otherwise the passed iterator is returned unchanged.

<a id="u-3c4b15767bce"></a>
### `format.h-convert-float-and-select`

`template <typename T> constexpr auto convert_float(T value) -> convert_float_result<T>` · [include/fmt/format.h:L1905-L1908][f1]

convert_float widens float (and same-size types) to double, leaving other types unchanged, to reduce formatter instantiations.

select is a compile-time branch returning the true or false value per the bool template parameter.

<a id="u-33feb2f24d21"></a>
### `format.h-copy-helpers`

`template <typename T, typename V, typename OutputIt> FMT_CONSTEXPR auto copy(basic_st…` · [include/fmt/format.h:L564-L567][f1]

copy forwards a string_view to the two-iterator copy from core.h; copy_noinline is a deliberately non-inline wrapper around the same copy to control code bloat and instantiation sites.

<a id="u-f49227c90b86"></a>
### `format.h-escape-detection`

`inline auto needs_escape(uint32_t cp) -> bool` · [include/fmt/format.h:L1988-L1992][f1]

needs_escape is true for control chars, 0x7f, quote and backslash, and (unless optimizing for size) for code points failing the out-of-line is_printable check.

find_escape scans for the first escapable unit: the generic version skips UTF-8 continuation bytes for narrow chars; the char overload, when UTF-8 is in use, walks code points via for_each_codepoint and reports the first code point needing escape with its byte range, or end/nullptr when none.

<a id="u-78378e411c1b"></a>
### `format.h-fp-normalize-and-multiply`

`template <int SHIFT = 0, typename F> FMT_CONSTEXPR auto normalize(basic_fp<F> value) …` · [include/fmt/format.h:L1862-L1877][f1]

normalize shifts a value (pre-multiplied by 2^SHIFT) left until the implicit bit position is set, decrementing e, then applies a fixed offset so the significand occupies the full F width.

multiply computes lhs*rhs/2^64 rounded half-up: native 128-bit product with a +1 on the high half's MSB, otherwise 32-bit-limb arithmetic with rounding via a biased mid sum. operator* multiplies two fps, adding exponents plus 64.

<a id="u-9c489cdb69df"></a>
### `format.h-locale-separators`

`template <typename Char> inline auto thousands_sep(locale_ref loc) -> thousands_sep_r…` · [include/fmt/format.h:L1369-L1373][f1]

thousands_sep and decimal_point fetch locale-specific separators: the char versions delegate to thousands_sep_impl<char>/decimal_point_impl<char> (defined in format-inl.h); the wchar_t specializations call the wchar_t implementations directly.

Results are returned by value; the impl functions are extern-template instantiated when not header-only.

<a id="u-7110ef856731"></a>
### `format.h-maybe-set-debug-format`

`template <typename Formatter> FMT_CONSTEXPR auto maybe_set_debug_format(Formatter& f,…` · [include/fmt/format.h:L934-L938][f1]

Calls f.set_debug_format(set) when the formatter supports it; the ellipsis overload is a no-op fallback selected otherwise, so callers can unconditionally request debug formatting.

<a id="u-7e6e7ff858b4"></a>
### `format.h-msvc-clz-wrappers`

`inline auto clz(uint32_t x) -> int` · [include/fmt/format.h:L209-L214][f1]

Provide count-leading-zeros for MSVC via _BitScanReverse(_64); the 64-bit version scans the high 32 bits first and returns 63^(r+32) when found, otherwise scans low 32 bits.

Each asserts nonzero input, since the intrinsics are undefined for zero.

<a id="u-0ab8aae7931b"></a>
### `format.h-named-arg-plumbing`

`static_named_arg(const T& v) : value(v)` · [include/fmt/format.h:L4016-L4016][f1]

static_named_arg wraps a value with a compile-time fixed_string name and is tagged as both named and static-named; udl_arg's operator= produces a static_named_arg with that name when nontype template args are supported, otherwise a runtime named_arg carrying the string pointer.

<a id="u-d030596f3e53"></a>
### `format.h-nested-formatter`

`template <typename T> struct nested_view` · [include/fmt/format.h:L4400-L4402][f1]

Formats a value with an outer nested spec (alignment/width) around an inner formatter.

parse runs nested_format_specs::parse for the outer part then the inner formatter's parse. write delegates to nested_format_specs::write, which either writes the body directly (zero width) or buffers it and re-writes with padding. write_arg formats either a nested_view through the inner formatter or a plain value through detail::write; write_body advances the context per argument and returns the final iterator. nested wraps a value in a nested_view for the inner-format path.

<a id="u-00797a49ec33"></a>
### `format.h-ptr-underlying-format-as-helpers`

`template <typename T> auto ptr(T p) -> const void*` · [include/fmt/format.h:L4305-L4308][f1]

ptr bit_casts a pointer to const void* (static_asserting the argument is a pointer); underlying casts an enum to its underlying type; enums::format_as does the same cast so enums format as integers by default.

<a id="u-b7f3cc166648"></a>
### `format.h-reserve`

`__attribute__((no_sanitize("undefined"))) #endif FMT_CONSTEXPR20 inline auto reserve(…` · [include/fmt/format.h:L471-L479][f1]

Attempts to make room for n more elements.

For back-insert iterators into contiguous containers it resizes the container and returns a pointer to the reserved region; for basic_appender it calls try_reserve on the buffer and returns the iterator unchanged; for any other iterator it is an identity no-op returning the iterator.

<a id="u-52fe81fe0fd6"></a>
### `format.h-string-float128-format-as-formatters`

`class formatter<std::basic_string<Char, Traits, Allocator>, Char> : public formatter<…` · [include/fmt/format.h:L4278-L4280][f1]

String-like formatter specializations: char arrays and std::basic_string inherit the basic_string_view formatter; float128 uses the native float formatter; types with a format_as result inherit the target's formatter and format by forwarding format_as(value) as an lvalue.

<a id="u-724705eed369"></a>
### `format.h-to-pointer`

`template <typename T, typename OutputIt> constexpr auto to_pointer(OutputIt, size_t) …` · [include/fmt/format.h:L498-L501][f1]

Tries to obtain a raw pointer to n reserved slots.

The generic overload returns nullptr; the pointer overload advances the pointer and returns the old position; the appender overload try_reserves, and returns a pointer into the buffer data only if capacity suffices (resizing by n), otherwise nullptr, letting callers fall back to iterator writes.

<a id="u-37727571a621"></a>
### `include/fmt/format.h:basic_memory_buffer (5)`

`class basic_memory_buffer : public detail::buffer<T>` · [include/fmt/format.h:L1058-L1066][f1]

Move-constructs a basic_memory_buffer by delegating to the private move routine, which transfers the allocator when it propagates, copies inline storage when the source used its inline array, and otherwise adopts the heap block while resetting the source to its empty inline store; the constructor is noexcept because move never allocates.

<a id="u-7144a4987f74"></a>
### `include/fmt/format.h:basic_string_view`

`FMT_EXPORT template <typename Char> constexpr auto compile_string_to_view(basic_strin…` · [include/fmt/format.h:L1179-L1183][f1]

Converts a compile-time char array to basic_string_view, dropping the trailing NUL when the last element is one (raw arrays without a terminator keep all N characters); the string_view overload is the identity.

<a id="u-c01148810f53"></a>
### `include/fmt/format.h:bit_cast (2)`

`template <typename To, typename From, FMT_ENABLE_IF(sizeof(To) == sizeof(From))> FMT_…` · [include/fmt/format.h:L261-L270][f1]

Implements std::bit_cast for same-size types: uses std::bit_cast under constant evaluation when available, otherwise memcpy from the source into a value-initialized To.

Only participates when sizeof(To)==sizeof(From).

<a id="u-86decb0e5906"></a>
### `display_width_of`

`FMT_CONSTEXPR inline auto display_width_of(uint32_t cp) noexcept -> size_t` · [include/fmt/format.h:L836-L850][f1]

Returns the terminal display width of a code point: 1 for anything below 0x1100, otherwise a binary search over the sorted wide_cp_data ranges returns 2 for East-Asian wide/fullwidth code points and 1 otherwise.

<a id="u-13f1ce13458e"></a>
### `include/fmt/format.h:formatted_size`

`template <typename... T> FMT_NODISCARD FMT_INLINE auto formatted_size(locale_ref loc,…` · [include/fmt/format.h:L4640-L4647][f1]

formatted_size formats into a counting_buffer and returns the counted byte length.

<a id="u-4c08b8156b39"></a>
### `getsign`

`template <typename Char> constexpr auto getsign(sign s) -> Char` · [include/fmt/format.h:L1241-L1244][f1]

Maps a sign enum to the corresponding character by selecting a byte from a packed ' ', '+', '-' literal shifted by the enum value.

<a id="u-38641960dd2e"></a>
### `prefix_append`

`FMT_CONSTEXPR inline void prefix_append(unsigned& prefix, unsigned value)` · [include/fmt/format.h:L2191-L2194][f1]

Accumulates a prefix (sign/base marker) into a packed unsigned: the first value occupies the low byte, later values shift up 8, and the top byte counts the prefix length (1 or 2 depending on whether the value fits a byte).

<a id="u-8b6a03b334a0"></a>
### `to_utf8_3bytes`

`inline void to_utf8_3bytes(buffer<char>& buf, uint32_t cp)` · [include/fmt/format.h:L1556-L1560][f1]

Appends a code point as three UTF-8 bytes (0xe0-prefixed) to the buffer; used by the wtf error policy to emit lone surrogates.

<a id="u-38368cc450c1"></a>
### `umul128`

`FMT_INLINE auto umul128(uint64_t x, uint64_t y) noexcept -> uint128` · [include/fmt/format.h:L1635-L1661][f1]

Computes the full 128-bit product of two 64-bit values: native __int128 when available, MSVC _umul128 on AMD64, otherwise a 32-bit-limb schoolbook multiplication assembling high and low halves.

<a id="u-0d35ef34dca4"></a>
### `utf8_decode`

`FMT_CONSTEXPR inline auto utf8_decode(const char* s, uint32_t* c, int* e) -> const char*` · [include/fmt/format.h:L592-L627][f1]

Branchless UTF-8 decoder (Wellons): reads four bytes unconditionally, so the buffer must have at least three zero bytes of padding after the stream.

It derives the sequence length from the first byte's high bits, assembles the code point by masking and shifting, and accumulates error flags (non-canonical encoding, surrogate half, out of range, bad continuation bytes) into *e. Returns a pointer to the next character; on error the pointer is a guess but always advances at least one byte.

<a id="u-369dd3e271a1"></a>
### `FMT_BEGIN_EXPORT.size_padding.write_nonfinite`

`template <typename Char, typename OutputIt> FMT_CONSTEXPR20 auto write_nonfinite(Outp…` · [include/fmt/format.h:L2610-L2626][f1]

Writes nan/inf: chooses "nan"/"NAN" or "inf"/"INF" per the upper flag, replaces a '0' fill with space (zero padding is meaningless for non-finite values), and right-pads writing the optional sign then the three letters.

<a id="u-2b9198660ba7"></a>
### `fixed_string.fixed_string`

`FMT_CONSTEXPR fixed_string(const Char (&s)[N])` · [include/fmt/format.h:L1164-L1167][f1]

Constructs a fixed_string by copying all N characters of the supplied character array into the zero-initialized member buffer via detail::copy, so the stored data is a fixed-size, compile-time string usable as a non-type template argument.

<a id="u-aa184826cd57"></a>
### `string_literal.basic_string_view`

`constexpr operator basic_string_view<Char>() const` · [include/fmt/format.h:L251-L253][f1]

Holds a compile-time char array of the packed parameter pack and converts to basic_string_view over it; pre-C++17 the static value array is defined out of line.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
