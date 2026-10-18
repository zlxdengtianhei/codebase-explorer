# Wide Format Entry Points

**Capability.** Public wide/exotic-char format, format_to (plain, locale, generic), format_to_n, formatted_size, to_wstring, print/println/vprint (FILE and wostream), and wide join overloads.

Call these from user code; each packs wide args and forwards to the core subtree's vformat family.

**Depends on.**

- [Exotic Char Format Core](xchar-core.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Wide Format Strings & Args](xchar-fstring.md) · model-inferred · 0 edge(s)

Parent: [Wide & Exotic Char Support](xchar-h.md)

## Units (15)

<a id="u-c25121bdc76a"></a>
### `include/fmt/xchar.h:format (2)`

`template <typename... T> auto format(wformat_string<T...> fmt, T&&... args) -> std::w…` · [include/fmt/xchar.h:L187-L190][f1]

Wide-string format entry point: takes a compile-time-checked wformat_string, packs arguments with make_wformat_args, and returns vformat's std::wstring.

Argument/format mismatches are caught at compile time through basic_fstring.

calls: [include/fmt/xchar.h:vformat (2)](xchar-core.md#u-3d812594b50c)

<a id="u-d178a8535105"></a>
### `include/fmt/xchar.h:format (3)`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L200-L207][f1]

Generic exotic-char format: Char is derived from the format string S via format_string_char_t and must be neither char nor wchar_t.

Converts S to a string view, builds arguments for buffered_context<Char>, and returns vformat's std::basic_string<Char>.

uses: [include/fmt/xchar.h:vformat (2)](xchar-core.md#u-3d812594b50c)

<a id="u-2b6b83b6d480"></a>
### `include/fmt/xchar.h:format (4)`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L219-L226][f1]

Locale-aware format overload: forwards the locale plus string view and packed buffered_context<Char> arguments to the locale vformat and returns its string.

Char must be exotic.

calls: [include/fmt/xchar.h:vformat (3)](xchar-core.md#u-3188ee0608a4)

<a id="u-b46162e99872"></a>
### `include/fmt/xchar.h:format`

`template <typename... T> inline auto format(text_style ts, wformat_string<T...> fmt, …` · [include/fmt/xchar.h:L348-L352][f1]

Color-aware wide format: packs wide arguments and returns vformat(ts, ...) so the styled result includes the text_style's ANSI escapes.

calls: [include/fmt/xchar.h:vformat](xchar-core.md#u-90bfb1dc242c)

<a id="u-9c0c1fe55c7c"></a>
### `include/fmt/xchar.h:format_to`

`template <typename OutputIt, typename... T> auto format_to(OutputIt out, wformat_stri…` · [include/fmt/xchar.h:L192-L196][f1]

Wide format_to: writes checked-format output through vformat_to to the given OutputIt and returns the iterator past the last written character.

uses: [include/fmt/xchar.h:vformat_to (2)](xchar-core.md#u-64e113389e95)

**Uncertainties.**

- The overload resolves against one of the vformat_to overloads declared later in the file; which one for a raw OutputIt depends on overload resolution outside this unit.

<a id="u-ede40b663f33"></a>
### `include/fmt/xchar.h:format_to (2)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L239-L247][f1]

Generic format_to for Char that is neither char nor wchar_t: packs arguments for buffered_context<Char> and forwards to vformat_to, returning the advanced OutputIt.

calls: [include/fmt/xchar.h:vformat_to (2)](xchar-core.md#u-64e113389e95)

<a id="u-f872eacd5360"></a>
### `include/fmt/xchar.h:format_to (3)`

`template <typename OutputIt, typename S, typename... T, typename Char = detail::forma…` · [include/fmt/xchar.h:L261-L269][f1]

Locale-aware format_to with a bool enable gate on output-iterator and exotic-char requirements: forwards the locale and packed arguments to vformat_to via SFINAE-enabled return; when enable is false the overload is removed from the candidate set.

calls: [include/fmt/xchar.h:vformat_to (3)](xchar-core.md#u-f8d71482a4f6)

<a id="u-1b65b660dd90"></a>
### `include/fmt/xchar.h:format_to_n`

`template <typename OutputIt, typename... T, FMT_ENABLE_IF(detail::is_output_iterator<…` · [include/fmt/xchar.h:L283-L288][f1]

Wide format_to_n: FMT_INLINE wrapper taking a checked wformat_string, packing make_wformat_args, and returning vformat_to_n's result (iterator past output plus total count).

The generic overload for non-char/non-wchar Char forwards the string view and buffered_context<Char> arguments identically.

calls: [vformat_to_n](xchar-core.md#u-7a64503e6cbc)

<a id="u-c6b9884589de"></a>
### `include/fmt/xchar.h:formatted_size`

`template <typename S, typename... T, typename Char = detail::format_string_char_t<S>,…` · [include/fmt/xchar.h:L301-L309][f1]

Computes the number of Char code units formatting would produce, without output: formats into a counting_buffer via detail::vformat_to and returns buf.count().

Enabled for exotic Char only.

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2)

<a id="u-cfba6dbb5108"></a>
### `to_wstring`

`template <typename T> inline auto to_wstring(const T& value) -> std::wstring` · [include/fmt/xchar.h:L372-L374][f1]

Converts any formattable value to std::wstring using the default '{}' format, via format(FMT_STRING(L"{}"), value); a compile-time-checked literal so malformed internal specs cannot occur.

<a id="u-d73413ffe7dc"></a>
### `include/fmt/xchar.h:print`

`template <typename... T> void print(std::FILE* f, wformat_string<T...> fmt, T&&... args)` · [include/fmt/xchar.h:L323-L326][f1]

Wide print wrappers: both pack arguments with make_wformat_args and forward to vprint — the first to an explicit FILE*, the second to stdout.

Return type void; formatting errors propagate from the engine and I/O errors from vprint.

calls: [include/fmt/xchar.h:vprint](xchar-entry.md#u-5d145e6cc2ac)

<a id="u-0f2076553706"></a>
### `include/fmt/xchar.h:println`

`template <typename... T> void println(std::FILE* f, wformat_string<T...> fmt, T&&... …` · [include/fmt/xchar.h:L332-L335][f1]

Wide println: formats the arguments with fmt::format, then calls print with L"{}\n" so the pre-formatted result is emitted followed by a newline — to a FILE* in one overload, to stdout in the other.

This double-formatting means runtime costs are two passes over the value.

calls: [include/fmt/xchar.h:format (2)](xchar-entry.md#u-c25121bdc76a), [include/fmt/xchar.h:print](xchar-entry.md#u-d73413ffe7dc)

**Uncertainties.**

- Because the value is formatted first and re-printed via '{}', dynamic width/precision specs in the original format apply to the inner format call, not the final print — an observable semantic worth noting but not proven beyond this code path.

<a id="u-5d145e6cc2ac"></a>
### `include/fmt/xchar.h:vprint`

`inline void vprint(std::FILE* f, wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L311-L317][f1]

Wide vprint to a FILE*: formats into a wmemory_buffer, appends a L'\0' terminator, and writes with std::fputws.

If fputws returns -1 it throws system_error(errno, "cannot write to file"); there is no silent-failure path. The one-argument overload forwards to this with stdout.

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2), [include/fmt/xchar.h:vprint](xchar-entry.md#u-5d145e6cc2ac)

<a id="u-5737a2b91886"></a>
### `include/fmt/xchar.h:vprint (3)`

`inline void vprint(std::wostream& os, wstring_view fmt, wformat_args args)` · [include/fmt/xchar.h:L354-L358][f1]

Wide vprint to a std::wostream: formats into a basic_memory_buffer<wchar_t> and writes it with detail::write_buffer.

No stream error checking is done here; failures depend on write_buffer's behavior. The print overload packs arguments for buffered_context<wchar_t> and forwards to it; the println overload routes through print with L"{}\n" like its FILE* counterpart.

calls: [include/fmt/xchar.h:vformat_to](xchar-core.md#u-1543a9ab5af2); uses: [write_buffer][f2]

**Uncertainties.**

- write_buffer's exception/flush behavior for wostream is not visible in this file.

<a id="u-f0c81b9d5d93"></a>
### `xchar.h-join`

`template <typename Range, typename S, typename Char = typename decltype(detail::to_st…` · [include/fmt/xchar.h:L153-L161][f1]

Four join overloads for exotic character types (Char derived from the separator's string view, enabled only when !std::is_same<Char, char>::value or, for the first overload, is_exotic_char).

The iterator/sentinel overload returns join_view{begin, end, separator}; the range overload (disabled for tuple-like ranges) uses std::begin/std::end; the deprecated initializer_list overload forwards to the iterator form with wstring_view separators; the tuple-like overload returns tuple_join_view{tuple, separator}. All separators are converted with detail::to_string_view and none of them format immediately — they return lazy views formatted later.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h