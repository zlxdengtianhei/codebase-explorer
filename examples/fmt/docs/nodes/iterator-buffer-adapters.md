# Iterator buffer adapters

**Capability.** Adapts output iterators and containers to the buffer interface, with optimized copy paths and detection traits for back-insert iterators.

This module makes arbitrary output iterators look like buffers so format_to can write anywhere. It includes container_buffer, iterator_buffer, and the traits that detect back-inserters for fast copies.

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (9)

<a id="u-a2b55306cba9"></a>
### `core.h-basic-appender`

`constexpr basic_appender(detail::buffer<T>& buf) : container(&buf)` · [include/fmt/core.h:L2453-L2453][f1]

Minimal output iterator wrapping a pointer to detail::buffer<T>: assignment push_backs the value, dereference and both increments are no-ops returning *this, satisfying output-iterator requirements without <iterator>.

<a id="u-635641f2634f"></a>
### `core.h-container-buffer`

`class container_buffer : public buffer<typename Container::value_type>` · [include/fmt/core.h:L2027-L2032][f1]

Buffer that grows a caller-owned container: grow resizes the container to the requested capacity and re-points the buffer at container[0] via set().

Holds the container by public reference; the constructor starts with the container's current size as capacity.

<a id="u-a6069a7ce5dc"></a>
### `core.h-copy-overloads`

`template <typename OutputIt, typename InputIt, typename = void> struct has_append : s…` · [include/fmt/core.h:L1886-L1887][f1]

Optimized range copy selected by traits: if the output is a back-insert iterator whose container has append(first, last), copy via container.append; else if it has insert, insert at end; otherwise fall back to an element-wise loop writing static_cast<T>(*begin++).

has_append/has_insert are the detection traits built on get_container.

<a id="u-6816a4df0a2a"></a>
### `core.h-get-container`

`template <typename OutputIt> inline FMT_CONSTEXPR auto get_container(OutputIt it) -> …` · [include/fmt/core.h:L491-L494][f1]

Extracts a reference to the container stored inside a std insert_iterator by deriving a subclass that exposes the protected `container` pointer and dereferencing it; constexpr-friendly via an accessor struct.

<a id="u-249d6536b9a4"></a>
### `core.h-is-back-insert-iterator`

`template <typename It, typename Enable = std::true_type> struct is_back_insert_iterat…` · [include/fmt/core.h:L481-L482][f1]

Trait that is true exactly when the iterator equals the type produced by adl back_inserter of its container_type, detected through an ADL-only namespace to avoid finding unrelated overloads.

<a id="u-a1382e13030a"></a>
### `core.h-is-output-iterator`

`template <typename It, typename T, typename Enable = void> struct is_output_iterator …` · [include/fmt/core.h:L2298-L2299][f1]

Trait true for appender, or for any iterator whose post-increment dereference is assignable from T; used to constrain format_to-style overloads.

<a id="u-436b5cd3d539"></a>
### `core.h-iterator-buffer-bridging`

`template <typename T> struct is_back_insert_iterator<basic_appender<T>> : std::true_type` · [include/fmt/core.h:L2085-L2086][f1]

is_buffer_appender is true when the iterator is a back-insert iterator into something deriving from buffer<value_type>.

get_buffer returns the container's buffer directly for such appenders, otherwise wraps the iterator in a fresh iterator_buffer. get_iterator returns buf.out() when available, or the original iterator when the buffer already wraps it (i.e. it was a buffer appender).

<a id="u-119f1f955c79"></a>
### `core.h-vformat-to-format-to`

`template <typename OutputIt, FMT_ENABLE_IF(detail::is_output_iterator<remove_cvref_t<…` · [include/fmt/core.h:L2806-L2815][f1]

Formats into an output iterator: vformat_to wraps the iterator with get_buffer (or uses its buffer directly for buffer appenders), calls detail::vformat_to with no locale, and returns the final iterator via get_iterator.

format_to builds the argument store from its compile-checked format string and forwards; neither appends a terminating null.

<a id="u-76315bbd0782"></a>
### `iterator_buffer<
    OutputIt,
    enable_if_t<is_back_insert_iterator<OutputIt>::value &&
                    is_contiguous<typename OutputIt::container_type>::value,
                typename OutputIt::container_type::value_type>>`

`class iterator_buffer< OutputIt, enable_if_t<is_back_insert_iterator<OutputIt>::value…` · [include/fmt/core.h:L2046-L2057][f1]

Specialization of iterator_buffer for a back_insert_iterator into a contiguous container; it simply inherits container_buffer over that container, so writes grow the container directly.

The constructor taking an iterator extracts the container via get_container; out() returns a fresh back_insert_iterator to the container.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
