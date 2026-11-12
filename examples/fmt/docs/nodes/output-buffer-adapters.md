# Output Buffer Adapters

**Capability.** Maps output iterators and containers to buffers and implements bounded, counting, and fixed-buffer formatting paths.

This module adapts formatting output to iterators and containers. It includes buffer mapping, bounded writes, counting buffers, and fixed-buffer formatting.

Parent: [Argument and Spec Pipeline](argument-and-spec-pipeline.md)

## Units (8)

<a id="u-a003f148e5ec"></a>
### `core.h-buffer-storage-and-append`

`class buffer` · [include/fmt/core.h:L1759-L1773][f1]

Contiguous memory buffer with optional growth callback.

It stores data pointer, size, capacity, and a grow function; copy is deleted and move is defaulted. clear sets size to zero. try_resize reserves then sets size to the smaller of requested count and capacity. try_reserve calls grow only when the requested capacity exceeds current capacity. push_back reserves one more element and writes it. append copies a range in chunks: when free capacity is insufficient it grows, recomputes free capacity, and copies at most that much; it repeats until the input is consumed. The element types must match or the input must be char.

<a id="u-ce6268be0a72"></a>
### `core.h-contiguous-container-buffer`

`static FMT_CONSTEXPR void grow(buffer<value_type>& buf, size_t capacity)` · [include/fmt/core.h:L2032-L2036][f1]

container_buffer grows by resizing its container to the requested capacity and pointing the buffer at the container's first element.

The iterator_buffer specialization for a back-insert iterator over a contiguous container derives from that buffer; it can be constructed from the container or from the output iterator by extracting the container, and out() returns a back-insert iterator for the container.

<a id="u-a5f2e0dc231e"></a>
### `core.h-format-to-n`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/core.h:L2840-L2848][f1]

vformat_to_n formats through a fixed-buffer iterator buffer limited to n characters, then returns the output iterator and the total untruncated count.

format_to_n builds the argument store and delegates to vformat_to_n.

<a id="u-08c86fe3ab90"></a>
### `core.h-format-to-output-iterator`

`template <typename OutputIt, FMT_ENABLE_IF(detail::is_output_iterator<remove_cvref_t<…` · [include/fmt/core.h:L2806-L2815][f1]

vformat_to maps the output iterator to a buffer, runs the type-erased formatter, and returns the iterator obtained from the buffer.

format_to builds the argument store from the forwarded arguments and calls vformat_to with the format string view.

<a id="u-74b6311b8859"></a>
### `core.h-get-buffer-overloads`

`template <typename T, typename OutputIt, FMT_ENABLE_IF(!is_buffer_appender<OutputIt>:…` · [include/fmt/core.h:L2099-L2103][f1]

Maps an output iterator to a buffer.

For a non-buffer appender it returns a new iterator_buffer for that output iterator. For a buffer appender it returns the underlying buffer reference from the container.

<a id="u-b40a1356f595"></a>
### `core.h-iterator-buffer`

`class iterator_buffer : public Traits, public buffer<T>` · [include/fmt/core.h:L1936-L1939][f1]

A buffer that writes to an output iterator when flushed.

flush clears the buffer before copying its data to the output, so a throwing copy leaves the buffer already cleared. The destructor flushes and swallows exceptions.

<a id="u-47470cb1ed32"></a>
### `counting_buffer.grow`

`static FMT_CONSTEXPR void grow(buffer<T>& buf, size_t)` · [include/fmt/core.h:L2071-L2075][f1]

counting_buffer growth counts a full internal buffer and clears it.

If the buffer size is not the fixed buffer size it does nothing; otherwise it adds the size to the accumulated count and clears the buffer.

<a id="u-7cc6f73ebfab"></a>
### `fixed_buffer_traits.limit`

`FMT_CONSTEXPR auto limit(size_t size) -> size_t` · [include/fmt/core.h:L1879-L1883][f1]

Limits a write to the remaining fixed-buffer budget.

It computes the remaining allowance as limit minus count when positive, otherwise zero; it adds the requested size to the internal count and returns the smaller of requested size and allowance.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
