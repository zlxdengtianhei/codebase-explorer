# OS Error Reporting

**Capability.** Windows-specific error message machinery: RAII FormatMessageW wrapper, UTF-8 error_category, non-throwing error description appends, and report_windows_error/vwindows_error.

Use for translating OS error codes into messages on Windows; the system message class backs the utf-8 category used by vwindows_error.

Parent: [OS & File I/O](os.md)

## Units (6)

<a id="u-b2055b3f53ae"></a>
### `os.cc-system-message`

`system_message(const system_message&) = delete;` · [src/os.cc:L76-L76][f1]

Windows-only RAII wrapper around a FormatMessageW result for one error code.

The constructor zeroes result_/message_, calls FormatMessageW with ALLOCATE_BUFFER|FROM_SYSTEM|IGNORE_INSERTS in the default language, and on success trims trailing whitespace and NUL characters by shrinking result_. The destructor frees message_ with LocalFree. Copy construction and assignment are deleted, giving the buffer a single owner. Conversion to bool tests result_ != 0; conversion to fmt::basic_string_view<wchar_t> yields the (possibly empty on failure) message span.

uses: [os.cc-utf8-system-category](os-impl-error.md#u-6d322f40605a), [src/os.cc:detail](os-impl-error.md#u-00c970cbac56)

**Uncertainties.**

- The trim loop reads message_[result_-1]; behavior if FormatMessageW returns nonzero length without a readable buffer cannot be established from this source.

<a id="u-6d322f40605a"></a>
### `os.cc-utf8-system-category`

`class utf8_system_category final : public std::error_category` · [src/os.cc:L107-L109][f1]

Windows-only final std::error_category that renders system error messages as UTF-8.

name() returns "system". message(int) builds a system_message for the code; if that succeeded, it converts the wide message with fmt::detail::to_utf8<wchar_t> and returns the UTF-8 string when conversion succeeds. If message lookup failed or conversion failed, it returns the literal "unknown error". The enclosing region also sets rwresult to int for Windows read/write return types.

<a id="u-00c970cbac56"></a>
### `src/os.cc:detail`

`void detail::format_windows_error(detail::buffer<char>& out, int error_code, const ch…` · [src/os.cc:L147-L159][f1]

Appends a Windows error description to a char buffer without ever throwing.

Inside FMT_TRY it builds a system_message for error_code, converts the wide message to UTF-8, and on success writes "<message>: <utf8 description>" into the buffer via fmt::format_to and returns. If message lookup fails, UTF-8 conversion fails, or any exception is caught by the trailing FMT_CATCH, it falls back to format_error_code(out, error_code, message), so the buffer always receives some content.

uses: [os.cc-system-message](os-impl-error.md#u-b2055b3f53ae)

<a id="u-652e3af257a0"></a>
### `report_windows_error`

`void report_windows_error(int error_code, const char* message) noexcept` · [src/os.cc:L164-L166][f1]

Reports a Windows error code and message to standard error by delegating to do_report_error with detail::format_windows_error as the formatter.

It is noexcept, so any failure of the reporting path itself is contained rather than propagated.

calls: [src/os.cc:detail](os-impl-error.md#u-00c970cbac56)

**Uncertainties.**

- Behavior of do_report_error (e.g. its write target and failure handling) is not in this source.

<a id="u-38adce146043"></a>
### `src/os.cc:system_category`

`FMT_API const std::error_category& system_category() noexcept` · [src/os.cc:L136-L139][f1]

Returns the Windows system error category as a std::error_category reference.

It constructs a function-local static utf8_system_category on first call and returns that same instance thereafter; declared noexcept. Only compiled when _WIN32 is defined.

uses: [os.cc-utf8-system-category](os-impl-error.md#u-6d322f40605a)

<a id="u-ff38e7182efd"></a>
### `vwindows_error`

`std::system_error vwindows_error(int err_code, string_view format_str, format_args args)` · [src/os.cc:L141-L145][f1]

Builds a std::system_error for a Windows error code whose what() message is format_str formatted with args.

It pairs err_code with system_category() to form an error_code and calls vformat eagerly, so formatting exceptions propagate from this construction rather than from later use of the error object.

calls: [src/os.cc:system_category](os-impl-error.md#u-38adce146043)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/os.cc