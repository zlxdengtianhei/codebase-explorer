# Core argument and buffer base

**Capability.** Defines core.h foundations: the buffer base class, type mapping and formattability traits, argument type encoding, and format-string parsing entry points.

Readers implementing new formattable types or buffer strategies come here for the buffer abstraction, type_mapper, SFINAE formattability probes, and the replacement-field parser. It also hosts print entry points and compile-time string gating shared by the rest of the library.

**Depends on.**

- [Printf implementation](printf-implementation.md) · graph-only · 3 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 2 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Value writing engine](value-writing-engine.md) · graph-only · 2 edge(s)
- [Float conversion entry points](float-conversion-entry-points.md) · graph-only · 1 edge(s)
- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-only · 1 edge(s)

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (30)

<a id="u-9512f627d6ef"></a>
### `core.h-buffer`

`class buffer` · [include/fmt/core.h:L1759-L1773][f1]

Internal contiguous-memory buffer base class with a data pointer, size, capacity, and a grow function pointer; non-copyable, movable.

set() (protected) installs a new pointer/capacity for subclasses. try_reserve calls grow_ only when the requested capacity exceeds the current one; grow implementations must guarantee space for at least one more element (possibly by flushing). try_resize reserves then clamps size_ to min(count, capacity_), possibly leaving the requested size unmet. push_back reserves one slot then writes. append copies a range in chunks, growing when free capacity is insufficient and re-reading size/capacity after growth, casting each element to T (char-to-T allowed). begin/end/data/size/capacity/clear and both operator[] overloads are thin accessors. The protected constructors initialize size/capacity/grow (the MSVC path also nulls ptr_ to silence a warning).

<a id="u-e6907f36f24c"></a>
### `core.h-counting-buffer`

`class counting_buffer : public buffer<T>` · [include/fmt/core.h:L2065-L2067][f1]

Buffer that discards output while counting code units: it stages in a 256-element array, and grow adds the full buffered size to count_ and clears only when the buffer is exactly full (smaller growth requests are ignored).

count() returns the accumulated total plus the currently buffered size, giving the untruncated formatted length.

<a id="u-b9521186e332"></a>
### `core.h-int128-identity-maps`

`inline auto map(native_int128 x) -> native_int128` · [include/fmt/core.h:L414-L414][f1]

When 128-bit integers are available, map() overloads return the argument unchanged; in the fallback build the enum-class placeholders map to monostate so SFINAE code compiles uniformly.

<a id="u-894032b64395"></a>
### `core.h-is-contiguous`

`template <typename T, typename Enable = void> struct is_contiguous : std::false_type` · [include/fmt/core.h:L501-L502][f1]

Trait true when a type supports data(), size() and operator[]\(size_t), used to select buffer strategies for containers with contiguous storage.

<a id="u-3986ca6aa824"></a>
### `core.h-is-std-string-like`

`template <typename T, typename Enable = void> struct is_std_string_like : std::false_…` · [include/fmt/core.h:L439-L440][f1]

Trait heuristic detecting std::string/string_view-like types without including <string_view>: primary template is false; the specialization is true iff the type has find_first_of(value_type, 0) and its data() converts to const value_type*.

<a id="u-a250b3abd528"></a>
### `core.h-locale-ref`

`class locale_ref` · [include/fmt/core.h:L904-L910][f1]

Type-erased non-owning reference to std::locale stored as const void* to avoid including <locale>.

When FMT_USE_LOCALE is on, the template constructor stores the address and probes that isalpha can be found via ADL; explicit operator bool tests non-null. When locale support is off, the class is empty and operator bool is always false. get<Locale>() is declared but defined elsewhere.

<a id="u-334df48dffdb"></a>
### `core.h-min-max-helpers`

`template <typename T> constexpr auto min_of(T a, T b) -> T` · [include/fmt/core.h:L362-L364][f1]

Constexpr templates returning the smaller (min_of) or larger (max_of) of two values by operator comparison.

<a id="u-680dbfacf2f4"></a>
### `core.h-native-formatter`

`template <typename T, typename Char, type TYPE> struct native_formatter` · [include/fmt/core.h:L2369-L2374][f1]

Base for built-in type formatters: parse() returns immediately on '}' or end, otherwise delegates to parse_format_specs and, for char types, validates via check_char_specs.

set_debug_format toggles the debug ('?') presentation for string/cstring/char types. format() is only declared here; concrete formatting lives in format.h specializations.

<a id="u-cc7a96c7256d"></a>
### `core.h-parse-replacement-field`

`template <typename Char, typename Handler> FMT_CONSTEXPR FMT_INLINE auto parse_replac…` · [include/fmt/core.h:L1594-L1612][f1]

Parses one replacement field starting at '{'.

