# format_as type mapping

**Capability.** Detects and applies format_as conversions, mapping user types to natively formattable ones for both parsing and storage.

This small module implements the format_as extension point: trait detection, constexpr parse invocation through the mapper, and the use_formatter gate. Come here to understand how enums and wrappers become formattable.

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (4)

<a id="u-8061d47f5132"></a>
### `core.h-use-format-as-traits`

`template <typename T, typename Enable = std::true_type> struct use_format_as : std::f…` · [include/fmt/core.h:L1139-L1140][f1]

Detect whether a type should be mapped through a free format_as() or a formatter<T>::format_as() member: true only when the result type (cvref-stripped) is arithmetic, so owning types map but views are not auto-mapped for safety.

<a id="u-2c442e1e3289"></a>
### `invoke_parse`

`FMT_CONSTEXPR auto invoke_parse(parse_context<Char>& ctx) -> const Char*` · [include/fmt/core.h:L1680-L1687][f1]

Invokes formatter<T>::parse in a constexpr context after mapping T through type_mapper: if the mapped type has no constructible formatter it returns ctx.begin() unchanged (the error surfaces later in the value constructor); otherwise it parses with the mapped type's formatter.

<a id="u-f6cac92895e6"></a>
### `include/fmt/core.h:FMT_END_EXPORT (28)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1153-L1167][f1]

Defines use_formatter, true for class, enum, union, or array types that are not string-like, not named args, and have neither a format_as free function nor a formatter::format_as member; such types are routed through the custom-formatter path.

<a id="u-b0ef003ad178"></a>
### `include/fmt/core.h:FMT_END_EXPORT (30)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1223-L1239][f1]

Type aliases applying type_mapper: mapped_t is the type type_mapper<Char> maps T to (void on error, making it SFINAE-friendly), mapped_type_constant is the type_constant of the mapped type, and stored_type_constant keeps the native type only for int or when the context uses builtin types, otherwise forcing custom_type.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
