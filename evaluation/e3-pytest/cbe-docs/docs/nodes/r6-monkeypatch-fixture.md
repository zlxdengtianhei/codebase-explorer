# monkeypatch Fixture

**Capability.** Exposes a fresh MonkeyPatch per test and calls undo() in teardown so all modifications through the fixture are reverted automatically.

Request the monkeypatch fixture in tests; no manual cleanup is needed. For non-fixture scoped patching use MonkeyPatch.context instead.

**Depends on.**

- [Patch Engine and Undo Journal](r6-monkeypatch-engine.md) · graph-confirmed · 2 edge(s)

Parent: [Monkey Patching](r6-monkeypatch-plugin.md)

## Units (1)

<a id="u-3f3ad22e01db"></a>
### `monkeypatch`

`def monkeypatch() -> Generator[MonkeyPatch]:` · [src/_pytest/monkeypatch.py:L30-L57][f1]

Fixture yielding a fresh MonkeyPatch instance; after the requesting test or fixture finishes, it calls mpatch.undo() in teardown, so all modifications made through the fixture are reverted automatically.

calls: [MonkeyPatch](r6-monkeypatch-engine.md#u-3cde513da82a)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/monkeypatch.py
