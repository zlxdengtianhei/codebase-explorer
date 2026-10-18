# printf Arg Visitors

**Capability.** Argument visitors and traits: arg/char converters rewriting args in place, get_cstring, zero/int probes, width/precision-safe int checks, and bool-preserving unsigned mapping.

These visitors are applied by convert_arg during engine processing; each answers one question about a type-erased argument.

**Depended on by.**

- [printf Engine & API](printf-engine.md) · model-inferred · 0 edge(s)

Parent: [printf Compatibility](printf-h.md)

## Units (8)

<a id="u-e998dc5b36e1"></a>
### `printf.h-arg-converter`

`arg_converter(basic_format_arg<Context>& arg, char_type type) : arg_(arg), type_(type)` · [include/fmt/printf.h:L128-L129][f1]

arg_converter<T, Context> is a visitor that rewrites the referenced format arg in place to a printf-appropriate integer type.

The bool overload delegates to the integral path unless the conversion specifier is 's', in which case the bool is preserved. The integral overload derives signedness from the specifier ('d' or 'i' means signed, anything else unsigned) and the target type: when the requested type T (or U itself if T is void) fits in an int, the value is narrowed through that type and stored as int (signed) or unsigned int (unsigned); otherwise it widens to long long for signed or to the unsigned form of U for unsigned, deliberately not mimicking glibc's non-sign-extension of small types since that is UB. Non-integral visited values are left untouched. The constructor takes the arg by reference and the conversion-specifier character, so assignments mutate the caller's arg.

**Notes.**

- side_effect: Each operator() overload assigns through the stored basic_format_arg& arg_, replacing the argument's stored value.

<a id="u-48de9e8f2997"></a>
### `printf.h-char-converter`

`explicit char_converter(basic_format_arg<Context>& arg) : arg_(arg)` · [include/fmt/printf.h:L176-L176][f1]

char_converter<Context> is a visitor that rewrites the referenced format arg to a Context::char_type character: integral visited values are stored as static_cast<typename Context::char_type>(value); non-integral values are left unchanged.

Used by vprintf for the '%c' conversion.

**Notes.**

- side_effect: Assigns through basic_format_arg<Context>& arg_, replacing the argument in place.

<a id="u-002edf2eb327"></a>
### `printf.h-get-cstring`

`template <typename T> auto operator()(T) -> const Char*` · [include/fmt/printf.h:L190-L190][f1]

get_cstring<Char> is a visitor extracting a C string pointer: any visited type other than const Char* yields nullptr, while const Char* yields the pointer itself.

vprintf uses the null result to treat the value as a non-string when applying precision truncation.

<a id="u-b8f55385065e"></a>
### `printf.h-int-checker`

`template <typename T> static auto fits_in_int(T value) -> bool` · [include/fmt/printf.h:L72-L74][f1]

int_checker<IS_SIGNED> provides a static fits_in_int(T) used to test range without triggering signed/unsigned comparison warnings.

For unsigned values (IS_SIGNED=false) it checks value <= to_unsigned(max_value<int>()) so large unsigned values above INT_MAX fail; the bool overload always returns true. For signed values it checks both numeric_limits<int>::min() and max_value<int>() bounds; the int overload always returns true. Instantiating with bool where IS_SIGNED is false matches the bool overload and trivially passes.

<a id="u-986df532695c"></a>
### `printf.h-is-zero-int`

`template <typename T, FMT_ENABLE_IF(std::is_integral<T>::value)> auto operator()(T va…` · [include/fmt/printf.h:L103-L106][f1]

is_zero_int is an argument visitor answering whether the visited arg is a zero integer: integral values return value == 0, any non-integral type returns false.

It is used in vprintf to decide C-printf semantics for the '#' flag on zero values.

<a id="u-d15cd413ad55"></a>
### `printf.h-make-unsigned-or-bool`

`template <typename T> struct make_unsigned_or_bool : std::make_unsigned<T>` · [include/fmt/printf.h:L114-L114][f1]

A trait mapping T to its unsigned counterpart via std::make_unsigned, with a bool specialization whose ::type stays bool so boolean arguments are not turned into 0/1 unsigned ints during printf argument conversion.

<a id="u-ea90dc0f4b07"></a>
### `convert_arg`

`template <typename T, typename Context, typename Char> void convert_arg(basic_format_…` · [include/fmt/printf.h:L165-L168][f1]

Applies arg_converter<T, Context> to the given format arg using the conversion-specifier character, converting integer arguments to the length-modified type T (or to signed/unsigned from the specifier when T is void).

Conversion happens only for integral visited values; everything else passes through unchanged.

calls: [printf.h-arg-converter](printf-support.md#u-e998dc5b36e1)

<a id="u-b6e9cfc87444"></a>
### `printf.h-detail-find`

`template <> inline auto find<false, char>(const char* first, const char* last, char v…` · [include/fmt/printf.h:L61-L67][f1]

Two overloads locate the first occurrence of a value in a pointer range, returning the result through an out parameter to work around gcc bug 77539.

The generic FMT_CONSTEXPR version walks from first to last with ++, setting out to each position; it returns true with out at the match, or false with out == last when nothing matches. The explicit find<false, char> specialization uses memchr over to_unsigned(last - first) bytes: out becomes the match pointer or nullptr, and the function returns out != nullptr. Callers in vprintf rely on the false case leaving it at last (they explicitly reset it to end), but the memchr overload actually leaves it nullptr on failure, which the caller compensates for.

uses: [vprintf](printf-engine.md#u-0f7d73d0497e)

**Uncertainties.**

- The generic overload's constexpr path is not exercised in this file; its compile-time behavior is unproven here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/printf.h