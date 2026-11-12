# OS Type Wrappers

**Capability.** Defines non-owning C-string views, file descriptor wrappers, buffered output streams, pipe holders, and output parameters.

Come here for OS-facing type wrappers. The units describe C-string views, descriptor ownership, buffered streams, pipes, and output-file parameters.

Parent: [C API and OS File Layer](c-api-and-os-file-layer.md)

## Units (8)

<a id="u-bd1b8fcafdbf"></a>
### `os.h-basic-cstring-view`

`basic_cstring_view(const std::basic_string<Char>& s) : data_(s.c_str())` · [include/fmt/os.h:L107-L107][f1]

Non-owning view of a null-terminated character string.

It can be constructed from a C string pointer or from a std::basic_string by storing that string c_str pointer; the accessor returns the stored pointer. The referenced string must outlive the view.

<a id="u-6d84f5baae28"></a>
### `os.h-buffer-size`

`struct buffer_size` · [include/fmt/os.h:L320-L321][f1]

Tag type carrying an output buffer size parameter.

Default value is zero. The const assignment operator does not mutate the left object; it creates a copy with the new value and returns it, matching the parameter-folding use in stream construction.

<a id="u-ecf01a5f5a02"></a>
### `os.h-file`

`class FMT_API file` · [include/fmt/os.h:L224-L229][f1]

Wraps and owns a POSIX file descriptor, with -1 representing no file.

Default construction uses -1; a private constructor stores a supplied descriptor; path/oflag construction opens a file. Copy is deleted; move steals the descriptor and sets the source to -1; move assignment is not noexcept because it calls close first. The destructor is declared noexcept. Methods expose the descriptor, close, size, read, write, static dup, dup2 with and without an error_code, and fdopen; a Windows-only static open helper exists when enabled. The flag enum maps to platform O_* values. Methods without noexcept may throw fmt::system_error per the class comment; actual system-call and error behavior is in external definitions. The class comment also warns that some errors, such as closing multiple times on Windows, may crash rather than throw.

**Uncertainties.**

- Most method bodies are outside this header; syscall and error handling details are not visible.

<a id="u-20235cc3b9cf"></a>
### `os.h-ostream`

`class ostream : private detail::buffer<char>` · [include/fmt/os.h:L361-L373][f1]

Single-threaded buffered output stream over a file.

It privately inherits a char buffer and holds a file; construction from path and parameters is private and external, as are move construction, destruction, and growth. It converts to a writer over its buffer. Flush does nothing when empty; otherwise it writes the buffer through the file, then clears it. Close flushes then closes the file. Print formats arguments into the stream through an appender and the formatting library. The public factory builds an ostream from a path and parameter pack. The class comment warns that concurrent writes without external synchronization may race.

**Uncertainties.**

- Private construction, move, destructor, and growth functions are external; exact allocation and close behavior is not visible.

<a id="u-7b1cd5c0076b"></a>
### `os.h-ostream-params`

`struct ostream_params` · [include/fmt/os.h:L330-L334][f1]

Parameter accumulator for output-file construction.

Defaults select write-only/create/truncate flags and a buffer size of BUFSIZ when larger than 32768, otherwise 32768. Constructors recursively delegate through preceding parameters; a trailing int replaces the open flags, and a trailing buffer-size tag replaces the buffer size. Intel-specific overloads mirror the single trailing int and buffer-size cases.

<a id="u-eba83094d57b"></a>
### `os.h-system-error-helpers`

`template <typename... T> auto windows_error(int error_code, string_view message, cons…` · [include/fmt/os.h:L151-L155][f1]

On Windows, the error factory builds a std::system_error by forwarding a formatted message and arguments to the external formatted Windows-error routine.

On non-Windows, the category accessor returns std::system_category. The two definitions are selected by platform preprocessor branches, so only one is present in a given build.

<a id="u-edce9227640e"></a>
### `include/fmt/os.h:FMT_BEGIN_EXPORT`

`class is most useful as a parameter type for functions that wrap C APIs. */ template …` · [include/fmt/os.h:L79-L107][f1]

Provides a non-owning wrapper around a null-terminated character string, constructible from a raw C string or a standard string, and exposes the underlying pointer through a C-string accessor.

It stores only the pointer, performs no copying or ownership transfer, and does not validate nullness or lifetime.

<a id="u-b66f0f4d505c"></a>
### `pipe`

`struct FMT_API pipe` · [include/fmt/os.h:L306-L313][f1]

A pipe holder with two file members for the read and write ends.

Its constructor is declared to create the pipe; actual creation and error behavior are defined outside this header.

**Uncertainties.**

- Pipe creation and failure behavior are not visible; only the declaration is in this header.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/os.h
