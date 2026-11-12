# Standard Type Formatters and Traits

**Capability.** Provides formatters and compile-time traits for standard-library types such as exceptions, paths, variants, smart pointers, and demangled names.

Consult this module for std.h formatter specializations and supporting traits for standard types. It includes exception, path, and variant formatting plus demangling helpers and compatibility traits for bit references, bit integers, thread ids, and complex.

Parent: [Standard Library Formatters](standard-library-formatters.md)

## Units (17)

<a id="u-bfe449534f58"></a>
### `std.h-exception-formatter`

`template <typename T> struct formatter< T, char, typename std::enable_if<std::is_base…` · [include/fmt/std.h:L590-L600][f1]

Formats std::exception-derived objects with optional type name, width/alignment, and nested exception chain.

Parsing returns early on empty input or '}', parses alignment and width, and enables type-name output on 't' only when RTTI is available. Formatting writes directly when no width is requested; otherwise it buffers the message and applies padding. The write path optionally prefixes the demangled dynamic type and, when RTTI and exceptions are enabled, recursively formats a nested exception after ": ", writing "unknown exception" for non-std::exception nested throws.

<a id="u-533817087557"></a>
### `std.h-exception-ptr-formatter`

`template <> struct formatter<std::exception_ptr> : formatter<std::exception>` · [include/fmt/std.h:L671-L672][f1]

Formats std::exception_ptr by inheriting the exception formatter.

A null pointer writes "none" with padding. With exceptions enabled, a non-null pointer is rethrown and caught as std::exception to delegate to the base formatter; other catches fall through. Without exceptions, or after a non-std::exception catch, it writes "unknown exception" with padding.

<a id="u-13e836531434"></a>
### `std.h-filesystem-path-formatter`

`template <typename Char> struct formatter<std::filesystem::path, Char>` · [include/fmt/std.h:L302-L310][f1]

Formats filesystem paths with optional debug escaping and optional generic path conversion.

Parsing returns immediately on empty input, parses alignment, parses width when the next character is 1-9 or '{', enables debug on '?', and records generic mode on 'g'. Formatting chooses native or generic string based on that flag, resolves dynamic width, then either writes the path string directly or escapes it into a buffer before writing with the parsed specs.

<a id="u-c5aca54d4476"></a>
### `std.h-pointer-accessors`

`template <typename T, typename Deleter> auto ptr(const std::unique_ptr<T, Deleter>& p…` · [include/fmt/std.h:L292-L295][f1]

Return the raw pointer held by a unique_ptr or shared_ptr via get(), without transferring ownership.

<a id="u-70a178516043"></a>
### `std.h-variant-formatter`

`template <typename Variant, typename Char> struct formatter<Variant, Char, std::enabl…` · [include/fmt/std.h:L488-L493][f1]

Formats variant-like types whose alternatives are all formattable.

Parsing is a no-op returning the current position. Formatting writes "variant(", visits the active alternative through escaped-alternative formatting, catches std::bad_variant_access and writes "valueless by exception", then writes ')'. The catch discards the iterator returned by the write call, so for non-appending output iterators the following ')' overwrites the first character of that message.

<a id="u-b25322466c3e"></a>
### `is_variant_formattable`

`class is_variant_formattable` · [include/fmt/std.h:L157-L165][f1]

Compile-time trait that checks whether every alternative of a std::variant is formattable with the given character type, using a conjunction over the variant's index sequence.

It exposes only a boolean value and has no runtime behavior.

<a id="u-47eb43378ce8"></a>
### `get_path_string`

`template <typename Char, typename PathChar> auto get_path_string(const std::filesyste…` · [include/fmt/std.h:L104-L113][f1]

Returns a filesystem path as a string in the requested character type.

When the requested type is char and the native path type is wchar_t, it converts the native wide string to UTF-8 using the wtf error policy; otherwise it calls the path's string conversion for the requested type.

<a id="u-24dc39a7a34c"></a>
### `normalize_libcxx_inline_namespaces`

`inline auto normalize_libcxx_inline_namespaces(string_view demangled_name_view, char*…` · [include/fmt/std.h:L170-L197][f1]

If a demangled name starts with "std::", compacts the buffer in place by removing inline namespace components that begin with "__" and end at "::"; otherwise returns the input view unchanged.

It assumes the buffer is NUL-terminated and mutates the buffer when normalization applies.