'}' means an automatic id via handler.on_arg_id(); '{{' emits a literal brace through on_text; ':' implies automatic id then falls through to spec parsing. Otherwise parse_arg_id runs with an id_adapter that forwards on_index/on_name to handler.on_arg_id, after which the field must end with '}' (replacement done) or ':' (specs follow); anything else triggers handler.on_error("missing '}' in format string"). After handler.on_format_specs, the parse must end at '}' or on_error("unknown format specifier") fires. Returns the iterator past the field, or end on error.

<a id="u-6948c3cb4653"></a>
### `core.h-primary-formatter-template`

`template <typename T, typename Char = char, typename Enable = void> struct formatter` · [include/fmt/core.h:L640-L643][f1]

The unspecialized formatter has a deleted default constructor, which makes types without a formatter specialization fail to construct and thus report as unformattable in SFINAE contexts.

<a id="u-7fb3885b177a"></a>
### `core.h-println`

`template <typename... T> FMT_INLINE void println(FILE* f, format_string<T...> fmt, T&…` · [include/fmt/core.h:L2938-L2943][f1]

Print with trailing newline: the FILE* overload uses vprintln when UTF-8 is enabled, otherwise vprint_mojibake with the newline flag; the stdout overload forwards to the FILE* version.

<a id="u-611941d10037"></a>
### `core.h-to-string-view-has-to-string-view`

`template <typename Char, FMT_ENABLE_IF(is_code_unit<Char>::value)> constexpr auto to_…` · [include/fmt/core.h:L945-L948][f1]

Three overloads construct fmt::basic_string_view from a code-unit pointer, a std-string-like type, or an existing view, deducing Char; explicitly-convertible-only types (e.g. FMT_STRING results) are intentionally excluded.

has_to_string_view is the corresponding detection trait using detail:: (non-ADL) lookup.

<a id="u-e3e26b629f82"></a>
### `core.h-type-descriptor-encoding`

`template <typename> constexpr auto encode_types() -> ullong` · [include/fmt/core.h:L2309-L2309][f1]

encode_types packs each argument's stored_type_constant into 4-bit fields of an ullong (recursively, LSB first); make_descriptor returns the packed encoding when the argument count fits max_packed_args (15), otherwise the count OR-ed with the high is_unpacked_bit.

<a id="u-23f6130e268d"></a>
### `check_char_specs`

`FMT_CONSTEXPR inline auto check_char_specs(const format_specs& specs) -> bool` · [include/fmt/core.h:L1662-L1673][f1]

Validates specs for char arguments: returns false (without error) if the presentation type is anything other than none/chr/debug, and reports "invalid format specifier for char" via report_error if numeric alignment, a sign, or '#' is present; returns true for char-like specs.

<a id="u-98ec1cc37bde"></a>
### `code_point_length`

`template <typename Char> FMT_CONSTEXPR auto code_point_length(const Char* begin) -> int` · [include/fmt/core.h:L1298-L1303][f1]

Returns the UTF-8 code point length (1-4) starting at begin using a 64-bit lookup table indexed by the lead byte's top bits; for non-byte Char it always returns 1.

Malformed leads yield a table-derived length, not an error.

<a id="u-bc618b1a2cc0"></a>
### `has_formatter`

`template <typename T, typename Char> constexpr auto has_formatter() -> bool` · [include/fmt/core.h:L1168-L1170][f1]

SFINAE-probes whether formatter<U, Char> is constructible and has a callable format(p, ctx) via has_formatter_impl overload resolution; T may be const-qualified to test const-formattability.

<a id="u-7f42b5d1d97e"></a>
### `include/fmt/core.h:parse_arg_id`

`template <typename Char, typename Handler> FMT_CONSTEXPR auto parse_arg_id(const Char…` · [include/fmt/core.h:L1343-L1369][f1]

Parses an argument id at begin: leading digits form an index (via parse_nonnegative_int, with a bare '0' handled specially), which must be followed by '}' or ':' or else report_error("invalid format string") fires before handler.on_index.

Otherwise, if FMT_OPTIMIZE_SIZE > 1 or the first char is not a name start, it reports the same error; a name consumes name-start chars and digits and calls handler.on_name with the range. Returns the iterator past the id.

<a id="u-50df9b1fecbb"></a>
### `parse_format_string`

`template <typename Char, typename Handler> FMT_CONSTEXPR void parse_format_string(bas…` · [include/fmt/core.h:L1641-L1659][f1]

Walks the whole format string, splitting it into on_text(begin, p) segments and dispatching '{' to parse_replacement_field.

A '}' not followed by a second '}' calls handler.on_error("unmatched '}' in format string") and returns; "}}" emits one brace and continues. A trailing on_text(begin, end) flushes the final segment.

<a id="u-e681cd240832"></a>
### `parse_nonnegative_int`

`template <typename Char> FMT_CONSTEXPR auto parse_nonnegative_int(const Char*& begin,…` · [include/fmt/core.h:L1307-L1328][f1]

