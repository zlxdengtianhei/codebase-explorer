# BitInt support

**Capability.** Conditional Clang _BitInt type aliases and formatters casting values of at most 64 bits to standard integer formatters.

Handles Clang's _BitInt extension: defines detail aliases when enabled and provides formatters that cast to long long variants. Larger widths are rejected at compile time.

Parent: [Standard library type formatters](standard-library-type-formatters.md)

## Units (3)

<a id="u-5bab8836a8a7"></a>
### `std.h-bitint-formatter`

`template <int N, typename Char> struct formatter<detail::bitint<N>, Char> : formatter…` · [include/fmt/std.h:L688-L691][f1]

Formats Clang _BitInt values of at most 64 bits by static_cast to long long and delegating to the long long formatter; a static_assert rejects N > 64.

The placeholder struct version (when _BitInt is unavailable) still compiles but has nothing to cast.

<a id="u-5ba3f04c3c8d"></a>
### `std.h-ubitint-formatter`

`template <int N, typename Char> struct formatter<detail::ubitint<N>, Char> : formatte…` · [include/fmt/std.h:L700-L703][f1]

Formats unsigned _BitInt values of at most 64 bits by casting to unsigned long long and delegating to the ullong formatter; N > 64 fails a static_assert.

<a id="u-0ef21667216f"></a>
### `include/fmt/std.h:FMT_BEGIN_NAMESPACE (11)`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/std.h:L89-L97][f1]

This region conditionally defines detail::bitint<N> and detail::ubitint<N>: as Clang _BitInt(N)/unsigned _BitInt(N) when FMT_USE_BITINT is enabled (Clang ≥15.0, not CUDA, with a -Wbit-int-extension pragma suppression), otherwise as empty struct placeholders so dependent formatters compile but are unusable.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
