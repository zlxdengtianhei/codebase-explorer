# Compiled Format String Engine

**Capability.** Compiles format strings into fragments and formats, measures, or writes compiled output with fixed and named fields.

This module implements compile-time compiled format strings. It covers fragment compilation, argument selection, field parsing, and compiled output paths.

Parent: [Compiled Formatting Engine](compiled-formatting-engine.md)

## Units (27)

<a id="u-ee725bc06fc8"></a>
### `compile.h-arg-id-handler`

`template <typename Char> struct arg_id_handler` · [include/fmt/compile.h:L313-L317][f1]

Callback used while parsing an argument id.

The auto case asserts false because automatic indexing is not accepted here. The index case records an index kind and reference; the name case records a name kind and reference. Both recording handlers return 0.

<a id="u-f7cbc87178b9"></a>
### `compile.h-code-unit`

`template <typename Char> struct code_unit` · [include/fmt/compile.h:L146-L150][f1]

A compiled single-character fragment stores one character and writes it by assigning through the output iterator then incrementing it.

It ignores formatting arguments.

<a id="u-4cc9f9ee9a42"></a>
### `compile.h-compile-time-argument-access`

`template <int N, typename T, typename... Args> constexpr auto get([[maybe_unused]] co…` · [include/fmt/compile.h:L76-L84][f1]

Selects the Nth argument from a parameter pack by reference and derives its type.

The selection uses a static_assert to reject N at or beyond the pack size; index 0 returns the first argument, otherwise it recurses on the tail. The type helper removes cv/ref from the selected argument type.

<a id="u-a5852dc6d5d0"></a>
### `compile.h-compiled-format-output`

`template <typename CompiledFormat, typename... T, typename Char = typename CompiledFo…` · [include/fmt/compile.h:L476-L485][f1]

Overloads for an already compiled format object.

The string-returning overload formats through a back inserter into a new basic_string and returns it. The iterator overload forwards directly to the compiled object format and returns the advanced iterator. Both are enabled only for compiled-format types.

<a id="u-5fe5d05c7f01"></a>
### `compile.h-concat`

`template <typename L, typename R> struct concat` · [include/fmt/compile.h:L244-L249][f1]

A compiled sequence of two fragments.

Formatting runs the left fragment first, then the right with the same arguments, returning the right fragment iterator; the factory constructs the aggregate. The character type comes from the left fragment.

<a id="u-9dbf88a38412"></a>
### `compile.h-field`

`template <typename Char, typename V, int N> struct field` · [include/fmt/compile.h:L172-L175][f1]

A replacement field for a fixed argument index.

It fetches and unwraps the argument, then formats in this order: as a string view when convertible, via format_as when available, via the formatter format_as member when available, otherwise via the library writer. It returns the advanced iterator.

<a id="u-68b6d44433e1"></a>
### `compile.h-field-type`

`template <typename T, typename Enable = void> struct field_type` · [include/fmt/compile.h:L346-L348][f1]

Maps an argument type to the type used for field formatting.

The default removes cv/ref. A named-argument specialization removes cv/ref from its value type instead, so fields format the underlying value.

<a id="u-d0beb62b0404"></a>
### `compile.h-named-argument-lookup`

`template <int N, typename T, typename... Args, typename Char> constexpr auto get_arg_…` · [include/fmt/compile.h:L87-L96][f1]

Searches argument types for a static named argument whose name matches.

The numbered search returns its zero-based index on a match, recurses to later arguments, and returns -1 when none remain. The pack wrapper starts at index 0 only when non-type template arguments are enabled and the pack is nonempty; otherwise it returns -1. The type-list overload delegates to the pack wrapper.

<a id="u-2154e0fbf21d"></a>
### `compile.h-parse-arg-id-result`

`template <typename Char> struct parse_arg_id_result` · [include/fmt/compile.h:L333-L337][f1]

Parses an argument id between two pointers into a result carrying the kind, the reference, and the end pointer.

It initializes a handler in none state and delegates to the library parser; the handler records index or name. Automatic indexing reaches the handler assertion failure path.

<a id="u-bc5f30ac8815"></a>
### `compile.h-parse-specs`

`template <typename T, typename Char> struct parse_specs_result` · [include/fmt/compile.h:L293-L297][f1]

Parses formatter specs starting at a position and reports the formatter, the absolute end offset, and the next argument id.

