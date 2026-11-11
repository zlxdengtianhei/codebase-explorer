# Standard type formatters

**Capability.** Formatters for standard library types: bitsets, complex, exceptions, variants, source_location, type_info, and path transcoding.

The bulk of std.h: formatters for common std types plus the demangling and path-conversion helpers they rely on. Variant and bitset detection traits and debug/quoted alternative output also live here.

Parent: [Standard library type formatters](standard-library-type-formatters.md)

## Units (19)

<a id="u-b30d09c073a8"></a>
### `std.h-bit-reference-formatter`

`template <typename BitRef, typename Char> struct formatter<BitRef, Char, enable_if_t<…` · [include/fmt/std.h:L715-L719][f1]

Formats bitset/vector<bool> proxy references (detected by the is_bit_reference_like trait: convertible to bool, nothrow-assignable from bool, and having flip()) by delegating to the bool formatter.

<a id="u-577c5905932d"></a>
### `std.h-bitset-formatter`

`template <size_t N, typename Char> struct formatter<std::bitset<N>, Char> : nested_fo…` · [include/fmt/std.h:L353-L357][f1]

Formats a std::bitset by converting it to its character-string representation and delegating to the nested_formatter machinery, so nested width/padding specs apply to the whole digit string.

<a id="u-992ba62e9a81"></a>
### `std.h-complex-formatter`

`template <typename T> struct is_tuple_like<std::complex<T>> : std::false_type` · [include/fmt/std.h:L764-L765][f1]

Formats std::complex<T> in mathematical notation: if the real part is nonzero it prints "(real±imagi)" with a '+' sign forced on the imaginary part; otherwise just "imagi".

Non-finite imaginary parts get a space before the 'i' so the output reads like "inf i". parse delegates to parse_format_specs with the scalar type constant (returning immediately on empty specs); format resolves dynamic width/precision, and when a width is set it formats the number unpadded into a buffer and then applies the outer width/fill/align to the whole string, so padding wraps the entire complex value. The is_tuple_like specialization opts complex out of tuple formatting.

<a id="u-bfe449534f58"></a>
### `std.h-exception-formatter`

`template <typename T> struct formatter< T, char, typename std::enable_if<std::is_base…` · [include/fmt/std.h:L590-L600][f1]

Formats any std::exception-derived type with optional align, width (static or dynamic), and 't' to prefix the demangled type name (only when RTTI is enabled; without RTTI 't' is consumed but the name is omitted).

format takes a fast path writing the message directly when no width is requested; otherwise it buffers the message and applies padding via write_padded, which resolves dynamic width. The private write emits the optional "Type: " prefix, then ex.what(), and—when RTTI and exceptions are both enabled—recursively formats the whole std::nested_exception chain as ": "-separated messages, printing "unknown exception" for a non-std::exception nested cause. parse returns immediately on empty input or '}'.

<a id="u-533817087557"></a>
### `std.h-exception-ptr-formatter`

`template <> struct formatter<std::exception_ptr> : formatter<std::exception>` · [include/fmt/std.h:L671-L672][f1]

Formats a std::exception_ptr by inheriting the std::exception formatter: a null pointer prints "none"; with exceptions enabled it rethrows the pointer and formats a caught std::exception via the base formatter, falling back to "unknown exception" for any other exception type (or when exceptions are disabled).

Padding is applied through the inherited write_padded.

<a id="u-60d3f4c56f3a"></a>
### `std.h-monostate-and-is-variant-like`

`template <typename T> struct is_variant_like` · [include/fmt/std.h:L472-L474][f1]

Formats std::monostate as the literal text "monostate" with no accepted format specs; is_variant_like is a thin public alias exposing the detail-level variant-detection trait.

<a id="u-5329a3e707a6"></a>
### `std.h-ptr-overloads`

`template <typename T, typename Deleter> auto ptr(const std::unique_ptr<T, Deleter>& p…` · [include/fmt/std.h:L292-L295][f1]

Return the raw pointer held by a unique_ptr or shared_ptr as const void*, enabling pointer formatting of smart pointers; null smart pointers yield nullptr.

<a id="u-6fbf3199c82a"></a>
### `std.h-reference-wrapper-formatter`

`template <typename T, typename Char> struct formatter<std::reference_wrapper<T>, Char…` · [include/fmt/std.h:L829-L837][f1]

Formats std::reference_wrapper<T> by unwrapping with get() and delegating to the formatter of the referenced type.

The enable_if guards against types with a format_as conversion (free or member), since reference_wrapper is implicitly convertible to T& and would otherwise hijack those formatters.

<a id="u-2e1b37d98674"></a>
### `std.h-source-location-formatter`

`template <> struct formatter<std::source_location>` · [include/fmt/std.h:L451-L452][f1]

Formats a std::source_location as file:line:column: function, writing each field with the library's write helpers; parse accepts no specs.

