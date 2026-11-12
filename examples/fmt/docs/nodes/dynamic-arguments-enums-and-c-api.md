# Dynamic Arguments, Enums, and C API

**Capability.** Provides dynamic argument storage, enum formatter support, and C-facing argument types and builders.

Use this module for args.h dynamic argument storage, enum.h annotation-based formatters, and fmt-c.h C API declarations. It groups type-erased argument handling, enum lookup/formatting, and C argument construction.

**Depends on.**

- [Core Formatting Internals](core-formatting-internals.md) · graph-confirmed · 1 edge(s)
- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 1 edge(s)

Parent: [fmt Formatting Library](fmt-formatting-library.md)

## Units (17)

<a id="u-88deca88db84"></a>
### `args.h-dynamic-arg-list`

`class dynamic_arg_list` · [include/fmt/args.h:L43-L44][f1]

dynamic_arg_list owns a singly linked list of typed_node<T> through a unique_ptr head_.

push allocates a typed_node<T> from the argument, links it before the current head, and returns a const reference to the stored value. typed_node stores T from a generic Arg or constructs it from a basic_string_view using data and size. The list has no clear method.

<a id="u-87f41d7daf06"></a>
### `args.h-dynamic-format-arg-store-core`

`class dynamic_arg_list { template <typename T> struct typed_node : node<> { T value; …` · [include/fmt/args.h:L66-L78][f1]

dynamic_format_arg_store<Context> is a type-erased argument store convertible to basic_format_args.

need_copy is true unless T is a reference_wrapper, basic_string_view, std_string_view, or maps to cstring/string/custom; stored_t converts string-convertible non-reference types to basic_string, otherwise T. data_ holds contiguous basic_format_arg entries; named_info_ holds named-argument metadata; dynamic_args_ provides stable storage for copied values. data() skips the first entry when named_info_ is nonempty. emplace_arg appends a basic_format_arg; the named overload inserts a placeholder at the front on first named argument, appends the unwrapped value, uses a guard to pop it if later steps throw, records the name and index, and updates the first entry. Conversion to basic_format_args passes data(), size(), and whether named arguments exist.

<a id="u-ece3d25151ca"></a>
### `args.h-node-base`

`template <typename = void> struct node` · [include/fmt/args.h:L38-L39][f1]

node is a fake template base for dynamically stored arguments; it has a virtual default destructor and a unique_ptr<node<>> next link.

The destructor is trivial; the next pointer lets dynamic_arg_list chain typed nodes.

<a id="u-13ec6de0d4b9"></a>
### `args.h-push-back-named-arg`

`class dynamic_arg_list { template <typename T> struct typed_node : node<> { T value; …` · [include/fmt/args.h:L178-L185][f1]

push_back(const named_arg<T, char_type>&) copies the name into dynamic_args_ as basic_string and keeps its c_str.

If need_copy<T>::value, it copies the value into dynamic_args_ as stored_t<T> and emplaces fmt::arg(name, stored value); otherwise it emplaces fmt::arg(name, arg.value) directly. The non-copy branch makes no explicit dynamic_args_ copy; basic_format_arg construction determines storage.

<a id="u-f20490a60230"></a>
### `args.h-push-back-reference-wrapper`

`class dynamic_arg_list { template <typename T> struct typed_node : node<> { T value; …` · [include/fmt/args.h:L158-L173][f1]

push_back(std::reference_wrapper<T>) is constrained by static_assert(need_copy<T>::value); the diagnostic says built-in types and string views are always copied.

It appends the referred object via emplace_arg(arg.get()).

<a id="u-46211a2d0934"></a>
### `args.h-push-back-value`

`class dynamic_arg_list { template <typename T> struct typed_node : node<> { T value; …` · [include/fmt/args.h:L136-L153][f1]

push_back(const T&) chooses storage by need_copy<T>::value.

If true, it copies into dynamic_args_ as stored_t<T> and appends a basic_format_arg referring to that stable copy. If false, it unwraps reference_wrapper and passes the value to emplace_arg; this branch does not copy into dynamic_args_, and basic_format_arg construction determines the stored representation.

**Uncertainties.**

- The exact storage representation chosen by basic_format_arg for the non-copy branch is not defined in this file.

<a id="u-c0efcacfde03"></a>
### `args.h-store-maintenance`

`void clear()` · [include/fmt/args.h:L197-L201][f1]

clear empties data_ and named_info_ and resets dynamic_args_ by assigning an empty dynamic_arg_list; dynamic_arg_list itself has no clear.

reserve asserts new_cap >= new_cap_named, then reserves data_ and named_info_. size returns data_.size() minus one when named_info_ is nonempty, otherwise data_.size().

<a id="u-2f63a5d16115"></a>
### `args.h-unwrap-overloads`

`template <typename T> auto unwrap(const T& v) -> const T&` · [include/fmt/args.h:L26-L26][f1]

unwrap returns a const reference to the input; the reference_wrapper overload returns a const reference to the referred object.

Neither overload copies the value.

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

<a id="u-9fab58079196"></a>
### `fmt-c.h-c-api-types-and-entry-declarations`

`enum` · [include/fmt/fmt-c.h:L36-L46][f3]

Defines the C-facing type tag, argument container, error codes, and declared formatting entry points.

The type enum assigns fmt_int=1, fmt_uint=2, fmt_bool=7, then char/float/double/long_double/cstring sequentially, and fmt_pointer=14. The argument struct stores a type tag plus a named union member value; callers access fields through arg.value, and uint_value is also documented for pointer/custom data. Error enum values are -1 and -2. The two entry functions are only declared here; no implementation or validation behavior is visible.

**Uncertainties.**

- The C entry functions are only declared; their implementation and error behavior are not in this file.

<a id="u-53c545306ca2"></a>
### `fmt-c.h-c-argument-constructors`

`static inline fmt_arg fmt_from_int(long long x)` · [include/fmt/fmt-c.h:L76-L78][f3]

Each constructor returns a C argument with the matching type tag and union field populated; no validation or conversion is performed.

String construction stores the pointer in the cstring field, and pointer construction stores it in the pointer field.

<a id="u-9305afad3162"></a>
### `fmt-c.h-c-argument-macro-and-support`

`enum` · [include/fmt/fmt-c.h:L117-L117][f3]

Provides the _Generic-based argument builder and its support declarations.

The signed-char alias is a real signed char except on non-clang MSVC, where it is an empty enum; a preprocessor error rejects traditional MSVC preprocessing. The macro maps signed/unsigned integer widths to int/uint constructors, bool/char/float/double/long double to their constructors, char* and const char* to string, and only void* and const void* to pointer. Other pointer types fall to the default fmt_unsupported_type. Because that default is declared with no parameters but invoked with (x), unsupported arguments fail at compile time with an argument-count error, not at link time.

<a id="u-cf071be77957"></a>
### `include/fmt/args.h:FMT_BEGIN_NAMESPACE (3)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/args.h:L30-L37][f1]

This symbol covers only the closing brace of the reference-wrapper unwrap overload and comments about the node workaround; it has no callable body, inputs, outputs, side effects, or failure paths.

**Uncertainties.**

- The symbol name and line range appear to be a parser artifact; the supplied lines contain only a closing brace and comments.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/args.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/enum.h
[f3]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/fmt-c.h
