# py.path test infrastructure

**Capability.** Provides the session-scoped path1 fixture that creates and populates (via idempotent setuptestfs) the canonical sample filesystem tree used by all CommonFSTests tests, plus ignore_encoding_warning for encoding-sensitive tests and the batch_make_numbered_dirs worker for the multiprocess-safety test.

Use this subtree to understand the shared test state: every common-API test receives the same prepared tree through path1. setuptestfs is idempotent, so repeated fixture use is safe. The helpers are test-only and should not leak into product code.

**Depended on by.**

- [Common py.path API suite](r1-local-commonfs-suite.md) · graph-confirmed · 4 edge(s)
- [Platform-specific & import suites](r1-local-platform-import-suite.md) · model-inferred · 0 edge(s)

Parent: [Legacy py.path compatibility](r1-legacy-py-path.md)

## Units (4)

<a id="u-45acc6187683"></a>
### `path1`

`def path1(tmpdir_factory):` · [testing/_py/test_local.py:L532-L537][f1]

Session-scoped pytest fixture yielding a fresh temporary directory created via tmpdir_factory.mktemp('path') and populated by setuptestfs, passed as the 'path1' argument to every CommonFSTests test.

On teardown it asserts 'samplefile' still exists, so any test deleting it fails at teardown rather than silently corrupting later tests.

calls: [setuptestfs](r1-local-test-support.md#u-07b0aa2ee739); uses: [test-local.py-commonfs](r1-local-commonfs-suite.md#u-ef4bd72abf8e)

**Uncertainties.**

- tmpdir_factory.mktemp resolves to a TempPathFactory/TempdirFactory implementation not visible in this file

<a id="u-07b0aa2ee739"></a>
### `setuptestfs`

`def setuptestfs(path):` · [testing/_py/test_local.py:L478-L519][f1]

Builds the canonical sample filesystem tree used by the path1 fixture; idempotent, returning immediately if 'samplefile' already exists under the given path.

Otherwise it creates: samplefile containing 'samplefile\n'; execfile and execfile.py containing 'x=42'; samplepickle holding the dumped dict {1: 2, 'hello': 'world', 'answer': 42}; sampledir with otherfile; otherdir containing __init__.py plus a.py ('from .b import stuff as result'), b.py ('stuff="got it"'), c.py and d.py that import a via two styles to exercise package-relative imports. Side effect: writes real files and directories under the fixture path.

**Notes.**

- side_effect: All writes use encoding='utf-8'; the pickle is written via ensure(...).dump with no explicit encoding.

uses: [path1](r1-local-test-support.md#u-45acc6187683)

<a id="u-d93d9534c9ed"></a>
### `ignore_encoding_warning`

`def ignore_encoding_warning():` · [testing/_py/test_local.py:L18-L23][f1]

Context manager suppressing EncodingWarning while its body runs.

It enters warnings.catch_warnings() so filters are restored on exit; only when sys.version_info >= (3,10) does it install an ignore filter for EncodingWarning, otherwise it changes nothing. It yields unconditionally, and exceptions raised in the with-body propagate after filters are restored. Tests wrap default-encoding read calls in it so Python 3.10+ does not warn.

uses: [test-local.py-commonfs](r1-local-commonfs-suite.md#u-ef4bd72abf8e)

**Uncertainties.**

- EncodingWarning is referenced unqualified with '# noqa: F821', so its import origin is not visible in this file

<a id="u-a3d6c19ed48a"></a>
### `batch_make_numbered_dirs`

`def batch_make_numbered_dirs(rootdir, repeats):` · [testing/_py/test_local.py:L552-L562][f1]

Worker routine for the multiprocess-safety test: for the requested number of repeats it creates a numbered directory under rootdir via local.make_numbered_dir(prefix='repro-', rootdir=rootdir), writes str(i) into 'foo' inside it, reads the file back, and asserts the parsed int equals i, raising AssertionError with a diagnostic message otherwise.

Each iteration removes the '.lock' file with ignore_errors=True so stale locks do not block later rounds. Returns True after all repeats succeed.

**Notes.**

- failure: A mismatch between written and read content raises AssertionError naming both values, which surfaces through pool result .get().

uses: [test-local.py-testlocalpath](r1-local-commonfs-suite.md#u-2f8275a2f0ee)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/_py/test_local.py
