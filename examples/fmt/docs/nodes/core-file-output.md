# FILE Output Backend

**Capability.** Platform-specific FILE wrappers (glibc/Apple/fallback) selected at compile time, Windows console and UTF-16 conversion, and print/vprint dispatch to streams.

Read this when touching how formatted bytes reach a FILE or console. Wrapper selection is resolved by the get-file overloads; fwrite_all and utf8_to_utf16 support the paths.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-only · 1 edge(s)

**Depended on by.**

- [std::ostream Support](ostream-h.md) · model-inferred · 0 edge(s)

Parent: [Core Runtime & Engine](core-runtime.md)

## Units (11)

<a id="u-8a2be7e7e190"></a>
### `format-inl.h-glibc-file`

`auto is_buffered() const -> bool` · [include/fmt/format-inl.h:L1547-L1549][f1]

FILE wrapper specialized for glibc's internal FILE layout, inheriting get/unget/flush from file_base.

is_buffered() tests that the _IO_UNBUFFERED flag (value 2) is clear. init_buffer() forces buffer initialization when _IO_write_ptr has reached _IO_write_end by writing and retracting a NUL with putc_unlocked. get_read_buffer() spans _IO_read_ptr.._IO_read_end; get_write_buffer() spans _IO_write_ptr.._IO_buf_end; advance_write_buffer(size) bumps _IO_write_ptr by size. needs_flush() is true only when the _IO_LINE_BUF flag (0x200) is set and a '\n' exists in the pending write region (searched with memchr over max(pending,0) bytes). flush() uses fflush_unlocked and throws system_error("fflush failed") on failure.

**Uncertainties.**

- Relies on glibc-specific _IO_* fields; correctness on other libcs is guarded only by get_file's enable_if on sizeof(F::_IO_read_ptr).

<a id="u-dc172dc27f95"></a>
### `format-inl.h-apple-file`

`auto is_buffered() const -> bool` · [include/fmt/format-inl.h:L1596-L1598][f1]

FILE wrapper for Apple's libc, mirroring glibc_file.

is_buffered() checks the unbuffered flag (value 2) is clear. init_buffer() forces buffer setup when _p is null by writing and retracting a NUL (adjusting _p and _w). get_read_buffer() exposes _p with _r bytes; get_write_buffer() exposes _p through _bf._base + _bf._size; advance_write_buffer(size) advances _p and decrements _w. needs_flush() is true only for line-buffered mode (flag value 1) when memchr finds a '\n' in the unwritten region of width -_w. read/unget/flush come from file_base.

**Uncertainties.**

- The enum comment mapping (line_buffered=__SNBF, unbuffered=__SLBF) looks swapped relative to glibc; the numeric values 1 and 2 are what the code actually tests.

<a id="u-0b1703ce9167"></a>
### `format-inl.h-fallback-file`

`auto is_buffered() const -> bool` · [include/fmt/format-inl.h:L1640-L1640][f1]

Portable FILE wrapper used when no glibc/Apple internals are detected.

It keeps at most one pushed-back character (next_, has_next_). is_buffered(), needs_flush(), and init_buffer() are no-ops returning false/false/nothing; get_read_buffer() returns a 0- or 1-element span of next_; get_write_buffer() returns {nullptr, 0}; advance_write_buffer does nothing. get() clears has_next_ then delegates to file_base::get (throwing on read error); unget(c) delegates to file_base::unget (throwing on failure) and then caches c in next_ so the read buffer reflects it.

<a id="u-72939dd80a5f"></a>
### `format-inl.h-file-base`

`file_base(F* file) : file_(file)` · [include/fmt/format-inl.h:L1513-L1513][f1]

Minimal FILE wrapper parameterized on F (F is a template parameter so system-API detection works via sizeof members).

Holds the F* and converts to F* implicitly. get() reads one code unit with getc_unlocked and throws system_error(errno, "getc failed") on EOF with ferror set; unget(c) throws system_error("ungetc failed") if ungetc returns EOF; flush() throws system_error("fflush failed") when fflush fails. Otherwise results are returned normally (get returns the character or EOF without ferror).

<a id="u-d350fb96551f"></a>
### `format-inl.h-get-file`

`template <typename F, FMT_ENABLE_IF(sizeof(F::_p) != 0 && !FMT_USE_FALLBACK_FILE)> au…` · [include/fmt/format-inl.h:L1668-L1672][f1]

Selects the appropriate FILE wrapper at compile time via overload resolution on a dummy int argument.

Two enable_if overloads return apple_file<F> when sizeof(F::_p) != 0 and glibc_file<F> when sizeof(F::_IO_read_ptr) != 0 (both only when FMT_USE_FALLBACK_FILE is 0, which is its default); the variadic overload always matches and returns fallback_file<FILE>. file_ref is the declared type of get_file(nullptr, 0), so the first viable enable_if overload determines which wrapper the whole printing path uses on the current platform.

**Uncertainties.**

- Which overload wins on a given platform depends on the stdio struct layout visible to the compiler; FMT_USE_FALLBACK_FILE is defined to 0 here unless overridden elsewhere.

