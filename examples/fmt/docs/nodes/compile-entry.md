# Compiled Format Entry Points

**Capability.** The compilation driver (compile), is_compiled_string machinery, detail argument access, public format/format_to/format_to_n/print overloads, and the fixed-size compile-time result buffer.

Users call the is_compiled_string-gated overloads here; the driver drives the parser and the static result buffer captures output produced at compile time.

**Depends on.**

- [Compile-Time Parser](compile-parser.md) · model-inferred · 0 edge(s)

Parent: [Compile-Time Format Strings](compile-h.md)

## Units (6)

<a id="u-e2f00286a2b6"></a>
### `compile.h-compiled-string-entry`

`template <typename S> struct is_compiled_string : std::is_base_of<compiled_string, S>` · [include/fmt/compile.h:L23-L24][f1]

Defines the compile-time string machinery that lets a string literal be parsed into efficient formatting code: the marker class compiled_string, the is_compiled_string trait (true only for types derived from compiled_string), and the user-facing conversion paths.

FMT_COMPILE(s) expands to FMT_STRING_IMPL producing a compiled_string when the compiler supports constexpr if and return type deduction, and falls back to FMT_STRING (runtime parsing) otherwise. The _cf literal operator, available only when FMT_USE_NONTYPE_TEMPLATE_ARGS is set, takes a detail::fixed_string template parameter and returns FMT_COMPILE of its data, enabling usage like "{}"_cf inside namespace fmt::literals.

**Notes.**

- condition: Both __cpp_if_constexpr and __cpp_return_type_deduction must be defined for FMT_COMPILE to produce a compiled string rather than FMT_STRING.
- condition: operator""_cf is only declared under FMT_USE_NONTYPE_TEMPLATE_ARGS.

