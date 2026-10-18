# Test Run Invocation

**Capability.** Runs pytest in-process or via subprocesses and wraps outcomes: runpytest/inline-run, runprocessing helpers, RunResult, programmatic Config bootstrapping, collection helpers, and the _pytest/PytestArg fixture entry points.

Use runpytest for the common in-process run, run-process helpers for subprocess isolation, and parseconfig/collection helpers when driving Config or collection directly. All runs funnel toward core and recording.

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-confirmed · 8 edge(s)
- [Output Capture and Line Matching](r6-pytester-output-matching.md) · graph-confirmed · 8 edge(s)
- [Hook Recording](r6-pytester-recording.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Explanation Formatting and Truncation](r6-assertion-formatting.md) · graph-confirmed · 5 edge(s)
- [Conftest, Packages and Import Modes](r6-collection-conftest-import.md) · graph-confirmed · 38 edge(s)
- [Collection Error Handling](r6-collection-errors.md) · graph-confirmed · 13 edge(s)
- [Filesystem Traversal and Symlinks](r6-collection-fs-symlinks.md) · graph-confirmed · 25 edge(s)
- [Session and Node Protocol](r6-collection-protocol.md) · graph-confirmed · 37 edge(s)
- [Terminal End-to-End Reporting](r6-terminal-functional.md) · graph-confirmed · 29 edge(s)
- [Progress and Output Styles](r6-terminal-progress.md) · graph-confirmed · 37 edge(s)
- [Summary Sections and Reporting](r6-terminal-report-sections.md) · graph-confirmed · 29 edge(s)
- [Assertion Rewriting Suite](r6-test-assertion.md) · graph-confirmed · 51 edge(s)
- [Pytest Codebase](r2-pytest-root.md) · graph-only · 191 edge(s)
- [Cache provider tests](r5-cacheprovider-tests.md) · graph-only · 106 edge(s)
- [Configuration test suite](r1-config-test-suite.md) · graph-only · 104 edge(s)
- [Python Collection Tests](r7-collect-tests.md) · graph-only · 94 edge(s)
- [Acceptance test suite](r1-acceptance-tests.md) · graph-only · 93 edge(s)
- [Skipping and xfail Tests](r8-skipping-tests.md) · graph-only · 83 edge(s)
- [unittest integration tests](r5-unittest-integration-tests.md) · graph-only · 71 edge(s)
- [Doctest Plugin Test Suite](r9-tests-doctest.md) · graph-only · 67 edge(s)
- [Capture end-to-end tests](r4-capture-endtoend-tests.md) · graph-only · 50 edge(s)
- [PDB and Breakpoint Tests](r7-pdb-tests.md) · graph-only · 49 edge(s)
- [Metafunc functional tests](r4-metafunc-functional-tests.md) · graph-only · 46 edge(s)
- [Rewriting & Explanations](r3-rewrite-core-tests.md) · graph-only · 37 edge(s)
- [Warning Handling Tests](r7-warnings-tests.md) · graph-only · 35 edge(s)
- [Pytester self-tests](r5-pytester-selftests.md) · graph-only · 33 edge(s)
- [Import Hook & Cache Tests](r3-rewrite-hook-tests.md) · graph-only · 29 edge(s)
- [pytest Framework Internals](r6-pytest-framework.md) · within containment · 1 edge(s)

Parent: [Pytester Test Harness](r6-pytester-harness.md)

## Units (8)

<a id="u-272699fd9346"></a>
### `pytester-runpytest`

`def runpytest_inprocess( self, *args: str | os.PathLike[str], **kwargs: Any ) -> RunR…` · [src/_pytest/pytester.py:L1153-L1175][f1]

Runs pytest in-process while capturing output, mimicking runpytest's interface.

