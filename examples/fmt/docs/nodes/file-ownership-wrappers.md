# File Ownership Wrappers

**Capability.** Owns and manages FILE handles and file descriptors, opening, closing, and associating streams with descriptors.

This module provides move-only file ownership wrappers. Readers find FILE and descriptor closing, opening, and stream association behavior.

Parent: [C API and OS File Layer](c-api-and-os-file-layer.md)

## Units (10)

<a id="u-cb6b56653b39"></a>
### `os.h-buffered-file`

`class buffered_file` · [include/fmt/os.h:L167-L173][f1]

Owns a FILE handle with move-only semantics and optional formatting to that stream.

Default construction stores null and a private constructor stores a supplied handle; copy construction and assignment are deleted. Move construction steals the handle and nulls the source; move assignment closes the current handle first, then steals and nulls. The destructor is declared noexcept and is documented to close the represented file if any. Close, descriptor, and the path/mode constructor are declared but defined elsewhere. Print formats through the handle, choosing buffered printing when any argument type reports locking and plain printing otherwise.

**Uncertainties.**

- Definitions of the destructor, close, descriptor, and path/mode constructor are outside this header; their exact file and error behavior is not visible.

<a id="u-d6f139e3bc1e"></a>
### `src/os.cc:buffered_file`

`buffered_file::~buffered_file() noexcept` · [src/os.cc:L170-L173][f2]

Closes the owned FILE on destruction.

If the handle is non-null and fclose fails, it reports the errno through report_system_error instead of throwing; the destructor is noexcept.

<a id="u-df5a61e7ef1a"></a>
### `src/os.cc:buffered_file (2)`

`buffered_file::buffered_file(cstring_view filename, cstring_view mode)` · [src/os.cc:L175-L181][f2]

Opens a buffered file with fopen using the supplied path and mode.

If the resulting handle is null, it throws a system_error carrying errno and the file name.

<a id="u-a87f2086d344"></a>
### `src/os.cc:buffered_file (3)`

`void buffered_file::close()` · [src/os.cc:L183-L189][f2]

Closes the buffered file if one is open.

It clears the stored handle before checking the fclose result, and throws a system_error with errno if closing failed.

<a id="u-065c8e13ace8"></a>
### `src/os.cc:buffered_file (4)`

`auto buffered_file::descriptor() const -> int` · [src/os.cc:L191-L206][f2]

Returns the underlying file descriptor for the buffered file.

It uses fileno through the system-call wrapper when available, _fileno on Windows, or plain fileno otherwise; if the result is -1 it throws a system_error with errno.

<a id="u-3b2dd84abd55"></a>
### `src/os.cc:file`

`file::file(cstring_view path, int oflag)` · [src/os.cc:L216-L227][f2]

Opens a file descriptor for a path and open flags.

On non-MinGW Windows it converts the UTF-8 path to UTF-16 and delegates to open_windows_file. Elsewhere it calls open with default_open_mode and throws a system_error with errno if the descriptor is -1. default_open_mode is the usual read/write bits for user, group, and other; on Windows those macros reduce to _S_IREAD|_S_IWRITE, so the effective Windows mode is 0600, not 0666.

<a id="u-c483f8b71181"></a>
### `src/os.cc:file (2)`

`file::~file() noexcept` · [src/os.cc:L229-L234][f2]

Closes the owned descriptor on destruction without retrying close.

If the descriptor is valid and close fails, it reports errno through report_system_error; the destructor is noexcept.

<a id="u-d3e320a10fdf"></a>
### `src/os.cc:file (3)`

`void file::close()` · [src/os.cc:L236-L244][f2]

Closes the owned descriptor if valid, without retrying close.

It clears the descriptor before checking the close result, and throws a system_error with errno if closing failed.

<a id="u-a684c6071862"></a>
### `src/os.cc:file (10)`

`auto file::fdopen(const char* mode) -> buffered_file` · [src/os.cc:L314-L328][f2]

Associates the current descriptor with a C stream and transfers ownership to a buffered_file.

It does not retry fdopen in either branch: the MinGW POSIX branch calls ::fdopen directly, and the other branch uses the system-call wrapper. If fdopen returns null it throws a system_error with errno; on success it wraps the FILE, clears the descriptor, and returns the buffered_file.

<a id="u-66708dbcce27"></a>
### `src/os.cc:file (11)`

`file file::open_windows_file(wcstring_view path, int oflag)` · [src/os.cc:L331-L339][f2]

Windows non-MinGW helper that opens a UTF-16 path with _wsopen_s using _SH_DENYNO and default_open_mode.

If the resulting descriptor is -1, it throws a system_error with the returned error code and the UTF-8 path; otherwise it returns a file owning the descriptor. On Windows default_open_mode is _S_IREAD|_S_IWRITE, i.e. 0600, not 0666.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/os.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/os.cc
