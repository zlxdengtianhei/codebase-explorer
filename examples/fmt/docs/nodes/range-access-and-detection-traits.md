# Range Access and Detection Traits

**Capability.** Detects and accesses ranges through member or ADL begin/end, C arrays, const references, and value-like expressions.

Use this module for ranges.h traits and helpers that determine whether a type is range-accessible. It provides begin/end forwarding, C-array bounds, const-range checks, and dereference reference-type computation.

Parent: [Range and Tuple Formatting](range-and-tuple-formatting.md)

## Units (9)

<a id="u-9a3813a91534"></a>
### `ranges.h-adl-range-access`

`template <typename T> auto range_begin(T&& rng) -> enable_if_t<!has_member_fn_begin_e…` · [include/fmt/ranges.h:L83-L88][f1]

Calls unqualified begin/end for ADL lookup, but only when the type lacks member begin/end.

The return type is the ADL call result; no fallback is attempted if ADL lookup fails.

<a id="u-6de9c9ef857f"></a>
### `ranges.h-all-view`

`template <typename Container> struct all` · [include/fmt/ranges.h:L804-L806][f1]

Small view holding a const reference to a container.

begin and end return the container's const_iterator, so it exposes only const iteration.

<a id="u-6931bbbf432d"></a>
### `ranges.h-c-array-range-access`

`template <typename T, size_t N> auto range_begin(const T (&arr)[N]) -> const T*` · [include/fmt/ranges.h:L54-L57][f1]

Returns the array address as the begin pointer and address plus element count as the end pointer for a C array.

Both results are const pointers to the element type.

<a id="u-259bde269e38"></a>
### `ranges.h-const-and-mutable-range-detection`

`template <typename T, typename Enable = void> struct has_const_begin_end : std::false…` · [include/fmt/ranges.h:L95-L96][f1]

has_const_begin_end is true when a const remove_cvref_t<T>& supports range_begin/range_end and dereference.

has_mutable_begin_end is true when T& supports the same; it adds an extra int to the SFINAE probe to work around older MSVC behavior.

<a id="u-e3f25ca5ab5d"></a>
### `ranges.h-member-begin-end-detection`

`template <typename T, typename Enable = void> struct has_member_fn_begin_end_t : std:…` · [include/fmt/ranges.h:L62-L63][f1]

Traits true when an expression can call .begin() and .end() on the type and dereference the begin result.

Used to suppress the ADL range accessors when member functions exist.

<a id="u-d2a88b8a58bd"></a>
### `ranges.h-member-range-access`

`template <typename T> FMT_CONSTEXPR auto range_begin(T&& rng) -> decltype(static_cast…` · [include/fmt/ranges.h:L71-L75][f1]

Forwards the range and returns the result of its .begin() or .end() member call.

These overloads participate when those member expressions are valid.

<a id="u-c4b88b1996af"></a>
### `ranges.h-optional-like-detection`

`template <typename T, typename _ = void> struct is_optional_like_ : std::false_type` · [include/fmt/ranges.h:L133-L134][f1]

Traits true when the type has both has_value() and value() expressions.

It does not inspect the return types or runtime state.

<a id="u-bc48c742e74b"></a>
### `ranges.h-range-detection`

`template <typename T, typename _ = void> struct is_range_ : std::false_type` · [include/fmt/ranges.h:L116-L116][f1]

The detail trait is true when either const or mutable begin/end access is available.

The public trait additionally excludes optional-like types and types with a to_string_view member, so those are not treated as ranges.

<a id="u-5cf0cf48d79e"></a>
### `ranges.h-range-reference-type`

`template <typename R> struct range_reference_type_impl` · [include/fmt/ranges.h:L231-L233][f1]

Computes the reference type produced by dereferencing range_begin.

On older MSVC it uses a helper with a C-array specialization returning T&; otherwise it uses decltype(*range_begin(declval<Range&>())). uncvref_type strips cv and reference from that result.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h
