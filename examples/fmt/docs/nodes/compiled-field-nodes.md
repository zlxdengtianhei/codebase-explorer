# Compiled field nodes

**Capability.** Defines the replacement-field node types and the per-field compiler that produces them from parsed argument ids and specs.

This module holds the node vocabulary for compiled formats: plain fields, named fields, spec fields, and the compiler that turns one replacement field plus its tail into nodes. It also defines the unknown_format fallback tag.

Parent: [fmt: Compile Format](fmt-compile-format.md)

## Units (7)

<a id="u-9dbf88a38412"></a>
### `compile.h-field`

`template <typename Char, typename V, int N> struct field` · [include/fmt/compile.h:L172-L175][f1]

A replacement field referring to argument N.

format fetches the argument (unwrapping named args) and branches at compile time: if convertible to basic_string_view it copies the string; else if format_as or a member format_as applies, it writes format_as(arg) or formatter<V>::format_as(arg); otherwise it writes the value directly with write<Char>.

<a id="u-68b6d44433e1"></a>
### `compile.h-field-type`

`template <typename T, typename Enable = void> struct field_type` · [include/fmt/compile.h:L346-L348][f1]

Maps an argument type to the type actually formatted: normally the cv/ref-stripped type, but for named arguments the type of the wrapped value.

<a id="u-f24d36d0dab8"></a>
### `compile.h-is-compiled-format-trait-family`

`template <typename T> struct is_compiled_format : std::false_type` · [include/fmt/compile.h:L125-L125][f1]

Primary template is false_type; each specialization (text, code_unit, field, runtime_named_field, spec_field, concat) is true_type, tagging node types produced by the compile-time format-string parser so format/format_to accept them via enable_if.

<a id="u-31a516e1e2d2"></a>
### `compile.h-runtime-named-field`

`template <typename Char> struct runtime_named_field` · [include/fmt/compile.h:L195-L199][f1]

A replacement field resolved by name at runtime.

format folds try_format_argument over the arguments: for each named argument whose name matches, it writes arg.value and returns true; if no argument matches, it throws format_error("argument with specified name is not found").

<a id="u-f57d7627461e"></a>
### `compile.h-spec-field`

`template <typename Char, typename V, int N> struct spec_field` · [include/fmt/compile.h:L227-L231][f1]

A replacement field with format specifiers for argument N.

format builds a basic_format_context over the output iterator and all arguments, then delegates to the stored formatter<V,Char> parsed at compile time, formatting the (named-arg-unwrapped) N-th argument.

<a id="u-7e9d67409ceb"></a>
### `parse_replacement_field_then_tail`

`template <typename T, typename Args, size_t END_POS, int ARG_INDEX, int NEXT_ID, bool…` · [include/fmt/compile.h:L355-L380][f1]

Compiles one replacement field plus its tail.

If the character after the field is '}', it builds a plain field for argument ARG_INDEX and continues at the next position; if it is not ':', it throws format_error("expected ':'"); otherwise it parses specs for the field type and, if the specs are not terminated by '}', throws format_error("expected '}'"), else builds a spec_field and continues with the parser's next_arg_id.

<a id="u-e0c6dfa08a74"></a>
### `unknown_format`

`struct unknown_format` · [include/fmt/compile.h:L264-L264][f1]

Empty tag type returned by the compiler when a format string cannot be compiled (e.g. runtime-named field with specs), signaling callers to fall back to runtime formatting.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h
