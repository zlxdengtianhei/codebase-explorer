# Pytester Environment and File Setup

**Capability.** Owns the isolated per-test directory, sys/module snapshots, environment patching, file and directory factories, example copying, and plugin activation glue (options, FD-leak checker, fixtures).

Start every Pytester-based test here: instantiate via fixtures, create files with the factories, and rely on snapshots/patching to keep runs isolated. copy_example pulls in example trees.

**Depends on.**

- [Output Capture and Line Matching](r6-pytester-output-matching.md) · graph-confirmed · 10 edge(s)

**Depended on by.**

- [Filesystem Traversal and Symlinks](r6-collection-fs-symlinks.md) · graph-confirmed · 17 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 8 edge(s)
- [Assertion Rewriting Suite](r6-test-assertion.md) · graph-confirmed · 56 edge(s)
- [Pytest Codebase](r2-pytest-root.md) · graph-only · 220 edge(s)
- [Acceptance test suite](r1-acceptance-tests.md) · graph-only · 103 edge(s)
- [Configuration test suite](r1-config-test-suite.md) · graph-only · 102 edge(s)
- [Doctest Plugin Test Suite](r9-tests-doctest.md) · graph-only · 85 edge(s)
- [unittest integration tests](r5-unittest-integration-tests.md) · graph-only · 70 edge(s)
- [Cache provider tests](r5-cacheprovider-tests.md) · graph-only · 69 edge(s)
- [JUnit XML reporting tests](r5-junitxml-tests.md) · graph-only · 69 edge(s)
- [Python Collection Tests](r7-collect-tests.md) · graph-only · 69 edge(s)
- [Skipping and xfail Tests](r8-skipping-tests.md) · graph-only · 67 edge(s)
- [PDB and Breakpoint Tests](r7-pdb-tests.md) · graph-only · 50 edge(s)
- [Capture end-to-end tests](r4-capture-endtoend-tests.md) · graph-only · 49 edge(s)
- [Metafunc functional tests](r4-metafunc-functional-tests.md) · graph-only · 48 edge(s)
- [Import Hook & Cache Tests](r3-rewrite-hook-tests.md) · graph-only · 45 edge(s)
- [Conftest, Packages and Import Modes](r6-collection-conftest-import.md) · graph-only · 42 edge(s)
- [Warning Handling Tests](r7-warnings-tests.md) · graph-only · 42 edge(s)
- [Rewriting & Explanations](r3-rewrite-core-tests.md) · graph-only · 41 edge(s)
- [Log File and Format Tests](r9-tests-logging-file-config.md) · graph-only · 40 edge(s)
- [Conftest loading tests](r5-conftest-tests.md) · graph-only · 36 edge(s)
- [-k / -m Selection Tests](r3-mark-selection-tests.md) · graph-only · 32 edge(s)
- [Live Logging Tests](r9-tests-logging-live-cli.md) · graph-only · 31 edge(s)
- [Pytester self-tests](r5-pytester-selftests.md) · graph-only · 30 edge(s)
- [Session and Node Protocol](r6-collection-protocol.md) · graph-only · 29 edge(s)
- [Terminal End-to-End Reporting](r6-terminal-functional.md) · graph-only · 29 edge(s)
- [pytest Framework Internals](r6-pytest-framework.md) · within containment · 1 edge(s)

Parent: [Pytester Test Harness](r6-pytester-harness.md)

## Units (8)

<a id="u-f18f003077f1"></a>
### `pytester-core`

`class Pytester:` · [src/_pytest/pytester.py:L648-L662][f1]

Pytester lifecycle: an isolated per-test directory plus environment patching.

