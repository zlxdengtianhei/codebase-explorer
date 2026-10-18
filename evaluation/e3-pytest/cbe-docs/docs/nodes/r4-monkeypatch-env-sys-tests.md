# Environment and sys.path tests

**Capability.** setitem/delitem on dicts and os.environ, setenv/delenv, syspath_prepend and chdir with undo, and namespace-package import fixup after sys.path prepend.

Covers the non-attribute patch targets; the namespace-package test verifies import-cache invalidation behavior.

Parent: [MonkeyPatch tests](r4-test-monkeypatch.md)

## Units (4)

<a id="u-2f3171e443be"></a>
### `test_monkeypatch.py-dictitems`

`def test_setitem() -> None:` · [testing/test_monkeypatch.py:L121-L136][f1]

Verifies setitem/delitem on dicts plus the analogous setenv_deleted_meanwhile case for os.environ, parametrized on whether the key pre-existed.

setitem records prior presence or absence so undo restores it; repeated setitem of a key keeps the original for undo; a key deleted externally before undo is restored only if it existed before patching, otherwise stays absent. delitem removes keys, raises KeyError for missing keys unless raising=False, and undo restores deletions while leaving keys added outside monkeypatch (e.g. 'hello', or d['x']=5 after undo) intact.

<a id="u-ed8ef9a23ee8"></a>
### `test_monkeypatch.py-environ`

`def test_setenv() -> None:` · [testing/test_monkeypatch.py:L181-L189][f1]

Verifies setenv/delenv on os.environ.

setenv with a non-str value emits PytestWarning (matched by exact message in TestEnvironWarnings) but still stores the string-converted value '2'; prepend inserts the new value before the old separated by the prepend string, yielding '3-2' after two prepends; undo removes keys that did not previously exist. delenv of a missing key raises KeyError with raising=True but not with raising=False; undo after delenv restores the deleted value, and undo after a subsequent setenv restores the pre-delenv value '1' rather than deleting the key.

**Uncertainties.**

- The non-str conversion and warning emission are implemented in monkeypatch.py, outside this batch.

<a id="u-5072d730ccb3"></a>
### `test_monkeypatch.py-syspath-chdir`

`def test_syspath_prepend(mp: MonkeyPatch) -> None:` · [testing/test_monkeypatch.py:L254-L263][f1]

Verifies syspath_prepend and chdir with undo.

Prepending inserts entries at the front of sys.path so the latest prepend is first; undo restores the original list and a second undo is a no-op; an entry appended to sys.path between two undos survives the second undo (asserted as the last element). chdir accepts Path or str and changes the process cwd; undo restores the cwd captured at chdir time; in the double-undo case the second undo does not move the process back, leaving the externally chdir'd tmp_path as the cwd.

**Uncertainties.**

- That chdir's second undo restores nothing is inferred from the assertion that cwd equals tmp_path, not from MonkeyPatch internals.

<a id="u-e39c1458d7e9"></a>
### `test_syspath_prepend_with_namespace_packages`

`def test_syspath_prepend_with_namespace_packages( pytester: Pytester, monkeypatch: Mo…` · [testing/test_monkeypatch.py:L433-L472][f1]

Builds two ns_pkg namespace packages (pkg_resources declare_namespace) in pytester dirs; verifies importing ns_pkg.hello after prepending 'hello', that ns_pkg.world raises ImportError before its path is prepended, that prepending 'world' triggers fixup so ns_pkg.world imports, and that prepending a fresh modules_tmpdir invalidates import caches so a newly written main_app.py imports.

Skipped for setuptools>=80 where pkg_resources is removed.

**Uncertainties.**

- fixup_namespace_packages and importlib.invalidate_caches behavior is asserted only through import outcomes here; the mechanism lives in monkeypatch.py.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_monkeypatch.py
