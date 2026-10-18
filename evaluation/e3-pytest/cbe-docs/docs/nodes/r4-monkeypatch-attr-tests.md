# Attribute patching tests

**Capability.** setattr/delattr on class attributes, dotted-string import-path targets, undo of staticmethod/classmethod descriptors (test_issue156), and name resolution into third-party modules (test_issue1338).

Read here for expected undo semantics when patching or deleting attributes, including descriptor edge cases.

Parent: [MonkeyPatch tests](r4-test-monkeypatch.md)

## Units (6)

<a id="u-91a4d3fdd570"></a>
### `test_monkeypatch.py-setattr`

`def test_setattr() -> None:` · [testing/test_monkeypatch.py:L27-L28][f1]

Verifies MonkeyPatch.setattr on class attributes.

setattr of a missing attribute raises AttributeError unless raising=False, which creates it; undo removes created attributes and restores overwritten ones; successive setattr of the same target still restores the original on undo; a second undo after external reassignment makes no modification; and a two-argument setattr call raises TypeError.

<a id="u-9c11a5921573"></a>
### `test_monkeypatch.py-setattr-importpath`

`class TestSetattrWithImportPath:` · [testing/test_monkeypatch.py:L54-L55][f1]

Exercises setattr/delattr with dotted string targets resolved as import paths.

'os.path.abspath' patches the resolved function, '_pytest.config.Config' resolves through intermediate modules, and delattr by string removes the attribute until mp.undo inside the context. A non-string target raises TypeError, an unimportable module path raises ImportError, a missing attribute raises AttributeError, and raising=False suppresses that error so the attribute is created (asserted as os.path.qweqwe == 42).

**Uncertainties.**

- The string-target import-resolution algorithm lives in src/_pytest/monkeypatch.py and is not visible in this batch.

<a id="u-47d5f5b4c508"></a>
### `test_monkeypatch.py-delattr`

`def test_delattr() -> None:` · [testing/test_monkeypatch.py:L101-L102][f1]

Verifies delattr on class attributes: undo restores the deleted attribute to its original value; deleting a missing attribute raises AttributeError unless raising=False; after delattr, setattr with raising=False recreates the attribute, and undo returns the class to its original state.

<a id="u-cc34deee979b"></a>
### `test_monkeypatch.py-class-descriptors`

`def test_undo_class_descriptors_delattr() -> None:` · [testing/test_monkeypatch.py:L375-L376][f1]

Verifies undo after delattr of classmethod and staticmethod descriptors.

The parent defines classmethod hello and staticmethod world; the test captures SampleChild.hello/world, deletes both on SampleParent (both become None via getattr default), then undo restores them so equality with the originals holds on the child, exercising restoration of inherited class descriptors.

<a id="u-6fe50adf7b21"></a>
### `test_issue156_undo_staticmethod`

`def test_issue156_undo_staticmethod(Sample: type[Sample]) -> None:` · [testing/test_monkeypatch.py:L360-L372][f1]

Parametrized over Sample and its subclass SampleInherit, sets the staticmethod 'hello' to None and asserts undo restores a callable: after undo, Sample.hello() returns truthy.

Covers undo of a staticmethod descriptor on both the defining class and an inheriting class.

<a id="u-b79a111f6189"></a>
### `test_issue1338_name_resolving`

`def test_issue1338_name_resolving() -> None:` · [testing/test_monkeypatch.py:L402-L408][f1]

Deletes requests.sessions.Session.request by dotted string and always undoes in a finally block, verifying name resolution for a method on a class attribute of a third-party module; skips if requests is unavailable.

calls: [MonkeyPatch.undo](r6-monkeypatch-engine.md#u-30d8caea45ae)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_monkeypatch.py
