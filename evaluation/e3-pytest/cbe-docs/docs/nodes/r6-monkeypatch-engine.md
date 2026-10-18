# Patch Engine and Undo Journal

**Capability.** Implements each patch kind (setattr/delattr, set/delitem, env, syspath, chdir) with undo records keyed by the sentinel notset; dotted-name resolution feeds string-target patching, and undo replays the journal in reverse.

Read this subtree for the mechanics of patching and undo. Methods record old values (or notset) so undo can restore or delete them; context and the fixture both funnel through undo().

**Depended on by.**

- [Filesystem Traversal and Symlinks](r6-collection-fs-symlinks.md) · graph-confirmed · 5 edge(s)
- [monkeypatch Fixture](r6-monkeypatch-fixture.md) · graph-confirmed · 2 edge(s)
- [Color and Code Highlighting](r6-terminal-color-highlight.md) · graph-confirmed · 4 edge(s)
- [Progress and Output Styles](r6-terminal-progress.md) · graph-confirmed · 7 edge(s)
- [Summary, Warnings and Misc Reporting](r6-terminal-summary-basics.md) · graph-confirmed · 6 edge(s)

Parent: [Monkey Patching](r6-monkeypatch-plugin.md)

## Units (17)

<a id="u-3cde513da82a"></a>
### `MonkeyPatch`

`class MonkeyPatch:` · [src/_pytest/monkeypatch.py:L116-L130][f1]

Helper for temporary modification of attributes, mapping entries, environment variables, sys.path, and the working directory.

It records an undo journal in __init__: _setattr list of (target, name, oldval), _setitem list of (mapping, key, oldval), plus _cwd and _savesyspath saved lazily on first chdir/syspath_prepend. Can be used as the monkeypatch fixture or standalone via MonkeyPatch()/context() since 6.2. Each mutating method records the previous state before changing it; undo() replays the journal in reverse order, so later patches are undone before earlier ones, consuming the stack (a second undo is a no-op unless new patching happened).

**Uncertainties.**

- Thread-safety is not addressed in the code; concurrent use of one instance is undefined here.

<a id="u-9f4e279d399a"></a>
### `src/_pytest/monkeypatch.py:Notset`

`class Notset:` · [src/_pytest/monkeypatch.py:L108-L109][f1]

Sentinel type whose single instance notset marks 'no value/attribute absent' in undo records and setattr/delattr defaults; its __repr__ returns '<notset>'.

Comparisons use identity (is notset) throughout MonkeyPatch.

<a id="u-bfbb7da64926"></a>
### `annotated_getattr`

`def annotated_getattr(obj: object, name: str, ann: str) -> object:` · [src/_pytest/monkeypatch.py:L88-L95][f1]

getattr wrapper that converts AttributeError into a more diagnostic one: raises AttributeError("'{TypeName}' object at {ann} has no attribute '{name}'") chained from the original, where ann is the dotted path being resolved.

Otherwise returns the attribute value.

<a id="u-1ef95a474153"></a>
### `derive_importpath`

`def derive_importpath(import_path: str, raising: bool) -> tuple[str, object]:` · [src/_pytest/monkeypatch.py:L98-L105][f1]

Splits a dotted 'module.attr' path for the string-target form of setattr/delattr.

Raises TypeError if import_path is not a str or contains no '.'; then rsplit on the last dot, resolve() the module part, and when raising is True verify the attribute exists via annotated_getattr (raising AttributeError if missing). Returns (attr, target_module); note that when raising=False the attribute is not checked here.

