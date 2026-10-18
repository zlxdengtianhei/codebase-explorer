# MonkeyPatch lifecycle tests

**Capability.** The leak-proof mp fixture (snapshot/restore of cwd and sys.path), monkeypatch.context() auto-restore semantics including classmethod-style usage, and integration tests running child pytest sessions.

Use here to understand context-manager guarantees and the fixture that guarantees cwd/sys.path restoration.

Parent: [MonkeyPatch tests](r4-test-monkeypatch.md)

## Units (4)

<a id="u-9ff2009450ac"></a>
### `mp`

`def mp() -> Generator[MonkeyPatch]:` · [testing/test_monkeypatch.py:L18-L24][f1]

Fixture yielding a fresh MonkeyPatch after snapshotting os.getcwd and sys.path, then at teardown it restores sys.path in place from the saved list and chdirs back, so cwd or sys.path changes leak-proof the test even if MonkeyPatch.undo is not called.

**Uncertainties.**

- Whether MonkeyPatch's internal undo state must also run is not guaranteed by this fixture; only cwd and sys.path are restored here.

<a id="u-7de50b007020"></a>
### `test_context`

`def test_context() -> None:` · [testing/test_monkeypatch.py:L411-L420][f1]

Replaces functools.partial inside a monkeypatch.context() and asserts partial is no longer a class while patched; after the with-block exits, inspect.isclass(functools.partial) is true again, showing context-exit restores the attribute without explicit undo.

<a id="u-ab94cfd066f6"></a>
### `testing/test_monkeypatch.py:test_context_classmethod`

`def test_context_classmethod() -> None:` · [testing/test_monkeypatch.py:L425-L430][f1]

Uses MonkeyPatch.context() as a classmethod-style entry point on a local class A: x becomes 2 inside the context and returns to 1 on exit, showing context works without a pre-built instance.

<a id="u-ddfb2d6db42f"></a>
### `test_monkeypatch.py-plugin-runs`

`def test_monkeypatch_plugin(pytester: Pytester) -> None:` · [testing/test_monkeypatch.py:L243-L251][f1]

Integration tests running child pytest sessions.

test_monkeypatch_plugin asserts the injected 'monkeypatch' fixture's class is MonkeyPatch (one passed outcome). test_issue185_time_breaks replaces time.time inside a child test and expects '1 passed', showing that patch does not break pytest's timing/reporting. test_importerror builds a package whose module raises ImportError on import and expects stdout to contain 'import error in package.a: No module named doesnotexist', showing string-target setattr surfaces a diagnostic rather than crashing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_monkeypatch.py