<a id="u-08d5ed043373"></a>
### `std.h-type-info-formatter`

`template <> struct formatter<std::type_info>` · [include/fmt/std.h:L576-L578][f1]

Formats a std::type_info by delegating to detail::write_demangled_name, so names are demangled and namespace-normalized per the platform; parse accepts no specs.

Only compiled with RTTI.

<a id="u-70a178516043"></a>
### `std.h-variant-formatter`

`template <typename Variant, typename Char> struct formatter<Variant, Char, std::enabl…` · [include/fmt/std.h:L488-L493][f1]

Formats any variant-like type whose alternatives are all formattable as "variant(" plus the active alternative in debug/quoted alternative form and ')'.

The value is visited via std::visit inside FMT_TRY; if the variant is valueless by exception, the catch writes "valueless by exception" instead. parse accepts no specs.

<a id="u-b25322466c3e"></a>
### `is_variant_formattable`

`class is_variant_formattable` · [include/fmt/std.h:L157-L165][f1]

Compile-time trait that is true iff every alternative type of a variant-like type is formattable with the given Char, checked by expanding an index sequence over variant_alternative_t and conjoining is_formattable.

<a id="u-47eb43378ce8"></a>
### `get_path_string`

`template <typename Char, typename PathChar> auto get_path_string(const std::filesyste…` · [include/fmt/std.h:L104-L113][f1]

Converts a path's native string to the target character type: for char output with a wide native string it transcodes with a WTF-8 error policy (invalid surrogates are preserved, not rejected); otherwise it returns p.string<Char>().

Only compiled when the library has filesystem support.

<a id="u-24dc39a7a34c"></a>
### `normalize_libcxx_inline_namespaces`

`inline auto normalize_libcxx_inline_namespaces(string_view demangled_name_view, char*…` · [include/fmt/std.h:L170-L197][f1]

Rewrites a demangled name in place, stripping libc++ inline namespaces (std::__1::, std::__1::__fs::) and libstdc++'s __cxx11 (including under std::filesystem::) so names read as plain std::*.

Only acts when the name starts with "std::"; it scans for '__' tokens followed by '::' and compacts the string, relying on the buffer being NUL-terminated for the lookahead safety.

<a id="u-7b16b420448d"></a>
### `normalize_msvc_abi_name`

`class OutputIt> auto normalize_msvc_abi_name(string_view abi_name_view, OutputIt out)…` · [include/fmt/std.h:L199-L221][f1]

Copies an MSVC-ABI type name to an output iterator while dropping the 'enum ', 'class ', 'union ', and 'struct ' prefixes MSVC inserts before type names.

It scans positionally, skipping the keyword characters, and copies every other non-space character.

<a id="u-8b3040208410"></a>
### `write_demangled_name`

`template <typename OutputIt> auto write_demangled_name(OutputIt out, const std::type_…` · [include/fmt/std.h:L223-L257][f1]

Writes a type_info's human-readable name.

With cxxabi demangling available it demangles and strips inline namespaces, falling back to the raw mangled name if demangling returns null. On MSVC with an STL update it applies normalize_msvc_abi_name; on MSVC ABI with libc++ it applies both normalizers to a copied string; otherwise it writes ti.name() verbatim. Only compiled when RTTI is enabled.

<a id="u-7dfa11f868a1"></a>
### `write_escaped_alternative`

`template <typename Char, typename OutputIt, typename T, typename FormatContext> FMT_C…` · [include/fmt/std.h:L137-L148][f1]

Writes a value in "alternative" (debug/quoted) form: string-like values are written as escaped strings, a single Char as an escaped character, and anything else is formatted by a default-constructed underlying formatter with debug format enabled via maybe_set_debug_format.

The context's output iterator is advanced before delegating. Only available when expected or variant support is present.

<a id="u-df0eb706fe75"></a>
### `write_escaped_path`

`template <typename Char, typename PathChar> void write_escaped_path(basic_memory_buff…` · [include/fmt/std.h:L115-L131][f1]

Appends an escaped, quoted form of a path to a buffer.

For char output from a wide native string it escapes the wide text first, then converts to UTF-8 and asserts the conversion succeeded (assertion failure on invalid UTF-16). When Char matches the path's value type it escapes the native string directly; otherwise it escapes p.string<Char>().

<a id="u-985f8618a77b"></a>
### `include/fmt/std.h:FMT_BEGIN_NAMESPACE (7)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/std.h:L272-L276][f1]

Primary template of detail::is_bit_reference_like: value is true only when T is convertible to bool, nothrow-assignable from bool, and has a .flip() member (detected via has_flip).

It is the enable_if gate for the generic BitRef formatter; a libc++-specific partial specialization for std::__bit_const_reference<C> forces value true to work around that library returning a proxy reference from bitset::operator[] const.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
