# C API and OS File Operations

**Capability.** Implements C formatting API, file read/write/duplication, pipes, Windows error categories, and ostream file handling.

Use this module for C API and OS-level file operations. The units describe formatting through C, file I/O, pipes, Windows errors, and ostream file support.

Parent: [C API and OS File Layer](c-api-and-os-file-layer.md)

## Units (22)

<a id="u-2becbe9607d2"></a>
### `fmt-c.cc-fmt-vformat`

`int fmt_vformat(char* buffer, size_t size, const char* fmt, const fmt_arg* args, size…` · [src/fmt-c.cc:L38-L49][f1]

Formats into a caller buffer through the C API, returning the formatted size or an error code.

It first converts up to 16 C arguments; conversion failure is returned immediately. Formatting runs inside a catch-all block, and any exception is swallowed and reported as fmt_error.

<a id="u-6dc59ba69141"></a>
### `fmt-c.cc-fmt-vprint`

`int fmt_vprint(FILE* stream, const char* fmt, const fmt_arg* args, size_t num_args)` · [src/fmt-c.cc:L54-L64][f1]

Prints formatted output to a FILE stream through the C API, returning 0 on success or an error code.

It first converts up to 16 C arguments; conversion failure is returned immediately. Printing runs inside a catch-all block, and any exception is swallowed and reported as fmt_error.

<a id="u-d6fbfe4a8444"></a>
### `os.cc-convert-rwcount`

`inline unsigned convert_rwcount(size_t count)` · [src/os.cc:L71-L73][f2]

Normalizes a byte count for the platform read/write call.

On Windows it returns an unsigned value clamped to UINT_MAX; on the non-Windows fcntl path it returns the size_t count unchanged.

<a id="u-b3a15a072321"></a>
### `os.cc-format-windows-error`

`void detail::format_windows_error(detail::buffer<char>& out, int error_code, const ch…` · [src/os.cc:L147-L159][f2]

Appends a Windows error description to a buffer without throwing.

It tries to obtain a system message and convert it to UTF-8; on success it appends "message: converted text" and returns. If the message is unavailable, conversion fails, or any exception is caught, it falls back to format_error_code with the original code and message.

<a id="u-b9bad2b0fb86"></a>
### `os.cc-pipe-constructor`

`pipe::pipe()` · [src/os.cc:L342-L346][f2]

Creates a pipe and stores both ends as file objects.

On Windows it requests a 65536-byte binary pipe; elsewhere it calls pipe without retry. A nonzero result throws a system_error with errno. After success it assigns the read and write descriptors to read_end and write_end; the source notes those assignments do not throw.

<a id="u-b2055b3f53ae"></a>
### `os.cc-system-message`

`class system_message` · [src/os.cc:L75-L76][f2]

Windows-only RAII wrapper around a FormatMessageW-allocated wide error string.

The constructor requests an allocated system message for the error code, stores the returned length and pointer, and trims trailing space, newline, carriage return, tab, or NUL characters by reducing the stored length. Copy construction and assignment are deleted. The destructor frees the message with LocalFree. Boolean conversion is true only when FormatMessageW returned a nonzero length; conversion to a wide string view exposes the stored pointer and trimmed length.

<a id="u-6d322f40605a"></a>
### `os.cc-utf8-system-category`

`class utf8_system_category final : public std::error_category` · [src/os.cc:L107-L109][f2]

Windows error category that reports system errors as UTF-8 text.

Its name is "system". Its message method builds a system_message for the code; if that message is truthy, it converts the wide text to UTF-8 and returns the converted string when conversion succeeds. If the message is empty or conversion fails, it returns "unknown error".

<a id="u-a6a4b5f8fb66"></a>
### `convert_c_format_args`

`static int convert_c_format_args( fmt::basic_format_arg<fmt::format_context>* format_…` · [src/fmt-c.cc:L14-L36][f1]

Converts a C argument array into fmt format arguments, rejecting unsupported or excessive input.

It returns fmt_error_invalid_arg when num_args exceeds 16 or when any argument type is not one of int, uint, bool, char, float, double, long double, cstring, or pointer; otherwise it assigns each value and returns 0.

<a id="u-2cc677da0e3e"></a>
### `src/os.cc:file (4)`

`auto file::size() const -> long long` · [src/os.cc:L246-L270][f2]

Returns the file size as a long long.

On Windows it obtains a HANDLE from the descriptor, calls GetFileSize, and throws windows_error if the lower result is INVALID_FILE_SIZE and GetLastError is not NO_ERROR; otherwise it combines the upper and lower DWORDs. On other platforms it calls fstat and throws a system_error with errno on failure, returning st_size after a compile-time size check.

