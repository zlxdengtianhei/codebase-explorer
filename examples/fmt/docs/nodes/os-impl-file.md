# File I/O Implementation

**Capability.** Implements descriptor open/read/write/dup/pipe/ostream operations with EINTR retry and Windows count clamping via convert_rwcount, plus the pipe factory.

Consult for the actual syscalls behind the os.h wrappers; every FMT_RETRY loop and the platform split live here.

**Depends on.**

- [OS Header Interface](os-interface.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [OS Header Interface](os-interface.md) · graph-only · 1 edge(s)

Parent: [OS & File I/O](os.md)

## Units (23)

<a id="u-c8edc3962b63"></a>
### `os.cc-pipe`

`pipe::pipe()` · [src/os.cc:L342-L346][f1]

Creates a connected pipe as a pair of file objects.

On Windows it calls pipe(fds, 65536, _O_BINARY) to match the default capacity of Linux 2.6.11+; elsewhere it calls pipe(fds) without retrying, since pipe does not return EINTR. A nonzero result throws system_error(errno, "cannot create pipe"). On success read_end and write_end are assigned file objects for fds[0] and fds[1]; the code notes these assignments do not throw.

<a id="u-7270c625e217"></a>
### `convert_rwcount`

`inline unsigned convert_rwcount(size_t count)` · [src/os.cc:L71-L73][f1]

Windows-only clamp for read/write byte counts: because the OS API's count argument is unsigned, a size_t count is cast to unsigned, capped at UINT_MAX when larger.

This prevents integer overflow for oversized requests, at the cost of a single call transferring at most UINT_MAX bytes.

<a id="u-646d32a10fcd"></a>
### `src/os.cc:convert_rwcount`

`inline auto convert_rwcount(size_t count) -> size_t` · [src/os.cc:L127-L127][f1]

Non-Windows FMT_USE_FCNTL counterpart of the Windows clamp: it returns the count unchanged as size_t, since POSIX read/write already take size_t.

The enclosing region defines rwresult as ssize_t for these platforms.

<a id="u-d6f139e3bc1e"></a>
### `src/os.cc:buffered_file`

`buffered_file::~buffered_file() noexcept` · [src/os.cc:L170-L173][f1]

Destructor for the buffered FILE wrapper.

If a FILE handle is held, it fcloses it via FMT_SYSTEM; on close failure it calls report_system_error(errno, "cannot close file") instead of throwing, since the destructor is noexcept. An empty wrapper is destroyed without action.

<a id="u-df5a61e7ef1a"></a>
### `src/os.cc:buffered_file (2)`

`buffered_file::buffered_file(cstring_view filename, cstring_view mode)` · [src/os.cc:L175-L181][f1]

Opens a buffered file.

It retries fopen(filename, mode) with FMT_RETRY_VAL until it returns non-null (retrying on EINTR); if it still yields null, it throws system_error with the current errno and message "cannot open file <filename>". On success the wrapper owns the FILE handle.

**Notes.**

- failure: fopen failure is fatal via thrown system_error; only transient EINTR is retried.

<a id="u-a87f2086d344"></a>
### `src/os.cc:buffered_file (3)`

`void buffered_file::close()` · [src/os.cc:L183-L189][f1]

Closes the buffered file explicitly.

If no handle is held it returns immediately. Otherwise it fcloses the handle, clears file_ before checking the result, and throws system_error(errno, "cannot close file") when fclose failed; after a throw or success the wrapper is left empty.

**Notes.**

- side_effect: file_ is set to null before the error check, so a failed close still leaves the wrapper empty.

<a id="u-065c8e13ace8"></a>
### `src/os.cc:buffered_file (4)`

`auto buffered_file::descriptor() const -> int` · [src/os.cc:L191-L206][f1]

Returns the integer descriptor of the wrapped FILE handle.

Under FMT_HAS_SYSTEM it goes through FMT_POSIX_CALL(fileno(...)), first undefining fileno when it is a macro (OpenBSD); on _WIN32 it uses _fileno, otherwise plain fileno. A result of -1 throws system_error(errno, "cannot get file descriptor"); otherwise the descriptor is returned.

<a id="u-3b2dd84abd55"></a>
### `src/os.cc:file`

`file::file(cstring_view path, int oflag)` · [src/os.cc:L216-L227][f1]

Opens a file descriptor for path with caller-supplied oflags.

On Windows/MSVC it first sets fd_ to -1, converts the UTF-8 path to UTF-16, and delegates to file::open_windows_file via assignment; on other platforms (and MinGW) it retries FMT_POSIX_CALL(open(path, oflag, default_open_mode)) where default_open_mode is S_IRUSR|S_IWUSR|S_IRGRP|S_IWGRP|S_IROTH|S_IWOTH (group/other bits defined as 0 on Windows). If open still returns -1 it throws system_error(errno, "cannot open file <path>").

uses: [src/os.cc:file (11)](os-impl-file.md#u-66708dbcce27)

**Uncertainties.**

- Whether the Windows branch actually throws on failure depends on open_windows_file, documented separately.

<a id="u-c483f8b71181"></a>
### `src/os.cc:file (2)`

`file::~file() noexcept` · [src/os.cc:L229-L234][f1]

Destructor for the RAII file descriptor.

If a descriptor is held and the POSIX close call fails, it reports via report_system_error(errno, "cannot close file") rather than throwing, because the destructor is noexcept. Per the code comment, close is deliberately not retried on EINTR.

<a id="u-d3e320a10fdf"></a>
### `src/os.cc:file (3)`

`void file::close()` · [src/os.cc:L236-L244][f1]

Explicit close for the descriptor.

If fd_ is -1 it returns; otherwise it calls close once (never retried on EINTR), sets fd_ to -1 before checking the result, and throws system_error(errno, "cannot close file") on failure. The wrapper ends empty regardless of outcome.

<a id="u-2cc677da0e3e"></a>
### `src/os.cc:file (4)`

`auto file::size() const -> long long` · [src/os.cc:L246-L270][f1]

Returns the file size as long long.

On Windows it obtains the handle via _get_osfhandle and uses GetFileSize (chosen over GetFileSizeEx for old _WIN32_WINNT MinGW defaults): if the low part is INVALID_FILE_SIZE and GetLastError is not NO_ERROR it throws windows_error(error, "cannot get file size"); the size is assembled as upper<<32 | lower. Elsewhere it fstats the descriptor, throwing system_error(errno, "cannot get file attributes") on -1, with a static_assert that long long can hold st_size.

**Uncertainties.**

- Whether INVALID_FILE_SIZE with NO_ERROR is a legitimate 4 GiB boundary case is not resolved in this code; it falls through and returns the assembled value.

<a id="u-4681d12c08d4"></a>
### `src/os.cc:file (5)`

`auto file::read(void* buffer, size_t count) -> size_t` · [src/os.cc:L272-L278][f1]

Reads up to count bytes into buffer, retrying through EINTR via FMT_RETRY on the POSIX read (count passed through convert_rwcount for the Windows unsigned limit).

If the final result is negative it throws system_error(errno, "cannot read from file"); otherwise the byte count is returned as unsigned.

uses: [convert_rwcount](os-impl-file.md#u-7270c625e217)

<a id="u-282a02e28abc"></a>
### `src/os.cc:file (6)`

`auto file::write(const void* buffer, size_t count) -> size_t` · [src/os.cc:L280-L286][f1]

Writes count bytes from buffer, retrying through EINTR via FMT_RETRY on the POSIX write, with count converted by convert_rwcount where the OS count type is unsigned.

A negative final result throws system_error(errno, "cannot write to file"); success returns the written byte count as unsigned.

<a id="u-7b8e15e3f9c2"></a>
### `src/os.cc:file (7)`

`auto file::dup(int fd) -> file` · [src/os.cc:L288-L296][f1]

Static factory duplicating an existing descriptor.

It calls dup once without retrying (the comment notes dup does not return EINTR); a -1 result throws system_error(errno, "cannot duplicate file descriptor <fd>"). On success it wraps the new descriptor in a file and returns it by value.

<a id="u-e1c55fbe51fe"></a>
### `src/os.cc:file (8)`

`void file::dup2(int fd)` · [src/os.cc:L298-L306][f1]

Duplicates this file's descriptor onto fd using dup2, retried through EINTR with FMT_RETRY.

A final -1 result throws system_error(errno, "cannot duplicate file descriptor <fd_> to <fd>"); on success fd now refers to the same open file as fd_.

<a id="u-0495e98fab20"></a>
### `src/os.cc:file (9)`

`void file::dup2(int fd, std::error_code& ec) noexcept` · [src/os.cc:L308-L312][f1]

Noexcept variant of dup2 that reports failure through an output error_code instead of throwing.

It retries dup2(fd_, fd) through EINTR; if the final result is -1 it sets ec to error_code(errno, std::generic_category()), otherwise ec is left untouched (assumed cleared by the caller).

<a id="u-a684c6071862"></a>
### `src/os.cc:file (10)`

`auto file::fdopen(const char* mode) -> buffered_file` · [src/os.cc:L314-L328][f1]

Associates a FILE stream with the descriptor and transfers ownership.

On MinGW with _POSIX_ it calls ::fdopen directly, otherwise FMT_POSIX_CALL(fdopen) (not retried; fdopen does not return EINTR). A null result throws system_error(errno, "cannot associate stream with file descriptor"). On success it builds a buffered_file around the FILE*, sets fd_ to -1 so the destructor will not close the descriptor, and returns the buffered_file.

<a id="u-66708dbcce27"></a>
### `src/os.cc:file (11)`

`file file::open_windows_file(wcstring_view path, int oflag)` · [src/os.cc:L331-L339][f1]

Windows/MSVC-only open using a wide path.

It calls _wsopen_s with _SH_DENYNO and default_open_mode; if the produced fd is -1 it throws system_error(err, "cannot open file <path>"), converting the wide path to UTF-8 for the message. Otherwise it wraps and returns the descriptor.

**Notes.**

- failure: err is the _wsopen_s error code passed to system_error, not necessarily errno.

<a id="u-9f2acaa51192"></a>
### `getpagesize`

`auto getpagesize() -> long` · [src/os.cc:L361-L377][f1]

Returns the memory page size as long.

On Windows it reads SYSTEM_INFO::dwPageSize via GetSystemInfo. On VxWorks kernel builds it calls the getpagesize syscall; otherwise sysconf(_SC_PAGESIZE). A negative size throws system_error(errno, "cannot get memory page size"). Compiled out under __MSDOS__.

<a id="u-2ba95821efed"></a>
### `src/os.cc:ostream`

`void ostream::grow(buffer<char>& buf, size_t)` · [src/os.cc:L380-L382][f1]

Buffer-growth callback for the output-stream buffer.

It ignores the requested new size and, only when the buffer is completely full (size == capacity), flushes the buffer by casting it to its derived ostream and calling flush, which drains the buffer to the underlying file so writing can proceed.

<a id="u-4df302ebdc51"></a>
### `src/os.cc:ostream (2)`

`ostream::ostream(cstring_view path, const detail::ostream_params& params) : buffer<ch…` · [src/os.cc:L384-L387][f1]

Opens an output stream to a path.

It initializes the buffer<char> base with grow as the flush callback, constructs file_ with the caller-supplied oflag from params, then allocates a new char array of params.buffer_size and installs it as the buffer via set. The stream is ready to buffer writes after construction.

contract: [src/os.cc:ostream](os-impl-file.md#u-2ba95821efed)

<a id="u-96e41e83f8f1"></a>
### `src/os.cc:ostream (3)`

`ostream::ostream(ostream&& other) noexcept : buffer<char>(grow, other.data(), other.s…` · [src/os.cc:L389-L394][f1]

Move constructor taking over another stream's buffer and file.

It constructs the buffer base from other's data/size/capacity with the same grow callback and moves other's file_. It then clears other's state and sets its buffer to (nullptr, 0), leaving the source empty so its destructor flushes nothing and frees nothing.

<a id="u-d6ac7306d738"></a>
### `src/os.cc:ostream (4)`

`ostream::~ostream()` · [src/os.cc:L396-L399][f1]

Destructor that flushes any buffered output to the underlying file and then frees the buffer array with delete[] on data().

Exceptions from flush are not caught here; the destructor is not declared noexcept in this source.

**Uncertainties.**

- Whether the implicit noexcept(false) destructor can leak on a throwing flush is not resolvable from this source alone.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/os.cc