It removes the prefix, builds a compile_parse_context with maximum value and optional next id, calls the formatter parse, then returns the formatter, the end offset, and either the manual-indexing sentinel when the incoming id was 0 or the context next id.

<a id="u-0d32abfafc1a"></a>
### `compile.h-print`

`template <typename S, typename... T, FMT_ENABLE_IF(is_compiled_string<S>::value)> voi…` · [include/fmt/compile.h:L554-L560][f1]

Writes formatted compiled-string output to a FILE.

The FILE-taking overload formats into a memory buffer and passes the buffer view to the library print routine. The overload without a FILE forwards to stdout. Both return void; I/O effects occur on the selected stream.

<a id="u-31a516e1e2d2"></a>
### `compile.h-runtime-named-field`

`template <typename Char> struct runtime_named_field` · [include/fmt/compile.h:L195-L199][f1]

A replacement field resolved by name at runtime.

The try helper writes only when the argument is a named argument whose name equals the requested name, returning true on a match. Formatting uses a short-circuiting fold over the argument pack, so only the first matching named argument is written even if later arguments share the name; if none matches it throws a format_error. A match advances the output iterator; no match throws.

<a id="u-f57d7627461e"></a>
### `compile.h-spec-field`

`template <typename Char, typename V, int N> struct spec_field` · [include/fmt/compile.h:L227-L231][f1]

A replacement field with parsed format specs for a fixed argument index.

It builds format_args for the supplied arguments, creates a formatting context over the output iterator, then calls the stored formatter on the selected and unwrapped argument and returns the context result. The formatter controls actual output and any formatting failures.

<a id="u-5003d2fa88d1"></a>
### `compile.h-static-format-result`

`class static_format_result` · [include/fmt/compile.h:L568-L573][f1]

Fixed-size compile-time result object.

The constructor formats the compiled string and arguments directly into its internal char array, then writes a null terminator at the returned iterator. The string accessor returns a view of length N-1; the C-string accessor returns the array pointer. The class does not verify that formatted output fits N; N must include the terminator and be large enough.

<a id="u-1dacce77fd97"></a>
### `compile.h-text-fragment`

`template <typename Char> struct text` · [include/fmt/compile.h:L127-L131][f1]

A compiled text fragment stores a string view and writes it to the output iterator.

The factory builds a view over a requested span beginning at a position. Formatting forwards to the library string writer and returns the advanced iterator.

<a id="u-697daeaddc23"></a>
### `compile`

`template <typename... Args, typename S, FMT_ENABLE_IF(is_compiled_string<S>::value)> …` · [include/fmt/compile.h:L454-L468][f1]

Entry point for a compile-time string type.

Empty strings compile directly to empty text; otherwise it chooses dynamic-name mode when the number of static named arguments differs from the total named arguments and starts recursive compilation at position 0 with automatic indexing. It returns the compiled representation, possibly unknown_format.

<a id="u-cde0d6536aec"></a>
### `compile_format_string`

`template <typename Args, size_t POS, int ID, bool DYNAMIC_NAMES, typename S> constexp…` · [include/fmt/compile.h:L384-L452][f1]

Recursively compiles a non-empty format string at compile time into text, code-unit, field, runtime-named-field, or concatenation fragments, returning unknown_format for unresolved named specs when dynamic names are enabled.

- At an opening brace: if it is final, throws a format_error for an unmatched opening brace; if the next character is another opening brace, emits one literal opening brace and continues after both; if the next character is a closing brace or colon, requires the current automatic id not be the manual-indexing sentinel, advances the automatic id, and parses the replacement field for the current argument type; otherwise parses an explicit argument id and requires the following character to be a closing brace or colon.
- Explicit numeric id: requires current indexing be manual or still at 0, then continues with that argument type and forces manual indexing.
- Explicit named id: looks up a static named argument. A static_assert requires either a found index or dynamic names allowed. If found, continues with the named argument value type and an advanced automatic id when not manual. If not found and the following character is a closing brace, emits a runtime named field; if it is a colon and dynamic names are allowed, returns unknown_format because no type is available for specs. If dynamic names are not allowed, the static_assert fails instead of returning unknown_format.
- At a closing brace: if final, throws a format_error for an unmatched closing brace; otherwise emits one literal closing brace and continues after both.
- Ordinary text: scans to the next brace; a run longer than one character becomes a text fragment, a single character becomes a code unit, and parsing continues at the scan end.

