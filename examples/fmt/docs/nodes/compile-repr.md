# Compiled Piece Representation

**Capability.** Types representing compiled format content: literal text, code units, indexed and spec-carrying fields, runtime-named fields, and concatenation nodes.

These types form the value tree produced by the compiler; the parser and entry points operate over them.

**Depended on by.**

- [Compile-Time Parser](compile-parser.md) · model-inferred · 0 edge(s)

Parent: [Compile-Time Format Strings](compile-h.md)

## Units (6)

<a id="u-07be70836afb"></a>
### `compile.h-text`

`template <typename Char> struct text` · [include/fmt/compile.h:L127-L131][f1]

Represents literal text segments of a compiled format string.

text stores a basic_string_view into the original format string and its format overload writes that view to the output iterator via write<Char>, ignoring any format arguments. make_text builds a text from a source string view, position and length, computing the subview pointer as &s[pos]; the resulting piece is marked as a compiled format through the is_compiled_format<text<Char>> specialization so it is accepted by the public format/format_to overloads. Because the view points into the format string, the text piece is only valid while the underlying string data lives.

uses: [compile.h-compile-format-string](../../catalog.json)

**Uncertainties.**

- make_text has no bounds check on pos, so callers must pass positions within the string; enforcement is in callers.

<a id="u-f7cbc87178b9"></a>
### `compile.h-code-unit`

`template <typename Char> struct code_unit` · [include/fmt/compile.h:L146-L150][f1]

Represents a single literal character of a compiled format string.

code_unit stores one Char and its format overload writes that character by *out++ and returns the advanced iterator, ignoring arguments. get_arg_checked<N, Args...> retrieves the argument at index N with detail::get and, when the retrieved argument is a named argument, unwraps and returns arg.value instead of the wrapper, ensuring the value type is convertible to const T&. The is_compiled_format<code_unit<Char>> specialization marks this piece as compiled so the public overloads accept it.

calls: [compile.h-detail-helpers](compile-entry.md#u-aff04a0392ad); uses: [compile.h-field](compile-repr.md#u-9dbf88a38412)

<a id="u-9dbf88a38412"></a>
### `compile.h-field`

`template <typename Char, typename V, int N> struct field` · [include/fmt/compile.h:L172-L175][f1]

A compiled replacement field referring to argument N with no format specifiers.

field stores only the value type V and index N; its format overload fetches the argument via get_arg_checked<V, N>(args...) and chooses the write path at compile time: if V is convertible to basic_string_view<Char>, it constructs the view and copies the character range to the output; if use_format_as<V> holds it writes format_as(arg); if use_format_as_member<V> holds it writes formatter<V>::format_as(arg); otherwise it writes the argument with the generic write<Char>. The is_compiled_format specialization marks field as a compiled format piece.

**Notes.**

- contract: The string_view branch bypasses the formatter for the argument, so only the character data is copied.

uses: [compile.h-code-unit](compile-repr.md#u-f7cbc87178b9), [compile.h-compile-format-string](../../catalog.json)

**Uncertainties.**

- The precedence of the string_view, format_as, and format_as_member branches is compile-time; whether V actually satisfies any branch depends on type traits defined outside this file.

<a id="u-f57d7627461e"></a>
### `compile.h-spec-field`

`template <typename Char, typename V, int N> struct spec_field` · [include/fmt/compile.h:L227-L231][f1]

A compiled replacement field referring to argument N that carries parsed format specifiers.

spec_field stores a formatter<V, Char> produced by parse_specs. Its FMT_INLINE format overload builds format args from the actual arguments, constructs a basic_format_context wrapping the output iterator and those args, fetches the target argument with get_arg_checked<V, N>, and delegates to the stored formatter's format. The is_compiled_format specialization marks spec_field as a compiled format piece.

uses: [compile.h-parse-replacement-field](../../catalog.json), [compile.h-code-unit](compile-repr.md#u-f7cbc87178b9)

<a id="u-31a516e1e2d2"></a>
### `compile.h-runtime-named-field`

`template <typename Char> struct runtime_named_field` · [include/fmt/compile.h:L195-L199][f1]

A compiled replacement field whose argument is resolved by name at runtime.

runtime_named_field stores the name from the format string. The static try_format_argument is constexpr but performs a runtime comparison: if the candidate argument is a named argument and its name equals arg_name, it writes arg.value to out and returns true; otherwise it returns false without touching out. format folds try_format_argument over all arguments with operator||; on the first match the output iterator has been advanced through the reference. If no argument matches, format throws format_error("argument not found").

**Notes.**

- failure: Unmatched names raise format_error at runtime, unlike static named fields which are diagnosed at compile time.

uses: [compile.h-compile-format-string](../../catalog.json)

<a id="u-5fe5d05c7f01"></a>
### `compile.h-concat`

`template <typename L, typename R> struct concat` · [include/fmt/compile.h:L244-L249][f1]

A binary tree node that concatenates two compiled format pieces.

concat stores left and right subpieces, derives char_type from the left one, and formats by writing lhs then rhs to the same output iterator, returning the final iterator. make_concat is a convenience constructor. The is_compiled_format<concat<L, R>> specialization marks it as a compiled format so public format/format_to overloads accept the resulting tree.

uses: [compile.h-parse-tail-and-field-parsing](compile-parser.md#u-903eb405f7b8)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h