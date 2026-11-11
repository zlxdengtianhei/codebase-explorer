# Inline implementation and stdio

**Capability.** Holds out-of-line definitions: FILE wrappers for glibc/Apple/MSVC, locale facet implementations, error formatting, UTF conversion, and vprint strategies.

format-inl.h's compiled bodies live here: platform-specific FILE wrappers, print buffering strategies, system error formatting, and Windows console fallbacks. Readers tracing link-time or platform issues should look here.

**Depends on.**

- [Float to decimal conversion](float-to-decimal-conversion.md) · graph-confirmed · 4 edge(s) · The out-of-line stdio implementation calls float conversion when producing compiled output.
- [Value writing and drivers](value-writing-and-drivers.md) · graph-confirmed · 4 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 4 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 3 edge(s)
- [Argument storage and checking](argument-storage-and-checking.md) · graph-only · 2 edge(s)
- [Core argument and buffer base](core-argument-and-buffer-base.md) · graph-only · 1 edge(s)
- [Integer decimal formatting](integer-decimal-formatting.md) · graph-only · 1 edge(s)

Parent: [Core formatting implementation](core-formatting-implementation.md)

## Units (25)

<a id="u-dc172dc27f95"></a>
### `format-inl.h-apple-file`

`class apple_file : public file_base<F>` · [include/fmt/format-inl.h:L1586-L1588][f1]

Apple-libc FILE wrapper inheriting file_base, selected by the presence of the _p member.

is_buffered checks the unbuffered flag; init_buffer allocates a buffer via a retracted putc when _p is null. Read buffer is {_p, _r}; write buffer spans from _p to the end of _bf; advance_write_buffer moves _p and decreases _w. needs_flush checks for a newline in the pending write region of line-buffered files. Note the enum comments swap the flag names (__SNBF/__SLBF), but the numeric values 1 and 2 are what matter; the code's behavior follows the values.

<a id="u-b3f92dd2532a"></a>
### `format-inl.h-error-reporting-helpers`

`FMT_FUNC void format_error_code(detail::buffer<char>& out, int error_code, string_vie…` · [include/fmt/format-inl.h:L92-L112][f1]

format_error_code clears the output buffer and writes "<message>: error <code>" entirely within the inline buffer size so no dynamic allocation occurs; the message is omitted if it would not fit, and a negative code adds a '-' counted in the size budget.

do_report_error formats via a callback into a memory_buffer and writes it plus a newline to stderr with plain fwrite (deliberately not fwrite_all, to avoid throwing). fwrite_all wraps std::fwrite and throws system_error(errno) if fewer than the requested bytes were written.

<a id="u-0b1703ce9167"></a>
### `format-inl.h-fallback-file`

`class fallback_file : public file_base<F>` · [include/fmt/format-inl.h:L1632-L1640][f1]

Generic FILE wrapper used when neither glibc nor Apple layouts are detected (or FMT_USE_FALLBACK_FILE is set).

It reports unbuffered and never needs flushing, exposes no write buffer, and emulates a one-character read buffer: unget remembers the character in next_ with has_next_=true so get_read_buffer can expose it; get clears the flag before delegating to file_base::get. All other operations inherit file_base's throwing behavior.

<a id="u-72939dd80a5f"></a>
### `format-inl.h-file-base`

`class file_base` · [include/fmt/format-inl.h:L1508-L1513][f1]

Minimal FILE wrapper holding a raw pointer with an implicit conversion back to it.

get reads one code unit via getc_unlocked and throws system_error(errno) if EOF was accompanied by ferror; unget pushes a character back and throws if ungetc returns EOF; flush throws system_error on fflush failure.

<a id="u-48bbbd2e1d6c"></a>
### `format-inl.h-file-lock-shims`

`template <typename F> auto flockfile(F* f) -> decltype(_lock_file(f))` · [include/fmt/format-inl.h:L1482-L1484][f1]

Thin template wrappers mapping flockfile/funlockfile/getc_unlocked onto the MSVC-specific _lock_file/_unlock_file/_fgetc_nolock when those are the available spellings, so system API detection works generically.

<a id="u-6144a070e24c"></a>
### `format-inl.h-file-print-buffer`

`class file_print_buffer : public buffer<char>` · [include/fmt/format-inl.h:L1683-L1686][f1]

buffer<char> that formats directly into a stdio file's own write buffer.

The primary template is a no-op null buffer for types without flockfile. The enabled specialization locks the file in the constructor (with TSan annotations under __SANITIZE_THREAD__), initializes the stdio buffer, and points the buffer at the file's write region. grow flushes when the write region is exhausted, re-derives the region, and asserts it is non-empty. The destructor advances the write pointer by the pending size, captures whether a flush is needed, unlocks the file, and flushes if needed — so output is committed even if formatting throws, and the lock is always released.

<a id="u-27fdb0b9e43e"></a>
### `format-inl.h-format-facet`