<a id="u-a2b513481272"></a>
### `first`

`template <typename T, typename... Tail> constexpr auto first(const T& value, const Ta…` · [include/fmt/compile.h:L67-L70][f1]

Returns a const reference to its first argument and requires at least one argument.

It lets callers inspect the first formatting argument without consuming it.

<a id="u-c46a14dbbea4"></a>
### `get_arg_checked`

`template <typename T, int N, typename... Args> constexpr auto get_arg_checked(const A…` · [include/fmt/compile.h:L158-L166][f1]

Returns the selected argument as a const reference, unwrapping a named argument to its value member when the selected type is a named argument.

It relies on compile-time index selection and adds no runtime bounds check.

<a id="u-7e9d67409ceb"></a>
### `parse_replacement_field_then_tail`

`template <typename T, typename Args, size_t END_POS, int ARG_INDEX, int NEXT_ID, bool…` · [include/fmt/compile.h:L355-L380][f1]

Parses what follows an argument id in a replacement field and continues the tail.

At the character after the id: a closing brace builds a plain field; a character other than colon throws a format_error for an expected colon; a colon parses specs. For specs, if the parsed end is past the string or not a closing brace it throws a format_error for an expected closing brace and returns 0; otherwise it builds a spec field and continues after the brace with the formatter next argument id. The field type comes from the compile-time argument type mapping.

<a id="u-b70e48c8c7d4"></a>
### `parse_tail`

`template <typename Args, size_t POS, int ID, bool DYNAMIC_NAMES, typename T, typename…` · [include/fmt/compile.h:L277-L291][f1]

Continues compilation after the current fragment.

If the position is not at the end, it recursively compiles the rest; an unknown-format result is returned unchanged, otherwise the head and tail are concatenated. At end it returns the head alone.

<a id="u-bf92ab59f46e"></a>
### `parse_text`

`template <typename Char> constexpr auto parse_text(basic_string_view<Char> str, size_…` · [include/fmt/compile.h:L266-L272][f1]

Scans from the given position to the end or until the next opening or closing brace and returns that position.

It does not consume the brace.

<a id="u-ced99c142479"></a>
### `include/fmt/compile.h:format (2)`

`template <typename S, typename... T, FMT_ENABLE_IF(is_compiled_string<S>::value)> FMT…` · [include/fmt/compile.h:L494-L519][f1]

Formats arguments using a compiled string type, with a fast path for the exact char literal consisting of opening and closing braces.

For that exact two-character char literal it converts the first argument to string, unwrapping a named argument value; otherwise it compiles the string. If compilation yields unknown_format it falls back to runtime formatting with the original string view and forwarded arguments; otherwise it formats with the compiled object.

<a id="u-fb8f4fb9f5eb"></a>
### `include/fmt/compile.h:format_to (2)`

`template <typename OutputIt, typename S, typename... T, FMT_ENABLE_IF(is_compiled_str…` · [include/fmt/compile.h:L521-L533][f1]

Formats a compiled string into an output iterator.

It compiles the string; an unknown_format result falls back to runtime format_to with the original string view, while a compiled result is formatted directly. It returns the advanced iterator and does not use the exact empty-field fast path.

<a id="u-7e6dba22ae1e"></a>
### `format_to_n`

`template <typename OutputIt, typename S, typename... T, FMT_ENABLE_IF(is_compiled_str…` · [include/fmt/compile.h:L536-L544][f1]

Writes at most n characters through a fixed buffer traits wrapper, formats the compiled string into an appender over that buffer, and returns the final output iterator plus the count of characters written.

The underlying iterator buffer controls truncation and accounting.

<a id="u-768f7d700ee9"></a>
### `formatted_size`

`template <typename S, typename... T, FMT_ENABLE_IF(is_compiled_string<S>::value)> FMT…` · [include/fmt/compile.h:L546-L552][f1]

Measures formatted output size without retaining it by formatting into a counting buffer and returning its count.

It uses the same compiled-string formatting path.

<a id="u-58b66c1600e1"></a>
### `operator""_cf`

`template <detail::fixed_string Str> constexpr auto operator""_cf()` · [include/fmt/compile.h:L57-L59][f1]

Defines a C++20 literal that turns a fixed string into a compiled format string.

It is exposed only when non-type template arguments are supported; otherwise the declaration is absent. It returns the macro-generated compiled string wrapper.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h
