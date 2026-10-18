# Error Reporting

**Capability.** Throwing and non-throwing error paths: assertion failure, format_error reporting, and allocation-free system-error message construction.

Callers reporting formatting or OS failures use these entry points; chrono, color, printf, ranges, and args code reaches them via calls to report_error and assert_fail.

**Depended on by.**

- [Dynamic Argument Stores](args-h.md) · graph-confirmed · 1 edge(s)
- [std::tm Formatting](chrono-tm.md) · graph-confirmed · 7 edge(s)
- [Style Model](color-model.md) · graph-confirmed · 4 edge(s)
- [printf Engine & API](printf-engine.md) · graph-confirmed · 6 edge(s)
- [printf Spec Parsing](printf-spec.md) · graph-confirmed · 7 edge(s)
- [Range Formatters](ranges-formatters.md) · graph-confirmed · 5 edge(s)
- [Floating-Point Shortest Formatting](core-float.md) · graph-only · 11 edge(s)
- [Duration Formatting](chrono-duration.md) · graph-only · 2 edge(s)
- [FILE Output Backend](core-file-output.md) · graph-only · 1 edge(s)

Parent: [Core Runtime & Engine](core-runtime.md)

## Units (7)

<a id="u-51c7265a0ebb"></a>
### `assert_fail`

`FMT_FUNC void assert_fail(const char* file, int line, const char* message)` · [include/fmt/format-inl.h:L49-L54][f1]

Reports a failed assertion by writing file, line, and message to stderr, then aborts.

It deliberately calls std::fprintf unchecked so that a failure writing to stderr cannot trigger a recursive assertion. It never returns; the process terminates via abort.

<a id="u-b95c8efa4f16"></a>
### `do_report_error`

`FMT_FUNC void do_report_error(format_func func, int error_code, const char* message) …` · [include/fmt/format-inl.h:L114-L121][f1]

Formats an error report into a memory_buffer using the supplied format_func, then writes it to stderr.

It intentionally avoids fwrite_all because that wrapper throws; a plain std::fwrite is used, and the trailing newline is written only if the fwrite reported success. Never throws and propagates no exceptions.

uses: [format_system_error](core-errors.md#u-53489fe46be6)

<a id="u-9071058d5fd4"></a>
### `format_error_code`

`FMT_FUNC void format_error_code(detail::buffer<char>& out, int error_code, string_vie…` · [include/fmt/format-inl.h:L92-L112][f1]

Writes '<message>: error <code>' into a char buffer without risking dynamic allocation, so it is noexcept and safe to use while handling errors.

It first clears the buffer, sizes the fixed ': error ' plus code representation (adding one for a minus sign on negative codes plus the digit count of the absolute value), and only prepends the message plus separator when the message fits within inline_buffer_size minus that overhead; otherwise the message is dropped and only the error text is written. An FMT_ASSERT guards that the result stays within inline_buffer_size.

uses: [format_system_error](core-errors.md#u-53489fe46be6)

**Uncertainties.**

- Behavior when the assertion fires (likely abort via assert_fail) is not shown in this unit.

<a id="u-53489fe46be6"></a>
### `format_system_error`

`FMT_FUNC void format_system_error(detail::buffer<char>& out, int error_code, const ch…` · [include/fmt/format-inl.h:L1442-L1448][f1]

Writes a description of an OS error into a char buffer without throwing.

In the FMT_TRY block it builds a std::error_code from the generic category, formats std::system_error(ec, message).what() into the buffer via detail::write, and returns. Any exception in that block (FMT_CATCH(...)) is swallowed and the allocation-free fallback format_error_code(out, error_code, message) writes a minimal message instead. Always returns with buffer content present and noexcept.

calls: [format_error_code](core-errors.md#u-9071058d5fd4)

<a id="u-4fe75221d1d1"></a>
### `report_error`

`FMT_FUNC void report_error(const char* message)` · [include/fmt/format-inl.h:L157-L165][f1]

Reports a formatting error by throwing format_error carrying the given message.

On MSVC and NVCC a volatile-true guard suppresses unreachable-code warnings. All exceptions propagate to the caller; there is no fallback.

<a id="u-9d0ac0b7e9fd"></a>
### `report_system_error`

`FMT_FUNC void report_system_error(int error_code, const char* message) noexcept` · [include/fmt/format-inl.h:L1453-L1456][f1]

Reports an OS error to stderr without throwing: it delegates to do_report_error with format_system_error as the formatting function, which builds the message and writes it to stderr using non-throwing fwrite.

calls: [do_report_error](core-errors.md#u-b95c8efa4f16); uses: [format_system_error](core-errors.md#u-53489fe46be6)

<a id="u-297522660db1"></a>
### `vsystem_error`

`FMT_FUNC auto vsystem_error(int error_code, string_view fmt, format_args args) -> std…` · [include/fmt/format-inl.h:L184-L188][f1]

Constructs a std::system_error from an error code and a formatted message: it wraps error_code in std::generic_category and pairs it with vformat(fmt, args) as the message string.

Returns the exception object without throwing it; the caller decides to throw.

calls: [include/fmt/format-inl.h:vformat](core-format-engine.md#u-16ecfa8aee04)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h