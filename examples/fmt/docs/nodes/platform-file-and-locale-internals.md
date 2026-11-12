# Platform File and Locale Internals

**Capability.** Wraps FILE internals, platform locking, locale facets, system-error formatting, UTF conversion, and allocation helpers.

Come here for platform-facing formatting internals. The units describe FILE wrappers, locale data, system-error text, UTF-16 conversion, and allocation behavior.

**Depends on.**

- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-confirmed · 1 edge(s)
- [Integer and Pointer Formatting](integer-and-pointer-formatting.md) · graph-only · 1 edge(s)
- [Type-Erased Argument Context](type-erased-argument-context.md) · graph-only · 1 edge(s)

Parent: [Platform and Dragonbox Support](platform-and-dragonbox-support.md)

## Units (26)

<a id="u-9afb6339725c"></a>
### `format-inl.h-apple-file-wrapper`

`class apple_file : public file_base<F>` · [include/fmt/format-inl.h:L1586-L1588][f1]

Wraps Apple libc FILE internals.

is_buffered is true unless the unbuffered flag is set. init_buffer returns when a buffer pointer exists, otherwise forces initialization by writing and removing a character and adjusting the write count. Read and write buffer accessors expose the current pointer and remaining sizes. advance_write_buffer moves the pointer and reduces the write count. needs_flush is false unless line buffering is set, then searches the pending write region for a newline.

<a id="u-d73fbf8fcd14"></a>
### `format-inl.h-bigint-formatter`

`FMT_CONSTEXPR auto parse(format_parse_context& ctx) -> format_parse_context::iterator` · [include/fmt/format-inl.h:L1402-L1405][f1]

Parses no format specification and returns the parse context begin iterator.

Formats bigint digits from most significant to least: the first digit uses plain hex, later digits use eight-digit zero-padded hex, and a positive exponent appends p followed by exponent times bigit bits.

<a id="u-9f9c2b8667b2"></a>
### `format-inl.h-console-writing`

`FMT_FUNC auto write_console(int, string_view) -> bool` · [include/fmt/format-inl.h:L1728-L1728][f1]

On non-Windows builds or when console writing is disabled, returns false.

On Windows it converts UTF-8 text to UTF-16 and calls WriteConsoleW on the file descriptor's OS handle, returning whether the call succeeded.

<a id="u-e5af806ceecf"></a>
### `format-inl.h-divide-by-ten-to-kappa-plus-one`

`inline auto divide_by_10_to_kappa_plus_1(uint32_t n) noexcept -> uint32_t` · [include/fmt/format-inl.h:L278-L281][f1]

Computes floor(n / 10^(kappa+1)) for float using a 64-bit multiply and shift, and for double using the upper 64 bits of a 128-bit multiply followed by a shift.

<a id="u-34d05ff86f86"></a>
### `format-inl.h-dragonbox-multiplication-helpers`

`inline auto umul96_upper64(uint32_t x, uint64_t y) noexcept -> uint64_t` · [include/fmt/format-inl.h:L211-L213][f1]

umul96_upper64 multiplies a 32-bit value shifted into the high half of a 64-bit value by a 64-bit value and returns the upper 64 bits.

umul192_lower128 multiplies a 64-bit value by a 128-bit value and returns the lower 128 bits, combining the high product with the high half of the low product. umul96_lower64 returns the low 64 bits of a 32-bit by 64-bit product.

<a id="u-b18a32f8eb29"></a>
### `format-inl.h-fallback-file-wrapper`

`class fallback_file : public file_base<F>` · [include/fmt/format-inl.h:L1632-L1640][f1]

Provides a non-buffered FILE wrapper.

It reports no buffering and no flush need, does nothing for buffer initialization or write advancement, exposes no write buffer, and exposes a one-character read buffer only after an unget. get clears the pending character and reads from the base FILE. unget first calls the base unget, then stores the character as the next unconsumed character.

<a id="u-dd1037c6c48f"></a>
### `format-inl.h-file-base-file-wrapper`

`class file_base` · [include/fmt/format-inl.h:L1508-L1513][f1]

Wraps a FILE pointer and exposes conversion to that pointer.

get reads with getc_unlocked and throws system_error with errno when EOF is accompanied by a stream error. unget calls ungetc and throws system_error on EOF. flush calls fflush and throws system_error when it fails.

<a id="u-6144a070e24c"></a>
### `format-inl.h-file-print-buffer`