__init__ enforces _ispytest via check_ispytest, stores the request and a WeakKeyDictionary cache of collected nodes, derives the base name from request.function (falling back to request.node.name when there is no function), and creates two numbered temp dirs via tmp_path_factory.mktemp (one for files, one as PYTEST_DEBUG_TEMPROOT). It takes a SysPathsSnapshot and a SysModulesSnapshot, registers _finalize as a request finalizer, reads the --runpytest option into _method, then uses the injected MonkeyPatch to chdir into the new directory and patch the environment: PYTEST_DEBUG_TEMPROOT set to the test tmproot, TOX_ENV_DIR and PYTEST_ADDOPTS deleted (raising=False), HOME and USERPROFILE set to the pytester path, PY_COLORS forced to 0. _finalize restores the sys.modules snapshot then the sys.path snapshot but deliberately leaves the temp directory in place for post-mortem inspection. __take_sys_modules_snapshot preserves modules whose names start with 'zope' or 'readline' (zope internal state and a readline/pexpect SIGWINCH issue). make_hook_recorder attaches a HookRecorder to a plugin manager (assigning it as pluginmanager.reprec) with a finish_recording finalizer. chdir monkeypatches the CWD to path; path and __repr__ are simple accessors. TimeoutExpired is a marker exception raised by run() on timeout. SIDE EFFECT: CWD and env changes persist for the whole test until monkeypatch teardown and _finalize run.

uses: [pytester-sys-snapshots](r6-pytester-core.md#u-8932706de301); calls: [pytester-hook-recorder](r6-pytester-recording.md#u-fb628c61b406)

**Uncertainties.**

- check_ispytest and the --runpytest option's accepted values come from other modules; a malformed option value surfaces later in runpytest as RuntimeError.

<a id="u-42fdcb995917"></a>
### `pytester-file-factories`

`def _makefile( self, ext: str, lines: Sequence[Any | bytes], files: dict[str, str], e…` · [src/_pytest/pytester.py:L755-L772][f1]

Helpers that create files and directories inside the pytester directory.

The engine is _makefile(ext, lines, files, encoding='utf-8'): a None ext raises TypeError; a non-empty ext without a leading dot raises ValueError suggesting '.<ext>'; if lines are given they are newline-joined and written to a file named after the requesting test, inserted before any kwargs entries. Each entry is written to path/<basename> with suffix ext (with_suffix, so a basename containing a dot is replaced), parent dirs created, content normalized through Source (line splitting/strip of the final text), and the first written path is returned; bytes entries are decoded with the given encoding. makefile forwards to _makefile; makepyfile/maketxtfile fix .py/.txt; makeconftest writes conftest.py via makepyfile; makeini writes tox.ini; makepyprojecttoml writes pyproject.toml; getinicfg writes a tox.ini and returns its ['pytest'] section parsed by IniConfig (KeyError if absent). syspathinsert prepends self.path (or the given path) to sys.path via monkeypatch, undone at teardown. mkdir creates a subdirectory with mkdir() (no parents; FileExistsError if present); mkpydir additionally touches an empty __init__.py to make it a package. Repeated makepyfile with the default name overwrites the existing file.

raises: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917); uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

**Uncertainties.**

- Behavior of Source(value) normalization for non-text values is defined in _pytest._code, not here.
- with_suffix means a kwarg name like 'my.file' yields 'my.py'-style results; whether that is intended is not stated.

<a id="u-b5c8a28929b8"></a>
### `pytester-fixtures`

`def linecomp() -> LineComp:` · [src/_pytest/pytester.py:L459-L463][f1]

Fixture entry points of this plugin.

linecomp yields a LineComp whose StringIO accumulates output to check. LineMatcher_fixture returns the LineMatcher class itself so tests can instantiate it with lines. pytester constructs Pytester(request, tmp_path_factory, monkeypatch, _ispytest=True), i.e. an isolated temporary test directory with CWD and environment patched for the test duration. _sys_snapshot wraps the body in a SysPathsSnapshot then a SysModulesSnapshot, restoring modules then paths after the yield. _config_for_test yields a fresh Config from get_config and calls config._ensure_unconfigure afterwards so capturing and tmpfiles are cleaned even if the test misuses the config.

