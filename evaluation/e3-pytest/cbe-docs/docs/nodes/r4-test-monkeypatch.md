# MonkeyPatch tests

**Capability.** Verifies MonkeyPatch setattr/delattr (including dotted import paths and descriptor undo), environment/dict/sys.path/chdir patching with undo, and context-manager lifecycle including a leak-proof mp fixture.

Attribute tests cover object/class patching; environment tests cover environ, dict items and sys.path; lifecycle tests cover context() and child pytest runs.

**Children.**

- [Attribute patching tests](r4-monkeypatch-attr-tests.md) `r4-monkeypatch-attr-tests` · 6 unit(s)
- [Environment and sys.path tests](r4-monkeypatch-env-sys-tests.md) `r4-monkeypatch-env-sys-tests` · 4 unit(s)
- [MonkeyPatch lifecycle tests](r4-monkeypatch-lifecycle-tests.md) `r4-monkeypatch-lifecycle-tests` · 4 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
