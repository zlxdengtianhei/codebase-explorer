# String and stream output

**Capability.** Converts buffers to std::string, transcodes UTF-16/32 to UTF-8, and prints to buffered streams or FILE*, with optimizer hints.

This small module handles the final mile: turning a memory_buffer into a std::string, transcoding wide input, and choosing between stream and FILE output. It also hosts the assume optimization hint.

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (5)

<a id="u-aff7ad21d860"></a>
### `format.h-string-buffer`

`class string_buffer` · [include/fmt/format.h:L1126-L1132][f1]

Owns a std::string plus a container_buffer view over it; converts to writer for the buffer path, and str() exposes the underlying string for reading the result.

<a id="u-37d8426eb840"></a>
### `format.h-to-utf8`

`class to_utf8` · [include/fmt/format.h:L1563-L1568][f1]

Converts UTF-16 or UTF-32 (host endian) input to UTF-8 in a memory_buffer.

The constructor converts and, on failure, throws std::runtime_error ("invalid utf16"/"invalid utf32" by char width) under the default abort policy. The static convert walks the input: for 16-bit input, a high surrogate must be followed by a low surrogate (combined via 0x35fdc00 arithmetic); a broken pair triggers the policy — abort returns false, replace appends U+FFFD, wtf emits the surrogate via to_utf8_3bytes and continues. Code points are encoded as 1–4 UTF-8 bytes by magnitude; anything outside valid ranges returns false. The member convert wraps the static one and appends a trailing NUL, so size() is buffer size minus one; c_str/str/string_view conversion expose the result.

<a id="u-6a77dd1101d6"></a>
### `format.h-writer`

`class writer` · [include/fmt/format.h:L1104-L1113][f1]

Prints to either a buffered stream or a FILE*, holding one of the two (the other null).

print formats into the buffer via format_to when a buffer is set, otherwise prints to the file; the class never owns the stream.

<a id="u-4ccf5930fd4b"></a>
### `assume`

`FMT_INLINE void assume(bool condition)` · [include/fmt/format.h:L456-L463][f1]

Hints the optimizer that the condition holds via __builtin_assume or __builtin_unreachable; the argument is otherwise unused, so the call has no effect on platforms without such builtins.

<a id="u-efe5f1d4eee8"></a>
### `include/fmt/format.h:to_string (3)`

`template <size_t SIZE> FMT_NODISCARD auto to_string(const basic_memory_buffer<char, S…` · [include/fmt/format.h:L1095-L1101][f1]

Converts a basic_memory_buffer<char> to std::string from its data and size, with an assume hint that the size fits std::string.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
