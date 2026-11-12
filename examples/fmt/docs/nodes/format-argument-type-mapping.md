# Format Argument Type Mapping

**Capability.** Defines string views, type-erased arguments, type mapping traits, argument encoding, and core format-to and print entry points.

This module covers core argument representation and type mapping. Readers find string views, type-erased values, type traits, and top-level formatting entry points.

**Depends on.**

- [Format Spec Parser](format-spec-parser.md) · graph-confirmed · 2 edge(s)
- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-only · 4 edge(s)
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 2 edge(s)

Parent: [Argument and Spec Pipeline](argument-and-spec-pipeline.md)

## Units (28)

<a id="u-788ca97b3a11"></a>
### `core.h-argument-descriptor-encoding`

`template <typename Context, typename First, typename... T> constexpr auto encode_type…` · [include/fmt/core.h:L2311-L2315][f1]

encode_types packs each argument's stored type constant into four-bit fields, recursively shifting later fields left; the empty pack is zero.

make_descriptor returns that packed encoding when the argument count is within the packed limit, otherwise it sets the unpacked bit and stores the count.

<a id="u-2f564a36213c"></a>
### `core.h-basic-string-view-core`

`class basic_string_view { private: const Char* data_; size_t size_; public: using val…` · [include/fmt/core.h:L512-L542][f1]

Non-owning pointer-and-size string view with constructors, prefix tests, and lexicographic comparison.

Default is null/zero; pointer-plus-count stores both; C-string constructor computes length with strlen for char when not constant-evaluated, otherwise by scanning; the std-string-like constructor requires the same value_type and stores data()/size(). starts_with(view) is true when this size is at least the other and the prefix compares equal; starts_with(Char) checks a nonempty first character; starts_with(const Char*) delegates to the view overload. compare compares the common prefix via detail::compare, returns that nonzero result directly, and otherwise orders by length (0 equal, -1 shorter, 1 longer).

<a id="u-a6069a7ce5dc"></a>
### `core.h-copy-overloads`

`template <typename T, typename InputIt, typename OutputIt, FMT_ENABLE_IF(is_back_inse…` · [include/fmt/core.h:L1907-L1913][f1]

Selects an optimized copy path for an output iterator.

For a back-insert iterator whose container has append, it appends the whole range and returns the iterator. If append is unavailable but insert is available, it inserts at the container end and returns the iterator. Otherwise it assigns each element through the output iterator, casting to the target value type, and returns the advanced iterator.

<a id="u-54c8c748c8b7"></a>
### `core.h-format-as-traits`

`template <typename T, typename Enable = std::true_type> struct use_format_as : std::f…` · [include/fmt/core.h:L1139-L1140][f1]

use_format_as and use_format_as_member are true when the respective format_as result is an arithmetic type.

They do not exclude view types; the comment about avoiding unsafe view mapping is not enforced by the trait.

<a id="u-35d1e6c061f5"></a>
### `core.h-format-to-fixed-array`

`template <size_t N> FMT_DEPRECATED auto vformat_to(char (&out)[N], string_view fmt, f…` · [include/fmt/core.h:L2874-L2879][f1]

vformat_to formats into a fixed char array by calling vformat_to_n with the array size and returns the output pointer plus whether the total size exceeded the array.

format_to builds the argument store and performs the same fixed-array call.

<a id="u-7d766cb0c814"></a>
### `core.h-native-formatter-parse-and-debug`

`FMT_CONSTEXPR auto parse(parse_context<Char>& ctx) -> const Char*` · [include/fmt/core.h:L2374-L2379][f1]

parse returns immediately at end of input or at '}', otherwise parses format specs for the native type and, for character type, runs the character-spec check.

set_debug_format is enabled for string, C-string, and character types; it sets the presentation type to debug when true and to none when false.

<a id="u-835534177dac"></a>
### `core.h-print-and-println`

`template <typename... T> FMT_INLINE void print(format_string<T...> fmt, T&&... args)` · [include/fmt/core.h:L2910-L2917][f1]

print builds the argument store and writes to stdout or a FILE.

If UTF-8 is not enabled it uses the mojibake path; otherwise it chooses buffered printing when any argument type is locking, and plain printing otherwise. println(FILE*) builds the store and, when UTF-8 is enabled, calls vprintln; otherwise it uses the mojibake path with newline enabled. println(stdout) delegates to println(FILE*, ...).

<a id="u-4777654399bb"></a>
### `core.h-to-string-view-overloads`

