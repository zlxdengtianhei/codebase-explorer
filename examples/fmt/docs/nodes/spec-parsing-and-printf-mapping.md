# Spec parsing and printf mapping

**Capability.** Parses the standard specifier grammar into dynamic specs, tracks argument indexing modes, and maps printf conversions to presentation types.

Come here for the grammar-level work: fill/align/sign/width/precision parsing, dynamic spec references, and the compile-time argument indexing state. The printf.h member maps conversion characters onto these presentation types.

**Depends on.**

- [Printf implementation](printf-implementation.md) · graph-only · 13 edge(s)
- [Value writing engine](value-writing-engine.md) · graph-only · 2 edge(s)
- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)

**Depended on by.**

- [OS file and C API](os-file-and-c-api.md) · graph-only · 1 edge(s)

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (14)

<a id="u-75db91c6ae20"></a>
### `core.h-arg-ref-and-dynamic-format-specs`

`template <typename Char> union arg_ref` · [include/fmt/core.h:L1275-L1276][f1]

arg_ref is a union holding either an int index (default 0) or a basic_string_view name for a dynamic width/precision reference.

dynamic_format_specs extends format_specs with width_ref/precision_ref so the same parsed specs can be reused with different argument sets.

<a id="u-04d2e1a8abd3"></a>
### `core.h-compile-parse-context`

`class compile_parse_context : public parse_context<Char>` · [include/fmt/core.h:L1240-L1248][f1]

A parse_context augmented with argument count and a type array, used only in compile-time checks.

next_arg_id() delegates to the base then reports "argument not found" if the id >= num_args_; check_arg_id(int) likewise validates range after the base call, while inheriting the string overload unchanged. check_dynamic_spec reports "width/precision is not integer" when the referenced argument exists and its type is not integral.

<a id="u-f68ad6b640b3"></a>
### `core.h-dynamic-spec-handler`

`template <typename Char> struct dynamic_spec_handler` · [include/fmt/core.h:L1371-L1376][f1]

Callback target for parse_arg_id inside dynamic width/precision parsing: on_index stores the int in ref, sets kind to index, and calls ctx.check_arg_id plus ctx.check_dynamic_spec (so compile-time checks reject non-integral sources); on_name stores the name, sets kind to name, and only calls ctx.check_arg_id(name).

<a id="u-0ad85c4b69da"></a>
### `core.h-format-specs`

`struct format_specs : basic_specs` · [include/fmt/core.h:L831-L835][f1]

Extends basic_specs with concrete int width (default 0) and precision (default -1, meaning unspecified).

<a id="u-4255fbfb52ed"></a>
### `core.h-is-locking`

`template <typename T = int> constexpr auto is_locking() -> bool` · [include/fmt/core.h:L2402-L2404][f1]

Compile-time OR over the locking<> trait of each argument type (cvref-stripped), deciding whether print must use the buffered, locking-safe path.

<a id="u-ce7c6297a217"></a>
### `core.h-parse-align-is-name-start`

`FMT_CONSTEXPR inline auto parse_align(char c) -> align` · [include/fmt/core.h:L1330-L1337][f1]

parse_align maps '<', '>', '^' to left/right/center and returns align::none otherwise; is_name_start accepts ASCII letters and underscore for argument identifiers.

<a id="u-1dbe5dd6b7ff"></a>
### `core.h-parse-context`

`class parse_context` · [include/fmt/core.h:L842-L847][f1]

Tracks the format-string range being parsed plus an argument-indexing mode: next_arg_id_ >= 0 means automatic indexing (value = next id), 0 after none used, and -1 after manual indexing.

next_arg_id() reports an error when switching from manual to automatic indexing, otherwise returns and post-increments the id and validates it via do_check_arg_id. check_arg_id(int) symmetrically rejects automatic-to-manual switching (when next_arg_id_ > 0), then sets manual mode and validates; the string overload just sets manual mode. advance_to shrinks the viewed range. do_check_arg_id and check_dynamic_spec only perform validation in constant evaluation and when the GCC constexpr-cast workaround is enabled: they static_cast `this` to compile_parse_context and check the id against num_args (reporting "argument not found") or that the referenced argument type is integral; at runtime they are no-ops because formatting revalidates.

<a id="u-0024f6f08466"></a>
### `core.h-parse-dynamic-spec`

`template <typename Char> struct parse_dynamic_spec_result` · [include/fmt/core.h:L1389-L1392][f1]

Parses either a literal nonnegative integer or a braced argument reference for width/precision.