syspathinsert=True as a kwarg first prepends the pytester path to sys.path. An Instant timer starts, a sys-style Multicapture starts capturing, and inline_run(*args, **kwargs) executes. Three exits are handled: SystemExit has its args[0] coerced to ExitCode when valid (raw int kept otherwise) and reprec becomes a stub class carrying ret; any other Exception is printed via traceback.print_exc() (not swallowed into a failure) and reprec becomes a stub with ret=ExitCode(3); the success path uses the recorder from inline_run. The finally block reads the capture, stops it, and re-writes out/err to the real stdout/stderr. The result is a RunResult(ret, stdout lines, stderr lines, elapsed) with reprec attached as an extra attribute; assert reprec.ret is not None fires if a stub was constructed with a None exit code. runpytest() itself prepends --basetemp when the caller did not pass one (via _ensure_basetemp, which appends '--basetemp=<path>/basetemp' only when no argument starts with '--basetemp') and dispatches on the --runpytest option: 'inprocess' to runpytest_inprocess, 'subprocess' to runpytest_subprocess, any other value raising RuntimeError.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d); uses: [pytester-run-result](r6-pytester-run.md#u-8d8286c1250f)

**Uncertainties.**

- _get_multicapture('sys') interaction with an active outer capture is defined in _pytest.capture; nested-capture behavior cannot be confirmed here.
- WarningsRecorder.pop appears in graph evidence for this method but no visible pop call exists in the shown source.

<a id="u-2e2ff834e74d"></a>
### `pytester-inline-run`

`def inline_run( self, *args: str | os.PathLike[str], plugins=(), no_reraise_ctrlc: bo…` · [src/_pytest/pytester.py:L1075-L1122][f1]

Runs pytest.main in the current process and returns a HookRecorder of the run.

It first calls importlib.invalidate_caches() to work around stale importlib caches between file creation and the run. Inside try/finally it appends two finalizers — a fresh SysModulesSnapshot restore and a SysPathsSnapshot restore — so any sys.modules/sys.path changes made by the inner run are reverted even on exception. A nested PytesterHelperPlugin is appended to the plugins; its pytest_configure hook records a HookRecorder made from the inner config's pluginmanager and stashes gc_collect_iterations_key=0 to disable the unraisable plugin's GC looping for speed. main([str(x) for x in args], plugins=plugins) runs; if the configure hook fired exactly once the recorder is used as reprec, otherwise an empty class stands in (ret is still set). reprec.ret is assigned the ExitCode from main. If the result is ExitCode.INTERRUPTED and no_reraise_ctrlc is False, and the last pytest_keyboard_interrupt call carries a KeyboardInterrupt, the KeyboardInterrupt is re-raised for the user; otherwise reprec is returned. The finally block always runs the snapshot finalizers.

calls: [pytester-core](r6-pytester-core.md#u-f18f003077f1); uses: [pytester-sys-snapshots](r6-pytester-core.md#u-8932706de301), [pytester-hook-recorder](r6-pytester-recording.md#u-fb628c61b406)

**Uncertainties.**

- Behavior of _pytest.config.main (including in-process side effects like capturing and SystemExit propagation) is defined elsewhere.
- With multiple pytest_configure firings the recorder is discarded; only `ret` is available, and which run's recorder is dropped is not recorded here.

<a id="u-7cf3beaa965f"></a>
### `pytester-run-processes`

`def popen( self, cmdargs: Sequence[str | os.PathLike[str]], stdout: int | TextIO = su…` · [src/_pytest/pytester.py:L1335-L1371][f1]

Subprocess execution helpers.

popen copies os.environ, prepends the CWD to PYTHONPATH (os.pathsep-joined, dropping empties), and sets stdin by case: the CLOSE_STDIN sentinel or bytes both use stdin=PIPE (the sentinel closes the pipe immediately after start, bytes are written to it), any other value passes through to Popen. run() writes the child's stdout/stderr into files named stdout/stderr under the pytester path, prints the command and CWD, spawns via popen with close_fds except on win32, and closes the inherited stdin pipe. Timeout handling: timeout=None blocks on popen.wait(); otherwise wait(timeout) is tried and on subprocess.TimeoutExpired handle_timeout kills and waits for the child and raises Pytester.TimeoutExpired with a message including the timeout and command. Output files are re-read line-split, dumped to the real stdout/stderr via _dump_lines (which suppresses UnicodeEncodeError with a notice), ret is coerced to ExitCode when valid (ValueError suppressed, raw int kept), and a RunResult with duration is returned; __tracebackhide__ hides internals from pytest failure reports. runpytest_subprocess creates a mode-0700 numbered 'runpytest-' dir for --basetemp, prepends '-p <name>' for each plugin — raising ValueError if a plugin is a non-string object (objects unsupported in subprocess mode) — then prefixes sys.executable '-mpytest' and delegates to run with the optional timeout. runpython runs sys.executable on a script; runpython_c runs 'python -c command'. _getpytestargs returns (sys.executable, '-mpytest'). spawn_pytest builds a command string invoking pytest with --basetemp under 'temp-python' dir 'temp-pexpect' (created mode 0o700) and delegates to spawn. spawn importorskips pexpect>=3.0, skips on 64-bit PyPy and when pexpect.spawn is missing, opens 'spawn.out' for binary logging, and returns a pexpect.spawn child whose logfile is closed by a request finalizer.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f); raises: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f); uses: [pytester-run-result](r6-pytester-run.md#u-8d8286c1250f)

**Uncertainties.**

- make_numbered_dir semantics (uniqueness, cleanup) come from _pytest.pathlib.
- Whether killing via popen.kill leaves grandchild processes alive is OS-defined, not handled here.
- The docstring for spawn_pytest says 'temp-pexpect' for basetemp naming; the code creates 'temp-pexpect' — consistent, but behavior of pexpect itself is external.

<a id="u-8d8286c1250f"></a>
### `pytester-run-result`

`class RunResult:` · [src/_pytest/pytester.py:L517-L521][f1]

Holds the outcome of a command run by Pytester.

__init__ stores ret (coercing to ExitCode when the value is a valid enum member, keeping the raw int on ValueError), outlines/errlines, LineMatcher wrappers as stdout/stderr, and duration. __repr__ renders ret, stdout/stderr line counts and duration. parseoutcomes parses the terminal summary: parse_summary_nouns scans outlines in reverse for the session-duration regex (\d+\.\d\ds), extracts 'count noun' pairs with rex_outcome, and raises ValueError 'Pytest terminal summary report not found' when no line matches; singular warning/error are pluralized, so '1 failed, 1 passed, 1 warning' becomes {'failed':1,'passed':1,'warnings':1}. assert_outcomes delegates to _pytest.pytester_assertions.assert_outcomes, checking parsed outcomes against expected counts where 0 means the outcome must not occur and warnings/deselected are only checked when not None; failures surface as pytest failures via __tracebackhide__.

**Uncertainties.**

- Precision of the duration regex (one decimal digit) means summaries like '74.34s' match but other formats may not; behavior for unusual summary lines is Python-regex-defined.

<a id="u-4da6110e81d7"></a>
### `pytester-parseconfig`

`def parseconfig(self, *args: str | os.PathLike[str]) -> Config:` · [src/_pytest/pytester.py:L1220-L1241][f1]

Bootstraps fresh Config objects for programmatic use.

parseconfig stringifies args, applies _ensure_basetemp, and calls _pytest.config._prepareconfig(new_args, self.plugins), so plugins listed on self.plugins are registered (subprocess-style string plugin names apply here too); it then registers config._ensure_unconfigure as a request finalizer so a half-configured config is always unconfigured (releasing capture/tmpfiles) even if the test forgets. parseconfigure additionally calls config._do_configure(), running pytest_configure hooks; a failure there propagates to the caller after the finalizer is already registered.

uses: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- _prepareconfig's failure modes (usage errors, plugin import errors) are defined in _pytest.config.

<a id="u-0183c0c437e7"></a>
### `pytester-collection-helpers`

`def getnode(self, config: Config, arg: str | os.PathLike[str]) -> Collector | Item:` · [src/_pytest/pytester.py:L979-L996][f1]

In-process collection and item-level helpers.

getnode builds a Session from a supplied Config, asserts the arg has no '::', then fires pytest_sessionstart, performs collect on the absolute path with genitems=False, fires pytest_sessionfinish with ExitCode.OK, and returns the first collected node. getpathnode is the same but first parses the path via parseconfigure to obtain the Config, collecting by best-relative path. genitems recurses colitems through session.genitems and returns all leaf Items (fails on an empty sequence via index 0). runitem collects the item via getitem and runs it with a getrunner() method on the calling test class instance — using this method requires the calling test to define getrunner, else AttributeError. inline_runsource writes source with makepyfile and delegates to inline_run with the file appended to cmdline args. inline_genitems runs inline_run('--collect-only', ...) and extracts items from pytest_itemcollected calls. getitems writes the source (via getmodulecol) and genitems the module; getitem returns the single item whose name equals funcname ('test_func' default), asserting with source and item list if absent. getmodulecol writes string source under the test name (or treats a PathLike as a path relative to the pytester dir, asserting withinit unsupported for paths), optionally writes an '__init__.py' for withinit, stores self.config from parseconfigure(path, *configargs), and returns self.getnode(config, path). collect_by_name caches modcol.collect() results in _mod_collections (WeakKeyDictionary keyed by the collector, so a garbage-collected module entry disappears) and returns the child whose name matches, else None.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d), [pytester-parseconfig](r6-pytester-run.md#u-4da6110e81d7), [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7); raises: [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7)

**Uncertainties.**

- Session.perform_collect / session.genitems failure modes (collection errors raising or being reported) are defined outside this file.
- getnode asserts '::' not in arg but raises plain AssertionError.

<a id="u-0d6c137cee14"></a>
### `pytester-pytest-arg`

`class PytestArg:` · [src/_pytest/pytester.py:L205-L206][f1]

Thin helper behind the `_pytest` fixture.

__init__ stores the FixtureRequest. gethookrecorder(hook) creates a HookRecorder over hook._pm (the plugin manager the hook object belongs to), registers hookrecorder.finish_recording as a request finalizer so hook-call monitoring is undone at teardown, and returns the recorder. Accessing hook._pm means passing a non-hook object fails at attribute access.

uses: [pytester-hook-recorder](r6-pytester-recording.md#u-fb628c61b406)

**Uncertainties.**

- Attribute `_pm` of the passed hook is assumed to be a PytestPluginManager; that convention is defined in pluggy/pytest internals not shown here.

<a id="u-bb5907c20961"></a>
### `_pytest`

`def _pytest(request: FixtureRequest) -> PytestArg:` · [src/_pytest/pytester.py:L197-L202][f1]

Fixture named `_pytest` returning a PytestArg built from the request, giving tests a gethookrecorder helper for asserting on called hooks.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