`template <typename Char, FMT_ENABLE_IF(is_code_unit<Char>::value)> constexpr auto to_…` · [include/fmt/core.h:L945-L948][f1]

Converts supported inputs to basic_string_view without taking ownership.

The code-unit pointer overload is enabled for code-unit character types and returns a view of that pointer. The std-string-like overload is enabled by the string-like trait and returns a view over the input's value_type using its data and size. Explicitly convertible types are not accepted by these overloads.

<a id="u-94b126e791fd"></a>
### `core.h-value-construction-and-custom-formatting`

`template <typename T, FMT_ENABLE_IF(is_code_unit<T>::value)> constexpr FMT_INLINE val…` · [include/fmt/core.h:L2187-L2192][f1]

Type-erased argument value that stores one active union member selected by the constructor.

The code-unit constructor stores char_value and rejects mixing character types. char_type* and const char_type* constructors store the string pointer and, in constant evaluation, leave the size zero. The non-pointer string-like constructor requires the same character type, converts through to_string_view, and stores data and size. The named-argument constructor stores the metadata pointer and count. The custom-formatter constructor stores a pointer to the object and a format callback; in constant evaluation the pointer is null unless the address is directly obtainable. If no formatter exists, the custom-tag constructor instantiates an undefined type to force a compile error. format_custom constructs the formatter, advances the parse context through parse, then calls format on the object, using const T when const formatting is available, and advances the output context.

<a id="u-e12b7425b42e"></a>
### `check_for_duplicate`

`template <typename Char> FMT_CONSTEXPR void check_for_duplicate(named_arg_info<Char>*…` · [include/fmt/core.h:L1092-L1099][f1]

Scans previously recorded named arguments and reports a duplicate when a stored name compares equal to the new name.

The comparison uses basic_string_view equality, so it compares contents, not pointer identity.

<a id="u-98ec1cc37bde"></a>
### `code_point_length`

`template <typename Char> FMT_CONSTEXPR auto code_point_length(const Char* begin) -> int` · [include/fmt/core.h:L1298-L1303][f1]

Returns the number of code units in a code point, or 1 on error.

For multi-byte character types it always returns 1. For one-byte character types it indexes a lookup table with the top bits of the first byte to produce 1 through 4.

<a id="u-d9aea2180a2a"></a>
### `is_name_start`

`template <typename Char> constexpr auto is_name_start(Char c) -> bool` · [include/fmt/core.h:L1339-L1341][f1]

Returns true for an ASCII letter or underscore, false otherwise.

<a id="u-e681cd240832"></a>
### `parse_nonnegative_int`

`template <typename Char> FMT_CONSTEXPR auto parse_nonnegative_int(const Char*& begin,…` · [include/fmt/core.h:L1307-L1328][f1]

Parses a nonempty digit range as a nonnegative int and advances the begin pointer past the digits.

It asserts the range starts with a digit. It accumulates in unsigned; if the digit count is within the safe decimal-digit count it returns the value. For one extra digit it returns the value only when the recomputed value is at most INT_MAX; otherwise it returns the supplied error value. It is noexcept.

<a id="u-cffe945f278b"></a>
### `to_ascii`

`template <typename Char, FMT_ENABLE_IF(std::is_integral<Char>::value)> constexpr auto…` · [include/fmt/core.h:L1292-L1295][f1]

Converts an integral character to ASCII.

Values up to 0xff become char(c); larger values return the NUL character.

<a id="u-72b7cc13fad5"></a>
### `include/fmt/core.h:FMT_END_EXPORT (4)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L966-L972][f1]

Deduces a string-like type's character type by applying detail::to_string_view and taking the result's value_type.

Substitution fails when no to_string_view overload exists, so the alias is SFINAE-friendly and has no runtime behavior.

<a id="u-0bd865e37da3"></a>
### `include/fmt/core.h:FMT_END_EXPORT (7)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1004-L1019][f1]

Macro-generated specializations map built-in C++ types to detail::type enum values, while the primary template defaults to custom_type.

The mappings cover integer, bool, character, floating-point, C-string, string-view, and pointer types and drive later type dispatch and formatter selection.

<a id="u-e990227ef461"></a>
### `include/fmt/core.h:FMT_END_EXPORT (23)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1128-L1138][f1]

Defines aliases that normalize long and unsigned long to int/unsigned or long long/ullong depending on long_short, which requires equal size with int and enabled builtin types.

