# Error & Exception Formatters

**Capability.** Formats error_code (with '?' escaping), std::exception and std::exception_ptr (the latter by rethrowing into the exception formatter), and source_location as file:line:column:function.

Use for diagnostics-oriented types; exception_ptr intentionally rethrows so message formatting reuses the exception formatter.

Parent: [std Type Formatters](std-h.md)

## Units (4)

<a id="u-ccf3d4253abe"></a>
### `std-h-error-code-formatter`

`template <> struct formatter<std::error_code>` · [include/fmt/std.h:L520-L527][f1]

Formats std::error_code with align, width, optional '?' escaping, and an 's' presentation.

parse parses align, then width (digit or '{') into specs_ with width_ref_, sets debug_ on '?', and on 's' sets presentation_type::string. format resolves dynamic width, builds the message into a memory_buffer: with the 's' type just ec.message(), otherwise 'category-name:value' where the integer is written via detail::write<char>. If debug_ is set, the string is escaped via write_escaped_string into a second buffer. The final string is written with the resolved specs.

<a id="u-a3fb5b7553ab"></a>
### `std-h-exception-formatter`

`template <typename T> struct formatter< T, char, typename std::enable_if<std::is_base…` · [include/fmt/std.h:L590-L600][f1]

Formats any type derived from std::exception (char only).

parse: empty or '}' stops immediately; otherwise align is parsed, width (digit or '{') with dynamic width_ref_, and 't' requests the type name, effective only when FMT_USE_RTTI is nonzero (with_typename_ records FMT_USE_RTTI != 0). format takes a const std::exception&; with no width requested it writes directly, otherwise buffers the message and applies fill/align/width via write_padded (which resolves dynamic width first). write() optionally emits the demangled typeid name followed by ': ', then ex.what(); with RTTI and exceptions enabled, if the exception derives from std::nested_exception and carries a nested_ptr, it writes ': ', rethrows, and recursively formats a caught std::exception or, for any other caught value, the literal 'unknown exception'.

**Notes.**

- failure: Non-std::exception values in a nested chain render as 'unknown exception'; nested formatting failures inside that recursion are not caught here.

**Uncertainties.**

- Whether dynamic_cast-based nesting detection succeeds depends on the concrete exception type's inheritance, not checkable here.

<a id="u-4a90575511ea"></a>
### `std-h-exception-ptr-formatter`

`template <> struct formatter<std::exception_ptr> : formatter<std::exception>` · [include/fmt/std.h:L671-L672][f1]

Formats std::exception_ptr by rethrowing.

It inherits formatter<std::exception>. For a null pointer it writes 'none' through write_padded. With exceptions enabled, it rethrows the pointer: a caught std::exception is delegated to the base formatter's format; any other caught value, or the case where FMT_USE_EXCEPTIONS is disabled, falls through to writing 'unknown exception' via write_padded.

inherits: [std-h-exception-formatter](std-error-exception.md#u-a3fb5b7553ab); calls: [std-h-exception-formatter](std-error-exception.md#u-a3fb5b7553ab)

<a id="u-aa5587038b13"></a>
### `std-h-source-location-formatter`

`template <> struct formatter<std::source_location>` · [include/fmt/std.h:L451-L452][f1]

Formats std::source_location as 'file:line:column: function'.

parse accepts no specs. format writes loc.file_name(), ':', the line, ':', the column, ": ", then loc.function_name(); numeric writes use detail::write<char> and are not padded or localized.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h