calls: [resolve](r6-monkeypatch-engine.md#u-154c51ff3360), [annotated_getattr](r6-monkeypatch-engine.md#u-bfbb7da64926)

<a id="u-154c51ff3360"></a>
### `resolve`

`def resolve(name: str) -> object: # Simplified from zope.dottedname.` · [src/_pytest/monkeypatch.py:L60-L85][f1]

Resolves a dotted name to an object, simplified from zope.dottedname.

It imports the first part via __import__, then for each remaining part first tries getattr; if that raises AttributeError it falls through to __import__ of the accumulated name. If that import raises ImportError, it compares the last whitespace-separated token of the error message with the name being imported: if equal it re-raises the original ImportError, otherwise raises ImportError('import error in {used}: {ex}') chained from the original. The attribute is then fetched with annotated_getattr(found, part, used). Returns the final object; any unhandled error propagates.

calls: [annotated_getattr](r6-monkeypatch-engine.md#u-bfbb7da64926)

<a id="u-ea16698e027a"></a>
### `MonkeyPatch.__init__`

`def __init__(self) -> None:` · [src/_pytest/monkeypatch.py:L130-L134][f1]

Initializes empty undo state: empty _setattr and _setitem lists, _cwd=None, _savesyspath=None.

The chdir/syspath originals are captured lazily by the corresponding methods, not here.

<a id="u-50a6dcd4ac47"></a>
### `MonkeyPatch.chdir`

`def chdir(self, path: str | os.PathLike[str]) -> None:` · [src/_pytest/monkeypatch.py:L364-L372][f1]

Changes the working directory via os.chdir(path).

The first call captures os.getcwd() into _cwd; later calls do not overwrite it, so undo() always returns to the directory current before the first chdir. Accepts str or os.PathLike.

<a id="u-c398333a36d2"></a>
### `MonkeyPatch.context`

`def context(cls) -> Generator[MonkeyPatch]:` · [src/_pytest/monkeypatch.py:L136-L161][f1]

Classmethod context manager: creates a new MonkeyPatch (cls()), yields it inside try, and always calls m.undo() in finally, so patches made inside the with block are reverted on exit even if the body raises.

Useful for scoped patches, e.g. mocking stdlib functions that could break pytest itself.

calls: [MonkeyPatch.undo](r6-monkeypatch-engine.md#u-30d8caea45ae)

<a id="u-cd3f9aba453d"></a>
### `MonkeyPatch.delattr`

`def delattr( self, target: object | str, name: str | Notset = notset, raising: bool =…` · [src/_pytest/monkeypatch.py:L253-L289][f1]

Deletes attribute name from target, recording the old value for undo.

Supports delattr(target, name, raising=True) or the string form delattr('dotted.path'). If name is the notset sentinel, target must be a str (else TypeError) and derive_importpath resolves module/attr. If the attribute does not exist and raising is True, raises AttributeError(name); if raising is False nothing is recorded or deleted. If it exists, oldval is captured via getattr with notset fallback, but for class targets from target.__dict__ (bypassing staticmethod/classmethod descriptors); the pair is journaled and delattr removes the attribute.

calls: [derive_importpath](r6-monkeypatch-engine.md#u-1ef95a474153)

<a id="u-7e894007c213"></a>
### `MonkeyPatch.delenv`

`def delenv(self, name: str, raising: bool = True) -> None:` · [src/_pytest/monkeypatch.py:L331-L338][f1]

Deletes name from os.environ by delegating to delitem(os.environ, name, raising=raising): KeyError when the variable does not exist unless raising=False, and undo records restore it when applicable.

calls: [MonkeyPatch.delitem](r6-monkeypatch-engine.md#u-153bd7b77854)

<a id="u-153bd7b77854"></a>
### `MonkeyPatch.delitem`

`def delitem(self, dic: Mapping[K, V], name: K, raising: bool = True) -> None:` · [src/_pytest/monkeypatch.py:L297-L309][f1]

Deletes dic[name].

If the key is absent and raising is True, raises KeyError(name); with raising=False nothing happens. If present, records (dic, name, old value) in the journal and deletes the key. The old value is always dic.get(name, notset); since presence was checked, it is the real prior value here.

<a id="u-7e3e8acd6062"></a>
### `src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)`

`def setattr( self, target: str | object, name: object | str, value: object = notset, …` · [src/_pytest/monkeypatch.py:L181-L251][f1]

Implementation of setattr's three overloads: (target, name, value, raising=True) or the string form setattr('dotted.path', value).

__tracebackhide__ is set to hide from tracebacks. Dispatch: if value is the notset sentinel, target must be a str (else TypeError); the string is split by derive_importpath, which also validates the attribute when raising=True, and value is taken from the name argument. If value is given, name must be a str (else TypeError). It reads oldval = getattr(target, name, notset); if raising and oldval is notset, raises AttributeError(f'{target!r} has no attribute {name!r}'). For class targets it reads oldval from target.__dict__ instead, deliberately avoiding staticmethod/classmethod descriptors, so restoring can restore the original descriptor. It appends (target, name, oldval) to the undo journal and then sets the attribute. Exceptions from resolve/import during the string form propagate before any change.

calls: [derive_importpath](r6-monkeypatch-engine.md#u-1ef95a474153)

**Uncertainties.**

- Values that are literally the Notset sentinel cannot be distinguished from absent attributes when restoring.

<a id="u-3bcdaba77d61"></a>
### `MonkeyPatch.setenv`

`def setenv(self, name: str, value: str, prepend: str | None = None) -> None:` · [src/_pytest/monkeypatch.py:L311-L329][f1]

Sets os.environ[name].

If value is not a str it emits PytestWarning (stacklevel=2) and converts via str(value). If prepend is truthy and name already exists in os.environ, the new value becomes value + prepend + old value (e.g. PATH-style prepending). The change is applied via self.setitem(os.environ, name, value), so undo restores the previous value or removes a newly created variable.

calls: [MonkeyPatch.setitem](r6-monkeypatch-engine.md#u-0494ec708f24)

<a id="u-0494ec708f24"></a>
### `MonkeyPatch.setitem`

`def setitem(self, dic: Mapping[K, V], name: K, value: V) -> None:` · [src/_pytest/monkeypatch.py:L291-L295][f1]

Records the current value of dic[name] (or notset if the key is absent) in the undo journal, then assigns dic[name] = value.

Typed as Mapping but indexed directly, with a comment that not all Mappings support indexing; mutable mappings are the practical requirement.

<a id="u-779499e353d6"></a>
### `MonkeyPatch.syspath_prepend`

`def syspath_prepend(self, path) -> None:` · [src/_pytest/monkeypatch.py:L340-L362][f1]

Prepends str(path) to sys.path.

Only the first call in an instance's lifetime saves the entire current sys.path into _savesyspath (subsequent calls do not re-save); undo() restores that snapshot. After inserting, if 'pkg_resources' is in sys.modules it imports fixup_namespace_packages and calls it on the path (needed only when pkg_resources was already loaded by a namespace package), then always calls importlib.invalidate_caches() because a prepend usually precedes importing freshly written files, and the mtime-based FileFinder cache is not invalidated otherwise, particularly with namespace packages.

**Notes.**

- side_effect: Import of pkg_resources.fixup_namespace_packages and importlib.invalidate_caches happens on every call, not only the first.

<a id="u-30d8caea45ae"></a>
### `MonkeyPatch.undo`

`def undo(self) -> None:` · [src/_pytest/monkeypatch.py:L374-L415][f1]

Reverts all recorded changes and consumes the journal; a second call is a no-op until new patching occurs.

Order: attribute changes are undone in reverse insertion order — setattr back to the old value, or delattr when the old value is the notset sentinel (i.e., the attribute did not exist); then mapping changes in reverse — restore key/value, or delete the key when the saved value is notset, swallowing KeyError because the key was already removed (desired state reached). Then, if a sys.path snapshot exists, sys.path is replaced with it and the snapshot cleared; if _cwd is set, os.chdir back and cleared. Note delattr-undo calls delattr unconditionally for sentinel entries, which would raise AttributeError if something else removed the attribute meanwhile; only the mapping path tolerates concurrent removal.

**Notes.**

- side_effect: Journal lists are cleared in place (self._setattr[:] = []), affecting any other reference to them.

**Uncertainties.**

- Whether sentinel-based attribute undo can hit AttributeError in practice depends on external mutation not visible here.

<a id="u-15542465dfa8"></a>
### `monkeypatch.py module code (L110–L115)`

`module_region` · [src/_pytest/monkeypatch.py:L110-L115][f1]

Creates the module-level singleton notset = Notset() used as the sentinel throughout MonkeyPatch.

Purely a constant, no behavior beyond the class above.

**Notes.**

- side_effect: notset is shared module-wide; users patching values that literally are this Notset instance would be indistinguishable from 'absent' in undo records.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/monkeypatch.py
