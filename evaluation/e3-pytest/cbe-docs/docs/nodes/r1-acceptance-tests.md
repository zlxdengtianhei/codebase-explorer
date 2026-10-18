# Acceptance test suite

**Capability.** End-to-end pytest behavior through the Pytester fixture: general CLI usage scenarios, alternate invocation styles (subprocess/inprocess, PYTHONPATH manipulation via prepend_pythonpath), --durations reporting including fixture phases, and module-level scenario tests spanning packaging, fixture lifetime, async, capture, and error propagation.

Use this suite to check user-visible behavior rather than internals; each test drives an isolated session and asserts exit codes and output patterns. Invocation-variant tests call prepend_pythonpath to shape subprocess environments. Duration tests rely on mocked timing, so observed timings are deterministic.

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 103 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 93 edge(s)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (6)

<a id="u-5989048c795b"></a>
### `acceptance-test-py-general-usage`

`class TestGeneralUsage:` · [testing/acceptance_test.py:L28-L29][f1]

Acceptance tests for general pytest CLI usage, each driving an isolated session through the Pytester fixture and asserting on exit codes and stdout/stderr patterns.

Covered areas: config and hook failures (conftest syntax error or exceptions in pytest_sessionstart/pytest_configure yield INTERNALERROR with native traceback, nonzero ret; configure errors go to stderr while sessionstart errors go to stdout); missing file or directory reports 'file or directory not found' and still runs configure/unconfigure under -s (issue143); plugin preloading via -p with an --xyz option added in a preparse plugin passes; setuptools entry-point plugin load order is checked by monkeypatching importlib.metadata.distributions with dummy entry points whose load() imports stub modules and records order, asserting ['-p mycov' loads mycov first, else entry-point order]; assertion rewriting produces 'assert 0' output under all three import modes; a nested ImportError during test-module import gives ret 2 with 'ImportError while importing test module'; uncollectable arguments (a .pyc) give USAGE_ERROR; conftest import failure prints an exact five-line stderr traceback and empty stdout on normal runs, but only a warning with --help; early skip via pytest_collect_file or pytest_ignore_collect yields NO_TESTS_COLLECTED with '1 skip(ped)'; conftest output appears in stdout only when the conftest errors; sibling-directory conftests are not loaded (sub2 runs clean even with a failing sub1 conftest, while running sub1 directly gives USAGE_ERROR); custom collectors and generated funcarg ids support direct node-id addressing (file::item), including skipping by id keyword; parametrized duplicates with duplicate, underscore-digit, and string variants count 8/9/5 passes; an unknown node id errors with 'ERROR*not found'; every pytest_ name in the hookspec module must have a docstring; an undefined name in pytest_configure is an internal error with ret 3; a SyntaxError during member collection reports SyntaxError on stdout and, when a ::nodeid was requested, ERROR on stderr with ret 4; two failing collections both report initargs and pytest_sessionfinish still sees USAGE_ERROR; namespace-package imports with handled ImportError do not crash (ret 0); unknown options print 'unrecognized'; monkeypatching inspect.getsourcelines to fail still surfaces the fixture-not-found error; plugins given as strings to pytest.main are imported (invalid module raises ImportError, sys.modules-resident module registers and passes); bytes-regex and null-byte/unicode parametrized values pass; and args can be read from an @file producing 2 passes.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- Exact failure formatting of pytest internals is asserted only through output patterns, so precise message text produced by the implementation under test is not verifiable from this file.

<a id="u-0580a0a12cfa"></a>
### `acceptance-test-py-invocation-variants`

`class TestInvocationVariants:` · [testing/acceptance_test.py:L577-L578][f1]

Acceptance tests for alternate ways of invoking pytest, all via Pytester subprocess/inprocess helpers.

Covered behavior: importing pytest exposes 'mark' at import time (earlyinit); help(pytest) documents MarkGenerator; 'from pytest import *' exposes main/skip/xfail; calling pytest.main() twice in one interpreter runs the suite twice ('1 passed' twice); 'python -m pytest' exits 0 on pass and 1 on failure; pytest.main rejects a bare string args ('-h') with a TypeError naming the value, accepts a list of path strings (NO_TESTS_COLLECTED here), and accepts plugin objects whose pytest_addoption options show in -h help; --pyargs reports 'collected 0 items / 1 error' when the module raises ImportError, imports a package module only once (print and conftest configure each appear once), treats 't.py' as a filename despite looking like a module (OK), collects a real package and single module (2 passed / 1 passed), resolves '.' against PYTHONPATH, and errors on a missing module or package; legacy pkg_resources namespace packages split across sys.path entries resolve both as module and as path and support node-id addressing (skipped on setuptools>=80); '::' addressing combined with --doctest-modules passes; a symlinked package path resolves conftest and reports tests under the symlink path (skipped if symlinks unsupported); --pyargs with a nonexistent package errors; a plain class with a failing test method is expected to collect via unittest.TestCase subclassing (xfail, feature undecided); a failing doctest in a .txt file reports under the id file::file and re-runs identically (guards doctest.DocTestFailure handling across re-imports); get_plugin_manager() returns exactly PytestPluginManager; and the running plugin manager has the 'python' plugin.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

**Uncertainties.**

- Behavior of the xfail-marked collection-discovery test depends on an undecided upstream feature, so its long-term expected outcome is deliberately unstable.

