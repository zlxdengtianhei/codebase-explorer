# Value writing engine

**Capability.** Implements the spec-aware write routines for strings, integers, and localized output, plus buffer-backed memory buffers and code-point iteration used by formatting.

Come here for how parsed specs turn into actual output bytes: fill, padding, precision, localized writes, and the inline memory_buffer. It is the central dispatch layer between parsing and the specialized writers.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 4 edge(s)
- [Printf implementation](printf-implementation.md) · graph-only · 3 edge(s)
- [Core argument and buffer base](core-argument-and-buffer-base.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Integer decimal formatting](integer-decimal-formatting.md) · graph-confirmed · 3 edge(s)
- [Float presentation writers](float-presentation-writers.md) · graph-only · 4 edge(s)
- [Argument storage and checking](argument-storage-and-checking.md) · graph-only · 3 edge(s)
- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-only · 3 edge(s)
- [Localized tm writer](localized-tm-writer.md) · graph-only · 2 edge(s)
- [Spec parsing and printf mapping](spec-parsing-and-printf-mapping.md) · graph-only · 2 edge(s)
- [Binary and float primitives](binary-and-float-primitives.md) · graph-only · 1 edge(s)
- [Core argument and buffer base](core-argument-and-buffer-base.md) · graph-only · 1 edge(s)
- [Float conversion entry points](float-conversion-entry-points.md) · graph-only · 1 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (18)

<a id="u-a4b2b0b9b51d"></a>
### `core.h-basic-string-view`

`class basic_string_view { private: const Char* data_; size_t size_; public: using val…` · [include/fmt/core.h:L512-L542][f1]

A lightweight non-owning string view (data pointer + size) used across the public API to avoid ABI/-std mismatches with std::basic_string_view.

The const Char* constructor computes length with __builtin_strlen for char when not constant-evaluated, otherwise with a constexpr loop; the template constructor accepts std-string-like types via data()/size(). remove_prefix advances data_ and shrinks size_ without bounds checking. starts_with has three overloads (view, single char, const Char* via view) and requires the stored size to be at least the prefix size. compare compares the common prefix with detail::compare, then breaks ties by length sign; the six relational/equality operators are defined in terms of compare, so mixed-length views with equal prefixes order by size.

<a id="u-fc6f98985b02"></a>
### `format.h-basic-memory-buffer`

`class basic_memory_buffer : public detail::buffer<T>` · [include/fmt/format.h:L965-L973][f2]

A growable buffer over trivially copyable T with the first SIZE elements stored inline in store_; it derives from detail::buffer<T> with grow as the growth callback.

