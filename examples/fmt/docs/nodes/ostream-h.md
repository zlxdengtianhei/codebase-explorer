# std::ostream Support

**Capability.** Enables formatting any type with operator<< into fmt buffers and provides print/println/vprint overloads writing to std::ostream, including a Windows console fast path.

Include ostream.h to format ostream-insertable types or print to std::ostream; detail support reaches the stream's FILE* and write_buffer flushes in chunks.

**Depends on.**

- [FILE Output Backend](core-file-output.md) · model-inferred · 0 edge(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Units (6)

<a id="u-dc9e029219fb"></a>
### `ostream-h-detail-support`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/ostream.h:L33-L37][f1]

Supplies internal helpers that let fmt reach a std::ostream's underlying FILE* and carry a by-reference value for ostream-based formatting.

file_access<Tag,BufType,member> declares a hidden friend get_file returning obj.*FileMemberPtr; an anonymous-namespace tag type forces a unique explicit instantiation per translation unit, emitted for std::filebuf::_Myfile when FMT_MSVC_STL_UPDATE is set, making the private FILE* reachable via get_file(std::filebuf&). streamed_view<T> trivially holds a const T& for streamed formatting.

**Notes.**

- side_effect: The explicit instantiation of file_access is a compile-time device whose only purpose is to open access to a private stdlib member.

uses: [write_buffer](ostream-h.md#u-9092171acc89)

**Uncertainties.**

- The instantiation assumes the stdlib layout member _Myfile exists; only the _MSVC_STL_UPDATE guard indicates this.

<a id="u-d2ebb53713bd"></a>
### `ostream-h-ostream-formatter`

`template <typename T, typename Context> auto format(const T& value, Context& ctx) con…` · [include/fmt/ostream.h:L82-L92][f1]

Enables formatting any type with an ostream operator<<.

basic_ostream_formatter<Char> derives from formatter<basic_string_view<Char>, Char>, deletes set_debug_format, and in format() builds a memory buffer, wraps it via detail::formatbuf in a temporary std::basic_ostream, imbues std::locale::classic() so output is unlocalized, streams the value, then enables exceptions (failbit|badbit) before delegating to the string-view formatter with the collected bytes. formatter<detail::streamed_view<T>, Char> inherits it and unwraps the stored reference; streamed(value) is a constexpr factory returning {value}.

**Notes.**

- failure: Stream errors during operator<< set fail/bad state that is only surfaced by the later exceptions-enabled operations, not thrown at the point of the failing << as written here.
- side_effect: Output goes through a temporary stream bound to a memory buffer, not the caller's stream.

**Uncertainties.**

- Whether a failed operator<< ultimately throws depends on formatbuf/stream behavior defined outside this file.

<a id="u-9092171acc89"></a>
### `write_buffer`

`template <typename Char> void write_buffer(std::basic_ostream<Char>& os, buffer<Char>…` · [include/fmt/ostream.h:L55-L68][f1]

Writes a buffer's contents to a std::ostream in chunks no larger than max_size, which must be positive and at most the maximum streamsize and defaults to that maximum.

A do/while loop always writes at least once: each iteration picks n = size if size <= max_size else max_size, calls os.write(buf_data, n), advances the pointer, and decrements the remaining size, so oversized buffers are split across multiple writes; the loop exits when size reaches zero.

**Uncertainties.**

- Stream write failures are not checked here; behavior depends on the stream's own error state.

<a id="u-cd7e90da9ca5"></a>
### `include/fmt/ostream.h:print`

`template <typename... T> void print(std::ostream& os, format_string<T...> fmt, T&&...…` · [include/fmt/ostream.h:L154-L161][f1]

Prints formatted data to a std::ostream.

It builds fmt::vargs<T...> from the forwarded arguments; if detail::use_utf8 is true at compile time it returns vprint(os, fmt.str, vargs), enabling the Windows console path; otherwise it formats into a local memory_buffer and calls detail::write_buffer directly, bypassing vprint's console logic.

calls: [include/fmt/ostream.h:vprint](ostream-h.md#u-358e426dd2e5), [write_buffer](ostream-h.md#u-9092171acc89)

**Uncertainties.**

- Behavioral differences beyond console handling depend on use_utf8, defined elsewhere.

<a id="u-399d39828066"></a>
### `include/fmt/ostream.h:println`

`template <typename... T> void println(std::ostream& os, format_string<T...> fmt, T&&.…` · [include/fmt/ostream.h:L163-L167][f1]

Appends a newline by delegating to fmt::print with format string "{}\n" and the result of fmt::format(fmt, std::forward<T>(args)...), so argument values are formatted twice: once into a string, then printed.

calls: [include/fmt/ostream.h:print](ostream-h.md#u-cd7e90da9ca5); uses: [ostream-h-ostream-formatter](ostream-h.md#u-d2ebb53713bd)

**Uncertainties.**

- FMT_STRING's expansion is unresolved in this file; double formatting may re-trigger side effects in argument formatters.

<a id="u-358e426dd2e5"></a>
### `include/fmt/ostream.h:vprint`

`inline void vprint(std::ostream& os, string_view fmt, format_args args)` · [include/fmt/ostream.h:L120-L145][f1]

Formats args into a memory_buffer and writes them to an ostream, with a Windows console fast path.

First detail::vformat_to fills the buffer. Under FMT_MSVC_STL_UPDATE && FMT_USE_RTTI, a dynamic_cast to std::filebuf extracts the FILE* via detail::get_file; alternatively on _WIN32 with __GLIBCXX__ and RTTI it tries __gnu_cxx::stdio_sync_filebuf<char>::file(), then __gnu_cxx::stdio_filebuf<char>::file(). On _WIN32, if a FILE* was found and _isatty(_fileno(f)) reports a terminal, it flushes the stream and tries detail::write_console, returning early only on success. Otherwise, and after a failed console write, detail::write_buffer(os, buffer) writes the data; f is otherwise unused (ignore_unused).

calls: [write_buffer](ostream-h.md#u-9092171acc89); uses: [ostream-h-detail-support](ostream-h.md#u-dc9e029219fb)

**Uncertainties.**

- Whether the stream remains consistent after flush followed by a failed write_console is not established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ostream.h