<a id="u-bade7e2a2429"></a>
### `prepend_pythonpath`

`def prepend_pythonpath(*dirs) -> str:` · [testing/acceptance_test.py:L21-L25][f1]

Builds a PYTHONPATH string placing the given directories ahead of any existing value.

Reads PYTHONPATH from the environment; if it is set and non-empty, the current value is appended after the supplied dirs. All entries are stringified and joined with os.pathsep. Pure function of its arguments and the environment; raises nothing expected.

<a id="u-26db923175dc"></a>
### `acceptance-test-py-durations`

`class TestDurations:` · [testing/acceptance_test.py:L942-L955][f1]

Tests the --durations reporting using a shared class-level source snippet of three tests with mocked sleeps (0.002/0.010/0.020 via _pytest.timing under the mock_timing fixture) run in-process.

Variants: '--durations=10' lists the slowest calls and hides the 8 durations under 0.005s with a hint to use -vv; '--durations=2' shows only the slowest two with '4 passed' visible after the header; '--durations=0' shows all call entries; adding -vv additionally exposes setup/teardown entries; '--durations-min=0.015' restricts output to test_3 only, with or without -vv. The static helper check_tests_in_output derives which 'test_N call' lines appear by matching lines ending in the test name containing ' call ', and asserts exactly the expected test numbers (default pool of three). Deselection via '-k test_3' still prints a durations section containing test_3. With a collection error introduced by an invalid file plus '-k test_1', the run is interrupted (ret 2), reports '1 error during collection', and prints no durations at all because execution aborts. '-k not 1' deselects everything and exits 0.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- The 'call'-line matching in check_tests_in_output depends on exact terminal line formatting, which is produced elsewhere and not verifiable here.

<a id="u-7cec3c692924"></a>
### `acceptance-test-py-durations-with-fixture`

`class TestDurationsWithFixture:` · [testing/acceptance_test.py:L1042-L1055][f1]

Verifies that --durations reports fixture lifecycle phases separately.

The shared source defines an autouse-less fixture 'setup_fixt' sleeping 2 (mocked) units and a test sleeping 5, run in-process with '--durations=10'. Output must contain a '5.00s call test_1' line and a '2.00s setup test_1' line, matched in random order, proving call and setup durations are tracked and labeled per phase.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-ba3ae624fdbd"></a>
### `acceptance-test-py-module-level-tests`

`def test_zipimport_hook(pytester: Pytester) -> None:` · [testing/acceptance_test.py:L1069-L1089][f1]

Module-level acceptance tests spanning packaging, fixture lifetime, async handling, capture, and error propagation.

Key behaviors: a zipapp-packaged pytest run exercises the zip import hook, expecting a 'not found: foo' error on stderr and no INTERNALERROR output (skipped without zipapp); a unicode-named plugin listed in conftest pytest_plugins loads fine; a package's pytest_plugins attribute being a module is accepted rather than an error; hooks registered during pytest_configure (add_hookspecs) are checked late enough that a conftest implementing them passes and returns [40]; fixture objects are garbage-collected after their test — a weakref to a function-scoped fixture object is dead by the next test after gc.collect(), verified in a subprocess so the HookRecorder holds no extra references (issue2981); autouse module-scope clean_data runs before the test's fixture update, proving scope ordering (issue2405); failing-test frames are collectable garbage — a weakref is dead in the next test after gc.collect(), run in a subprocess (issue2798); a mock-decorated fixture from a copied example still works; an unknown option yields USAGE_ERROR; sync tests calling async def functions or async generators are each reported as failures with 'async def functions are not natively supported' naming all three tests; a sync test requesting an async fixture — plain, generator-based, or autouse=True — passes but emits one PytestRemovedIn9Warning stating this becomes an error in pytest 9, with the autouse variant wording calling out autouse=True; a custom 'pdb' module registered for assertion rewriting gets rewritten assertion output, run in a subprocess with the debugging plugin disabled to avoid an INTERNALERROR; --capture=tee-sys live-prints stdout/stderr while still recording both into junitxml; closing the pipe of a '--help' subprocess prints nothing to stderr and exits 1 (skipped on Windows, where an OSError occurs instead); a test returning non-None warns 'Did you mean to use `assert` instead of `return`?'; with importlib import mode plus --doctest-modules, a module already in sys.modules is not re-imported (identity assert passes, regression #10811); issue #9765 reproducer (skipped: not isolated) pip-installs a package editable and runs pytest via subprocess.run rather than Pytester to avoid PYTHONPATH pollution, converting CalledProcessError into an AssertionError carrying captured stdout/stderr; running without the terminal plugin still reports TESTS_FAILED; a StopIteration raised at module import during collection interrupts with one collection error and ret INTERRUPTED (StopIteration is not swallowed as a stop signal); and StopIteration raised in setup, teardown finalizer, or call yields respectively errors for setup/teardown and a failure for call — '1 failed, 1 passed, 2 errors' with ret TESTS_FAILED.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320)

**Uncertainties.**

- test_issue_9765 shells out to pip and a system 'pytest' executable, so its behavior depends on the host environment; it is skipped in practice.
- The exact warning text for async fixtures is asserted only via fnmatch patterns; full emitted wording comes from elsewhere.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/acceptance_test.py
