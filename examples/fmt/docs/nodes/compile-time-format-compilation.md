# Compile-time format compilation

**Capability.** Compiles format strings into node trees at compile time and provides format/format_to/format_to_n entry points over compiled strings.

The FMT_COMPILE machinery lives here: parsing a compiled_string into nodes, resolving argument ids and specs at compile time, and the formatting entry points that execute the node tree. Readers using compile-time formats should start here.

Parent: [fmt: Compile Format](fmt-compile-format.md)

## Units (20)

<a id="u-ee725bc06fc8"></a>
### `compile.h-arg-id-handler`

`template <typename Char> struct arg_id_handler` · [include/fmt/compile.h:L313-L317][f1]

Handler for parse_arg_id callbacks: on_auto asserts false (automatic indexing unsupported here); on_index and on_name record the kind and an arg_ref carrying the numeric index or name string.

<a id="u-00bbd92fa850"></a>
### `compile.h-compiled-string-trait-and-literal`

`template <typename S> struct is_compiled_string : std::is_base_of<compiled_string, S>` · [include/fmt/compile.h:L23-L24][f1]

Trait detecting types deriving from the empty marker class compiled_string; the _cf literal operator (C++20 non-type template parameter path) wraps a fixed_string literal into FMT_COMPILE, producing a compile-time format string.

FMT_COMPILE itself falls back to FMT_STRING when constexpr-if or return-type deduction is unavailable.

<a id="u-3747e99fbdfa"></a>
### `compile.h-named-argument-index-lookup`

`template <int N, typename T, typename... Args, typename Char> constexpr auto get_arg_…` · [include/fmt/compile.h:L87-L96][f1]

Overloads resolving a named argument's positional index at compile time.

The variadic version walks the pack: if a type is a static named arg whose name matches, returns its index; otherwise recurses, finally returning -1 when no match or the pack is empty. The type_list overload and the empty-args overload delegate to this logic, always returning -1 on failure.

<a id="u-10d6ea1bd4a1"></a>
### `compile.h-parse-arg-id`

`template <typename Char> struct parse_arg_id_result` · [include/fmt/compile.h:L333-L337][f1]

Parses an argument id between begin and end using arg_id_handler, returning the kind, the arg_ref, and the pointer just past the parsed id.

<a id="u-bc5f30ac8815"></a>
### `compile.h-parse-specs`

`template <typename T, typename Char> struct parse_specs_result` · [include/fmt/compile.h:L293-L297][f1]

Parses format specifiers for type T starting at pos using a compile_parse_context with the given next_arg_id and a formatter<T,Char>; returns the parsed formatter, the absolute end position, and the next argument id (manual_indexing_id when next_arg_id was 0, i.e. manual indexing).

<a id="u-0d32abfafc1a"></a>
### `compile.h-print`

`template <typename S, typename... T, FMT_ENABLE_IF(is_compiled_string<S>::value)> voi…` · [include/fmt/compile.h:L554-L560][f1]

Formats into a memory_buffer and writes it to the given FILE* (or stdout in the two-argument overload) via detail::print.

<a id="u-5003d2fa88d1"></a>
### `compile.h-static-format-result`

`class static_format_result` · [include/fmt/compile.h:L568-L573][f1]

Holds a fixed-size char array; the constructor formats into it with format_to and NUL-terminates.

str() returns a string_view of length N-1 and c_str() the raw pointer; used by FMT_STATIC_FORMAT, whose size comes from a constexpr formatted_size plus one for the terminator.

<a id="u-697daeaddc23"></a>
### `compile`

`template <typename... Args, typename S, FMT_ENABLE_IF(is_compiled_string<S>::value)> …` · [include/fmt/compile.h:L454-L468][f1]

Entry point compiling a compiled_string: an empty string yields an empty text node; otherwise it compiles with a type_list of the argument types, enabling dynamic names when the count of static named args differs from the total named args.

<a id="u-cde0d6536aec"></a>
### `compile_format_string`

`template <typename Args, size_t POS, int ID, bool DYNAMIC_NAMES, typename S> constexp…` · [include/fmt/compile.h:L384-L452][f1]

Core compile-time parser turning a non-empty format string into a node tree, returning unknown_format for uncomposable constructs.