`class file_print_buffer : public buffer<char>` · [include/fmt/format-inl.h:L1683-L1686][f1]

The primary template is a buffer with null storage.

The flockfile-enabled specialization locks the FILE, performs thread-sanitizer acquire, initializes the file buffer, and points the buffer at the file write buffer. Its grow callback advances the file write buffer by the current size, flushes when no write buffer remains, asserts a nonempty buffer, then resets the buffer to the new file write region. The destructor advances by the current size, records whether a flush is needed, performs thread-sanitizer release, unlocks the file, and flushes when needed.

<a id="u-2e6abdd51798"></a>
### `format-inl.h-file-wrapper-selection`

`template <typename F, FMT_ENABLE_IF(sizeof(F::_p) != 0 && !FMT_USE_FALLBACK_FILE)> au…` · [include/fmt/format-inl.h:L1668-L1672][f1]

Selects an Apple wrapper when the FILE type exposes the Apple buffer member and fallback is disabled, selects a glibc wrapper when it exposes the glibc read pointer and fallback is disabled, and otherwise uses the fallback wrapper through the ellipsis overload.

<a id="u-68a2e41f6f37"></a>
### `format-inl.h-format-facet-locale-facet`

`template <typename Locale> format_facet<Locale>::format_facet(Locale& loc)` · [include/fmt/format-inl.h:L169-L173][f1]

The constructor reads the char numpunct facet, stores its grouping string, and stores a one-character separator only when grouping is nonempty.

The locale specialization's do_put visits the value with a locale writer carrying the output appender, specs, separator, grouping, and decimal point.

<a id="u-089bab5d072c"></a>
### `format-inl.h-formatting-entrypoints`

`FMT_FUNC auto vformat(string_view fmt, format_args args) -> std::string` · [include/fmt/format-inl.h:L1458-L1464][f1]

vformat formats into a memory buffer and returns it as a string.

vformat_to wraps the buffer in an appender; for the exact two-character format string {} it visits the first argument with the default char formatter, otherwise it parses the format string with a format handler carrying the parse context, output, arguments, and locale.

<a id="u-40f65bba61f7"></a>
### `format-inl.h-glibc-file-wrapper`

`class glibc_file : public file_base<F>` · [include/fmt/format-inl.h:L1537-L1539][f1]

Wraps glibc FILE internals.

is_buffered is true unless the unbuffered flag is set. init_buffer returns when a write buffer already exists, otherwise forces initialization by writing and removing a character. Read and write buffer accessors expose the current glibc pointers and remaining sizes. advance_write_buffer moves the write pointer. needs_flush is false unless line buffering is set, then searches the pending write region for a newline. flush uses fflush_unlocked and throws system_error on failure.

<a id="u-728ebc12dce2"></a>
### `format-inl.h-locale-numeric-punctuation`

`template <typename Char> FMT_FUNC auto thousands_sep_impl(locale_ref loc) -> thousand…` · [include/fmt/format-inl.h:L130-L137][f1]

thousands_sep_impl obtains the locale, reads the numpunct grouping string, and returns an empty separator when grouping is empty; otherwise it returns the facet thousands separator.

decimal_point_impl returns the numpunct decimal point for the locale.

<a id="u-efc4295dee4d"></a>
### `format-inl.h-platform-file-api-wrappers`

`template <typename F> auto flockfile(F* f) -> decltype(_lock_file(f))` · [include/fmt/format-inl.h:L1482-L1484][f1]

Thin wrappers select platform file locking and unlocked character input APIs: flockfile calls _lock_file, funlockfile calls _unlock_file, and getc_unlocked calls _fgetc_nolock when the macro is not already defined.

<a id="u-04483a347540"></a>
### `format-inl.h-print-entrypoints`

`FMT_FUNC void vprint_buffered(std::FILE* f, string_view fmt, format_args args)` · [include/fmt/format-inl.h:L1764-L1768][f1]

vprint_buffered formats into a memory buffer and writes it through the FILE print helper.

vprint(FILE*,...) uses the buffered path when the selected FILE wrapper is not buffered or flockfile support is unavailable; otherwise it formats directly into a file_print_buffer. vprintln formats, appends a newline, and prints. The stdout overload delegates to the FILE overload with stdout.

<a id="u-6c58ca94f94e"></a>
### `format-inl.h-printable-code-point-checks`

