# Locale Support

**Capability.** Retrieves locale-dependent numeric punctuation via the numpunct facet, bridges locale_ref, and performs locale-aware numeric writing.

Use for locale-sensitive numeric formatting; format_facet and write_loc feed the engine when a locale is supplied.

Parent: [Core Runtime & Engine](core-runtime.md)

## Units (4)

<a id="u-3082fa11c74c"></a>
### `format-inl.h-locale-facet-accessors`

`template <typename Char> FMT_FUNC auto thousands_sep_impl(locale_ref loc) -> thousand…` · [include/fmt/format-inl.h:L130-L137][f1]

Retrieve locale-dependent numeric punctuation through the numpunct facet.

thousands_sep_impl obtains the locale via locale_ref::get (a workaround for a gcc 14 bug), asks use_facet for numpunct<Char>, takes its grouping string, and returns the facet's thousands separator only when the grouping is non-empty (otherwise Char(), meaning no separator); decimal_point_impl returns the facet's decimal_point character. Both propagate whatever the facet calls return and behave differently under FMT_USE_LOCALE versus the stub facets.

calls: [locale_ref](core-locale.md#u-584bdbd8244c)

<a id="u-584bdbd8244c"></a>
### `locale_ref`

`template <typename Locale> auto locale_ref::get() const -> Locale` · [include/fmt/format-inl.h:L75-L82][f1]

Extracts the std::locale-like object stored in a locale_ref as type Locale.

A static_assert requires Locale to be exactly detail::locale, so only that type is retrievable. When locale support is enabled and the stored pointer is non-null, it dereferences the pointer; otherwise (no support or null pointer) it returns a default-constructed locale.

**Notes.**

- failure: With FMT_USE_LOCALE disabled, a fallback empty locale/numpunct stub set makes get return a valueless locale whose facets supply grouping "\03", ',' thousands separator, and '.' decimal point.

uses: [locale][f1]

<a id="u-eaf81af5e2af"></a>
### `include/fmt/format-inl.h:format_facet`

`template <> FMT_API FMT_FUNC auto format_facet<std::locale>::do_put( appender out, lo…` · [include/fmt/format-inl.h:L176-L181][f1]

Builds a format_facet from a locale by copying its numpunct<char> facet settings: grouping_ gets the facet's grouping string, and separator_ becomes a one-character string of the facet's thousands separator only when grouping is non-empty.

The facet returned by the stub use_facet (locale support disabled) yields grouping '\03' and separator ','.

calls: [format-inl.h-locale-facet-accessors](core-locale.md#u-3082fa11c74c)

<a id="u-fcde12893ba2"></a>
### `write_loc`

`FMT_FUNC auto write_loc(appender out, loc_value value, const format_specs& specs, loc…` · [include/fmt/format-inl.h:L144-L153][f1]

Formats a loc_value with the given specs using a locale-aware facet, returning true if the locale path handled the value.

It fetches std::locale from the locale_ref; if the locale already holds a format_facet<std::locale> it uses use_facet to get it, otherwise constructs one from the locale, and in both cases delegates to put(out, value, specs). It exists only when FMT_USE_LOCALE is set; the num_put facet is deliberately avoided for encoding reasons. The boolean return reflects whether put wrote the output.

**Uncertainties.**

- Whether put can return false (falling back to the default writer) is decided in format_facet's put, not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format-inl.h