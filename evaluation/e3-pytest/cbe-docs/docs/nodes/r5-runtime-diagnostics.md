# Runtime diagnostics and shared primitives

**Capability.** Process-level behavior around test execution: crash-time traceback dumping via faulthandler, deterministic time abstractions, the fixture Scope enum, and the --setupshow/--setuponly display hooks.

Use this subtree for cross-cutting runtime concerns that are not part of collection or reporting but affect how runs behave and what the user sees.

**Children.**

- [Faulthandler plugin](r5-faulthandler-plugin.md) `r5-faulthandler-plugin` · 9 unit(s)
- [Timing and scope primitives](r5-time-scope-primitives.md) `r5-time-scope-primitives` · 4 unit(s)
- [Fixture setup display plugin](r5-setuponly-display.md) `r5-setuponly-display` · 5 unit(s)

Parent: [pytest codebase](r5-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