`inline auto is_printable(uint16_t x, const singleton* singletons, size_t singletons_s…` · [include/fmt/format-inl.h:L1795-L1824][f1]

The 16-bit helper checks singleton upper-byte exclusions first, then walks normal ranges by subtracting encoded lengths and toggling a printable flag.

The 32-bit helper dispatches BMP and second-plane code points to the corresponding singleton and normal tables, returns false for several explicit reserved ranges, and otherwise returns true only below the Unicode maximum.

<a id="u-63924cdb404c"></a>
### `format-inl.h-rotate-right-helpers`

`FMT_INLINE auto rotr(uint32_t n, uint32_t r) noexcept -> uint32_t` · [include/fmt/format-inl.h:L198-L201][f1]

Rotates the 32-bit or 64-bit value right by the masked count.

The count is masked to 31 or 63 bits; when the masked count is zero, the expression shifts by the full width, which is undefined behavior rather than a no-op.

<a id="u-a1060c18bf90"></a>
### `format-inl.h-system-error-formatting`

`FMT_FUNC void format_system_error(detail::buffer<char>& out, int error_code, const ch…` · [include/fmt/format-inl.h:L1442-L1448][f1]

format_system_error tries to write the what() text of a std::system_error built from the error code and generic category; if any exception occurs it falls back to format_error_code.

report_system_error routes through do_report_error with format_system_error, so the newline is written only when the underlying fwrite succeeds.

<a id="u-c0431acc1027"></a>
### `allocate`

`FMT_FUNC auto allocate(size_t size) -> void*` · [include/fmt/format-inl.h:L86-L90][f1]

Allocates the requested byte count with malloc and throws std::bad_alloc when allocation returns null.

<a id="u-490e09f720fd"></a>
### `include/fmt/format-inl.h:operator==`

`template <typename F> inline auto operator==(basic_fp<F> x, basic_fp<F> y) -> bool` · [include/fmt/format-inl.h:L192-L195][f1]

Compares two basic floating-point carriers by both significand field and exponent field.

<a id="u-14c9f341a339"></a>
### `include/fmt/format-inl.h:print`

`FMT_FUNC void print(std::FILE* f, string_view text)` · [include/fmt/format-inl.h:L1752-L1761][f1]

Writes text to a FILE.

On Windows without the console override, it checks whether the descriptor is a terminal, flushes, and tries console writing first; if that fails or is not applicable it writes the text with fwrite_all.

<a id="u-6d02bd7b7d27"></a>
### `include/fmt/format-inl.h:vprint_mojibake`

`FMT_FUNC void vprint_mojibake(std::FILE* f, string_view fmt, format_args args, bool n…` · [include/fmt/format-inl.h:L1743-L1749][f1]

Windows-only helper formats into a memory buffer, optionally appends a newline, and writes the buffer to the FILE with fwrite_all.

<a id="u-fcde12893ba2"></a>
### `write_loc`

`FMT_FUNC auto write_loc(appender out, loc_value value, const format_specs& specs, loc…` · [include/fmt/format-inl.h:L144-L153][f1]

When locale support is enabled, writes a locale-aware value through a format_facet.

It uses an existing facet from the locale when present, otherwise constructs a facet for that locale and calls put; returns the facet put result.

<a id="u-72c151e3efed"></a>
### `include/fmt/format-inl.h:detail`

`FMT_FUNC detail::utf8_to_utf16::utf8_to_utf16(string_view s)` · [include/fmt/format-inl.h:L1427-L1440][f1]

Converts UTF-8 to UTF-16 by iterating code points, throwing runtime_error on invalid UTF-8, emitting one wchar_t for BMP code points and a surrogate pair for larger code points, then appending a null terminator.

<a id="u-584bdbd8244c"></a>
### `include/fmt/format-inl.h:locale_ref`

`template <typename Locale> auto locale_ref::get() const -> Locale` · [include/fmt/format-inl.h:L75-L82][f1]

Returns the stored locale when locale support is enabled and a locale pointer is present; otherwise returns a default-constructed locale.

A static assertion requires the requested type to match the detail locale type.

<a id="u-297522660db1"></a>
### `vsystem_error`

`FMT_FUNC auto vsystem_error(int error_code, string_view fmt, format_args args) -> std…` · [include/fmt/format-inl.h:L184-L188][f1]

Builds a std::system_error from the error code and generic category, using vformat to produce the message text.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