<a id="u-6144a070e24c"></a>
### `format-inl.h-file-print-buffer`

`static void grow(buffer<char>& base, size_t)` · [include/fmt/format-inl.h:L1695-L1703][f1]

The generic file_print_buffer template is inert: its constructor ignores the FILE* and creates an empty unowned buffer, so printing to a FILE without lock support takes a different path.

The enabled specialization (only when has_flockfile<F> holds) is a buffer<char> writing directly into the stream's internal write buffer. The constructor locks the file (flockfile, with __tsan_acquire under thread sanitizers), initializes the buffer (init_buffer), and points the base buffer at the stream's write region. grow(), invoked when the buffer fills, advances the write pointer by the consumed size, flushes if the remaining region is empty (asserting a non-empty region afterwards), and re-seats the buffer. The destructor advances the write pointer by the unconsumed size, remembers whether a line-buffer flush is needed, releases the lock (__tsan_release, then funlockfile), and only then performs fflush when needed — so the flush happens unlocked, after the destructor's flush decision.

calls: [flockfile][f1]

**Uncertainties.**

- If grow's FMT_ASSERT fails or a flush throws, lock-release behavior depends on stack unwinding through the destructor and is not provable from this excerpt.

<a id="u-0d94365948e5"></a>
### `format-inl.h-write-console`

`FMT_FUNC auto write_console(int, string_view) -> bool` · [include/fmt/format-inl.h:L1728-L1728][f1]

Windows console output with UTF-16 conversion plus the legacy fallback.

The non-Windows (or FMT_USE_WRITE_CONSOLE) write_console is a stub returning false, signaling the caller to use ordinary fwrite. The Windows version converts text via utf8_to_utf16 and calls WriteConsoleW on _get_osfhandle(fd), returning whether the call succeeded; any conversion error from utf8_to_utf16 propagates as std::runtime_error. vprint_mojibake (Windows only) formats into a memory_buffer, appends '\n' when newline is true, and writes with fwrite_all, assuming the console's legacy non-Unicode encoding — hence its name; a write failure throws system_error via fwrite_all.

<a id="u-14c9f341a339"></a>
### `include/fmt/format-inl.h:print`

`FMT_FUNC void print(std::FILE* f, string_view text)` · [include/fmt/format-inl.h:L1752-L1761][f1]

Writes preformatted text to a FILE, with a Windows console special case.

On Windows without FMT_USE_WRITE_CONSOLE, if the descriptor is a terminal (_isatty) it first fflushes the stream (to preserve ordering) and tries write_console; if that succeeds it returns, otherwise (or when not a tty) it falls through. The normal path is fwrite_all(text.data(), text.size(), f), which throws system_error on short writes.

calls: [grp:format-inl.h-write-console][f1]

<a id="u-2eff762cb4cf"></a>
### `include/fmt/format-inl.h:vprint`

`FMT_FUNC void vprint(std::FILE* f, string_view fmt, format_args args)` · [include/fmt/format-inl.h:L1770-L1775][f1]

Prints formatted output to a FILE, choosing between a direct-to-stream-buffer path and a buffered path.

If the stream reports unbuffered (file_ref(f).is_buffered() false) or locking is unavailable (has_flockfile<>() false), it delegates to vprint_buffered, which formats into a memory_buffer and detail::print's it. Otherwise it constructs a file_print_buffer (which locks the stream) and formats straight into the stream's internal buffer; flushing/unlocking happens in that buffer's destructor. Exceptions from formatting or writing propagate.

uses: [grp:format-inl.h-file-print-buffer][f1]; calls: [include/fmt/format-inl.h:print](core-file-output.md#u-14c9f341a339)

**Uncertainties.**

- vprintln builds the message in a memory buffer, appends '\n', and detail::print's it; the file_print_buffer fast path is not used for println. The zero-argument vprint(fmt, args) forwards to vprint(stdout, ...).

<a id="u-72c151e3efed"></a>
### `include/fmt/format-inl.h:detail`

`FMT_FUNC detail::utf8_to_utf16::utf8_to_utf16(string_view s)` · [include/fmt/format-inl.h:L1427-L1440][f1]

utf8_to_utf16 constructor: converts a UTF-8 string_view to a UTF-16 wchar_t buffer.

It walks code points with for_each_codepoint; an invalid code point throws std::runtime_error("invalid utf8"). Code points <= 0xFFFF are pushed directly; larger ones are encoded as a surrogate pair (0xD800 + high 10 bits, 0xDC00 + low 10 bits) after subtracting 0x10000. A terminating null is appended at the end, so c_str() is safe. Exceptions from the conversion propagate; the partially filled buffer is discarded.

<a id="u-e586611bfc56"></a>
### `fwrite_all`

`inline void fwrite_all(const void* ptr, size_t count, FILE* stream)` · [include/fmt/format-inl.h:L124-L128][f1]

Writes count bytes from ptr to stream with std::fwrite.

If fewer bytes than requested were written, it throws system_error carrying the current errno with the message 'cannot write to file'; on full success it returns normally.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h