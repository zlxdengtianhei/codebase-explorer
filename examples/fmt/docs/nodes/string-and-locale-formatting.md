# String and Locale Formatting

**Capability.** Formats locale strings into buffers and constructs fixed compile-time strings from character arrays.

This small module handles string-buffer conversion and fixed-string construction. It appears to support locale string formatting and compile-time string storage.

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (3)

<a id="u-557574e6a020"></a>
### `format.h-locale-format-entry-points`

`inline auto vformat(locale_ref loc, string_view fmt, format_args args) -> std::string` · [include/fmt/format.h:L4611-L4616][f1]

The locale string formatter formats into a memory buffer and returns a string.

The variadic wrapper builds arguments and calls it. The output-iterator formatter gets a buffer for the iterator, formats, and returns the iterator. The variadic wrapper forwards. The size function formats into a counting buffer and returns the count.

<a id="u-efe5f1d4eee8"></a>
### `include/fmt/format.h:to_string (3)`

`template <size_t SIZE> FMT_NODISCARD auto to_string(const basic_memory_buffer<char, S…` · [include/fmt/format.h:L1095-L1101][f1]

This function converts a character memory buffer to a standard string using its data and size.

It assumes the size is below the string maximum.

<a id="u-2b9198660ba7"></a>
### `fixed_string.fixed_string`

`FMT_CONSTEXPR fixed_string(const Char (&s)[N])` · [include/fmt/format.h:L1164-L1167][f1]

Constructs a fixed_string by copying all N characters of the supplied character array into the zero-initialized member buffer via detail::copy, so the stored data is a fixed-size, compile-time string usable as a non-type template argument.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