At each position: '{' at the very end throws "unmatched '{'"; "{{" emits a literal '{' text node; "{" followed by '}' or ':' uses automatic indexing (static_assert forbids switching from manual), advancing the id; otherwise it parses an explicit id, requiring '}' or ':' after it, and for an index forbids switching from automatic indexing (only from id 0 or manual), while for a name it looks up the static index and either compiles a typed field, falls back to a runtime_named_field when the name is unknown and dynamic names are allowed, or returns unknown_format when specs follow an unresolved name. '}' at the end throws "unmatched '}'"; otherwise a lone '}' emits a literal '}' text node. Plain text runs become a text node, or a code_unit node for a single character.

<a id="u-a2b513481272"></a>
### `first`

`template <typename T, typename... Tail> constexpr auto first(const T& value, const Ta…` · [include/fmt/compile.h:L67-L70][f1]

Returns the first of a variadic argument pack by reference; used to access the sole argument of a "{}" compiled format without materializing a tuple.

<a id="u-3b7380d4ef10"></a>
### `get`

`template <int N, typename T, typename... Args> constexpr auto get([[maybe_unused]] co…` · [include/fmt/compile.h:L76-L84][f1]

Recursively returns the N-th argument of a pack by reference with a static_assert bounding N against the pack size; the base case returns the first argument.

<a id="u-c46a14dbbea4"></a>
### `get_arg_checked`

`template <typename T, int N, typename... Args> constexpr auto get_arg_checked(const A…` · [include/fmt/compile.h:L158-L166][f1]

Fetches the N-th argument and unwraps named arguments to their .value, guaranteeing the returned reference is convertible to const T& for the field's formatting call.

<a id="u-bf92ab59f46e"></a>
### `parse_text`

`template <typename Char> constexpr auto parse_text(basic_string_view<Char> str, size_…` · [include/fmt/compile.h:L266-L272][f1]

Scans a format string from pos forward, returning the index of the first '{' or '}' (or the end of the string).

<a id="u-813833e97e76"></a>
### `include/fmt/compile.h:format`

`template <typename CompiledFormat, typename... T, typename Char = typename CompiledFo…` · [include/fmt/compile.h:L476-L485][f1]

Formats through an already-compiled format node into a fresh std::basic_string via back_inserter, returning the string.

<a id="u-ced99c142479"></a>
### `include/fmt/compile.h:format (2)`

`template <typename S, typename... T, FMT_ENABLE_IF(is_compiled_string<S>::value)> FMT…` · [include/fmt/compile.h:L494-L519][f1]

Formats using a compiled_string.

For char strings exactly "{}" it short-circuits to fmt::to_string of the first argument (unwrapping named args). Otherwise it compiles the string; if compilation yields unknown_format it falls back to runtime fmt::format with the string view, else formats through the compiled node.

<a id="u-88b80d5d3f42"></a>
### `include/fmt/compile.h:format_to`

`template <typename OutputIt, typename CompiledFormat, typename... T, FMT_ENABLE_IF(de…` · [include/fmt/compile.h:L487-L492][f1]

Formats through a compiled format node directly to the output iterator, returning the advanced iterator.

<a id="u-fb8f4fb9f5eb"></a>
### `include/fmt/compile.h:format_to (2)`

`template <typename OutputIt, typename S, typename... T, FMT_ENABLE_IF(is_compiled_str…` · [include/fmt/compile.h:L521-L533][f1]

Compiles the compiled_string and formats to the output iterator; on unknown_format it falls back to runtime fmt::format_to with the string view.

<a id="u-7e6dba22ae1e"></a>
### `format_to_n`

`template <typename OutputIt, typename S, typename... T, FMT_ENABLE_IF(is_compiled_str…` · [include/fmt/compile.h:L536-L544][f1]

Formats to at most n characters by routing output through an iterator_buffer with fixed_buffer_traits, returning the advanced iterator and the count of characters produced.

<a id="u-768f7d700ee9"></a>
### `formatted_size`

`template <typename S, typename... T, FMT_ENABLE_IF(is_compiled_string<S>::value)> FMT…` · [include/fmt/compile.h:L546-L552][f1]

Computes the formatted length by formatting into a counting_buffer and returning its count; no output is stored.

<a id="u-3147295007de"></a>
### `get_type_impl<N, type_list<Args...>>`

`template <int N, typename... Args> struct get_type_impl<N, type_list<Args...>>` · [include/fmt/compile.h:L117-L120][f1]

Maps index N and a type_list of argument types to the cv/ref-stripped type of the N-th argument, via get_type.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/compile.h
