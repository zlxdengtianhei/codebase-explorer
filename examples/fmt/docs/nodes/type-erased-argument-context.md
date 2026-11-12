# Type-Erased Argument Context

**Capability.** Holds type-erased formatting arguments, argument views, and char formatting contexts for the formatting pipeline.

This module defines type-erased argument and context objects. Readers find argument views, descriptors, and char-output formatting context types.

**Depended on by.**

- [Platform File and Locale Internals](platform-file-and-locale-internals.md) · graph-only · 1 edge(s)

Parent: [Argument and Spec Pipeline](argument-and-spec-pipeline.md)

## Units (5)

<a id="u-ce0fb7dcfe66"></a>
### `core.h-basic-format-arg`

`class basic_format_arg` · [include/fmt/core.h:L2466-L2476][f1]

Type-erased formatting argument holding a value and a type tag.

The nested handle wraps a custom value and formats it by calling the stored callback. Default construction is none; a named-argument constructor stores metadata; the templated constructor stores a value and derives its type from the stored type constant. Conversion to bool is true for any non-none type. visit switches on the tag and calls the visitor with the matching union member; 128-bit values pass through map, strings pass a string_view, custom values pass a handle, and none falls through to monostate. format_custom returns false for non-custom arguments; for custom arguments it advances the parse context to the given position, invokes the custom callback, and returns true.

<a id="u-674075b02c81"></a>
### `core.h-basic-format-args`

`class basic_format_args` · [include/fmt/core.h:L2547-L2554][f1]

View over formatting arguments with a packed or unpacked descriptor.

The descriptor stores packed type nibbles, an unpacked bit, a named-args bit, and the count when unpacked. Constructors from a store set the descriptor and choose the packed values pointer or unpacked args pointer; the dynamic constructor marks unpacked and records count and named-args presence. type(index) extracts the four-bit type at that index. get(id) returns none for out-of-range ids; for unpacked args it returns the stored argument when id is below max_size; for packed args it returns none at or above the packed limit, otherwise sets the type and copies the value only when the type is not none. get(name) resolves through get_id and returns none when not found. get_id returns -1 without named args; otherwise it reads the named metadata from the slot before the arguments and linearly searches by name content. max_size is the packed limit when packed, otherwise the descriptor count with the unpacked bit removed.

<a id="u-56a2e405540f"></a>
### `core.h-fstring-constructors`

`struct fstring` · [include/fmt/core.h:L2698-L2724][f1]

The array constructor static_asserts that no view is passed as an lvalue and then parses the format string.

The const S& constructor only parses the format string; it does not repeat the view-lvalue static_assert.

<a id="u-523333dfa908"></a>
### `context`

`class context` · [include/fmt/core.h:L2644-L2654][f1]

Formatting context for char output.

It holds an appender, format_args, and a locale reference; char_type is char and builtin_types reflects the build setting. It exposes argument lookup by id or name, name-to-id lookup, the argument view, the output appender, a no-op advance_to, and the locale reference. Copy is deleted; move is defaulted.

<a id="u-453afce36cbc"></a>
### `include/fmt/core.h:basic_format_args (8)`

`class basic_format_args` · [include/fmt/core.h:L2684-L2693][f1]

A type-erased view over formatting arguments and a descriptor.

The descriptor encodes packed type bits and flags; packed arguments live in a value array, unpacked arguments in a basic_format_arg array. get(id) returns an empty argument for out-of-range or none types, get(name) scans named arguments via get_id, and max_size reports the packed limit or descriptor count. Constructors from argument stores set the named-argument flag; the view does not own argument storage.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
