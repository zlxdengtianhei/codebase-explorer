# Formatting driver and contexts

**Capability.** Drives parse callbacks during formatting and provides the argument visitors and generic formatting contexts that connect args to writers.

This module is the runtime engine that walks a parsed format string, dispatches each argument to the right visitor, and carries the output iterator, args, and locale in a context. Read it to understand how formatting actually executes.

**Depends on.**

- [Printf implementation](printf-implementation.md) · graph-only · 4 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 2 edge(s)

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (5)

<a id="u-313a38e7da29"></a>
### `format.h-arg-formatter`

`template <typename Char> struct arg_formatter` · [include/fmt/format.h:L3961-L3966][f1]

Argument visitor applying parsed specs: builtin values go through detail::write with specs and locale; non-builtin types assert false; handles are skipped here because custom types need the parse context and are handled earlier by format_custom.

<a id="u-4087969ad06e"></a>
### `format.h-default-arg-formatter`

`template <typename Char> struct default_arg_formatter` · [include/fmt/format.h:L3936-L3941][f1]

Argument visitor for default (no-specs) formatting: monostate reports "argument not found"; builtin types are written directly; non-builtin types assert false; user-defined handles are formatted with empty parse/format contexts and a null locale so the default form stays unlocalized.

<a id="u-54764412cbe3"></a>
### `format.h-format-handler`

`template <typename Char = char> struct format_handler` · [include/fmt/format.h:L4044-L4048][f1]

Drives parse callbacks during formatting: on_text copies literal text to the output; on_arg_id overloads allocate/check the next id, validate an explicit id, or resolve a name ("argument not found" when the id is negative); on_replacement_field visits the argument with default_arg_formatter; on_format_specs first lets custom types format themselves (returning the advanced parse position), otherwise parses format specs, resolves dynamic width/precision, and visits with arg_formatter.

on_error reports the message.

<a id="u-d2b2072ea02b"></a>
### `format.h-generic-context`

`constexpr generic_context(OutputIt out, basic_format_args<generic_context> args, loca…` · [include/fmt/format.h:L4179-L4182][f1]

A formatting context over a custom output iterator and char type: holds the iterator, args, and locale.

arg overloads fetch by id or name; arg_id maps a name to an id; args exposes the store; out returns the iterator; advance_to updates it only for non-back-insert iterators; locale returns the stored ref. Move-constructible, non-copyable, non-assignable.

<a id="u-50c1515699cb"></a>
### `FMT_BEGIN_EXPORT`

`class fallback_digit_grouping { public: constexpr fallback_digit_grouping(locale_ref,…` · [include/fmt/format.h:L4161-L4177][f1]

generic_context is a formatting context carrying an arbitrary output iterator, a basic_format_args pack, and a locale_ref; it supports move construction, deletes copy and assignment, and exposes arg lookup by index or name, the argument pack, the iterator, advance_to (a no-op for back-insert iterators), and the locale.

Its accessor members are trivial; the class exists so formatting can target custom iterator/character-type combinations.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