Also defines format_as_result and format_as_member_result as cv/ref-stripped return types of format_as and formatter::format_as.

<a id="u-f6cac92895e6"></a>
### `include/fmt/core.h:FMT_END_EXPORT (28)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1153-L1167][f1]

use_formatter is true for class, enum, union, or array types that are not string-like, named arguments, or format_as-mapped.

has_formatter_impl SFINAE-detects formatter<T, Char>().format(*p, *ctx), and has_formatter reports that detection result, including const-qualified checks.

<a id="u-b0ef003ad178"></a>
### `include/fmt/core.h:FMT_END_EXPORT (30)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1223-L1239][f1]

mapped_t applies type_mapper<Char>::map to T; mapped_type_constant converts the mapped type through type_constant; stored_type_constant yields custom_type when builtin types are disabled except for int_type.

Unsupported mappings become void, keeping the aliases SFINAE-friendly.

<a id="u-e41019f00c2b"></a>
### `include/fmt/core.h:FMT_END_EXPORT (39)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L939-L944][f1]

Marks char8_t as a code unit only when UTF-8 is enabled.

The specialization derives from bool_constant<is_utf8_enabled>; when char8_t is unavailable the primary false trait applies.

<a id="u-863109659f69"></a>
### `basic_string_view`

`template < typename S, FMT_ENABLE_IF(detail::is_std_string_like<S>::value&& // std::i…` · [include/fmt/core.h:L549-L554][f1]

The template constructor accepts std-string-like types only when S::value_type equals Char, then initializes from data() and size().

<a id="u-ae5690cbc06a"></a>
### `include/fmt/core.h:compare`

`template <typename Char> FMT_CONSTEXPR auto compare(const Char* s1, const Char* s2, s…` · [include/fmt/core.h:L463-L471][f1]

Compares two character ranges.

In constant evaluation or when Char is wider than one byte, it returns -1, 0, or 1 based on lexicographic comparison. Otherwise it calls memcmp, whose return value is only specified as negative, zero, or positive.

<a id="u-5c575518b771"></a>
### `to_unsigned`

`template <typename Int> FMT_CONSTEXPR auto to_unsigned(Int value) -> make_unsigned_t<…` · [include/fmt/core.h:L428-L432][f1]

Converts a nonnegative integer to its unsigned counterpart.

It asserts that the input is unsigned or nonnegative; on assertion failure it reports through the assertion mechanism. The result is a static_cast to make_unsigned_t<Int>.

<a id="u-4937a88583fa"></a>
### `include/fmt/core.h:formatted_size`

`template <typename... T> FMT_NODISCARD FMT_INLINE auto formatted_size(format_string<T…` · [include/fmt/core.h:L2889-L2895][f1]

Returns the number of chars the formatted output would contain.

It formats into a counting_buffer and returns its count.

<a id="u-7f35e3063da6"></a>
### `include/fmt/core.h:is_locking`

`template <typename T1, typename T2, typename... Tail> constexpr auto is_locking() -> …` · [include/fmt/core.h:L2405-L2408][f1]

Recursively reports whether any type in the pack has a locking trait.

The single-type overload checks locking<remove_cvref_t<T>>; the variadic overload ORs the first check with the rest.

<a id="u-c05bc7c2d101"></a>
### `format_to_result.operator char*`

`FMT_CONSTEXPR operator char*() const` · [include/fmt/core.h:L2867-L2871][f1]

Converts a format_to_result to char*.

If the result was truncated it reports output is truncated; otherwise it returns the output pointer.

<a id="u-4f3ccb795504"></a>
### `include/fmt/core.h:locale_ref.locale_ref`

`template <typename Locale, FMT_ENABLE_IF(sizeof(Locale::collate) != 0)> locale_ref(co…` · [include/fmt/core.h:L912-L916][f1]

Type-erased locale reference constructor.

It is enabled when Locale has a collate member, stores the address of the locale without owning it, and checks that isalpha('x', loc) is found via ADL by evaluating its sizeof through ignore_unused.

<a id="u-8e9cc0ceb8aa"></a>
### `type_mapper`

`template <typename Char> struct type_mapper` · [include/fmt/core.h:L1174-L1223][f1]

Maps formatting argument types to natively supported types or user-defined types with formatters.

long and unsigned long map to int/unsigned or long long/ullong only when long_short is true, which requires equal size with int and enabled builtin types; otherwise they map to long long/ullong. Unsupported mappings return void.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