A digit lead uses parse_nonnegative_int with error value -1 and reports "number is too big" on overflow, storing the value. A '{' lead: empty braces or ':' take the next automatic id (ctx.next_arg_id, kind=index, check_dynamic_spec); otherwise parse_arg_id with dynamic_spec_handler records the reference. The closing '}' must be present or report_error("invalid format string") fires; the result carries the end iterator and the arg_id_kind (none for literal values).

<a id="u-2b7a14c5470d"></a>
### `core.h-parse-format-specs`

`template <typename Char> FMT_CONSTEXPR auto parse_format_specs(const Char* begin, con…` · [include/fmt/core.h:L1456-L1470][f1]

Parses the standard specifier grammar (fill+align, sign, '#', '0', width, precision, 'L', then a presentation type) into dynamic_format_specs, enforcing both ordering and type compatibility.

An enter_state functor rejects going backwards in the state order or an invalid transition with report_error("invalid format specifier"). A two-char lookahead treats a fill character only when the next char is an alignment token. Per-case behavior: align tokens set alignment; '+'/' ' set sign plus/space and '-' falls through to the same state, valid only for signed-integer or float args; '#' requires arithmetic; '0' requires arithmetic and, if no alignment was set, sets numeric alignment with '0' fill (ignored otherwise for std::format compatibility); digits or '{' parse width; '.' parses precision (valid for float/string/cstring); 'L' requires arithmetic and sets localized. Presentation types validate against type bitsets via parse_presentation_type, which reports "invalid format specifier" on mismatch and returns begin+1: d/x/X/o/b/B for integrals (X/B also set uppercase), e/E/f/F/g/G/a/A for floats, c for integrals but rejected for bool, s for bool/string/cstring, p for pointer/cstring, '?' debug for char/string/cstring. '}' or end terminates; the default case parses a fill code point (rejecting '{' as fill and a missing following alignment) and loops. Non-ASCII spec chars are dropped via to_ascii returning '\0', which falls to the default case.

<a id="u-bbff78b602fc"></a>
### `core.h-parse-width-parse-precision`

`template <typename Char> FMT_CONSTEXPR auto parse_width(const Char* begin, const Char…` · [include/fmt/core.h:L1428-L1435][f1]

parse_width delegates to parse_dynamic_spec, stores the resulting kind in specs via set_dynamic_width, and returns the end iterator.

parse_precision first skips the '.', reports "invalid precision" if the string ends there, then does the same through set_dynamic_precision.

<a id="u-fd5c52fecbe3"></a>
### `core.h-print`

`template <typename... T> FMT_INLINE void print(format_string<T...> fmt, T&&... args)` · [include/fmt/core.h:L2910-L2917][f1]

Writes formatted output to stdout (or a given FILE*): builds the argument store, then chooses a path — when the compile-time literal encoding is not UTF-8 (Windows without /utf-8) it calls vprint_mojibake; otherwise it uses the buffered, lock-aware vprint_buffered when any argument type is locking<>, and plain vprint otherwise.

<a id="u-337f5478e67c"></a>
### `core.h-type-predicates-and-bitset-helpers`

`constexpr auto is_integral_type(type t) -> bool` · [include/fmt/core.h:L1020-L1022][f1]

is_integral_type/is_arithmetic_type test whether a type enum falls in the integer or full numeric range; set(type) builds a single-bit mask and in(type, set) tests membership, used to validate presentation specifiers against argument types.

<a id="u-3c540a60f3cf"></a>
### `include/fmt/core.h:FMT_END_EXPORT (32)`

`FMT_END_EXPORT namespace detail` · [include/fmt/core.h:L1281-L1285][f1]

Extends format_specs with two arg_ref members, width_ref and precision_ref, so width and precision can be recorded as argument references at parse time and resolved per formatting call, enabling reuse of precompiled specifiers with different argument sets.

<a id="u-1b44d7ac70be"></a>
### `parse_printf_presentation_type`

`inline auto parse_printf_presentation_type(char c, type t, bool& upper) -> presentati…` · [include/fmt/printf.h:L391-L413][f2]

Maps a printf conversion character plus the argument's type to a presentation_type, setting `upper` for the uppercase variants.

'd' → dec, 'o' → oct, 'x'/'X' → hex, 'c' → chr (all only for integral-ish types); 'e'/'f'/'g'/'a' and their uppercase forms map to exp/fixed/general/hexfloat for floating types; 's' → string for string/cstring types; 'p' → pointer for pointer or cstring types. Any mismatch between specifier and argument type, or an unknown character, yields presentation_type::none, which vprintf then reports as an invalid format specifier.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/printf.h