grow aborts under fuzzing above 5000 elements, computes new capacity as 1.5x old (or the requested size if larger, clamped to the allocator's max_size), allocates, copies existing elements (element-wise under constant evaluation, memcpy otherwise), re-points the buffer, and frees the old block if it was heap-allocated. The destructor deallocates only when data() is not the inline store. The move constructor and move assignment (which asserts self-assignment is absent and deallocates first) both call move: if the allocator propagates (move_alloc returns true) the heap block is adopted and the source is reset to its inline store; if not and allocators differ, the contents are copied instead. When the source used its inline store, the data is copied into the destination's inline store. resize/reserve forward to try_resize/try_reserve; append has an extra overload for contiguous ranges. get_allocator returns a copy of the allocator.

<a id="u-a344bca280bc"></a>
### `format.h-bounded-string-write-char`

`struct bounded_output_iterator` · [include/fmt/format.h:L2488-L2492][f2]

Writes a narrow string_view honoring precision and width.

Fast path: no precision and no width copies (escaped when debug) directly. Otherwise it walks code points accumulating display width and size: in debug mode escaped code points count their escaped byte length (ASCII, so bytes equal columns), with the closing quote accounted when it fits; non-debug code points add display_width_of columns and their byte size; the walk stops when the limit would be exceeded, and an empty debug string with nonzero precision still gets its quotes. bounded_output_iterator is a sink that drops writes once its bound is exhausted, letting write_escaped_string run while emitting only the computed size. Finally write_padded applies width using the computed display width, copying size bytes (escaped via the bounded iterator, or raw).

<a id="u-7de42e77fa51"></a>
### `format.h-fill-and-write-padded`

`template <typename Char, typename OutputIt> FMT_CONSTEXPR FMT_NOINLINE auto fill(Outp…` · [include/fmt/format.h:L1919-L1928][f2]

fill writes n fill units: one code unit when fill_size is 1, otherwise the multi-unit fill string copied n times.

write_padded computes padding as spec width minus the given display width (zero when width already meets it), splits it left/right according to specs.align via encoded shift tables (default_align fixes the fallback), reserves size+padding*fill_size, writes left fill, invokes f, then right fill. The two-size overload passes size as width.

<a id="u-35cf57afe4b9"></a>
### `format.h-fill-n`

`template <typename OutputIt, typename Size, typename T> FMT_CONSTEXPR auto fill_n(Out…` · [include/fmt/format.h:L533-L538][f2]

Writes value count times.

The generic loop assigns through the iterator; the char* overload uses memset at runtime (static_asserting sizeof(T)==1) and the generic loop under constant evaluation; the appender overload fills in capacity-limited chunks via try_reserve/try_resize so it works with buffers that cannot grow to n at once.

<a id="u-e8d23c29ebe6"></a>
### `format.h-float-classification`

`template <typename T> constexpr auto isnan(T value) -> bool` · [include/fmt/format.h:L2878-L2880][f2]

isnan uses value!=value (works for __float128).

has_isfinite detects std::isfinite usability via SFINAE. The isfinite overloads return std::isfinite at runtime, or a NaN-and-infinity comparison under constant evaluation / for types lacking std::isfinite. signbit inspects the sign bit of the double bit pattern under constant evaluation on IEC559 systems, otherwise std::signbit.

<a id="u-6eadf8ec1e9d"></a>
### `format.h-integral-write-dispatch`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_integral<T>:…` · [include/fmt/format.h:L2401-L2414][f2]

The specs-aware integral write first tries localized output via write_loc, then builds the write_int_arg and calls write_int (out-of-line for basic_appender to limit bloat).

The char overload either writes as a character (when specs pass check_char_specs) or rewrites the char as unsigned char/unsigned and formats as an integer. The no-specs integral overload computes the absolute value (via ~abs+1 to avoid sanitizer issues), writes '-' if negative, and formats the digits via to_pointer when possible, else through the iterator.

<a id="u-f57abbee477f"></a>
### `format.h-loc-value`

`class loc_value` · [include/fmt/format.h:L4210-L4215][f2]

A type-erased value passed to locale formatting: stores a basic_format_arg for everything except float128 (whose constructor is a no-op since locale support cannot handle it); visit forwards to the stored argument's visitor.

<a id="u-03d97780aec3"></a>
### `format.h-localized-int-writing`

`template <typename OutputIt> inline auto write_loc(OutputIt, const loc_value&, const …` · [include/fmt/format.h:L2261-L2265][f2]

write_loc dispatches localized formatting: the FMT_USE_LOCALE overloads are FMT_API (defined with the locale support), and the fallback template returns false so callers skip localization.

make_write_int_arg packs sign and absolute value: negatives get prefix 0x01000000|'-'; non-negatives take '-', '+', ' ' or nothing per the sign enum. loc_writer is a visitor that, for integer values, writes via write_int with a digit_grouping built from its stored grouping/separator strings and returns true; non-integers return false.

<a id="u-735cdbf03012"></a>
### `format.h-misc-write-overloads`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_floating_poi…` · [include/fmt/format.h:L3851-L3856][f2]

Remaining write overloads: monostate asserts false (unreachable); string_view copies via copy_noinline; to_string_view-able types convert then copy; enums with non-custom mapping cast to the underlying type; bool writes 1/0 for numeric presentations or "true"/"false" bytes; a single char reserves one slot; a null const Char* reports "string pointer is null" (non-null copies the view); void* writes as a pointer; custom non-fundamental types are formatted through a default-constructed formatter with empty parse and format contexts.

<a id="u-f1c31e2d1801"></a>
### `format.h-nested-format-specs`

`class nested_format_specs` · [include/fmt/format.h:L4114-L4120][f2]

Parses and applies the outer alignment/width around a nested value.

parse stops immediately at end or '}', otherwise parses fill/align then a width (literal or '{' reference); the separator-aware overload returns early when the next char is the separator, since a separator is never a fill character. write resolves the dynamic width, and with zero width formats directly; otherwise it formats the body into a basic_memory_buffer via a buffer-backed context and writes that string with the parsed specs.

<a id="u-b4b3ebcebb22"></a>
### `format.h-string-write-wide-and-pointer-write`

`template <typename Char, typename OutputIt, FMT_ENABLE_IF(!std::is_same<Char, char>::…` · [include/fmt/format.h:L2517-L2538][f2]

For non-char strings, size is truncated to precision (in code units), debug mode re-measures via a counting_buffer escape pass, and the content is written padded (escaped or raw).

The locale overload forwards to the plain overload. The const Char* overload with pointer presentation writes the address; a null pointer reports "string pointer is null"; otherwise it formats as a string_view.

<a id="u-65858c41686d"></a>
### `format.h-write-int-sized`

`struct size_padding` · [include/fmt/format.h:L2309-L2328][f2]

size_padding computes output size and zero padding: with numeric alignment, width beyond size becomes padding and size grows to width; otherwise precision beyond the digit count becomes leading-zero padding.

write_int formats into a stack buffer of num_bits<T> chars per presentation type (dec via do_format_decimal, hex/oct/bin via do_format_base2e with alt prefixes, octal '0' only when precision does not exceed digits and the value is nonzero, chr delegating to write_int_chr). Fast path: when width and precision are unset it reserves and writes prefix bytes plus digits directly. Otherwise it right-pads, writing prefix, then '0' padding, then digits. write_int_noinline is a non-inline forwarder to limit bloat for appender instantiations.

<a id="u-e233491117b6"></a>
### `is_constant_evaluated`

`constexpr auto is_constant_evaluated(bool default_value = false) noexcept -> bool` · [include/fmt/core.h:L378-L392][f1]

Returns whether the current evaluation is constant-evaluated, with three compile-time selected paths: a clang 14 + libstdc++ 12 workaround using __builtin_is_constant_evaluated, the std function when available, or the caller-supplied default (false) otherwise.

<a id="u-6e4ee9204cf4"></a>
### `for_each_codepoint`

`template <typename F> FMT_CONSTEXPR void for_each_codepoint(string_view s, F f)` · [include/fmt/format.h:L633-L666][f2]

Invokes f(cp, sv) for each code point of s, passing invalid_code_point on decode error with a one-byte view.

It decodes in 4-byte blocks while at least four bytes remain; the tail is copied into a zero-padded 7-byte buffer (utf8_decode always reads 4 bytes) and decoded there. If f returns false the walk stops early; on error the input pointer advances one byte so the loop always progresses.

<a id="u-fa90bc1ea1ab"></a>
### `write_bytes`

`template <typename Char, align default_align = align::left, typename OutputIt> FMT_CO…` · [include/fmt/format.h:L1961-L1969][f2]

Writes a raw byte string padded per specs, copying the bytes inside the padded callback; the default specs make it an unpadded copy.

<a id="u-e50e61ba7bee"></a>
### `FMT_BEGIN_EXPORT.size_padding.parse_align`

`template <typename Char> FMT_CONSTEXPR auto parse_align(const Char* begin, const Char…` · [include/fmt/format.h:L2575-L2608][f2]

Parses an optional fill+alignment at the start of format specs: it looks ahead one code point for an alignment char; if found with a preceding fill sequence, '}' ends the spec without consuming, '{' as fill reports "invalid fill character '{'", and any other fill is stored; otherwise the alignment char alone is consumed.

When no alignment is found the input is returned unchanged with align::none set.

<a id="u-fe480160173d"></a>
### `include/fmt/format.h:FMT_BEGIN_EXPORT.size_padding.write (19)`

`template <typename Char, typename OutputIt, typename T, FMT_ENABLE_IF(is_integral<T>:…` · [include/fmt/format.h:L2555-L2573][f2]

Completes the char string_view writer by defining a local bounded_output_iterator that swallows writes once its byte bound reaches zero, then returns the padded result: for debug output the escaped string is written through the bounded iterator so the precomputed size (which accounts for quotes and escapes under the precision/display-width limit) is respected, otherwise the string is copied directly up to the computed size.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
