# Core Support Libraries

**Capability.** Self-contained, low-level utilities (legacy path objects, exception-proof reprs, source introspection, reversible monkey patching) with no knowledge of pytest's plugin machinery; they belong together as dependency-free foundations for plugins and tests.

Use this subtree for infrastructure primitives rather than test-run logic. Consumers include Pytester, the skipping plugin, and the regression suites.

**Children.**

- [Legacy LocalPath Library](r6-legacy-path.md) `r6-legacy-path` · 0 unit(s)
- [Safe Repr Formatting](r6-safe-repr.md) `r6-safe-repr` · 7 unit(s)
- [Source Code Introspection](r6-source-introspection.md) `r6-source-introspection` · 8 unit(s)
- [Monkey Patching](r6-monkeypatch-plugin.md) `r6-monkeypatch-plugin` · 0 unit(s)

Parent: [pytest Framework Internals](r6-pytest-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
