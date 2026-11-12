# Compile-Time Format Checking

**Capability.** Validates format strings against argument packs during constant evaluation and tracks argument indexing and character specs.

Use this module for compile-time format-string validation. The units describe parse contexts, argument indexing, character-spec checks, and constexpr enforcement.

**Depends on.**

- [Format Spec Parser](format-spec-parser.md) · graph-confirmed · 7 edge(s) · compile-time-format-checking depends on format-spec-parser for parsing and validating format specs.
- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Format Spec Parsing and Writing](format-spec-parsing-and-writing.md) · graph-only · 1 edge(s)

Parent: [Argument and Spec Pipeline](argument-and-spec-pipeline.md)

## Units (7)

<a id="u-04d2e1a8abd3"></a>
### `core.h-compile-parse-context`

`class compile_parse_context : public parse_context<Char>` · [include/fmt/core.h:L1240-L1248][f1]

A parse context with extra data for compile-time checks.

next_arg_id and check_arg_id report 'argument not found' when the id is at least num_args. check_dynamic_spec reports 'width/precision is not integer' only when the id is in range, types_ is non-null, and the type is not integral.

<a id="u-e7fb7ad77211"></a>
### `core.h-format-string-checker`

`class format_string_checker` · [include/fmt/core.h:L1692-L1713][f1]

Compile-time handler that validates a format string against a fixed argument pack.

It stores mapped types, named-argument metadata, a compile parse context, and per-argument parse functions; construction fills named arguments with the static initializer. on_text is a no-op. on_arg_id() uses the next automatic id; on_arg_id(int) checks and returns the id; on_arg_id(name) searches named arguments by content and, if not found, reports argument not found when dynamic names are disabled, otherwise returns -1. on_replacement_field parses empty specs. on_format_specs advances the context to the spec start; for an in-range id it calls that argument's parse function, otherwise it skips to the matching '}' while counting nested braces. on_error reports the message.

<a id="u-902bed1f6d61"></a>
### `core.h-parse-context-argument-indexing`

`FMT_CONSTEXPR auto next_arg_id() -> int` · [include/fmt/core.h:L873-L881][f1]

Tracks automatic versus manual argument indexing during parsing.

next_arg_id reports an error and returns 0 if manual indexing was already selected; otherwise it returns the current automatic id and increments it, then runs the compile-time id check. check_arg_id(int) reports an error and returns if automatic indexing was already used; otherwise it switches to manual and runs the id check. check_arg_id(string_view) switches to manual without an id check. The id check only runs at constant evaluation and reports argument not found when the id is outside the compile-time argument count.

<a id="u-ba2de7ba069c"></a>
### `core.h-parse-context-compile-time-checks`

`template <typename Char> FMT_CONSTEXPR void parse_context<Char>::do_check_arg_id(int …` · [include/fmt/core.h:L2425-L2433][f1]

Out-of-class parse-context checks that only act during constant evaluation when the constexpr cast is enabled.

The id check casts to compile_parse_context and reports argument not found when the id is outside the compile-time argument count. The dynamic-spec check casts and delegates to the compile parse context's dynamic-spec validation.

<a id="u-23f6130e268d"></a>
### `check_char_specs`

`FMT_CONSTEXPR inline auto check_char_specs(const format_specs& specs) -> bool` · [include/fmt/core.h:L1662-L1673][f1]

Checks character presentation specs.

It returns false when the presentation type is set and is not char or debug. Otherwise it reports invalid format specifier for char if numeric alignment, a sign, or alternate form is set, and returns true.

<a id="u-2c442e1e3289"></a>
### `invoke_parse`

`FMT_CONSTEXPR auto invoke_parse(parse_context<Char>& ctx) -> const Char*` · [include/fmt/core.h:L1680-L1687][f1]

Parses a compile-time format string for one argument type.

It maps the type, checks whether a formatter is constructible; if not it returns the current parse position because the value constructor reports the error. Otherwise it constructs the formatter for the mapped type and calls its parse.

<a id="u-b9700dd22dc0"></a>
### `enforce_compile_checks`

`template <bool B> constexpr bool enforce_compile_checks()` · [include/fmt/core.h:L2393-L2400][f1]

Returns true after optionally enforcing compile-string checks.

When FMT_ENFORCE_COMPILE_STRING is defined it static_asserts that consteval is available and the boolean condition is true.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
