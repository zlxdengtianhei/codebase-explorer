# Dynamic args, enums, ostream

**Capability.** Dynamic argument stores, enum reflection formatters, the C API value model, and ostream-based formatting integration.

A mixed module of integration features: dynamic argument storage for vformat-style calls, annotated enum formatting, the C API's tagged value model, and operator<<-based formatting via streamed views.

**Depends on.**

- [Core formatting implementation](core-formatting-implementation.md) · graph-confirmed · 1 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)

Parent: [fmt formatting library](fmt-formatting-library.md)

## Units (21)

<a id="u-5630f49ac26b"></a>
### `args.h-dynamic-arg-list-intrusive-node-storage`

`template <typename = void> struct node` · [include/fmt/args.h:L38-L39][f1]

A type-erased singly linked list that owns dynamically allocated argument copies so stored values never relocate.

node is a fake template (MSVC/clang workarounds) holding a unique_ptr to the next node with a virtual destructor; typed_node<T> derives from it and adds a T value, with a special constructor for string views that copies the data into a std::string-like value. push allocates a new typed_node<T> from the argument, links it as the new head by moving the old head into next, and returns a reference to the stored value; the reference stays valid because nodes are only destroyed with the whole list. Allocation failure propagates (new throws); no other failure path exists.

<a id="u-a57da63b3eaf"></a>
### `args.h-dynamic-format-arg-store`

`class dynamic_arg_list { template <typename T> struct typed_node : node<> { T value; …` · [include/fmt/args.h:L66-L78][f1]

A growable, type-erased formatting-argument store that owns copies of arguments that do not fit in a basic_format_arg and can be implicitly converted to basic_format_args<Context> for vformat-style calls.

Storage is threefold: a contiguous vector data_ of basic_format_arg, a vector named_info_ of named-argument metadata, and a dynamic_arg_list dynamic_args_ whose nodes data_ entries point into, which is why dynamic storage must grow without relocation. need_copy<T> decides per type whether to copy: reference wrappers, string views, and types mapping to non-string/cstring/custom categories are stored by reference (after unwrap); everything else (notably strings and custom types) is copied into dynamic_args_ via push<stored_t<T>>, where stored_t converts string-convertible non-wrapper types to std::basic_string. push_back(const T&) branches on need_copy at compile time; push_back(reference_wrapper<T>) stores a reference to the wrapped object and static_asserts that T itself is a copy-required type. Named push_back copies the name into dynamic_args_ as a basic_string (the name is always copied), then either copies the value or stores a reference, and registers it via the named_arg overload of emplace_arg: on the first named argument a placeholder basic_format_arg is inserted at data_[0]; the value is appended; a pop_back guard protects the exception-unsafe window while named_info_ is updated and data_[0] is set to point at the named-info array, then released on success. data() skips the placeholder when named arguments exist; size() subtracts that one placeholder; the conversion operator passes data(), size(), and a has-named-args flag to basic_format_args. clear() empties both vectors and resets dynamic_args_ (freeing all copies); reserve() asserts new_cap >= new_cap_named (FMT_ASSERT) and reserves both vectors. reserve's assertion failure and any allocation exception propagate uncaught.

<a id="u-5d039d4b81f6"></a>
### `args.h-unwrap-reference-wrappers`

`template <typename T> auto unwrap(const T& v) -> const T&` · [include/fmt/args.h:L26-L26][f1]

These two overloads return the underlying value of an argument, transparently unwrapping std::reference_wrapper.

The generic overload returns the value as-is; the reference_wrapper overload static_casts to a const reference to the wrapped object, so formatting sees the referenced value rather than the wrapper.

<a id="u-318e0c378703"></a>
### `enum.h-annotation-detection-traits`

`template <typename A, typename U> consteval auto is_annotated() -> bool` · [include/fmt/enum.h:L66-L68][f2]

These consteval helpers decide, at compile time, whether a type is an enum carrying one of the fmt reflection annotations.

is_annotated checks whether std::meta::annotations_of_with_type reports any annotation of type A on U. use_identifiers returns true only when the decayed type is an enum annotated with as_identifiers_t, false otherwise. use_underlying first static_asserts that a type is not annotated with both as_underlying_t and as_identifiers_t (mutually exclusive, giving a clear diagnostic instead of an ambiguous formatter specialization), then returns true only for enums annotated with as_underlying_t; non-enums return false.

<a id="u-25917c8fb885"></a>
### `enum.h-as-identifiers-formatter`

`template <typename E> struct formatter<E, char, enable_if_t<detail::use_identifiers<E…` · [include/fmt/enum.h:L223-L229][f2]

Formatter specialization for enums annotated with fmt::as_identifiers, delegating format-spec parsing and string output to an embedded formatter<string_view>.

