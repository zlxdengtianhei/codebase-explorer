# Truncated formatting

**Capability.** Implements format_to_n and deprecated fixed-buffer overloads using fixed_buffer_traits to count and truncate output.

Readers needing bounded output—format_to_n and the legacy safe_sprintf-style char-array API—will find the truncation traits and result types here. It reports both the advanced iterator and the untruncated count.

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (5)

<a id="u-2e787a128f85"></a>
### `core.h-buffer-traits`

`struct buffer_traits` · [include/fmt/core.h:L1865-L1866][f1]

State-less default buffer traits: the constructor ignores its size argument, count() is always 0, and limit() passes sizes through unchanged.

<a id="u-5755aff9dcc1"></a>
### `core.h-fixed-buffer-traits`

`class fixed_buffer_traits` · [include/fmt/core.h:L1871-L1877][f1]

Traits for truncated output: tracks count_ of code units already written and a fixed limit_.

limit(size) returns how many of `size` units may actually be written (min(size, remaining limit)) while advancing count_ by the full size, so the total (untruncated) size is still measurable.

<a id="u-8fea8a6057c9"></a>
### `core.h-format-to-into-char-arrays`

`template <size_t N> FMT_DEPRECATED auto vformat_to(char (&out)[N], string_view fmt, f…` · [include/fmt/core.h:L2874-L2879][f1]

Deprecated overloads formatting into a fixed char buffer: both delegate to vformat_to_n with capacity N and wrap the result as {out, size > N}, flagging truncation for the format_to_result conversion to detect.

<a id="u-a5f2e0dc231e"></a>
### `core.h-format-to-n`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/core.h:L2840-L2848][f1]

Truncated output: vformat_to_n wraps the iterator in an iterator_buffer with fixed_buffer_traits (limit n), formats, and returns {buf.out(), buf.count()} — the advanced iterator plus the total untruncated size.

format_to_n packages the compile-checked call with the argument store.

<a id="u-75ad7a396fa0"></a>
### `core.h-format-to-result`

`struct format_to_result` · [include/fmt/core.h:L2863-L2867][f1]

Result of the deprecated char-array format_to: a past-the-end pointer and a truncated flag.

The implicit conversion to char* calls report_error("output is truncated") when truncation occurred, so silently discarding output fails loudly.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
