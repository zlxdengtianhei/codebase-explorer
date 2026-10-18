# Terminal Color & Styling

**Capability.** Models text styles (packed foreground/background/emphasis), renders them as ANSI escape sequences, and exposes styled format/print/println APIs.

Use fg/bg/operator| to build styles and styled() or the styled format overloads to apply them; the model subtree defines the packed representation the API renders.

**Children.**

- [Style Model](color-model.md) `color-model` · 7 unit(s)
- [Styled Formatting API](color-format-api.md) `color-format-api` · 11 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