contract: [compile](compile-entry.md#u-697daeaddc23); uses: [compile.h-compiled-string-entry](compile-entry.md#u-e2f00286a2b6)

**Uncertainties.**

- FMT_STRING_IMPL and FMT_STRING definitions live outside this file, so their expansion is not verified here.

<a id="u-697daeaddc23"></a>
### `compile`

`template <typename... Args, typename S, FMT_ENABLE_IF(is_compiled_string<S>::value)> …` · [include/fmt/compile.h:L454-L468][f1]

Entry point that compiles an is_compiled_string type into a format piece tree for the argument types Args...

For an empty format string it returns an empty text piece directly. Otherwise it counts static versus total named arguments to set DYNAMIC_NAMES (true exactly when there are runtime-only named arguments), then invokes compile_format_string over a type_list of the argument types starting at position 0 with id 0. If any field could not be compiled, the returned unknown_format propagates to the callers, which fall back to runtime formatting. This function is only defined when the compiler supports constexpr if and return type deduction.

calls: [compile_format_string](compile-parser.md#u-cde0d6536aec); uses: [compile.h-text](compile-repr.md#u-07be70836afb)

<a id="u-aff04a0392ad"></a>
### `compile.h-detail-helpers`

`FMT_END_EXPORT namespace detail` · [include/fmt/compile.h:L63-L66][f1]

Compile-time argument-access helpers inside namespace detail.

first(value, ...) returns a reference to its first argument, used by the fast path in format for single-argument strings. get<N>(first, rest...) returns a reference to the argument at index N by recursively returning get<N-1>(rest...); a static_assert fires when N exceeds the argument count. The three get_arg_index_by_name overloads resolve a format argument name to a positional index: the templated overload walks the argument list, returning N when the argument is a static named arg whose T::name matches; otherwise, if more arguments remain it recurses with N+1, and after exhausting the list returns -1. A variadic wrapper forwards to that walker when FMT_USE_NONTYPE_TEMPLATE_ARGS is enabled and there are arguments, otherwise returning -1; a type_list overload adapts the call. get_type_impl maps index N to remove_cvref_t of decltype(get<N>(declval<Args>()...)), so get_type yields the static argument type at N. The primary is_compiled_format template is std::false_type; later specializations mark recognized compiled-format pieces as true. The (void)name statements exist to silence an MSVC unused-parameter warning.

**Notes.**

- failure: get<N> fails at compile time via static_assert for out-of-range indices.
- condition: Name-based index lookup is only wired up when FMT_USE_NONTYPE_TEMPLATE_ARGS is enabled; otherwise the wrapper always returns -1.

uses: [compile.h-compile-format-string](../../catalog.json)

<a id="u-1806810465fc"></a>
### `compile.h-format-overloads`

`template <typename CompiledFormat, typename... T, typename Char = typename CompiledFo…` · [include/fmt/compile.h:L476-L485][f1]

Public formatting entry points that consume compiled formats.

The first format overload accepts any type satisfying is_compiled_format and appends via cf.format into a std::basic_string, returning it; format_to likewise forwards cf.format on an arbitrary output iterator. The string-based format overload (for is_compiled_string types) first takes a char-only fast path: when the format string is exactly "{}" it returns fmt::to_string of the first argument, unwrapping the value if it is a named argument. Otherwise it compiles the string with detail::compile<T...>; if compilation returned unknown_format it falls back to the ordinary runtime fmt::format with the string as a view, and otherwise formats with the compiled tree. The string-based format_to mirrors this: compile, then dispatch to runtime fmt::format_to for unknown_format or to the compiled-format overload. Both are only defined under constexpr-if/return-type-deduction support.

**Notes.**

- condition: The fast path applies only when char_type is char and the format string is exactly two characters, '{' followed by '}'.
- failure: unknown_format (e.g. named args with specs) silently degrades to runtime format-string parsing rather than failing.

calls: [compile](compile-entry.md#u-697daeaddc23), [compile.h-detail-helpers](compile-entry.md#u-aff04a0392ad)

**Uncertainties.**

- The runtime fmt::format and fmt::format_to overloads resolved here are declared elsewhere; their behavior is taken as given.

<a id="u-ebb18a601d49"></a>
### `compile.h-format-to-n-and-prints`

`template <typename OutputIt, typename S, typename... T, FMT_ENABLE_IF(is_compiled_str…` · [include/fmt/compile.h:L536-L544][f1]

Bounded and sink-based entry points over compiled strings, all gated on is_compiled_string.

format_to_n wraps the output iterator in an iterator_buffer with fixed_buffer_traits sized to n, runs fmt::format_to through it, and returns the resulting iterator plus the count produced by the buffer. formatted_size formats into a counting_buffer and returns buf.count(), computing the output size without producing text. print(std::FILE*, ...) formats into a memory_buffer and passes it to detail::print; the one-argument print overload forwards to print(stdout, ...). These do not use the compile-time piece trees directly; they go through fmt::format_to with the compiled string.

**Notes.**

- side_effect: The print overloads write to the given FILE stream (stdout by default).

uses: [compile.h-format-overloads](compile-entry.md#u-1806810465fc)

**Uncertainties.**

- detail::iterator_buffer, counting_buffer, memory_buffer, and detail::print are defined outside this file; their truncation and counting semantics are not verified here.

<a id="u-5003d2fa88d1"></a>
### `compile.h-static-format-result`

`class static_format_result` · [include/fmt/compile.h:L568-L573][f1]

A fixed-size, N-byte char buffer holding a fully formatted, null-terminated string produced at compile time.

The explicit constexpr constructor formats the given compiled string and arguments into data via fmt::format_to and writes '\0' at the returned position, so the buffer must be exactly large enough plus one. str() returns a fmt::string_view of length N-1 over the buffer and c_str() returns the raw pointer. FMT_STATIC_FORMAT(fmt_str, ...) instantiates static_format_result with N set to fmt::formatted_size(FMT_COMPILE(fmt_str), __VA_ARGS__) + 1 and constructs it with the same compiled string, making both size computation and contents constant-expression work.

**Notes.**

- contract: If the actual output would differ from the constant-expression size computation, writing the terminator could run past the buffer; size and arguments must match.

uses: [compile.h-format-to-n-and-prints](compile-entry.md#u-ebb18a601d49)

**Uncertainties.**

- No runtime bounds check exists in the constructor; safe use depends on the macro's size expression being evaluated with identical arguments.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h