Parses [begin, end) as an unsigned decimal integer, assuming the first char is a digit (asserted).

It consumes all digits, then: if the digit count is within the safe bound (about 0.3 * bits per digit) it returns the value; with one extra digit it checks overflow against INT_MAX and returns error_value on overflow or too many digits. begin is advanced past all digits.

<a id="u-cffe945f278b"></a>
### `to_ascii`

`template <typename Char, FMT_ENABLE_IF(std::is_integral<Char>::value)> constexpr auto…` · [include/fmt/core.h:L1292-L1295][f1]

Converts an integral character to char, returning '\0' when the value exceeds 0xff, so wide spec characters can be matched against ASCII spec syntax.

<a id="u-72b7cc13fad5"></a>
### `include/fmt/core.h:FMT_END_EXPORT (4)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L966-L972][f1]

SFINAE specialization marking has_to_string_view true exactly when detail::to_string_view(std::declval<T>()) is well-formed; because detail:: is used, ADL cannot inject matches.

<a id="u-0bd865e37da3"></a>
### `include/fmt/core.h:FMT_END_EXPORT (7)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1004-L1019][f1]

Defines the FMT_TYPE_CONSTANT macro, which expands to a partial specialization of type_constant mapping a fixed C++ type to the given detail::type constant for any character type; the subsequent invocations register int, unsigned, long long, ullong, 128-bit, bool, char, floating-point, string, and pointer types.

<a id="u-e990227ef461"></a>
### `include/fmt/core.h:FMT_END_EXPORT (23)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1128-L1138][f1]

Chooses the storage type for long and unsigned long: long_short is true when sizeof(long)==sizeof(int) and FMT_BUILTIN_TYPES, in which case long_type=int and ulong_type=unsigned; otherwise long long and ullong, minimizing distinct argument types.

<a id="u-e41019f00c2b"></a>
### `include/fmt/core.h:FMT_END_EXPORT (39)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L939-L944][f1]

Specializes the code-unit trait for char8_t: it derives from bool_constant<is_utf8_enabled>, so char8_t counts as a code unit only when the literal encoding is UTF-8; the specialization exists only under __cpp_char8_t.

<a id="u-ae5690cbc06a"></a>
### `include/fmt/core.h:compare`

`template <typename Char> FMT_CONSTEXPR auto compare(const Char* s1, const Char* s2, s…` · [include/fmt/core.h:L463-L471][f1]

Lexicographically compares the first n code units of two ranges, returning -1/0/1.

For single-byte Char outside constant evaluation it delegates to memcmp; otherwise it uses an element-wise constexpr loop.

<a id="u-5c575518b771"></a>
### `to_unsigned`

`template <typename Int> FMT_CONSTEXPR auto to_unsigned(Int value) -> make_unsigned_t<…` · [include/fmt/core.h:L428-L432][f1]

Casts an integer to its unsigned counterpart, asserting (via FMT_ASSERT, which calls assert_fail in debug builds) that a signed input is nonnegative before the static_cast.

<a id="u-b9700dd22dc0"></a>
### `enforce_compile_checks`

`template <bool B> constexpr bool enforce_compile_checks()` · [include/fmt/core.h:L2393-L2400][f1]

Compile-time gate: when FMT_ENFORCE_COMPILE_STRING is defined, static_asserts that consteval is available and the format string is a compile-time string; otherwise trivially returns true.

<a id="u-4937a88583fa"></a>
### `include/fmt/core.h:formatted_size`

`template <typename... T> FMT_NODISCARD FMT_INLINE auto formatted_size(format_string<T…` · [include/fmt/core.h:L2889-L2895][f1]

Computes the exact output length by formatting into a counting_buffer (which discards data while counting) and returning its count; the format string is compile-checked.

<a id="u-8e9cc0ceb8aa"></a>
### `type_mapper`

`template <typename Char> struct type_mapper` · [include/fmt/core.h:L1174-L1223][f1]

Declares the mapping from argument types to the natively supported set: small integers widen to int/unsigned, long collapses to int or long long depending on sizeof, 128-bit types pass through, code units map to Char only when compatible with the context char type (else void), strings become basic_string_view when char types match, pointers become const void* (other/member pointers map to void to disable formatting), format_as results recurse through map, and user types map to T& only when has_formatter holds; named args recurse on their value.

Returning void makes failures SFINAE-friendly.

<a id="u-db3d0d7f1463"></a>
### `formatter<T, Char,
                 enable_if_t<detail::type_constant<T, Char>::value !=
                             detail::type::custom_type>>`

`template <typename T, typename Char> struct formatter<T, Char, enable_if_t<detail::ty…` · [include/fmt/core.h:L2759-L2764][f1]

Formatter specialization for natively supported types: inherits native_formatter parameterized by the type's type_constant, so built-ins get the shared parse/format implementation.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
