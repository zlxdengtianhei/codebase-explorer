# Monkey Patching

**Capability.** Provides reversible, journaled modification of attributes, mapping entries, environment, sys.path and cwd; the engine records undo state while the fixture guarantees restoration after each test, keeping tests isolated from global state changes.

Use the fixture in tests for automatic undo, or MonkeyPatch.context for scoped patching outside fixtures. The engine layer implements patch semantics and the undo journal.

**Children.**

- [Patch Engine and Undo Journal](r6-monkeypatch-engine.md) `r6-monkeypatch-engine` · 17 unit(s)
- [monkeypatch Fixture](r6-monkeypatch-fixture.md) `r6-monkeypatch-fixture` · 1 unit(s)

Parent: [Core Support Libraries](r6-support-libraries.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
