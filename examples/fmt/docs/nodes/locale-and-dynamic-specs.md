# Locale and dynamic specs

**Capability.** Adds locale-aware formatting wrappers (bytes, group_digits), digit grouping models, and dynamic width/precision resolution from format arguments.

Readers interested in localized digit grouping or runtime-resolved width/precision will find the facet, grouping model, and dynamic spec getters here. It bridges parsed arg references and the write routines.

**Depends on.**

- [Printf implementation](printf-implementation.md) · graph-only · 3 edge(s)

Parent: [Value writing and drivers](value-writing-and-drivers.md)

## Units (7)

<a id="u-ac44050f5e99"></a>
### `format.h-bytes-formatter`

`struct bytes` · [include/fmt/format.h:L4330-L4333][f1]

bytes wraps a string_view for raw byte formatting; its formatter parses full format specs as a string type, resolves dynamic width/precision at format time, and writes via write_bytes.

<a id="u-9f8eda7ff970"></a>
### `format.h-digit-grouping`

`class digit_grouping` · [include/fmt/format.h:L2127-L2132][f1]

Models locale digit grouping: constructed either from a locale (skipped entirely when not localized, leaving empty separator) or from explicit grouping/separator strings.

next() yields the next separator position: max int when there is no separator; when the grouping iterator is exhausted the last group size repeats; a non-positive or max-char group ends grouping. count_separators counts positions below num_digits. apply writes the digit string inserting the thousands separator at each recorded position (positions collected up front, then walked from the last backward as digits are emitted). has_separator reports whether a separator exists.

<a id="u-9d68bc4962bc"></a>
### `format.h-dynamic-spec-getter`

`struct dynamic_spec_getter` · [include/fmt/format.h:L3982-L3983][f1]

Visitor extracting a width/precision from an argument: integers are returned as ullong, with negative values mapped to ~0ull so the range check rejects them; non-integers report "width/precision is not integer".

<a id="u-adbc9f29f25e"></a>
### `format.h-format-facet`

`class format_facet : public Locale::facet` · [include/fmt/format.h:L4228-L4242][f1]

A locale facet that formats values in UTF-8, holding separator, grouping, and decimal-point strings (defaults: empty separator, "\3" grouping, ".").

put dispatches to the virtual do_put (defined out of line), returning whether the facet handled the value; the locale-taking constructor is also out of line. The class carries a static locale id.

<a id="u-637b49c04ab5"></a>
### `format.h-group-digits`

`template <typename T> struct group_digits_view` · [include/fmt/format.h:L4358-L4360][f1]

group_digits returns a view wrapping an integer; its formatter parses specs as an int type, resolves dynamic width/precision, and writes via write_int with a fixed digit_grouping of "\3" and ',' — a locale-independent thousands separator.

<a id="u-2fe2b63dd5fe"></a>
### `FMT_BEGIN_EXPORT.size_padding.handle_dynamic_spec`

`template <typename Context> FMT_CONSTEXPR void handle_dynamic_spec( arg_id_kind kind,…` · [include/fmt/format.h:L3995-L4007][f1]

Resolves a dynamic width/precision: no-op when the ref kind is none; otherwise looks up the argument by index or name ("argument not found" when absent), visits it with dynamic_spec_getter, and reports "width/precision is out of range" when the value exceeds int, else stores it.

<a id="u-f50fdbcd05bb"></a>
### `FMT_BEGIN_EXPORT.size_padding.native_formatter`

`template <typename T, typename Char, type TYPE> template <typename FormatContext> FMT…` · [include/fmt/format.h:L4099-L4111][f1]

native_formatter::format writes the value with stored specs; when the specs are dynamic it copies them, resolves dynamic width/precision against the context, and writes with the resolved copy.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