<a id="u-7b16b420448d"></a>
### `normalize_msvc_abi_name`

`class OutputIt> auto normalize_msvc_abi_name(string_view abi_name_view, OutputIt out)…` · [include/fmt/std.h:L199-L221][f1]

Copies a demangled ABI name to an output iterator while skipping the substrings "enum ", "class ", "union ", and "struct " and skipping space characters.

It returns the advanced output iterator.

<a id="u-8b3040208410"></a>
### `write_demangled_name`

`template <typename OutputIt> auto write_demangled_name(OutputIt out, const std::type_…` · [include/fmt/std.h:L223-L257][f1]

Writes a demangled type name to an output iterator.

With cxxabi demangling available it calls __cxa_demangle, normalizes libc++ inline namespaces on success, falls back to the raw name on failure, and writes bytes. With MSVC STL update it normalizes the MSVC ABI name. With MSVC plus libc++ it applies both normalizations. Otherwise it writes the raw type_info name.

<a id="u-7dfa11f868a1"></a>
### `write_escaped_alternative`

`template <typename Char, typename OutputIt, typename T, typename FormatContext> FMT_C…` · [include/fmt/std.h:L137-L148][f1]

Writes an escaped representation of a variant or expected alternative.

If the alternative has a to_string_view, it escapes that view; if it is the output character type, it escapes the character; otherwise it constructs the underlying formatter, enables debug formatting, advances the context to the output iterator, and delegates formatting. Returns the resulting output iterator.

<a id="u-df0eb706fe75"></a>
### `write_escaped_path`

`template <typename Char, typename PathChar> void write_escaped_path(basic_memory_buff…` · [include/fmt/std.h:L115-L131][f1]

Appends an escaped filesystem path to a quoted buffer.

Compile-time cases: char output from wchar_t native input escapes into a wide buffer, converts to UTF-8, and asserts conversion validity; matching output/native character types escape the native string directly; other combinations escape the path's string conversion for the output character type. Invalid UTF-16 conversion triggers an assertion.

<a id="u-985f8618a77b"></a>
### `include/fmt/std.h:FMT_BEGIN_NAMESPACE (7)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/std.h:L272-L276][f1]

Guards the libc++ workaround that specializes is_bit_reference_like for std::__bit_const_reference<C> to true when _LIBCPP_VERSION is defined and FMT_IMPORT_STD is not.

**Notes.**

- condition: The specialization is compiled only under _LIBCPP_VERSION without FMT_IMPORT_STD.

**Uncertainties.**

- The symbol is labeled FMT_BEGIN_NAMESPACE, but the visible source region is the preprocessor guard preceding the libc++ specialization; the label likely reflects parser macro handling.

<a id="u-0ef21667216f"></a>
### `include/fmt/std.h:FMT_BEGIN_NAMESPACE (11)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/std.h:L89-L97][f1]

Defines detail::bitint and detail::ubitint as _BitInt aliases when FMT_USE_BITINT is true, otherwise as empty structs; Clang diagnostic pragmas suppress extension warnings around the aliases.

**Notes.**

- condition: FMT_USE_BITINT true selects _BitInt aliases; false selects empty struct fallbacks.

**Uncertainties.**

- The symbol is labeled FMT_BEGIN_NAMESPACE, but the visible source region is the FMT_USE_BITINT conditional block; the label likely reflects parser macro handling.

<a id="u-e93a07e635ae"></a>
### `formatter<std::thread::id, Char>`

`template <typename Char> struct formatter<std::thread::id, Char> : basic_ostream_form…` · [include/fmt/std.h:L366-L367][f1]

Empty formatter specialization for std::thread::id that inherits the ostream formatter, so thread ids are formatted through their ostream operator<<.

<a id="u-20a807f37dbf"></a>
### `is_tuple_like<std::complex<T>>`

`template <typename T> struct is_tuple_like<std::complex<T>> : std::false_type` · [include/fmt/std.h:L764-L765][f1]

Trait specialization marking std::complex<T> as not tuple-like, preventing tuple-style formatting from applying to complex values.

<a id="u-6d9462b5a222"></a>
### `is_variant_like`

`template <typename T> struct is_variant_like` · [include/fmt/std.h:L472-L474][f1]

Trait exposing whether a type is recognized as variant-like by the internal variant-like trait.

It has only a compile-time boolean value.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
