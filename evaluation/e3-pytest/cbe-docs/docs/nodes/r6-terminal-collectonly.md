# Collect-Only Output

**Capability.** Tests --collect-only tree rendering with docstrings, module skips and import errors, fatal collection failures, missing-path parse errors, and quietness levels including selection-aware summary status lines.

Use it to pin expected collect-only trees, exit codes and -q/-qq collapsing. Error cases confirm collection failures still report under collect-only.

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (12)

<a id="u-0d3386024e73"></a>
### `TestCollectonly`

`class TestCollectonly:` · [testing/test_terminal.py:L481-L482][f1]

Groups tests of '--collect-only' output: tree rendering with docstrings, module-level skips and errors, exit codes, quietness levels, and selection-aware summary status lines.

<a id="u-9c492970201d"></a>
### `TestCollectonly.test_collectonly_basic`

`def test_collectonly_basic(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L482-L496][f1]

With --collect-only a single passing function renders as Dir/Module/Function tree lines.

<a id="u-77d2b35ec3f8"></a>
### `TestCollectonly.test_collectonly_skipped_module`

`def test_collectonly_skipped_module(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L498-L506][f1]

A module calling pytest.skip at import time under --collect-only -rs is reported as 'ERROR collecting'.

<a id="u-8ded3926fd14"></a>
### `TestCollectonly.test_collectonly_displays_test_description`

`def test_collectonly_displays_test_description( self, pytester: Pytester, dummy_yaml_…` · [testing/test_terminal.py:L508-L535][f1]

With --collect-only --verbose, function docstrings render indented under the Function node, preserving blank and nested indentation lines; also lists a yaml custom item (from dummy_yaml_custom_test) lacking obj, proving description display works for items without one.

<a id="u-1b69138a0eb2"></a>
### `TestCollectonly.test_collectonly_failed_module`

`def test_collectonly_failed_module(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L537-L540][f1]

A module raising ValueError at import shows the raise line in the collection error and reports '1 error'.

<a id="u-20e98b001d55"></a>
### `TestCollectonly.test_collectonly_fatal`

`def test_collectonly_fatal(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L542-L551][f1]

A conftest whose pytest_collectstart asserts (raising AssertionError 'urgs') causes an INTERNAL error line during --collect-only and exit code 3.

<a id="u-47725f2fe2ae"></a>
### `TestCollectonly.test_collectonly_simple`

`def test_collectonly_simple(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L553-L573][f1]

Collect-only on a module with a function and a class method exits 0 and renders Module/Function/Class/Function tree lines.

<a id="u-7e4801b631bc"></a>
### `TestCollectonly.test_collectonly_error`

`def test_collectonly_error(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L575-L588][f1]

Importing a nonexistent module under --collect-only exits 2 with ERROR/ImportError/'No module named'/'1 error' lines.

<a id="u-b76bd429b22e"></a>
### `TestCollectonly.test_collectonly_missing_path`

`def test_collectonly_missing_path(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L590-L597][f1]

A missing path argument yields exit code 4 and a stderr line 'ERROR: file or directory not found: uhm_missing_path', exercising parse-time failure before a session with items exists.

<a id="u-202f4ba078cf"></a>
### `TestCollectonly.test_collectonly_quiet`

`def test_collectonly_quiet(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L599-L602][f1]

-q collect-only still prints the test name.

<a id="u-0111f96dee44"></a>
### `TestCollectonly.test_collectonly_more_quiet`

`def test_collectonly_more_quiet(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L604-L607][f1]

-qq collect-only collapses to a per-file count line 'test_fun.py: 1'.

<a id="u-568de873160f"></a>
### `TestCollectonly.test_collect_only_summary_status`

`def test_collect_only_summary_status(self, pytester: Pytester) -> None:` · [testing/test_terminal.py:L609-L649][f1]

Checks the collect-only summary header across selection states: 3 tests, 1 test singular, '2/3 tests collected (1 deselected)' with -k foo, '1/3 (2 deselected)', 'no tests collected (3 deselected)' for a non-matching -k, 'no tests collected' for an empty dir, and ', 1 error' suffixes when a module fails to import.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
