# Argument storage and checking

**Capability.** Defines formatting arguments, their type-erased storage, named-argument handling, and compile-time format string validation.

Come here for the argument system: basic_format_arg, the packed/unpacked format_args view, named-argument stores and duplicate checks, and the compile-time format string checker. It is the data model everything else formats.

**Depends on.**

- [Value writing engine](value-writing-engine.md) · graph-only · 3 edge(s)
- [Printf implementation](printf-implementation.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Inline implementation and stdio](inline-implementation-and-stdio.md) · graph-only · 2 edge(s)

Parent: [Format argument infrastructure](format-argument-infrastructure.md)

## Units (15)

<a id="u-ce0fb7dcfe66"></a>
### `core.h-basic-format-arg`

`class basic_format_arg` · [include/fmt/core.h:L2466-L2476][f1]

One formatting argument: a detail::value union plus a detail::type tag; default-constructed as none_type (falsy via explicit operator bool).

The template constructor stores the value and tags it with stored_type_constant (built-ins may be forced to custom_type when the context disables builtin types). The nested handle class wraps a custom_value and its format() invokes the stored function pointer with the argument pointer, parse context, and format context. visit() switches on the tag and calls the visitor with the concrete stored value (128-bit values pass through detail::map, strings pass string_view, custom passes a handle); none_type falls through to vis(monostate()). format_custom returns false for non-custom types, otherwise advances the parse context to the given begin and invokes the custom format callback, returning true.

<a id="u-674075b02c81"></a>
### `core.h-basic-format-args`

`class basic_format_args { private: // A descriptor that contains information about fo…` · [include/fmt/core.h:L2547-L2547][f1]

Non-owning view of formatting arguments, described by an ullong descriptor: packed mode stores 4-bit type codes in desc_ and values in a value array; unpacked mode sets the high bit and stores the count plus a basic_format_arg array; a second high bit marks named arguments.

The union pointer aliases values_ or args_ depending on mode.
The store constructors copy the descriptor (OR-ing the named-args bit when needed) and point at the store's array; the dynamic constructor builds an unpacked descriptor from a pointer and count. get(id) returns a default (none) argument when out of range; in unpacked mode it indexes args_, in packed mode it extracts the type from desc_ and, if not none, copies the corresponding value. get(name) resolves the id via get_id then get(id). get_id returns -1 when there are no named args, otherwise reads the named-arg table stored just before the values array (values_[-1] packed, args_[-1].value_ unpacked) and linearly matches names. max_size returns max_packed_args in packed mode or the count masked out of the descriptor.

<a id="u-1756748a259a"></a>
### `core.h-check-for-duplicate`

`template <typename Char> struct named_arg_info` · [include/fmt/core.h:L1086-L1089][f1]

Scans the already-registered named_arg_info entries (indices [0, named_arg_index)) and calls report_error("duplicate named arg") if any name pointer-equals the new arg_name; named_arg_info itself is just a {name, id} pair.

<a id="u-337ec0cac97f"></a>
### `core.h-compile-time-counters`

`template <bool B = false> constexpr auto count() -> int` · [include/fmt/core.h:L1074-L1074][f1]

count<B...> sums boolean template parameters; count_named_args/count_static_named_args apply it to the is_named_arg/is_static_named_arg traits over a pack, yielding the number of named arguments at compile time.

<a id="u-9dac999707b8"></a>
### `core.h-context`

`class context` · [include/fmt/core.h:L2644-L2654][f1]

The char formatting context: holds an output appender, the format_args view, and a type-erased locale_ref (which occupies no storage when empty via FMT_NO_UNIQUE_ADDRESS).

Movable, non-copyable, non-assignable. arg(id)/arg(name) fetch arguments by index or name, arg_id(name) returns the numeric id (-1 if absent), args() exposes the store, out() returns the output iterator, advance_to is a no-op (appenders need no repositioning), and locale() returns the stored locale reference. builtin_types reflects the FMT_BUILTIN_TYPES configuration, which affects how stored_type_constant tags built-in values.

<a id="u-4a02041a04c5"></a>
### `core.h-format-arg-store-make-format-args`

`template <typename Context, int NUM_ARGS, int NUM_NAMED_ARGS, ullong DESC> struct for…` · [include/fmt/core.h:L2358-L2366][f1]

format_arg_store chooses between a plain value/basic_format_arg array (when no named args) and named_arg_store, sizing arrays at compile time.

make_format_args takes arguments by lvalue reference (to avoid dangling temporaries) and returns the store for the given Context, with descriptor, counts, and named-arg tallies computed at compile time; the store converts implicitly to format_args.

<a id="u-e7fb7ad77211"></a>
### `core.h-format-string-checker`

`class format_string_checker { private: type types_[max_of<size_t>(1, NUM_ARGS)]; name…` · [include/fmt/core.h:L1691-L1691][f1]

Compile-time format string validator holding per-argument type enums, static named-arg info, a compile_parse_context, and one parse function pointer per argument (invoke_parse for each T).

