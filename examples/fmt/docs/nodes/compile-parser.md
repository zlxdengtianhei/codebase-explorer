# Compile-Time Parser

**Capability.** Recursive constexpr parsing of a format string at a position into pieces, including text-run scanning and replacement-field tail parsing.

compile_format_string dispatches on the next character; parse-tail builds field and text pieces referencing the representation types.

**Depends on.**

- [Compiled Piece Representation](compile-repr.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Compiled Format Entry Points](compile-entry.md) · model-inferred · 0 edge(s)

Parent: [Compile-Time Format Strings](compile-h.md)

## Units (3)

<a id="u-cde0d6536aec"></a>
### `compile_format_string`

`template <typename Args, size_t POS, int ID, bool DYNAMIC_NAMES, typename S> constexp…` · [include/fmt/compile.h:L384-L452][f1]

Parses one element of a non-empty format string at position POS and returns the compiled piece for it, dispatching on the character at POS.

If it is '{': a '{' at the last position throws format_error("unmatched '{' in format string"); '{{' emits a one-character text piece and continues at POS+2; '{' followed by '}' or ':' requires automatic indexing (static_assert forbids switching from manual indexing), computes next_id as ID+1 unless already manual, and delegates to parse_replacement_field_then_tail with get_type<ID, Args>; any other character parses an argument id, static_asserts the next character is '}' or ':' ("missing '}' in format string"), and then branches by id kind: an explicit index forbids switching from automatic indexing (ID must be manual or 0) and continues with manual_indexing_id; a name is resolved via get_arg_index_by_name, where a found index (>=0, or accepted under static_assert only when not found and DYNAMIC_NAMES) continues with field parsing for the named argument's value type, otherwise a '}' terminator emits a runtime_named_field, while a ':' terminator returns unknown_format because there is no static type information for spec parsing. If str[POS] is '}': a '}' at the last position throws format_error("unmatched '}' in format string"); otherwise '}}' emits a one-character text piece and continues at POS+2. Any other character scans to the next brace with parse_text and emits either a text piece (run longer than one character) or a single code_unit. All pieces are threaded through parse_tail, which concatenates them.

**Notes.**

- failure: Unmatched braces and malformed argument ids are compile-time errors via FMT_THROW/static_assert.
- condition: DYNAMIC_NAMES (true when the call has more named args than static named args) is what permits falling back to runtime_named_field instead of failing the 'named argument not found' static_assert.

calls: [compile.h-parse-tail-and-field-parsing](compile-parser.md#u-903eb405f7b8), [compile.h-parse-text](compile-parser.md#u-3f6574b02ed5); uses: [compile.h-text](compile-repr.md#u-07be70836afb)

**Uncertainties.**

- Whether get_type<ID, Args> is well-formed for every reachable ID depends on caller-provided Args; mismatched argument counts are diagnosed in the helpers via static_assert.

<a id="u-3f6574b02ed5"></a>
### `compile.h-parse-text`

`struct unknown_format` · [include/fmt/compile.h:L264-L264][f1]

Scans literal text to find the end of a text run, and marks unrecognized input.

parse_text walks the string from pos, stopping at the first '{' or '}' or at the string end, and returns the stopping position; callers use it to carve out literal text segments. unknown_format is an empty tag type returned by compile_format_string when input cannot be compiled (notably named arguments with specifiers, where there is no static type information to parse specs against), causing the public entry points to fall back to the runtime formatter.

uses: [compile_format_string](compile-parser.md#u-cde0d6536aec)

<a id="u-903eb405f7b8"></a>
### `compile.h-parse-tail-and-field-parsing`

`template <typename Args, size_t POS, int ID, bool DYNAMIC_NAMES, typename T, typename…` · [include/fmt/compile.h:L277-L291][f1]

The recursive replacement-field parser for compiled format strings.

parse_tail continues compilation at POS: if POS reaches the string size it returns the accumulated head piece; otherwise it calls compile_format_string for the remainder and, unless that yields unknown_format, combines head and tail with make_concat. parse_specs<T> strips the prefix before the specifiers, creates a compile_parse_context (with max int range and the incoming next_arg_id), runs formatter<T>::parse, and returns the formatter, the end position, and a next id that becomes the sentinel manual_indexing_id (-1) once an explicit index has been seen (next_arg_id == 0). arg_id_handler records the parsed id kind: on_auto asserts false and returns 0 (automatic indexing is handled before this handler is used), on_index/on_name record an index or name reference. parse_arg_id<ID> parses the id between '{' and the following character, returning kind, reference, and end pointer. field_type maps a type to remove_cvref_t<T>, or to the type of T::value for named arguments. parse_replacement_field_then_tail<T, Args, END_POS, ARG_INDEX, NEXT_ID, DYNAMIC_NAMES> looks at the character at END_POS: if it is '}' it emits a field (with field_type-unwrapped T) and continues after it; if it is neither '}' nor ':' it throws format_error("expected ':'"); if it is ':', it parses specifiers, throws format_error("expected '}'") when the closing brace is missing, and otherwise emits a spec_field and continues with the resulting next_arg_id. parse_specs_result carries the formatter, end offset, and next id; the anonymous enum defines manual_indexing_id = -1.

**Notes.**

- failure: Malformed fields throw format_error with messages 'expected :' or 'expected }' during constant evaluation.
- contract: Once an explicit index appears, NEXT_ID becomes manual_indexing_id so later automatic fields are rejected by static_asserts in compile_format_string.

calls: [compile_format_string](compile-parser.md#u-cde0d6536aec), [compile.h-concat](compile-repr.md#u-5fe5d05c7f01); uses: [compile.h-spec-field](compile-repr.md#u-f57d7627461e), [compile.h-field](compile-repr.md#u-9dbf88a38412)

**Uncertainties.**

- arg_id_handler::on_auto asserts and returns 0; whether this is reachable depends on callers, and the assert behavior in constexpr evaluation is not established here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h