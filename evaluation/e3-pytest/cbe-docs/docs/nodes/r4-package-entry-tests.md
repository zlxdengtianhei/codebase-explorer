# Package and entry-point integrity tests

**Capability.** Guards that 'pytest' and 'py.test' distribution entry points are equivalent, that every internal module imports warning-free in a clean interpreter (xdist-critical), and provides the python -m pytest entry point.

test_meta enumerates internal modules and imports each with warnings escalated to errors; the entry-point test pins distribution metadata.

Parent: [CLI, config and package integrity tests](r4-cli-package-tests.md)

## Units (5)

<a id="u-55407f59392c"></a>
### `__main__.py module code (L1–L9)`

`module_region` · [src/pytest/__main__.py:L1-L9][f1]

Provide 'python -m pytest' as a command-line entry point.

When this module is executed as the main script, it calls pytest.console_main() and raises SystemExit with that call's return value, propagating the console main's exit code to the process. The call is guarded by 'if __name__ == "__main__"', so importing the module ordinarily has no side effects. Behavior of console_main itself (argument handling, exit codes) lives in _pytest.config and is not visible here.

imports: [__init__.py module code (L1–L180)](r1-public-api-surface.md#u-bbcdcae30a33); calls: [console_main](../../catalog.json)

**Uncertainties.**

- Exit codes and argument handling of pytest.console_main depend on _pytest.config, which is not supplied in this batch.

<a id="u-2339a0131d0c"></a>
### `test_pytest_entry_points_are_identical`

`def test_pytest_entry_points_are_identical():` · [testing/test_entry_points.py:L7-L10][f2]

Guards that the distribution exposes equivalent 'pytest' and 'py.test' entry points.

It reads the installed pytest distribution via importlib.metadata, builds a name→EntryPoint map, and asserts the 'value' of the 'pytest' entry equals that of 'py.test'. If the distribution is not installed or the entries are missing, the test fails with KeyError from the mapping lookups.

<a id="u-3f9a95bf34b5"></a>
### `test_meta.py module code (L1–L16)`

`module_region` · [testing/test_meta.py:L1-L16][f3]

Docstring stating the goal (all internal packages importable without the pytest namespace set, critical for xdist initialization) plus imports only; no behavior of its own.

<a id="u-27e82f4b8c9c"></a>
### `_modules`

`def _modules() -> list[str]:` · [testing/test_meta.py:L17-L22][f3]

Enumerates internal pytest modules for parametrization: walks _pytest.__path__ with pkgutil.walk_packages under the '_pytest.' prefix and returns the sorted module names.

Evaluated at collection time as a parametrize argument, so enumeration problems surface before any test runs.

<a id="u-8ecf0cd9ce6a"></a>
### `test_no_warnings`

`def test_no_warnings(module: str) -> None: # fmt: off` · [testing/test_meta.py:L25-L34][f3]

Imports one internal module in a clean interpreter with warnings escalated to errors; marked slow and parametrized over _modules().

Runs '<python> -W error -c "__import__(<module>)"' via subprocess.check_call; any warning, import failure, or nonzero child exit makes check_call raise and fails that case.

uses: [_modules](r4-package-entry-tests.md#u-27e82f4b8c9c)

**Uncertainties.**

- Whether the subprocess inherits environment customizations of the running pytest cannot be established from this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/pytest/__main__.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_entry_points.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/test_meta.py