`template <typename Locale> format_facet<Locale>::format_facet(Locale& loc)` · [include/fmt/format-inl.h:L169-L173][f1]

format_facet's constructor reads grouping from the numpunct<char> facet and stores a one-character separator string only when grouping is non-empty.

The std::locale specialization of do_put dispatches the value through loc_writer configured with the stored separator, grouping, and decimal point, returning whether it handled the value.

<a id="u-2b002e0c34e0"></a>
### `format-inl.h-formatter-detail-bigint`

`FMT_CONSTEXPR auto parse(format_parse_context& ctx) -> format_parse_context::iterator` · [include/fmt/format-inl.h:L1402-L1405][f1]

Debug formatter for bigint: parse accepts no specs (returns ctx.begin()).

format emits the bigits most-significant first — the top one with {:x} and the rest zero-padded to 8 hex digits — and appends "p<exp*bigit_bits>" when exp_ > 0.

<a id="u-dd0fd18d5b6a"></a>
### `format-inl.h-get-file-dispatch`

`template <typename F, FMT_ENABLE_IF(sizeof(F::_p) != 0 && !FMT_USE_FALLBACK_FILE)> au…` · [include/fmt/format-inl.h:L1668-L1672][f1]

Selects the FILE wrapper at compile time: apple_file if the type has an _p member, glibc_file if it has _IO_read_ptr, otherwise fallback_file for plain FILE*.

FMT_USE_FALLBACK_FILE forces the fallback. file_ref is the resulting wrapper type.

<a id="u-8a2be7e7e190"></a>
### `format-inl.h-glibc-file`

`class glibc_file : public file_base<F>` · [include/fmt/format-inl.h:L1537-L1539][f1]

glibc-specific FILE wrapper inheriting file_base.

is_buffered checks the _IO_UNBUFFERED flag. init_buffer forces stdio to allocate a buffer by writing and retracting a NUL when the write pointer is at the end. Read/write buffers are exposed as spans over _IO_read_ptr.._IO_read_end and _IO_write_ptr.._IO_buf_end; advance_write_buffer bumps the write pointer. needs_flush returns true only for line-buffered files whose pending region contains a newline (memchr). flush uses fflush_unlocked and throws system_error on failure. All of this depends on glibc's _IO_FILE layout, which is why the class is selected by SFINAE on the _IO_read_ptr member.

<a id="u-dc679473725b"></a>
### `format-inl.h-is-printable`

`inline auto is_printable(uint16_t x, const singleton* singletons, size_t singletons_s…` · [include/fmt/format-inl.h:L1795-L1824][f1]

Determines whether a Unicode code point is printable using compact generated tables.

The 16-bit overload checks singleton ranges (per-upper-byte lists of excluded low bytes, scanned in order and stopped when the upper byte is smaller) then walks a run-length "normal" table, toggling a printable flag per run and stopping once the value falls before the current run. The 32-bit overload dispatches: cp < 0x10000 uses table 0, cp < 0x20000 table 1, then a series of explicit unprintable ranges (e.g. 0x2a6e0–0x2a700, 0x3347a–0xe0100, 0xe01f0–0x110000), and finally returns cp < 0x110000, so values at or above 0x110000 are unprintable.

<a id="u-ba62243fae1d"></a>
### `format-inl.h-locale-dependent-punctuation`

`template <typename Char> FMT_FUNC auto thousands_sep_impl(locale_ref loc) -> thousand…` · [include/fmt/format-inl.h:L130-L137][f1]

thousands_sep_impl fetches the numpunct facet and returns its grouping string plus separator; the separator is a default-constructed Char when grouping is empty.

decimal_point_impl returns the facet's decimal point. write_loc (locale builds only) formats a value via a format_facet: an installed facet is used, otherwise a temporary facet constructed from the locale; returns the facet's put result.

<a id="u-d2696f29fb9f"></a>
### `format-inl.h-remove-trailing-zeros`

`FMT_INLINE auto remove_trailing_zeros(uint32_t& n, int s = 0) noexcept -> int` · [include/fmt/format-inl.h:L1172-L1190][f1]

Removes trailing decimal zeros from a 32-bit (with optional starting count s) or 64-bit significand in place using multiplications by modular inverses of 5 and 25 combined with rotate-right, returning the number of zeros removed; asserts n != 0.

The 64-bit variant first checks divisibility by 10^8 and, if divisible, delegates to the 32-bit variant on the quotient with a base count of 8, which is faster. The loop removes pairs of zeros while the quotient stays within uint32/uint64 range, then possibly one more single zero.

<a id="u-f1fced95228f"></a>
### `format-inl.h-rotr`

`FMT_INLINE auto rotr(uint32_t n, uint32_t r) noexcept -> uint32_t` · [include/fmt/format-inl.h:L198-L201][f1]

Rotate-right of a 32- or 64-bit value; the rotation count is masked to the width minus one, so r==0 leaves the value unchanged (shift by full width is avoided).

