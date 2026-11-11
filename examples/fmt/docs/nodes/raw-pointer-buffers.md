# Raw pointer buffers

**Capability.** Provides buffer specializations writing directly to raw pointers, with optional hard limits or effectively unlimited capacity.

These iterator_buffer specializations let formatting write straight into caller memory, either bounded by fixed_buffer_traits or unbounded. They are the mechanism behind format_to into char arrays.

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (3)

<a id="u-13a8f99d9470"></a>
### `core.h-iterator-buffer-fixed-raw-pointer`

`class iterator_buffer<T*, T, fixed_buffer_traits> : public fixed_buffer_traits, publi…` · [include/fmt/core.h:L1974-L1979][f1]

Specialization writing through a raw T* with a hard limit via fixed_buffer_traits, again staging in a 256-element array.

Initially the buffer aliases the caller's memory (capacity = n); grow flushes when size reaches capacity. flush applies the limit: if the buffer still points at the caller's memory it advances out_ by the written count and rebinds the buffer to the internal array; otherwise data is simply dropped after counting, implementing truncation. The destructor flushes unconditionally. The move constructor rebinds to the internal array and clears when the source was not already using it. out() flushes and returns the advanced pointer; count() reports the total (untruncated) size.

<a id="u-b08d5f9d942c"></a>
### `core.h-iterator-buffer-generic`

`class iterator_buffer : public Traits, public buffer<T>` · [include/fmt/core.h:L1936-L1939][f1]

Buffer that stages output in a 256-element inline array and flushes it to the wrapped output iterator when full.

grow flushes only when the buffer is exactly at its fixed size (otherwise growth requests are ignored, relying on the one-element guarantee). flush clears the buffer, applies Traits::limit to truncate, and copies to out_ via the copy overloads. The destructor flushes inside FMT_TRY/FMT_CATCH(...) so an exception during unwinding does not crash. out() flushes and returns the final iterator; count() adds the traits count to the buffered size. The move constructor rebinds to its own data_ array and copies the output iterator.

<a id="u-1a831980a917"></a>
### `core.h-iterator-buffer-unbounded-raw-pointer`

`class iterator_buffer<T*, T> : public buffer<T>` · [include/fmt/core.h:L2019-L2021][f1]

Specialization wrapping a raw T* with effectively unlimited capacity (~size_t()) and a no-op grow, so writes go directly to the pointer; out() returns one-past-the-end of the written data.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
