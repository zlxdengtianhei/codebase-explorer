# OS file and C API

**Capability.** File and stream abstractions: RAII file/descriptor wrappers, buffered output streams, pipes, Windows errors, and the C API.

Operating-system layer: buffered_file, file, ostream, pipe creation, and Windows-specific error plumbing, plus extern-C wrappers exposing fmt to C. Readers implementing file-backed output or C interop come here.

**Depends on.**

- [Format argument infrastructure](format-argument-infrastructure.md) · graph-confirmed · 1 edge(s) · The OS/C API layer uses the argument infrastructure to pack arguments for its formatting entry points.
- [Spec parsing and printf mapping](spec-parsing-and-printf-mapping.md) · graph-only · 1 edge(s)

Parent: [fmt formatting library](fmt-formatting-library.md)

## Units (27)

<a id="u-2d3228c7b530"></a>
### `fmt-c.cc-c-api-entry-points`

`int fmt_vformat(char* buffer, size_t size, const char* fmt, const fmt_arg* args, size…` · [src/fmt-c.cc:L38-L49][f1]

Extern-C wrappers exposing fmt formatting to C: fmt_vformat formats into a caller buffer and returns the untruncated formatted size, while fmt_vprint writes to a FILE stream and returns 0 on success.

Both first convert the C argument array via convert_c_format_args and propagate its fmt_error_invalid_arg return on bad counts or types. The formatting call is wrapped in FMT_TRY/FMT_CATCH(...): any exception is swallowed and the generic fmt_error code is returned instead. fmt_vformat's return is the result.size from vformat_to_n, cast to int, so sizes beyond INT_MAX would wrap (implementation-defined).

