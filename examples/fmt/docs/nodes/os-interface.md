# OS Header Interface

**Capability.** Platform configuration macros, cstring_view for C APIs, and the owning file/buffered_file/pipe/ostream types plus Windows error helpers declared for consumers.

Include os.h and use these RAII types; they compile only under FMT_USE_FCNTL where applicable and are implemented in src/os.cc.

**Depends on.**

- [File I/O Implementation](os-impl-file.md) · graph-only · 1 edge(s)

**Depended on by.**

- [File I/O Implementation](os-impl-file.md) · model-inferred · 0 edge(s)

Parent: [OS & File I/O](os.md)

## Units (7)

<a id="u-73520771d026"></a>
### `os.h-macros-and-include-selection`

`namespace detail` · [include/fmt/os.h:L119-L122][f1]

Builds the OS layer's platform configuration.

Includes are selected when not built as a module, with xlocale.h pulled in only when available. FMT_USE_FCNTL is enabled when fcntl.h is available (or on Apple/Linux) and the target is not UWP or wasm; otherwise it is 0. FMT_POSIX prefixes POSIX calls with '_' on Windows (except MinGW) to avoid deprecated-symbol warnings. FMT_SYSTEM defaults to direct ::call, and FMT_POSIX_CALL similarly; when FMT_SYSTEM is predefined (testability hook), FMT_POSIX_CALL routes through it and FMT_HAS_SYSTEM is set. FMT_RETRY_VAL retries an expression while it yields error_result and errno is EINTR on POSIX; on Windows it evaluates once. FMT_RETRY is the -1-error specialization.

**Notes.**

- condition: The EINTR retry loop exists only on non-Windows builds.

**Uncertainties.**

- Macro effects depend on target macros (_WIN32, WINAPI_FAMILY, __wasm__) not visible here.

<a id="u-bd1b8fcafdbf"></a>
### `os.h-basic-cstring-view`

`class is most useful as a parameter type for functions that wrap C APIs. */ template …` · [include/fmt/os.h:L79-L107][f1]

A non-owning reference to a null-terminated string, intended as a parameter type for wrappers around C APIs.

basic_cstring_view<Char> stores a const Char pointer obtained either from a C string or from std::basic_string::c_str(), and c_str() returns it. The aliases cstring_view and wcstring_view fix Char to char and wchar_t. Lifetime is the caller's responsibility: the view does not extend the source string's lifetime.

<a id="u-ecf01a5f5a02"></a>
### `os.h-file`

`class FMT_API file` · [include/fmt/os.h:L224-L229][f1]

An owning POSIX-style file descriptor wrapper, compiled only when FMT_USE_FCNTL is 1.

A closed file is represented by descriptor -1; the default constructor sets that. The (path, oflag) constructor opens the file via the OS (implemented elsewhere), and the static open flags RDONLY, WRONLY, RDWR, CREATE, APPEND, TRUNC expand to FMT_POSIX-prefixed O_* constants. Copying is deleted; move construction steals the descriptor and resets the source to -1, while move assignment closes the current file first (hence it is not noexcept, since close may throw). The destructor closes any open file. read/write attempt count-byte transfers, size() returns the file size as long long, dup returns a duplicated descriptor as a new file, dup2 makes fd a copy of this descriptor (an overload reporting via std::error_code is noexcept), and fdopen wraps the descriptor in a buffered_file, detaching it from this object. On Windows (non-MinGW) open_windows_file opens via a wide path.

**Notes.**

- failure: Per the class comment, methods not declared noexcept may throw fmt::system_error on failure, and some Windows errors (e.g. closing twice) crash rather than throw.
- side_effect: fdopen detaches the descriptor from this file object.