<a id="u-04ce5a142b4d"></a>
### `format-inl.h-system-error-reporting`

`FMT_FUNC void format_system_error(detail::buffer<char>& out, int error_code, const ch…` · [include/fmt/format-inl.h:L1442-L1448][f1]

format_system_error writes std::system_error(ec, message).what() into the buffer; if anything throws, it falls back to format_error_code so output stays within the inline buffer.

report_system_error routes through do_report_error with format_system_error as the callback, printing to stderr with a newline, never throwing.

<a id="u-d94e3c8cb261"></a>
### `format-inl.h-vformat-entrypoints`

`FMT_FUNC auto vformat(string_view fmt, format_args args) -> std::string` · [include/fmt/format-inl.h:L1458-L1464][f1]

vformat formats into a memory_buffer via detail::vformat_to and returns it as std::string; the "{}" case is deliberately not special-cased for binary size.

detail::vformat_to special-cases a format string of exactly "{}" by visiting argument 0 with the default formatter; otherwise it parses the format string with a format_handler carrying the parse context, output appender, args, and optional locale.

<a id="u-cb1947b17352"></a>
### `format-inl.h-vprint-family`

`FMT_FUNC void vprint_buffered(std::FILE* f, string_view fmt, format_args args)` · [include/fmt/format-inl.h:L1764-L1768][f1]

vprint(f, fmt, args) chooses a strategy: if the file is unbuffered or lacks flockfile support, it formats into a memory_buffer and calls detail::print (vprint_buffered); otherwise it formats directly into a file_print_buffer that holds the stdio lock and writes into the file's buffer.

vprintln appends a newline to the formatted buffer before printing. vprint(fmt, args) forwards to stdout.

<a id="u-0d94365948e5"></a>
### `format-inl.h-write-console`

`FMT_FUNC auto write_console(int, string_view) -> bool` · [include/fmt/format-inl.h:L1728-L1728][f1]

On non-Windows builds (or with FMT_USE_WRITE_CONSOLE) it is a stub returning false.

On Windows it converts the text to UTF-16 via utf8_to_utf16 and writes it with WriteConsoleW on the given fd's OS handle, returning whether the call succeeded; conversion failure propagates from the constructor.

<a id="u-c0431acc1027"></a>
### `allocate`

`FMT_FUNC auto allocate(size_t size) -> void*` · [include/fmt/format-inl.h:L86-L90][f1]

Allocates memory with malloc and throws std::bad_alloc on failure rather than returning null.

<a id="u-490e09f720fd"></a>
### `include/fmt/format-inl.h:operator==`

`template <typename F> inline auto operator==(basic_fp<F> x, basic_fp<F> y) -> bool` · [include/fmt/format-inl.h:L192-L195][f1]

Equality of two basic_fp values comparing both significand and exponent fields.

<a id="u-14c9f341a339"></a>
### `include/fmt/format-inl.h:print`

`FMT_FUNC void print(std::FILE* f, string_view text)` · [include/fmt/format-inl.h:L1752-L1761][f1]

Writes text to a stdio file.

On Windows without FMT_USE_WRITE_CONSOLE, if the file is a TTY it first flushes the FILE and tries write_console, returning on success. Otherwise (and on all other platforms) it uses fwrite_all, which throws system_error on short writes.

<a id="u-6d02bd7b7d27"></a>
### `include/fmt/format-inl.h:vprint_mojibake`

`FMT_FUNC void vprint_mojibake(std::FILE* f, string_view fmt, format_args args, bool n…` · [include/fmt/format-inl.h:L1743-L1749][f1]

Windows-only fallback that formats into a memory buffer, optionally appends a newline, and writes it with fwrite_all under the system's legacy (non-Unicode) encoding; write errors throw.

<a id="u-72c151e3efed"></a>
### `include/fmt/format-inl.h:detail`

`FMT_FUNC detail::utf8_to_utf16::utf8_to_utf16(string_view s)` · [include/fmt/format-inl.h:L1427-L1440][f1]

Constructs utf8_to_utf16 by iterating the input's code points: an invalid code point throws std::runtime_error; code points <= 0xFFFF are pushed as one wchar_t, larger ones as a surrogate pair (0xD800/0xDC00 based).

A terminating null is appended.

<a id="u-584bdbd8244c"></a>
### `include/fmt/format-inl.h:locale_ref`

`template <typename Locale> auto locale_ref::get() const -> Locale` · [include/fmt/format-inl.h:L75-L82][f1]

Returns the stored locale, or a default-constructed locale when no pointer is stored (or when locale support is disabled).

Only the detail::locale type is accepted, enforced by static_assert.

<a id="u-297522660db1"></a>
### `vsystem_error`

`FMT_FUNC auto vsystem_error(int error_code, string_view fmt, format_args args) -> std…` · [include/fmt/format-inl.h:L184-L188][f1]

Builds a std::system_error from a generic-category error code whose message is produced by vformatting the format string with the given args.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h