The constructor fills types_ with mapped_type_constant values and registers static named args via init_static_named_arg. on_text is a no-op. on_arg_id() takes the next automatic id (range-checked by the context); on_arg_id(int) validates via check_arg_id; on_arg_id(name) linearly searches named_args_ and, when not found, reports "argument not found" unless dynamic names are allowed (then returns -1). on_replacement_field re-enters on_format_specs with an empty range so parse() still runs. on_format_specs advances the context and, for a known id, calls that argument's parse function; for out-of-range ids it skips the spec text with a bracket counter that tolerates nested '{'...'}' pairs. on_error forwards to report_error, which is a compile-time error in constant evaluation.

<a id="u-eb7683569819"></a>
### `core.h-fstring`

`struct fstring` · [include/fmt/core.h:L2698-L2724][f1]

Compile-time-checked format string: stores the string_view and, when consteval is supported, runs parse_format_string with a format_string_checker parameterized on the argument types during construction in constant evaluation, so invalid format strings fail to compile.

The const char(&)[N] constructor also static_asserts that no view types are passed as lvalues. The const S& constructor (convertible to string_view) performs the same check; the compile_string-based constructor (FMT_STRING) checks in a FMT_CONSTEXPR expression. A runtime_format_string argument skips checking. Conversion to string_view is deprecated; get() returns the stored view. format_string<T...> is this type, used in the public API to prevent deduction.

<a id="u-dd7c4a35527a"></a>
### `core.h-init-named-arg-init-static-named-arg`

`template <typename Char, typename T, FMT_ENABLE_IF(!is_named_arg<T>::value)> void ini…` · [include/fmt/core.h:L1101-L1104][f1]

Pack-expansion helpers that walk arguments in order: the non-named overloads just increment arg_index; the named overloads run check_for_duplicate and append {name, arg_index} to the named_args array, using T::name for static named args.

Dispatch is by the is_named_arg/is_static_named_arg traits.

<a id="u-d8ed3822f62d"></a>
### `core.h-named-arg`

`template <typename T, typename Char = char> struct named_arg : view` · [include/fmt/core.h:L1066-L1070][f1]

Deprecated-in-detail wrapper holding a name pointer and a const reference to the value, deriving from view; a static_assert rejects nested named arguments.

<a id="u-391fffc3f17c"></a>
### `core.h-named-arg-store`

`template <typename Context, int NUM_ARGS, int NUM_NAMED_ARGS, ullong DESC> struct nam…` · [include/fmt/core.h:L2327-L2327][f1]

Storage for arguments that include named ones: an args array whose slot 0 holds a pointer to the named_args table (so format_args can find names), plus the named_arg_info array itself.

The variadic constructor initializes args from the values and registers named args via init_named_arg (which also rejects duplicates). The move constructor rebuilds args[0] to point at this object's own named_args and copies the remaining slots; copy and assignment are deleted. Implicitly converts to a pointer to args+1 for consumption by basic_format_args.

<a id="u-6b93a9b0ffc1"></a>
### `core.h-runtime-format-string`

`template <typename Char = char> struct runtime_format_string` · [include/fmt/core.h:L2682-L2684][f1]

runtime_format_string is a plain wrapper around a string_view; runtime(s) marks a format string to be checked at runtime rather than compile time by wrapping it in this type.

<a id="u-a091c555d2c0"></a>
### `core.h-value`

`template <typename Char> struct string_value` · [include/fmt/core.h:L2122-L2125][f1]

Type-erased formatting argument stored in a union (integers by width, bool, char, floats, pointer, string_value {data,size}, custom_value {void* value, format function pointer}, named_arg_value).

Constructors narrow small integer types, collapse long/unsigned long via long_type, and pass built-in types through the FMT_BUILTIN_TYPES configuration (when disabled, built-ins take the custom path as monostate). Code-unit values static_assert against mixing character types. char_type pointers store only the data pointer and set size 0 in constant evaluation (size computed later at runtime); string-like types store data+size from to_string_view with a char-type static_assert. void*/const void*/volatile-void pointers store as const void*; nullptr stores a null pointer; non-void object and member pointers trigger a static_assert forbidding their formatting. format_as and formatter::format_as results recurse into the matching constructor; named args recurse on their value. Types with formatters go to the custom_tag constructor: it stores the object's address (via reinterpret_cast to dodge overloaded operator&, or nullptr with a constexpr-conditional address in constant evaluation) and format_custom as the callback; format_custom constructs formatter<T>, runs parse, then calls const format with the possibly-const qualified argument and advances the context. Types without a formatter instantiate the intentionally-undefined type_is_unformattable_for, producing a compile-time error. The named_arg_info overload stores a pointer to the named-argument table in the union.

<a id="u-453afce36cbc"></a>
### `include/fmt/core.h:basic_format_args (8)`

`class basic_format_args` · [include/fmt/core.h:L2684-L2693][f1]

Named lookup on basic_format_args: get(name) resolves the name to an id with get_id and returns get(id), or a default (none-type) argument when the id is negative.

get_id returns -1 immediately when the descriptor lacks the named-args bit; otherwise it reads the named_arg_info array stored in the slot just before the values (values_[-1] when packed, args_[-1].value_ otherwise) and returns the id of the first entry whose name compares equal, or -1 if none matches.

<a id="u-f90b3841b598"></a>
### `arg`

`template <typename T> inline auto arg(const char* name, const T& arg) -> named_arg<T>` · [include/fmt/core.h:L2800-L2803][f1]

Creates a named_arg binding a name string to a value reference for use inside a single formatting call; such dynamic named args are not compile-time checked.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