<a id="u-4681d12c08d4"></a>
### `src/os.cc:file (5)`

`auto file::read(void* buffer, size_t count) -> size_t` · [src/os.cc:L272-L278][f2]

Reads up to count bytes into the buffer, retrying the read call through the platform wrapper.

A negative result throws a system_error with errno; otherwise the result is converted to size_t and returned.

<a id="u-282a02e28abc"></a>
### `src/os.cc:file (6)`

`auto file::write(const void* buffer, size_t count) -> size_t` · [src/os.cc:L280-L286][f2]

Writes up to count bytes from the buffer, retrying the write call through the platform wrapper.

A negative result throws a system_error with errno; otherwise the result is converted to size_t and returned.

<a id="u-7b8e15e3f9c2"></a>
### `src/os.cc:file (7)`

`auto file::dup(int fd) -> file` · [src/os.cc:L288-L296][f2]

Duplicates a file descriptor into a new file object without retrying the dup call.

If dup returns -1, it throws a system_error with errno and the source descriptor; otherwise it returns a file owning the new descriptor.

<a id="u-e1c55fbe51fe"></a>
### `src/os.cc:file (8)`

`void file::dup2(int fd)` · [src/os.cc:L298-L306][f2]

Duplicates this file's descriptor onto another descriptor, retrying the dup2 call.

If the result is -1, it throws a system_error with errno and both descriptor values.

<a id="u-0495e98fab20"></a>
### `src/os.cc:file (9)`

`void file::dup2(int fd, std::error_code& ec) noexcept` · [src/os.cc:L308-L312][f2]

Duplicates this file's descriptor onto another descriptor, retrying the dup2 call.

On failure it stores errno in the supplied error_code using the generic category and does not throw; the function is noexcept.

<a id="u-9f2acaa51192"></a>
### `getpagesize`

`auto getpagesize() -> long` · [src/os.cc:L361-L377][f2]

Returns the system memory page size as a long.

On Windows it reads dwPageSize from GetSystemInfo. Elsewhere it calls getpagesize on VxWorks kernel or sysconf(_SC_PAGESIZE) otherwise; a negative result throws a system_error with errno. The function is excluded on MSDOS.

<a id="u-2ba95821efed"></a>
### `src/os.cc:ostream`

`void ostream::grow(buffer<char>& buf, size_t)` · [src/os.cc:L380-L382][f2]

Flushes the ostream buffer when it is full.

It compares size and capacity and, on equality, calls flush through the ostream base.

<a id="u-4df302ebdc51"></a>
### `src/os.cc:ostream (2)`

`ostream::ostream(cstring_view path, const detail::ostream_params& params) : buffer<ch…` · [src/os.cc:L384-L387][f2]

Constructs an ostream over a path and ostream parameters.

It initializes the buffer with the grow callback, opens the file with the parameter open flags, and installs a newly allocated buffer of the requested size.

<a id="u-96e41e83f8f1"></a>
### `src/os.cc:ostream (3)`

`ostream::ostream(ostream&& other) noexcept : buffer<char>(grow, other.data(), other.s…` · [src/os.cc:L389-L394][f2]

Move-constructs an ostream by taking the other object's buffer storage and file, then clearing the source buffer and setting its data pointer to null with zero size.

The move constructor is noexcept.

<a id="u-d6ac7306d738"></a>
### `src/os.cc:ostream (4)`

`ostream::~ostream()` · [src/os.cc:L396-L399][f2]

Destroys an ostream by flushing pending output and deleting the allocated buffer array.

<a id="u-652e3af257a0"></a>
### `report_windows_error`

`void report_windows_error(int error_code, const char* message) noexcept` · [src/os.cc:L164-L166][f2]

Reports a Windows error by delegating to do_report_error with the Windows error formatter, error code, and message; the function is noexcept.

<a id="u-38adce146043"></a>
### `src/os.cc:system_category`

`FMT_API const std::error_category& system_category() noexcept` · [src/os.cc:L136-L139][f2]

Returns the process-wide Windows system error category as a reference to a function-local static utf8_system_category.

<a id="u-ff38e7182efd"></a>
### `vwindows_error`

`std::system_error vwindows_error(int err_code, string_view format_str, format_args args)` · [src/os.cc:L141-L145][f2]

Builds a std::system_error for a Windows error code, using the system category and formatting the supplied format string and arguments as the exception text.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/fmt-c.cc
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/os.cc
