# Packed format specs

**Capability.** Stores format specifier state compactly in one unsigned word with mask-based accessors for type, alignment, sign, and flags.

The basic_specs representation lives here: a bit-packed word plus fill storage, avoiding bitfields for portability. Readers investigating spec memory layout or accessor semantics should look here.

**Depends on.**

- [Numeric core and assertions](numeric-core-and-assertions.md) · graph-only · 1 edge(s)

Parent: [Parsing and buffer foundations](parsing-and-buffer-foundations.md)

## Units (3)

<a id="u-d8fd25336591"></a>
### `core.h-basic-specs-accessors`

`constexpr auto type() const -> presentation_type` · [include/fmt/core.h:L732-L734][f1]

Mask-based constexpr getters/setters for presentation type, alignment, dynamic width/precision arg-id kinds, sign, uppercase, alternate form (set/clear), and localized flag; dynamic() reports whether any width/precision reference is set.

Each setter clears its field's bits before OR-ing the new value.

<a id="u-bdc15eaf9dc4"></a>
### `core.h-basic-specs-storage-layout`

`class basic_specs` · [include/fmt/core.h:L682-L701][f1]

Packs format specifier state into one unsigned word (type, align, dynamic width/precision kinds, sign, uppercase, alternate, localized, fill size in explicit masks/shifts, avoiding bitfields due to compiler bugs) plus a char fill_data_[4] array erased to char to prevent template bloat; data_ starts with fill size 1 and fill defaults to a space.

set_fill_size is the private writer for the fill-size field.

<a id="u-3f58cdd5cdcf"></a>
### `core.h-fill-handling`

`template <typename Char, FMT_ENABLE_IF(std::is_same<Char, char>::value)> constexpr au…` · [include/fmt/core.h:L788-L791][f1]

Fill access: for Char==char fill() returns fill_data_, otherwise nullptr; fill_unit() reassembles a single code unit from the first three bytes.

set_fill(char) stores one byte and fill size 1. set_fill(string_view) stores size 1 by spreading the code unit's bytes (little-endian style) across fill_data_[0..2]; for larger fills it asserts size <= 4 and writes bytes cyclically into fill_data_[i & 3]. copy_fill_from copies both the size field and all four fill bytes from another specs object.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
