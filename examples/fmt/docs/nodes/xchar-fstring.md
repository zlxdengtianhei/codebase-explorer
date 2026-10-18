# Wide Format Strings & Args

**Capability.** basic_fstring (compile-time-checked wide format-string wrapper), format-string character traits, runtime_format_string escape hatch, make_wformat_args, and wide named-arg machinery (L"name"_a, arg()).

These are the string/argument building blocks; runtime() deliberately bypasses compile-time checking for runtime format strings.

**Depends on.**

- [Wide Format Entry Points](xchar-entry.md) · model-inferred · 0 edge(s)

Parent: [Wide & Exotic Char Support](xchar-h.md)

## Units (6)

<a id="u-c91ec548f8ca"></a>
### `xchar.h-basic-fstring`

`template <typename S, FMT_ENABLE_IF( std::is_convertible<const S&, basic_string_view<…` · [include/fmt/xchar.h:L95-L101][f1]

basic_fstring<Char, T...> is the wide/exotic-char format-string wrapper (basic_format_string): it stores a basic_string_view<Char> and compile-time-checks the format.

The string convertible constructor is FMT_CONSTEVAL; when FMT_USE_CONSTEVAL is active it parses the format at compile time with format_string_checker built from count_static_named_args/count_named_args and the argument pack, so mismatched arguments become compile errors. The compile_string constructor parses the embedded string in a constexpr context; the runtime_format_string constructor bypasses checking entirely, enabling runtime format strings via runtime(). The deprecated basic_string_view conversion operator and get() both return the stored view. The nested using t = basic_fstring lets wformat_string name the type.

uses: [function::FMT_END_EXPORT.count_static_named_args::34477][f2], [runtime](xchar-fstring.md#u-a216619ae5e5)

**Uncertainties.**

- Whether the non-consteval build skips checking entirely depends on the FMT_USE_CONSTEVAL macro definition, not visible here.

<a id="u-5e72cb1025e6"></a>
### `xchar.h-format-string-char`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/xchar.h:L23-L28][f1]

Trait selecting the character type of a format string S.

The primary template is empty (substitution failure when S is not a string). The first specialization applies when detail::to_string_view(S) is well-formed, yielding char_t<S>; the second applies when S derives from detail::compile_string, yielding S::char_type, and takes precedence for compile-time strings. format_string_char_t is the convenience alias.

<a id="u-a216619ae5e5"></a>
### `runtime`

`inline auto runtime(wstring_view s) -> runtime_format_string<wchar_t>` · [include/fmt/xchar.h:L122-L124][f1]

Wraps a wide string view in a runtime_format_string<wchar_t> so it can be passed where a checked wformat_string is expected, deliberately bypassing compile-time format checking.

uses: [xchar.h-basic-fstring](xchar-fstring.md#u-c91ec548f8ca)

<a id="u-a27e9d38377d"></a>
### `include/fmt/xchar.h:operator""_a`

`inline auto operator""_a(const wchar_t* s, size_t) -> detail::udl_arg<wchar_t>` · [include/fmt/xchar.h:L134-L136][f1]

Wide literal for named arguments: L"name"_a yields a udl_arg<wchar_t> capturing the name.

Only available when FMT_USE_NONTYPE_TEMPLATE_ARGS is disabled (the inline literals namespace is otherwise not opened); the size parameter is ignored.

<a id="u-74fdf36fafde"></a>
### `include/fmt/xchar.h:arg`

`template <typename T> auto arg(const wchar_t* name, const T& arg) -> named_arg<T, wch…` · [include/fmt/xchar.h:L140-L143][f1]

Creates a named_arg<T, wchar_t> binding a wide name to a value, the non-literal counterpart of L"name"_a; the value is referenced, not stored.

<a id="u-9babc9f02b27"></a>
### `make_wformat_args`

`template <typename... T> constexpr auto make_wformat_args(T&... args) -> decltype(fmt…` · [include/fmt/xchar.h:L126-L130][f1]

Builds format arguments for wformat_context from lvalue references via fmt::make_format_args, producing wformat_args.

Arguments are referenced, not copied, so they must outlive the result.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h