uses: [pytester-core](r6-pytester-core.md#u-f18f003077f1), [pytester-sys-snapshots](r6-pytester-core.md#u-8932706de301)

<a id="u-8932706de301"></a>
### `pytester-sys-snapshots`

`class SysModulesSnapshot:` · [src/_pytest/pytester.py:L626-L627][f1]

Restorable snapshots of interpreter import state.

SysModulesSnapshot optionally takes a preserve(name)->bool predicate: restore() first folds any currently-loaded modules whose names the predicate accepts into the saved dict, then clears sys.modules and restores the saved mapping, so preserved modules are never removed. SysPathsSnapshot saves list(sys.path) and list(sys.meta_path); restore() assigns both back in place. Snapshots must be restored in LIFO order relative to other mutations for correctness; restoration itself does not reload or import anything.

**Uncertainties.**

- Clearing sys.modules while modules are mid-import could break live references; the classes do not guard against that.

<a id="u-304df992bcf0"></a>
### `pytester-lsof-fd-leak-checker`

`class LsofFdLeakChecker:` · [src/_pytest/pytester.py:L121-L122][f1]

An optional plugin that detects leaked file descriptors around each test.

get_open_files() runs `lsof -Ffn0 -p <pid>` with check=True, decoding output with locale.getencoding() on Python 3.11+ or locale.getpreferredencoding(False) earlier; a non-zero lsof exit raises subprocess.CalledProcessError, which propagates. It keeps only lines starting with 'f' that do not mention deleted/mem/txt/cwd, splits on NUL to extract fd and filename, skips filenames listed in IGNORE_PAM, and returns (fd, filename) pairs for absolute paths. matching_platform() returns False if `lsof -v` raises OSError or CalledProcessError, True otherwise. pytest_runtest_protocol is a tryfirst wrapper hook: it snapshots open files before the test, yields, and in a finally block (calling gc.collect() first on PyPy) snapshots again; fds present after but not before are reported by calling item.warn with a PytestFDWarning containing before/after listings and the item location — the test outcome itself is unaffected. Side effects: lsof subprocesses per snapshot.

raises: [pytester-lsof-fd-leak-checker](r6-pytester-core.md#u-304df992bcf0); calls: [pytester-lsof-fd-leak-checker](r6-pytester-core.md#u-304df992bcf0)

**Uncertainties.**

- Exact lsof output format (-Ffn0) is assumed, not verified; malformed lines could make fields[1] IndexError.
- Whether item.warn affects the run result beyond emitting a warning is defined elsewhere.

<a id="u-9c53cf11a097"></a>
### `src/_pytest/pytester.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/pytester.py:L83-L105][f1]

Registers the command-line options and ini setting this plugin needs.

It adds --lsof (store_true, default False), --runpytest restricted to 'inprocess' or 'subprocess' with default 'inprocess', and the pytester_example_dir ini entry naming the directory example files are copied from.

<a id="u-6932b1b9aa4f"></a>
### `src/_pytest/pytester.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/pytester.py:L108-L118][f1]

Activates FD-leak checking and declares a marker.

If the --lsof option is truthy, it constructs an LsofFdLeakChecker and, only when matching_platform() is true, registers it with the config plugin manager; otherwise no checker runs. It also adds the pytester_example_path marker definition to the config so tests can use it without warnings.

uses: [pytester-lsof-fd-leak-checker](r6-pytester-core.md#u-304df992bcf0)

<a id="u-c15c0894e320"></a>
### `Pytester.copy_example`

`def copy_example(self, name: str | None = None) -> Path:` · [src/_pytest/pytester.py:L933-L977][f1]

Copies an example file or directory from the project's configured example dir into the pytester directory.

It reads the pytester_example_dir ini value, raising ValueError if unset, resolves it against the config rootpath, and extends it with args of any pytester_example_path markers on the test. With name=None it looks for a directory or '<funcname>.py' named after the requesting test, raising LookupError if neither exists; with an explicit name it joins that path. If the resolved example is a directory without __init__.py it is copied recursively (symlinks preserved, existing files overwritten) and self.path is returned; if it is a file it is copied and the destination path returned; otherwise LookupError is raised. Files copied as-is; directories inside a package dir (with __init__.py) hit the final else and raise LookupError.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917); raises: [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320)

**Uncertainties.**

- Copying a directory that contains __init__.py falls into the final LookupError branch; whether package-dir examples are supported another way is not visible.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