uses: [os.h-buffered-file](os-interface.md#u-cb6b56653b39), [os.h-pipe](os-interface.md#u-6033aa2ed6f4)

**Uncertainties.**

- The bodies of the constructor, close, size, read, write, dup, dup2, fdopen, and open_windows_file are in os.cc and are not visible here.

<a id="u-cb6b56653b39"></a>
### `os.h-buffered-file`

`class buffered_file` · [include/fmt/os.h:L167-L173][f1]

An owning wrapper around a C FILE* stream.

Construction from a raw FILE* is private and reserved for friend class file. Copying is deleted; the default constructor holds nullptr, and the destructor (implemented in os.cc) closes any open file. Move construction steals the pointer and nulls the source; move assignment closes the current file first, then steals the source pointer. The (cstring_view, cstring_view) constructor opens a file with fopen semantics; close() and descriptor() are FMT_API with definitions elsewhere. get() returns the raw FILE*. print formats the arguments and either calls fmt::vprint_buffered when the argument types require locking or fmt::vprint otherwise, writing to this file.

**Notes.**

- side_effect: Destruction and move assignment close the associated file; double close is the caller's responsibility to avoid.

uses: [os.h-file](os-interface.md#u-ecf01a5f5a02), [function::is_locking::81813][f2]

**Uncertainties.**

- close(), the opening constructor, descriptor(), and the destructor are FMT_API with implementations in os.cc; their exact failure behavior (exception types on fopen/fclose failure) is not visible here.

<a id="u-6033aa2ed6f4"></a>
### `os.h-pipe`

`struct FMT_API pipe` · [include/fmt/os.h:L306-L313][f1]

A pair of file objects representing the read and write ends of an OS pipe.

The public members read_end and write_end are file instances; the default constructor (FMT_API, implemented in os.cc) creates the pipe and initializes both ends. Being a friend of file, it can construct them from raw descriptors. Only available when FMT_USE_FCNTL is enabled.

uses: [os.h-file](os-interface.md#u-ecf01a5f5a02)

**Uncertainties.**

- pipe's constructor body is not in this file; failure handling (e.g. on _pipe/pipe failure) is not visible.

<a id="u-20235cc3b9cf"></a>
### `os.h-ostream`

`namespace detail` · [include/fmt/os.h:L318-L319][f1]

Buffered file output stream machinery, guarded by FMT_USE_FCNTL.

detail::buffer_size is a tag whose operator= converts an integer assignment into a buffer_size carrying that value; the exported constexpr buffer_size variable provides the syntax buffer_size=8192. detail::ostream_params accumulates open flags (default WRONLY|CREATE|TRUNC) and buffer size (max(BUFSIZ, 32768)) by recursively unpacking parameters: a trailing int sets oflag, a trailing buffer_size sets the size; Intel-compiler workarounds provide direct single-argument constructors. ostream privately inherits detail::buffer<char>, holds a file, and grows the buffer via a static callback; its conversion operator to writer exposes the underlying buffer. flush() writes the buffered bytes to the file (skipping when empty) and clears the buffer; close() flushes then closes the file; print() formats into the in-memory buffer via vformat_to without flushing. output_file(path, params...) is a friend factory that builds an ostream from ostream_params. The class is documented for single-threaded use only.

**Notes.**

- side_effect: print accumulates in the buffer and only reaches the file on flush, close, or destruction; move and destructor are FMT_API with implementations elsewhere.
- condition: flush is a no-op when the buffer is empty.

uses: [os.h-file](os-interface.md#u-ecf01a5f5a02), [os.h-pipe](os-interface.md#u-6033aa2ed6f4)

**Uncertainties.**

- ostream's FMT_API constructor, move, destructor, and grow are implemented in os.cc; flush's error behavior on short writes is not visible here.

<a id="u-b33c79ce2bda"></a>
### `os.h-windows-error`

`template <typename... T> auto windows_error(int error_code, string_view message, cons…` · [include/fmt/os.h:L151-L155][f1]

Windows-only error reporting (guarded by _WIN32).

windows_error(error_code, message, args...) is a template wrapper that packs the arguments and calls vwindows_error, producing a std::system_error whose description is the formatted message followed by the system message for the Windows error code, as documented. On non-Windows builds, system_category() simply returns std::system_category(). report_windows_error and the detail error-formatting function are declared here and implemented elsewhere.

uses: [os.h-windows-error](os-interface.md#u-b33c79ce2bda)

**Uncertainties.**

- vwindows_error, format_windows_error, and report_windows_error have no visible implementation in this file; exact message construction cannot be verified here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/os.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h