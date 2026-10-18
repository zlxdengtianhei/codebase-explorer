# command-line option processing

**Capability.** Turning argv into tool configuration: option-table lookup, per-flag dispatch by argument kind, and dedicated value parsers for complex option syntaxes.

parse_args iterates argv into getparameter, which resolves the flag via the lookup helpers and dispatches to the opt_* family; complex values are handed to the parse_*/set_* helpers. The easygetopt units provide the library-side name/id lookup over easy setopt options and are kept here for their shared option-table responsibility.

**Children.**

- [option table lookup](r11-option-table-lookup.md) `r11-option-table-lookup` · 7 unit(s)
- [flag dispatch and simple assignment](r11-arg-dispatch.md) `r11-arg-dispatch` · 18 unit(s)
- [complex option value parsers](r11-option-value-parsers.md) `r11-option-value-parsers` · 25 unit(s)

Parent: [curl codebase](r11-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
