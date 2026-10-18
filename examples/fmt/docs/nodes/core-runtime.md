# Core Runtime & Engine

**Capability.** Owns the non-header runtime of the library: the narrow-char format engine, error reporting, floating-point shortest-representation, FILE output plumbing, locale access, explicit template instantiations, and the C++20 module interface.

Use this subtree for anything that appears in the compiled library rather than a feature header. Children separate concerns that multiple extension headers depend on.

**Children.**

- [Core Format Engine](core-format-engine.md) `core-format-engine` · 4 unit(s)
- [Error Reporting](core-errors.md) `core-errors` · 7 unit(s)
- [Floating-Point Shortest Formatting](core-float.md) `core-float` · 8 unit(s)
- [FILE Output Backend](core-file-output.md) `core-file-output` · 11 unit(s)
- [Locale Support](core-locale.md) `core-locale` · 4 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Units (2)

<a id="u-c6c33bedd668"></a>
### `src/format.cc:detail`

`namespace detail` · [src/format.cc:L17-L42][f1]

Provides explicit API-instantiation points so library symbols are emitted once in this translation unit.

Under FMT_USE_LOCALE, locale_ref's std::locale constructor and get<std::locale> are instantiated (the constructor marked deprecated). In namespace detail it instantiates dragonbox::to_decimal for float and double, thousands_sep_impl and decimal_point_impl for char and wchar_t, and the deprecated buffer<char>/buffer<wchar_t>::append. Each FMT_API instantiation makes the corresponding template callable across translation units.

<a id="u-10d22acdbac7"></a>
### `fmt.cc module code (L1–L165)`

`module_region` · [src/fmt.cc:L1-L165][f2]

Defines the fmt C++20 module interface.

Standard and implementation headers are placed in the global module fragment (or replaced by 'import std' under FMT_IMPORT_STD) so they do not attach to the module; FMT_EXPORT/FMT_BEGIN_EXPORT/FMT_END_EXPORT are mapped to export keywords; all library headers are included in the module purview; and format.cc and os.cc are textually included when FMT_HAS_INCLUDE supports it. Under FMT_ATTACH_TO_GLOBAL_MODULE the declarations are wrapped in extern "C++" so symbols keep traditional mangling and can be mixed with including TUs. FMT_OS gates inclusion of fmt/os.h and os.cc.

**Notes.**

- condition: FMT_ATTACH_TO_GLOBAL_MODULE changes linkage/mangling so importers and includers can be mixed; FMT_IMPORT_STD switches the whole prelude to 'import std'.

**Uncertainties.**

- Exact compiler behavior of module attachment under FMT_ATTACH_TO_GLOBAL_MODULE is asserted by comments, not provable from this source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/format.cc
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/fmt.cc