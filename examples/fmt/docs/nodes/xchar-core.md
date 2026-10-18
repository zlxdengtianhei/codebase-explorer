# Exotic Char Format Core

**Capability.** The non-char detail::vformat_to pipeline into buffers, locale-sensitive vformat/vformat_to variants, the color-aware wide vformat, bounded vformat_to_n, and the wide locale writer.

All wide/exotic entry points funnel here; the core static_asserts against Char == char and runs the standard parse/format handler over an appender.

**Depends on.**

- [Core Format Engine](core-format-engine.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Wide Format Entry Points](xchar-entry.md) · model-inferred · 0 edge(s)

Parent: [Wide & Exotic Char Support](xchar-h.md)

## Units (8)

<a id="u-1543a9ab5af2"></a>
### `include/fmt/xchar.h:vformat_to`

`template <typename Char> void vformat_to(buffer<Char>& buf, basic_string_view<Char> f…` · [include/fmt/xchar.h:L60-L68][f1]

Detail-level formatting into a buffer for non-char character types: static_asserts against Char == char, wraps the buffer in a basic_appender, and runs parse_format_string with a format_handler holding a fresh parse_context and a context bundling the appender, args, and optional locale.

This is the shared engine behind the public xchar formatting entry points.

uses: [format_handler][f2]

**Uncertainties.**

- The unresolved graph reference to FMT_THROW indicates error paths inside format_handler, whose behavior is defined in format.h, not here.

<a id="u-29b8e5ac1e06"></a>
### `include/fmt/xchar.h:write_loc`

`inline auto write_loc(basic_appender<wchar_t> out, loc_value value, const format_spec…` · [include/fmt/xchar.h:L46-L58][f1]

Locale-aware numeric writer for wchar_t output.

When FMT_USE_LOCALE is enabled it fetches the std::locale, reads numpunct grouping and thousands separator (empty separator when grouping is empty), and visits the value with a loc_writer<wchar_t> carrying those settings, returning the visitor's result. When locale support is disabled it ignores all parameters and returns false, signaling that locale formatting did not happen.

uses: [loc_writer][f2]

**Uncertainties.**

- The false return's downstream effect depends on callers outside this file.

<a id="u-3d812594b50c"></a>
### `include/fmt/xchar.h:vformat (2)`

`template <typename Char, FMT_ENABLE_IF(!std::is_same<Char, char>::value)> auto vforma…` · [include/fmt/xchar.h:L178-L185][f1]

Formats wide/exotic-char arguments into a basic_memory_buffer via detail::vformat_to and returns std::basic_string<Char>.

Enabled only for Char != char. Errors originate in the underlying format handler.

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

<a id="u-3188ee0608a4"></a>
### `include/fmt/xchar.h:vformat (3)`

`template <typename S, typename Char = detail::format_string_char_t<S>, FMT_ENABLE_IF(…` · [include/fmt/xchar.h:L209-L217][f1]

Locale-sensitive vformat for exotic characters: formats into a memory buffer with detail::vformat_to, passing the locale_ref through, and returns the resulting string.

Enabled for any Char != char.

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

<a id="u-90bfb1dc242c"></a>
### `include/fmt/xchar.h:vformat`

`inline auto vformat(text_style ts, wstring_view fmt, wformat_args args) -> std::wstring` · [include/fmt/xchar.h:L341-L346][f1]

Color-aware wide vformat: formats into a wmemory_buffer passing a text_style through detail::vformat_to, then returns the string including ANSI escape sequences implied by the style.

uses: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

**Uncertainties.**

- The two-argument detail::vformat_to overload taking text_style is not shown in this file; its escape-sequence behavior is defined in color.h.

<a id="u-64e113389e95"></a>
### `include/fmt/xchar.h:vformat_to (2)`

`template <typename OutputIt, typename S, typename Char = detail::format_string_char_t…` · [include/fmt/xchar.h:L228-L237][f1]

vformat_to for arbitrary output iterators and exotic chars: obtains a buffer adapter for the iterator via detail::get_buffer, runs detail::vformat_to on it without locale, and returns detail::get_iterator(buf, out) so the caller receives an appropriate iterator for the underlying sink type.

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

<a id="u-f8d71482a4f6"></a>
### `include/fmt/xchar.h:vformat_to (3)`

`template <typename S, typename OutputIt, typename... Args, typename Char = detail::fo…` · [include/fmt/xchar.h:L249-L259][f1]

Locale-sensitive vformat_to for output iterators: wraps the iterator in a buffer, formats with the given locale_ref (note this call site uses the unqualified vformat_to, resolving to the detail overload taking a locale), and returns the adapted iterator via detail::get_iterator.

uses: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

**Uncertainties.**

- The unqualified call could in principle resolve to a different visible overload; resolution depends on declarations outside this file.

<a id="u-7a64503e6cbc"></a>
### `vformat_to_n`

`template <typename OutputIt, typename Char, typename... Args, FMT_ENABLE_IF(detail::i…` · [include/fmt/xchar.h:L271-L281][f1]

Bounded formatting: wraps the output iterator in an iterator_buffer with fixed_buffer_traits limited to n characters, runs detail::vformat_to, and returns format_to_n_result{buf.out(), buf.count()} — the possibly-flushed iterator and the number of code units that would have been written (count may exceed n when output was truncated).

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h