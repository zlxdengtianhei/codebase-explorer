# Wide & Exotic Char Support

**Capability.** Full formatting API surface for wchar_t and other exotic character types: checked wide format strings, wide args and named-arg literals, locale-aware formatting, and print/println to FILE and wostream.

Use for non-char encodings; format-string traits pick the character type, and every entry point funnels into the exotic-char detail::vformat_to.

**Children.**

- [Wide Format Strings & Args](xchar-fstring.md) `xchar-fstring` · 6 unit(s)
- [Exotic Char Format Core](xchar-core.md) `xchar-core` · 8 unit(s)
- [Wide Format Entry Points](xchar-entry.md) `xchar-entry` · 15 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
