# Localized tm writer

**Capability.** Coordinates writing a formatted std::tm through chrono spec callbacks, honoring locale settings and transcoding output.

The class-level driver that turns a tm plus parsed specs into output, deciding when locale-dependent formatting applies. It routes localized field output and string transcoding.

**Depends on.**

- [Primitive tm emitters](primitive-tm-emitters.md) · model-inferred · 1 inferred relation(s) · The localized tm writer routes field output through the primitive emitters for digits and name tables.
- [Value writing engine](value-writing-engine.md) · graph-only · 2 edge(s)

Parent: [Chrono and time formatting](chrono-and-time-formatting.md)

## Units (5)

<a id="u-6ca74aa9ba86"></a>
### `chrono.h-locale-writer`

`template <bool UseLocale = FMT_USE_LOCALE != 0> struct locale_writer` · [include/fmt/chrono.h:L412-L413][f1]

Compile-time switch for locale-dependent output, parameterized on FMT_USE_LOCALE.

The true specialization compares the stored locale against the classic one, delegates localized time formatting to write<Char> with the actual locale, and transcodes strings via write_tm_str using the classic locale for non-localized text. The false specialization is a no-op facade: is_classic always returns true, write_time returns the iterator unchanged (never called), and write_str copies verbatim since zone names are ASCII.

<a id="u-1ffe3f379864"></a>
### `chrono.h-tm-writer-core`

`class tm_writer` · [include/fmt/chrono.h:L1083-L1096][f1]

Formats a std::tm (optionally with subsecond duration) through chrono spec callbacks into an output iterator.

The constructor stores locale, localized flag, a precomputed is_classic_ (false only when localized and the locale differs from classic), the output iterator, optional subseconds pointer, and the tm reference; out() returns the advanced iterator after parsing. All on_* handlers choose between built-in English/classic formatting and locale-facade output via locale_writer depending on is_classic_ and the numeric system.

<a id="u-7aad686173c0"></a>
### `include/fmt/chrono.h:tm_writer (5)`

`class tm_writer` · [include/fmt/chrono.h:L1130-L1136][f1]

Class-level coordination of the tm-based chrono writer: it holds a locale_ref, localized flag, precomputed is_classic_ (false only when localized and the locale differs from classic), the output iterator, an optional subsecond duration pointer, and a reference to the std::tm being formatted.

Every on_* callback follows one shared policy: if is_classic_ or the numeric system is standard, emit a hand-rolled ASCII representation via the private write helpers; otherwise delegate to the locale-aware locale_writer (std::time_put facet). The constructor computes is_classic_ once so callbacks can branch cheaply; subsecs_ is only consumed by on_second. Members with their own units in this batch (the field accessors, ISO-week math, write helpers, and each on_* callback) are documented separately.

calls: [chrono.h-locale-writer](localized-tm-writer.md#u-6ca74aa9ba86), [chrono.h-low-level-writers](primitive-tm-emitters.md#u-47017e069603)

**Uncertainties.**

- The class header region alone excludes the separately listed member definitions; member behavior is covered by their own units.

<a id="u-5ea0e9a84337"></a>
### `get_classic_locale`

`inline auto get_classic_locale() -> const std::locale&` · [include/fmt/chrono.h:L310-L313][f1]

Returns a static reference to the classic ("C") locale, avoiding per-call locale construction.

<a id="u-226585ad9fdf"></a>
### `write_encoded_tm_str`

`template <typename OutputIt> auto write_encoded_tm_str(OutputIt out, string_view in, …` · [include/fmt/chrono.h:L336-L363][f1]

Writes a localized tm string to an output iterator, transcoding when needed.

If UTF-8 is in use and the locale is not the classic one, it converts via codecvt to wchar_t (MSVC or single-ABI libstdc++) or char32_t, then re-converts to UTF-8 with to_utf8, throwing format_error on conversion failure; otherwise it copies the input bytes verbatim.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