parse forwards to impl_.parse. format looks up the identifier via detail::identifier_of: if nonempty it formats that string view; otherwise it falls back to the underlying value written in decimal into a memory_buffer (unary plus promotes char/bool underlying types so they print as numbers rather than characters or true/false) and formats the resulting string view through impl_.

<a id="u-713fa3c9873f"></a>
### `enum.h-as-underlying-formatter`

`template <typename E, typename Char> struct formatter<E, Char, enable_if_t<detail::us…` · [include/fmt/enum.h:L248-L251][f2]

Formatter specialization for enums annotated with fmt::as_underlying, inheriting from the formatter of the mapped underlying type so the enum accepts that type's format specs.

format_as converts the enum to its underlying value noexcept. format applies format_as and delegates to the base formatter's format, so e.g. {:04x} formats the underlying integer.

<a id="u-4a5b80616a7a"></a>
### `enum.h-identifier-hash-map-and-lookup`

`template <typename E> consteval auto identifier_map_size() -> size_t` · [include/fmt/enum.h:L158-L162][f2]

Fallback lookup structure for sparse enums.

identifier_map_size returns the smallest power of two at least twice the enumerator count, keeping load factor ≤0.5 so a free slot always exists and probing terminates. identifier_slot mixes the uint64 bits (xor-shift 33, multiply by 0xff51afd7ed558ccd, xor-shift 33) and masks to N-1, since enumerator values are usually small. make_identifier_map builds an open-addressed table with linear probing: for each enumerator it probes from its slot, skipping slots held by other values, keeping the first identifier for duplicate values, and inserting into the first empty slot. identifier_of first tries the dense table when identifier_table_size is nonzero: it computes the wrapped distance from the minimum and returns the table entry if in range, else an empty string view (out-of-range values wrap and are rejected by the bounds check). Otherwise it linearly probes the hash map, returning the entry's identifier when the slot is empty (search terminator, empty result) or the value matches; a matching entry's identifier is returned, an empty slot yields an empty string view.

<a id="u-f5816e6f48a6"></a>
### `enum.h-identifier-table-construction`

`template <typename E, typename Char> using underlying_formatter = formatter<mapped_t<…` · [include/fmt/enum.h:L98-L99][f2]

Builds a dense lookup table mapping enumerator values to their identifier strings.

underlying_formatter is an alias for the formatter of the mapped underlying type of E. to_uint64 converts an enum value to uint64_t via its underlying type; negative values wrap, so differences measure distance. min_enumerator returns the smallest enumerator value, or E() for an empty enum. identifier_table_size returns 0 for an empty enum; otherwise it computes the value span (max value minus min) and returns span+1 only if the span is below enumerators.size()*10/7 (≥70% density), else 0 to signal the values are too sparse. make_identifier_table fills a std::array<string_view, N> indexed by value distance from the minimum, keeping the identifier of the first enumerator for duplicate values; identifier_of yields views with static storage duration so no copying is needed. identifier_table is the inline constexpr instance; holes stay as empty string views.

<a id="u-f7f1203ea905"></a>
### `fmt-c.h-c-api-argument-types`

`enum` · [include/fmt/fmt-c.h:L36-L46][f3]

Defines the C API's tagged value model: fmt_type enumerates supported value kinds with explicit discriminants (fmt_int=1, fmt_bool=7, fmt_pointer=14), and fmt_arg is a struct holding that tag plus an anonymous union of the possible value representations.

The union is untagged beyond `type`, so reading the wrong member is undefined; the uint member is documented as reused for pointer/custom data.

<a id="u-c933f0b66203"></a>
### `fmt-c.h-fmt-from-constructors`

`static inline fmt_arg fmt_from_int(long long x)` · [include/fmt/fmt-c.h:L76-L78][f3]

Nine inline C functions that each wrap one scalar into a fmt_arg by setting the matching type tag and union member (e.g. fmt_from_int stores into int_value with fmt_int).

They exist only in C mode and are the building blocks the FMT_MAKE_ARG macro dispatches to; no validation or conversion is performed.

<a id="u-49bd10398c06"></a>
### `ostream.h-file-access-friend-hack`

`class file_access` · [include/fmt/ostream.h:L41-L43][f4]

Exposes a private FILE* member of a std::filebuf-derived buffer to fmt via a friend function, using a per-TU anonymous-namespace tag type to force a unique explicit instantiation.

Only instantiated for std::filebuf's _Myfile when FMT_MSVC_STL_UPDATE is set, so vprint can reach the underlying C file on old MSVC STLs.

<a id="u-cf071be77957"></a>
### `include/fmt/args.h:FMT_BEGIN_NAMESPACE (3)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/args.h:L30-L37][f1]

Unwraps a std::reference_wrapper<T> by static_cast-ing it to a const T&, returning a reference to the wrapped object so callers can treat wrapped and plain values uniformly; the plain overload (identity) is the sibling template.

Pure constexpr conversion with no side effects.