calls: [convert_c_format_args](os-file-and-c-api.md#u-a6a4b5f8fb66)

<a id="u-dc63f141305f"></a>
### `os.cc-buffered-file-lifecycle-and-descriptor`

`buffered_file::~buffered_file() noexcept` · [src/os.cc:L170-L173][f2]

RAII wrapper over a FILE*: the filename/mode constructor retries fopen and throws system_error(errno, "cannot open file {}") on failure; the destructor closes an open file and, if fclose fails, reports via report_system_error rather than throwing (it is noexcept).

close() is idempotent (returns if already closed), nulls file_ before checking the result, and throws system_error on fclose failure. descriptor() obtains fileno through three platform paths (FMT_POSIX_CALL with a fileno-macro undef under FMT_HAS_SYSTEM, _fileno on _WIN32, plain fileno otherwise) and throws system_error if the result is -1.

**Notes.**

- failure: Destructor swallows close errors by reporting them, so destruction never throws.

<a id="u-1950a42eb84f"></a>
### `os.cc-convert-rwcount-variants`

`inline unsigned convert_rwcount(size_t count)` · [src/os.cc:L71-L73][f2]

Platform-dependent adapter clamping the size_t byte count passed to read/write.

On Windows (47) it returns the count cast to unsigned, capped at UINT_MAX to avoid unsigned-count overflow; on POSIX (66) it is the identity. Exactly one definition compiles per platform, selected by _WIN32 vs FMT_USE_FCNTL.

<a id="u-fb826cd263d9"></a>
### `os.cc-dup-family`

`auto file::dup(int fd) -> file` · [src/os.cc:L288-L296][f2]

Descriptor duplication: static dup(fd) duplicates an external fd without EINTR retry and throws system_error naming the fd on -1, returning a new file.

dup2(fd) retries and throws system_error naming both descriptors on -1. The two-argument dup2(fd, ec) is the noexcept variant: on -1 it writes std::error_code(errno, std::generic_category()) into ec instead of throwing, leaving ec untouched on success.

<a id="u-78230a27039e"></a>
### `os.cc-file-open-close-lifecycle`

`file::file(cstring_view path, int oflag)` · [src/os.cc:L216-L227][f2]

RAII wrapper over a POSIX fd: the constructor opens with FMT_RETRY and default mode 0666, throwing system_error(errno, "cannot open file {}") on failure; on MSVC Windows it instead converts the path to UTF-16 and delegates to open_windows_file.

The destructor closes a valid fd and reports (never throws) on close failure, deliberately not retrying on EINTR. close() is idempotent for fd_ == -1, sets fd_ = -1 before checking the result, and throws system_error on failure.

**Notes.**

- contract: Close is not retried on EINTR by design, per the cited kernel discussion.

<a id="u-5eac500ea024"></a>
### `os.cc-file-read-write`

`auto file::read(void* buffer, size_t count) -> size_t` · [src/os.cc:L272-L278][f2]

Byte-level I/O on the raw descriptor: read and write both retry the POSIX call on EINTR via FMT_RETRY, clamp the count through convert_rwcount, and throw system_error(errno, "cannot read/write from/to file") if the result is negative; otherwise they return the count cast to unsigned size_t.

Partial transfers are returned as-is, not treated as errors.

<a id="u-47c2cb2a8222"></a>
### `os.cc-ostream`

`void ostream::grow(buffer<char>& buf, size_t)` · [src/os.cc:L380-L382][f2]

A file-backed output buffer: grow flushes when the buffer is completely full (size == capacity), delegating to the ostream's flush.

The constructor opens the file with the given oflag and installs a heap-allocated buffer of params.buffer_size bytes. The move constructor steals the buffer and file, then resets the source to a null, empty buffer so its destructor's delete[] is safe. The destructor flushes and deletes the buffer; flush failures inside the destructor propagate per flush's behavior, which is not shown in this file.

**Notes.**

- side_effect: Constructor leaks nothing but allocates with new[]; only the destructor deletes, so a moved-from object must not double-delete (handled by nulling the source).

**Uncertainties.**

- flush() and the buffer<char> base are declared elsewhere; their exception behavior during the destructor is not visible here.

<a id="u-b9bad2b0fb86"></a>
### `os.cc-pipe-constructor`

`pipe::pipe()` · [src/os.cc:L342-L346][f2]

Creates an anonymous pipe into two file members.

On Windows it passes a 65536-byte capacity and _O_BINARY to mimic Linux 2.6.11+ defaults; on POSIX it calls pipe(fds) without EINTR retry. If the pipe call returns nonzero it throws system_error(errno, "cannot create pipe"); otherwise read_end and write_end adopt fds[0] and fds[1], which the comment asserts cannot throw.

<a id="u-b2055b3f53ae"></a>
### `os.cc-system-message`

`class system_message` · [src/os.cc:L75-L76][f2]

Windows-only RAII helper that formats a Win32 error code into an owned wide-character message.

The constructor calls FormatMessageW with ALLOCATE_BUFFER|FROM_SYSTEM|IGNORE_INSERTS into message_; on success it trims trailing whitespace (space, newline, CR, tab, NUL) by shrinking result_. The destructor frees the buffer with LocalFree; copying and assignment are deleted. operator bool reports success (result_ != 0) and the string_view conversion exposes the trimmed message; a failed FormatMessageW yields a false object with a null message_, so the view must not be used in that case.

**Notes.**

- failure: If FormatMessageW fails, result_ stays 0 and message_ stays nullptr; bool conversion is false.

**Uncertainties.**

- Whether message_ can be non-null with result_ == 0 is not established by the source.

<a id="u-6d322f40605a"></a>
### `os.cc-utf8-system-category`

`class utf8_system_category final : public std::error_category` · [src/os.cc:L107-L109][f2]

Windows-only std::error_category subclass named "system" whose message() converts a Win32 error code to a UTF-8 std::string.

It builds a system_message; if formatting succeeded and to_utf8 conversion succeeds, it returns the converted string, otherwise it falls back to the literal "unknown error". name() is a trivial noexcept override returning the category name. A single static instance is created by system_category (symbol 69).

uses: [os.cc-system-message](os-file-and-c-api.md#u-b2055b3f53ae)

<a id="u-f813ef1199a5"></a>
### `os.cc-windows-error-reporting`

`FMT_API const std::error_category& system_category() noexcept` · [src/os.cc:L136-L139][f2]

Windows-only error plumbing: system_category returns a static utf8_system_category instance; vwindows_error builds a std::system_error from an error code plus a formatted message; detail::format_windows_error appends "<message>: <system text>" to a char buffer, falling back to format_error_code when the message cannot be obtained or any exception escapes the FMT_TRY block; report_windows_error reports via do_report_error and is noexcept.

format_windows_error is noexcept, so the catch-all is what guarantees exceptions never escape; the fallback still emits error code and message when FormatMessageW or UTF-8 conversion fails.

uses: [os.cc-system-message](os-file-and-c-api.md#u-b2055b3f53ae); calls: [os.cc-windows-error-reporting](os-file-and-c-api.md#u-f813ef1199a5)

<a id="u-bd1b8fcafdbf"></a>
### `os.h-basic-cstring-view`

`basic_cstring_view(const std::basic_string<Char>& s) : data_(s.c_str())` · [include/fmt/os.h:L107-L107][f3]

Non-owning reference to a null-terminated string, constructible from a const Char* or a std::basic_string (storing s.c_str()); c_str() returns the stored pointer.

Aliased as cstring_view/wcstring_view.

<a id="u-6d84f5baae28"></a>
### `os.h-buffer-size`

`struct buffer_size` · [include/fmt/os.h:L320-L321][f3]

A constexpr value holder defaulting to 0 whose operator=(size_t) returns a new buffer_size carrying the value, enabling named-parameter syntax like buffer_size=4096 in ostream parameter packs.

<a id="u-cb6b56653b39"></a>
### `os.h-buffered-file`

`class buffered_file` · [include/fmt/os.h:L167-L173][f3]

RAII wrapper around a FILE*.

Default construction holds nullptr; move construction/assignment steal the handle and null the source (move assignment closes the current file first, so it may throw). Copying is deleted. The destructor closes any represented file. Opening by filename/mode, close, and descriptor() are FMT_API (defined out of header). print() builds a vargs pack and chooses fmt::vprint_buffered when detail::is_locking<T...>() holds, otherwise fmt::vprint. get() exposes the FILE*.

<a id="u-d923c0f45c3e"></a>
### `os.h-error-helpers`

`template <typename... T> auto windows_error(int error_code, string_view message, cons…` · [include/fmt/os.h:L151-L155][f3]

On Windows, windows_error builds a std::system_error whose description combines the formatted message with the system message for the given Windows error code, via vwindows_error; on non-Windows platforms system_category() simply returns std::system_category().

<a id="u-ecf01a5f5a02"></a>
### `os.h-file`

`class FMT_API file` · [include/fmt/os.h:L224-L229][f3]

RAII wrapper around a POSIX/Windows file descriptor; a closed file is descriptor -1.

The oflag enum exposes RDONLY/WRONLY/RDWR/CREATE/APPEND/TRUNC mapped through FMT_POSIX. Default construction yields -1; move operations steal the descriptor and reset the source to -1 (move assignment closes first and may throw). Copying is deleted; the destructor closes. Opening, close, size, read, write, dup, dup2 (throwing and error_code overloads), fdopen (yielding a buffered_file and detaching), and the Windows-only wide-path open are FMT_API declarations whose bodies are out of header; per the class comment, non-noexcept methods may throw fmt::system_error and double-close may crash on Windows.

<a id="u-20235cc3b9cf"></a>
### `os.h-ostream`

`class ostream : private detail::buffer<char>` · [include/fmt/os.h:L361-L373][f3]

Fast single-threaded buffered output stream deriving privately from detail::buffer<char> and owning a file.

Construction (FMT_API) takes a path and ostream_params; grow, move, and the destructor are FMT_API. flush() is a no-op when the buffer is empty, otherwise writes the buffered data to the file and clears the buffer. close() flushes then closes the file (so it can throw). Conversion to writer exposes the buffer, and print() formats via vformat_to into the buffer through an appender. Writing from multiple threads without external synchronization is a data race per the class comment.

<a id="u-7b1cd5c0076b"></a>
### `os.h-ostream-params`

`struct ostream_params` · [include/fmt/os.h:L330-L334][f3]

Aggregates open flags (default WRONLY|CREATE|TRUNC) and buffer size (BUFSIZ or 32768, whichever is larger).

Variadic constructors peel a trailing int oflag or buffer_size off the parameter pack, delegating to the rest, so output_file accepts flags and buffer_size in any order; an Intel-compiler workaround adds single-argument constructors.

<a id="u-f2b0cc404380"></a>
### `system_error`

`template <typename... T> auto system_error(int error_code, format_string<T...> fmt, T…` · [include/fmt/format.h:L4585-L4589][f4]

system_error formats the message with the given args and returns a std::system_error carrying the code, via the out-of-line vsystem_error.

<a id="u-edce9227640e"></a>
### `include/fmt/os.h:FMT_BEGIN_EXPORT`

`class is most useful as a parameter type for functions that wrap C APIs. */ template …` · [include/fmt/os.h:L79-L107][f3]

A non-owning reference to a null-terminated character string, constructible from a C string or a std::basic_string, exposing the stored pointer via c_str().

It stores only the pointer; the std::string overload relies on the caller keeping the string alive, since only the pointer is retained. Intended as a parameter type for wrappers of C APIs that require NUL-terminated input.

group: [os.h-basic-cstring-view](os-file-and-c-api.md#u-bd1b8fcafdbf)

<a id="u-b42ed80b5079"></a>
### `output_file`

`template <typename... T> inline auto output_file(cstring_view path, T... params) -> o…` · [include/fmt/os.h:L412-L415][f3]

Opens a file for writing and returns an ostream configured by the parameter pack (open flags as int, buffer_size=...), forwarded into ostream_params.

<a id="u-b66f0f4d505c"></a>
### `pipe`

`struct FMT_API pipe` · [include/fmt/os.h:L306-L313][f3]

Creates a pipe whose read_end and write_end file objects are set up for reading and writing respectively; construction is FMT_API.

<a id="u-a6a4b5f8fb66"></a>
### `convert_c_format_args`

`static int convert_c_format_args( fmt::basic_format_arg<fmt::format_context>* format_…` · [src/fmt-c.cc:L14-L36][f1]

Translates an array of C API argument descriptors into fmt basic_format_arg entries, validating as it goes.

Returns fmt_error_invalid_arg immediately if num_args exceeds 16 or if any descriptor's type tag is not one of the nine recognized cases (int, uint, bool, char, float, double, long double, cstring, pointer); otherwise writes each value into the corresponding slot and returns 0. The switch default is the only failure path; no exceptions are thrown here.

**Notes.**

- contract: Caller must supply a format_args array with capacity for at least max_c_format_args (16) entries.

**Uncertainties.**

- Behavior of fmt_arg values for type tags not listed cannot be verified beyond the default rejection path.

<a id="u-2cc677da0e3e"></a>
### `src/os.cc:file (4)`

`auto file::size() const -> long long` · [src/os.cc:L246-L270][f2]

Returns the file size in bytes.

On Windows it uses GetFileSize with a 64-bit result assembled from the two DWORD halves; INVALID_FILE_SIZE is only an error if GetLastError() != NO_ERROR, otherwise it is a legitimate low word. On POSIX it fstats and throws system_error(errno, "cannot get file attributes") if fstat returns -1; a static_assert guarantees long long can hold st_size.

**Notes.**

- failure: Windows path throws windows_error only when GetFileSize fails with a real error, not on a size whose low word equals INVALID_FILE_SIZE.

<a id="u-a684c6071862"></a>
### `src/os.cc:file (10)`

`auto file::fdopen(const char* mode) -> buffered_file` · [src/os.cc:L314-L328][f2]

Associates a FILE stream with the owned descriptor via fdopen and returns it as a buffered_file, transferring ownership by setting fd_ = -1 only after fdopen succeeds.

On failure it throws system_error(errno, "cannot associate stream with file descriptor"); no EINTR retry is done. On MinGW with _POSIX_ defined it calls ::fdopen directly instead of the FMT_POSIX_CALL wrapper.

<a id="u-66708dbcce27"></a>
### `src/os.cc:file (11)`

`file file::open_windows_file(wcstring_view path, int oflag)` · [src/os.cc:L331-L339][f2]

MSVC-Windows-only helper opening a wide-character path via _wsopen_s with _SH_DENYNO and the default 0666 mode.

If the returned fd is -1 it throws system_error using the _wsopen_s error value and a UTF-8 rendition of the path; otherwise it returns a file owning the fd. Called by the file constructor after UTF-8-to-UTF-16 path conversion.

<a id="u-9f2acaa51192"></a>
### `getpagesize`

`auto getpagesize() -> long` · [src/os.cc:L361-L377][f2]

Returns the OS memory page size as a long.

On Windows it reads SYSTEM_INFO.dwPageSize; on VxWorks kernel it calls POSIX getpagesize; otherwise it uses sysconf(_SC_PAGESIZE), throwing system_error(errno, "cannot get memory page size") if the result is negative. Compiled only when FMT_USE_FCNTL and not MSDOS.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/fmt-c.cc
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/os.cc
[f3]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/os.h
[f4]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
