# Wrapper type formatters

**Capability.** Formatters for error_code, expected, filesystem::path, optional, and unexpected with their specific format spec options.

Formatters for std wrapper types, each supporting its own spec extensions (debug quoting, message-only, generic separators). Readers adding support for a new wrapper type should model these.

Parent: [Standard library type formatters](standard-library-type-formatters.md)

## Units (5)

<a id="u-697553c07cd8"></a>
### `std.h-error-code-formatter`

`template <> struct formatter<std::error_code>` · [include/fmt/std.h:L520-L527][f1]

Formats std::error_code with optional align, width (static or dynamic), '?' debug quoting, and 's' to print only the message.

Default output is "category: value"; with 's' it is ec.message(). Debug mode escapes the resulting string before applying specs; dynamic width is resolved from the context at format time.

<a id="u-dfb7e77ff6c1"></a>
### `std.h-expected-formatter`

`template <typename T, typename E, typename Char> struct formatter<std::expected<T, E>…` · [include/fmt/std.h:L402-L407][f1]

Formats std::expected as "expected(value)" when it holds a value (void T prints just "expected()"), or "unexpected(error)" otherwise, with the contained value written in debug/quoted alternative form.

parse accepts no specs and returns immediately. Enabled when T is void or formattable and E is formattable.

<a id="u-13e836531434"></a>
### `std.h-filesystem-path-formatter`

`template <typename Char> struct formatter<std::filesystem::path, Char>` · [include/fmt/std.h:L302-L310][f1]

Formats a std::filesystem::path with optional alignment, width (including dynamic '{' width), '?' debug (quoted/escaped) mode, and 'g' to use generic separators instead of native ones.

parse handles each spec in order and bails out early at end of input; format resolves dynamic width from the context, then either writes the (possibly transcoded) path string with the specs, or escapes it via write_escaped_path when debug mode is on. Only present when the standard library has filesystem support.

<a id="u-f97809faedbb"></a>
### `std.h-optional-formatter`

`template <typename T, typename Char> struct formatter<std::optional<T>, Char, std::en…` · [include/fmt/std.h:L370-L382][f1]

Formats std::optional: an empty optional prints "none"; a value prints "optional(" followed by the value formatted by an underlying formatter (with debug format pre-enabled in parse, which fully delegates spec parsing to it) and a closing ')'.

Only enabled when the contained type is formattable and <optional> support exists.

<a id="u-331cf6cad2b9"></a>
### `std.h-unexpected-formatter`

`template <typename E, typename Char> struct formatter<std::unexpected<E>, Char, std::…` · [include/fmt/std.h:L429-L432][f1]

Formats std::unexpected as "unexpected(" plus the error in debug/quoted alternative form and a closing ')'; parse accepts no format specs.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
