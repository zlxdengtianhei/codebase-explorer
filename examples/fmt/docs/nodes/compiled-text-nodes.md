# Compiled text nodes

**Capability.** Implements literal text, code-unit, and concatenation nodes that execute compiled format strings by writing directly to the output iterator.

The leaf nodes of compiled formats live here: text, single code unit, and the concat combiner that chains compiled head and tail. Read this to see how a compiled format string actually emits output.

Parent: [fmt: Compile Format](fmt-compile-format.md)

## Units (4)

<a id="u-f7cbc87178b9"></a>
### `compile.h-code-unit`

`template <typename Char> struct code_unit` · [include/fmt/compile.h:L146-L150][f1]

A single-character text node; format appends the stored code unit through the output iterator and ignores arguments.

<a id="u-c67b13a24e8d"></a>
### `compile.h-concat-node`

`template <typename L, typename R> struct concat` · [include/fmt/compile.h:L244-L249][f1]

Binary node chaining two compiled-format nodes; format runs the left node, then the right with the same output iterator and arguments, returning the final iterator.

make_concat constructs it.

<a id="u-a64ee9b34523"></a>
### `compile.h-text-node`

`template <typename Char> struct text` · [include/fmt/compile.h:L127-L131][f1]

A literal-text node holding a string_view; its format writes the text via write<Char> and ignores all arguments.

make_text builds a node from a position and length of a format string.

<a id="u-b70e48c8c7d4"></a>
### `parse_tail`

`template <typename Args, size_t POS, int ID, bool DYNAMIC_NAMES, typename T, typename…` · [include/fmt/compile.h:L277-L291][f1]

Given a compiled head node and the remaining format string, recursively compiles the tail; if the tail is unknown_format it propagates that tag, otherwise it returns concat(head, tail); when the position reaches the string end it returns just the head.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h
