# Ostream Formatting Bridge

**Capability.** Bridges fmt formatting to std::ostream, including streamed value views, buffer writes, and FILE detection.

This module connects fmt to ostream output. It covers streamed value wrapping, chunked buffer writes, ostream formatting, and FILE detection.

Parent: [OS and Stream Integration](os-and-stream-integration.md)

## Units (9)

<a id="u-a26e09e0382f"></a>
### `ostream.h-file-access-helper`

`class file_access` · [include/fmt/ostream.h:L41-L43][f1]

A tag-parameterized helper that grants a friend function access to a buffer type's private FILE* member; the friend returns that member.

Under MSVC STL update it is explicitly instantiated for std::filebuf and used to recover the underlying FILE*. No runtime side effects beyond the returned pointer.

<a id="u-7a2504b5dc8d"></a>
### `ostream.h-streamed-view`

`template <typename T> struct streamed_view` · [include/fmt/ostream.h:L70-L72][f1]

Wraps a value by reference for ostream-based formatting without copying; the returned view's lifetime is tied to the referenced argument.

The formatter specialization later forwards the referenced value to the ostream formatter.

<a id="u-a7b55b0a5c4f"></a>
### `ostream.h-streamed-view-formatter`

`template <typename T, typename Char> struct formatter<detail::streamed_view<T>, Char>…` · [include/fmt/ostream.h:L97-L100][f1]

Specializes formatting for the streamed view by inheriting the ostream formatter and forwarding the referenced value to it.

It adds no parsing or escaping of its own.

<a id="u-9092171acc89"></a>
### `write_buffer`

`template <typename Char> void write_buffer(std::basic_ostream<Char>& os, buffer<Char>…` · [include/fmt/ostream.h:L55-L68][f1]

Writes a buffer to an ostream in chunks no larger than max_size, advancing the data pointer and reducing the remaining size until zero.

It does not set an exception mask, so a failed os.write may only set stream state rather than throw. The comment requires max_size positive and no greater than streamsize maximum, but the code does not validate it.

<a id="u-787715de9c22"></a>
### `include/fmt/ostream.h:FMT_BEGIN_NAMESPACE (3)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/ostream.h:L44-L54][f1]

Conditionally emits the MSVC STL file-access helper: when FMT_MSVC_STL_UPDATE is nonzero, it explicitly instantiates file_access for std::filebuf and declares get_file(std::filebuf&) -> FILE*; when zero, neither declaration is emitted.

**Uncertainties.**

- The symbol is labeled FMT_BEGIN_NAMESPACE, but the visible source region is a preprocessor conditional around file_access; the label likely reflects parser macro handling rather than a callable function.

<a id="u-206231478489"></a>
### `include/fmt/ostream.h:format`

`template <typename T, typename Context> auto format(const T& value, Context& ctx) con…` · [include/fmt/ostream.h:L82-L92][f1]

Streams a value into a memory buffer through a formatbuf, imbues the classic locale, inserts the value, then sets failbit/badbit exceptions before delegating to the string-view formatter.

Because the exception mask is set after insertion, an already-set failure state can throw at that point; insertion failures before the mask is set may only set stream state.

<a id="u-cd7e90da9ca5"></a>
### `include/fmt/ostream.h:print`

`template <typename... T> void print(std::ostream& os, format_string<T...> fmt, T&&...…` · [include/fmt/ostream.h:L154-L161][f1]

Builds argument storage, then either calls vprint when the compile-time use_utf8 condition holds or formats into a memory buffer and writes it with write_buffer.

The two paths differ in whether FILE*/console detection is attempted.

<a id="u-399d39828066"></a>
### `include/fmt/ostream.h:println`

`template <typename... T> void println(std::ostream& os, format_string<T...> fmt, T&&.…` · [include/fmt/ostream.h:L163-L167][f1]

Formats the arguments into a string, then calls print with a literal newline format and that string.

The newline is appended after the formatted text; the resulting string is formatted again by print.

<a id="u-358e426dd2e5"></a>
### `include/fmt/ostream.h:vprint`

`inline void vprint(std::ostream& os, string_view fmt, format_args args)` · [include/fmt/ostream.h:L120-L145][f1]

Formats arguments into a memory buffer, then tries to detect a FILE* backing the ostream under MSVC STL or Windows libstdc++ with RTTI.

On Windows, only when a FILE* is found and its descriptor is a tty does it flush the stream and try console writing; if console writing succeeds it returns, otherwise it falls through. Non-tty file buffers and all other cases fall through to write_buffer without flushing. It does not set an exception mask.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ostream.h
