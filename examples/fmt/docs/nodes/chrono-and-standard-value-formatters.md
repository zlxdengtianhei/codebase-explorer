# Chrono and Standard Value Formatters

**Capability.** Formats std::tm and standard value types including complex, error_code, expected, optional, monostate, source_location, type_info, and unexpected.

Use this module for formatter specializations for chrono tm and selected std value wrappers. It groups std.h value formatters with the chrono tm formatter because they share formatting responsibilities.

Parent: [Standard Library Formatters](standard-library-formatters.md)

## Units (9)

<a id="u-a248eb6ff1a1"></a>
### `chrono.h-tm-formatter`

`template <typename Char> struct formatter<std::tm, Char>` · [include/fmt/chrono.h:L2115-L2123][f1]

Parses and formats std::tm values.

The default format is ISO date plus space plus ISO time. Parsing handles alignment, width, the localized flag, and chrono format specifiers through the tm checker; a non-empty parsed format replaces the default. Formatting handles dynamic width, constructs a tm writer with locale, localized state, output, tm, and optional subseconds, parses the stored format, and writes the buffer with the specs. The public parse uses whether std::tm has a gmtoff member as the timezone flag; the public format uses seconds and no subseconds.

<a id="u-992ba62e9a81"></a>
### `std.h-complex-formatter`

`template <typename T, typename Char> struct formatter<std::complex<T>, Char>` · [include/fmt/std.h:L767-L771][f2]

Formats std::complex values with real/imaginary parts and width handling.

Parsing returns early on empty input or '}', otherwise parses format specs for the value type. Formatting resolves dynamic width and precision; with zero width it formats directly, otherwise it formats into a buffer with inner width/fill/alignment cleared and writes the buffer using outer width/fill/alignment. The inner formatter writes parentheses only when the real part is nonzero, always writes the imaginary part with a plus sign when parenthesized, adds a space before 'i' for non-finite imaginary parts, and omits parentheses when the real part is zero.

<a id="u-697553c07cd8"></a>
### `std.h-error-code-formatter`

`template <> struct formatter<std::error_code>` · [include/fmt/std.h:L520-L527][f2]

Formats std::error_code with optional debug escaping and string-only mode.

Parsing handles alignment, width, '?' for debug, and 's' for string presentation. Formatting resolves dynamic width, builds either the error message or category name plus ':' plus value, optionally escapes it, and writes it with the parsed specs.

<a id="u-dfb7e77ff6c1"></a>
### `std.h-expected-formatter`

`template <typename T, typename E, typename Char> struct formatter<std::expected<T, E>…` · [include/fmt/std.h:L402-L407][f2]

Formats std::expected values.

Parsing is a no-op returning the current position. Formatting writes "expected(" when a value is present and, unless the value type is void, writes the escaped value; otherwise it writes "unexpected(" and the escaped error. It then writes ")".

<a id="u-36b20fa646ed"></a>
### `std.h-monostate-formatter`

`template <typename Char> struct formatter<std::monostate, Char>` · [include/fmt/std.h:L476-L477][f2]

Formats std::monostate.

Parsing is a no-op returning the current position. Formatting writes the literal "monostate".

<a id="u-f97809faedbb"></a>
### `std.h-optional-formatter`

`template <typename T, typename Char> struct formatter<std::optional<T>, Char, std::en…` · [include/fmt/std.h:L370-L382][f2]

Formats std::optional values.

Parsing enables debug formatting on the underlying value formatter and delegates parsing to it. Formatting writes "none" for an empty optional; otherwise it writes "optional(", advances the context, formats the contained value with the underlying formatter, and writes ")".

<a id="u-2e1b37d98674"></a>
### `std.h-source-location-formatter`

`template <> struct formatter<std::source_location>` · [include/fmt/std.h:L451-L452][f2]

Formats std::source_location.

Parsing is a no-op returning the current position. Formatting writes file name, ':', line, ':', column, ": ", and function name in that order.

<a id="u-08d5ed043373"></a>
### `std.h-type-info-formatter`

`template <> struct formatter<std::type_info>` · [include/fmt/std.h:L576-L578][f2]

Formats std::type_info by writing its demangled name through the demangling helper.

Parsing is a no-op returning the current position. This specialization is present only when RTTI is enabled.

<a id="u-331cf6cad2b9"></a>
### `std.h-unexpected-formatter`

`template <typename E, typename Char> struct formatter<std::unexpected<E>, Char, std::…` · [include/fmt/std.h:L429-L432][f2]

Formats std::unexpected values.

Parsing is a no-op returning the current position. Formatting writes "unexpected(", the escaped error, and ")".

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