group: [args.h-unwrap-reference-wrappers](dynamic-args-enums-ostream.md#u-5d039d4b81f6)

<a id="u-d4e112260c88"></a>
### `FMT_MAKE_ARG`

`# define FMT_MAKE_ARG(x) \ _Generic((x), \ fmt_signed_char: fmt_from_int, \ unsigned …` · [include/fmt/fmt-c.h:L126-L214][f3]

A C11 _Generic macro mapping an expression's static type to the matching fmt_from_* constructor: all signed integer types to fmt_from_int, unsigned to fmt_from_uint, bool, char, the three floating types, char*/const char* to fmt_from_str, and pointers to fmt_from_ptr.

Any other type selects fmt_unsupported_type, a declared-but-undefined function, so unsupported arguments fail at link time (or via the error-emitting typedef/MSVC checks nearby). signed char is normalized via fmt_signed_char because plain char may be unsigned.

<a id="u-9092171acc89"></a>
### `write_buffer`

`template <typename Char> void write_buffer(std::basic_ostream<Char>& os, buffer<Char>…` · [include/fmt/ostream.h:L55-L68][f4]

Writes the full contents of a buffer to an ostream in chunks bounded by max_size, looping until all bytes are consumed.

max_size must be positive and not exceed the maximum streamsize; each iteration writes min(remaining, max_size) bytes and advances the data pointer. Any ostream write failure propagates as an exception from os.write.

<a id="u-787715de9c22"></a>
### `include/fmt/ostream.h:FMT_BEGIN_NAMESPACE (3)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/ostream.h:L44-L54][f4]

This namespace-scope region defines an anonymous-namespace tag type and a `file_access` template that exposes a private FILE* member of a stream buffer type via a friend function `get_file`, enabling vprint to retrieve the underlying C file from a std::filebuf on MSVC STL.

The explicit instantiation for std::filebuf::_Myfile is guarded by FMT_MSVC_STL_UPDATE; a matching out-of-line declaration of get_file follows so other translation units share the same tag.

<a id="u-206231478489"></a>
### `include/fmt/ostream.h:format`

`template <typename T, typename Context> auto format(const T& value, Context& ctx) con…` · [include/fmt/ostream.h:L82-L92][f4]

Formats an arbitrary value by streaming it through operator<< into a memory buffer backed by a formatbuf streambuf, then reformatting the resulting text as a string_view with the inherited string formatter (so width/align specs apply to the streamed text).

The stream is imbued with the classic locale and set to throw on failbit/badbit, so a failing operator<< propagates an ios exception.

<a id="u-cd7e90da9ca5"></a>
### `include/fmt/ostream.h:print`

`template <typename... T> void print(std::ostream& os, format_string<T...> fmt, T&&...…` · [include/fmt/ostream.h:L154-L161][f4]

Prints to an ostream: when the library uses UTF-8 it delegates to vprint; otherwise it formats into a memory buffer and writes it via detail::write_buffer, bypassing vprint's console fast path.

<a id="u-399d39828066"></a>
### `include/fmt/ostream.h:println`

`template <typename... T> void println(std::ostream& os, format_string<T...> fmt, T&&.…` · [include/fmt/ostream.h:L163-L167][f4]

Prints the formatted result of fmt::format followed by a newline to the given ostream, i.e. formats to a string first and prints it with a "{}\n" wrapper.

<a id="u-3b8c3acaeaef"></a>
### `streamed`

`template <typename T> constexpr auto streamed(const T& value) -> detail::streamed_vie…` · [include/fmt/ostream.h:L115-L118][f4]

Returns a lightweight constexpr view holding a const reference to the value, marking it for ostream-based formatting; the value must outlive the view.

<a id="u-358e426dd2e5"></a>
### `include/fmt/ostream.h:vprint`

`inline void vprint(std::ostream& os, string_view fmt, format_args args)` · [include/fmt/ostream.h:L120-L145][f4]

Formats into a memory buffer, then writes it to the stream, with a Windows fast path: if RTTI is on and the stream's rdbuf is a recognized file buffer (std::filebuf on MSVC, stdio_sync_filebuf or stdio_filebuf on MinGW), it flushes the stream and tries writing directly to the console via write_console, returning early on success.

Otherwise it falls back to chunked write_buffer. The buffer-extraction branches are compile-time platform-gated; on non-Windows builds it always uses write_buffer.

<a id="u-788122168447"></a>
### `include/fmt/ostream.h:format (2)`

`template <typename Context> auto format(detail::streamed_view<T> view, Context& ctx) …` · [include/fmt/ostream.h:L100-L104][f4]

Unwraps a streamed_view and delegates to the shared ostream-based formatter, so fmt::streamed(x) formats x via operator<< with string-format specs applied to the result.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/args.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/enum.h
[f3]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/fmt-c.h
[f4]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ostream.h
