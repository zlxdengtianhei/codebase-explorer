# PDB and Breakpoint Tests

**Capability.** testing/test_debugging.py: pytest's debugger integration — post-mortem entry per outcome, capture suspension around the prompt, --pdbcls/custom Pdb classes, breakpoint()/sys.breakpointhook, --trace, and doctest interaction, verified via in-process runs and pexpect sessions.

Use these suites when changing --pdb behavior or capture interaction. Shared runpdb helpers and the two dummy-debugger fixtures are the common harness; outcome tests call the report/stdout helpers.

**Depends on.**

- [Hook Specifications](r7-core-hook-contracts.md) · model-inferred · 0 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 50 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 49 edge(s)

Parent: [pytest's Own Test Suites](r7-internal-test-suites.md)

## Units (15)

<a id="u-e1ec1020b3ce"></a>
### `test_debugging.py module code (L1–L12)`

`module_region` · [testing/test_debugging.py:L1-L12][f1]

Module header: mypy pragma, future annotations import, and imports of sys, _pytest._code, _validate_usepdb_cls, MonkeyPatch, Pytester, and pytest used by the fixtures and tests below.

<a id="u-3858599a1a13"></a>
### `pdb_env`

`def pdb_env(request):` · [testing/test_debugging.py:L13-L18][f1]

Autouse fixture disabling pdb++ hijacking for pytester-based inner test runs.

When the requesting test's fixturenames include 'pytester', it fetches that fixture and sets PDBPP_HIJACK_PDB=0 through the pytester fixture's own monkeypatch; otherwise it does nothing. The setting is undone with that monkeypatch's teardown.

**Notes.**

- side_effect: Mutates the environment only via the pytester fixture's MonkeyPatch, so the change is scoped to that fixture.

calls: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469)

<a id="u-f14af0a8fa40"></a>
### `runpdb`

`def runpdb(pytester: Pytester, source: str):` · [testing/test_debugging.py:L21-L23][f1]

Helper that writes source text as a test module and runs pytest in-process with --pdb, returning the result object for further inspection.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-5b72d8a6bf53"></a>
### `runpdb_and_get_stdout`

`def runpdb_and_get_stdout(pytester: Pytester, source: str):` · [testing/test_debugging.py:L26-L28][f1]

Runs the source via runpdb and returns the string form of the in-process run's captured stdout.

calls: [runpdb](r7-pdb-tests.md#u-f14af0a8fa40)

<a id="u-f0a4b78570fe"></a>
### `runpdb_and_get_report`

`def runpdb_and_get_report(pytester: Pytester, source: str):` · [testing/test_debugging.py:L31-L35][f1]

Runs the source via runpdb, asserts the run produced exactly three runtest logreports (setup/call/teardown; AssertionError listing the reports on mismatch), and returns the middle call-phase report.

calls: [runpdb](r7-pdb-tests.md#u-f14af0a8fa40)

<a id="u-1f60e51ea628"></a>
### `TestPDB`

`class TestPDB:` · [testing/test_debugging.py:L103-L104][f1]

Test suite for pytest's PDB integration: post-mortem entry per outcome, capture suspend/resume around pdb, custom --pdbcls classes, enter/leave hooks, doctest and recursive-debug interaction, exercised through in-process runs and pexpect-driven terminal sessions.

Its pdblist fixture fetches monkeypatch, defines mypdb(*args) that appends its args to a returned list, resolves the 'debugging' plugin from the plugin manager, and monkeypatches the plugin's post_mortem attribute with mypdb, so tests assert when and with what argument post-mortem was entered.

calls: [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062); group: [test_debugging.py-testpdb-outcome-tests](r7-pdb-tests.md#u-37f2e36f7344)

<a id="u-d041030dbf19"></a>
### `test_debugging.py-custom-pdb-calls-fixture`

`def custom_pdb_calls() -> list[str]:` · [testing/test_debugging.py:L38-L43][f1]

Fixture installing a recording dummy Pdb class as the module attribute _pytest._CustomPdb and returning the list its methods append to.

__init__ appends 'init', reset appends 'reset', interaction appends 'interaction'; do_debug/do_continue/do_quit are no-op placeholders whose only purpose is carrying docstrings that pytest copies onto wrapped commands. The assignment into the _pytest package is global and the fixture has no teardown, so the class remains installed after the test.

**Uncertainties.**

- No teardown deletes _pytest._CustomPdb, unlike custom_debugger_hook; whether the leakage is intentional is not visible here.

<a id="u-afa856c1534a"></a>
### `test_debugging.py-custom-debugger-hook-fixture`

`def custom_debugger_hook():` · [testing/test_debugging.py:L69-L74][f1]

Fixture installing a recording dummy debugger class as _pytest._CustomDebugger for breakpoint()/sys.breakpointhook tests.

__init__/reset/interaction append 'init'/'reset'/'interaction' to the returned list; set_trace prints '**CustomDebugger**' and appends 'set_trace'; do_debug/do_continue/do_quit are docstring-carrying no-ops. Unlike custom_pdb_calls this is a yield fixture: after the test it deletes _pytest._CustomDebugger, restoring the module attribute.

<a id="u-37f2e36f7344"></a>
### `test_debugging.py-testpdb-outcome-tests`

`def test_pdb_on_fail(self, pytester: Pytester, pdblist) -> None:` · [testing/test_debugging.py:L116-L130][f1]

Verifies when --pdb enters post-mortem via the pdblist fixture.

On a plain failing assert, the report is failed and post-mortem is entered once; the recorded traceback's last frame is test_func, read from pdblist[0][0] directly on Python < 3.13 and from its __traceback__ on 3.13+. An xfail-marked failing test, a pytest.skip, and a module-level unittest.SkipTest during collection enter post-mortem zero times (xfail report carries the xfail keyword; the skiptest case asserts 'entering PDB' is absent from stdout). A raised bdb.BdbQuit fails the test without post-mortem — the debugger's quit signal is treated as terminal — while a raised KeyboardInterrupt fails the test and does enter post-mortem once.

calls: [runpdb_and_get_report](r7-pdb-tests.md#u-f0a4b78570fe), [runpdb_and_get_stdout](r7-pdb-tests.md#u-5b72d8a6bf53)

<a id="u-2aa665a2bd51"></a>
### `test_debugging.py-testpdb-capture-tests`

`def test_pdb_unittest_postmortem(self, pytester: Pytester) -> None:` · [testing/test_debugging.py:L198-L216][f1]

Verifies what captured output is shown when the PDB prompt appears, via spawn_pytest sessions finished with the shared flush helper.

A failing test that writes to stdout and stderr shows both 'captured stdout' and 'captured stderr' sections before the Pdb prompt; a failing test with no output shows neither. Captured log output appears before the prompt for --show-capture=all and --show-capture=log but not 'no', and is absent when the logging plugin is disabled with -p no:logging. test_pdb_unittest_postmortem evaluates self.filename inside post-mortem of a unittest failure; test_pdb_unittest_skip confirms a skipped unittest class prints the skip reason and summary without entering pdb. test_pdb_interaction_exception drops into pdb on pytest.raises failure and can evaluate globalfunc; test_pdb_interaction_on_collection_issue181 enters pdb on a collection NameError and continues to '1 error'; test_pdb_interaction_on_internal_error asserts the INTERNALERROR traceback is printed exactly once; test_pdb_prevent_ConftestImportFailure_hiding_exception runs in a subprocess and expects the underlying 'import unknown' error rather than a wrapping ConftestImportFailure.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [test_debugging.py-testpdb-outcome-tests](r7-pdb-tests.md#u-37f2e36f7344)

**Uncertainties.**

- Several tests depend on pexpect output ordering of the pytest terminal writer; exact interleaving beyond the expected() calls is not established here.

<a id="u-a5ca49dc3c75"></a>
### `test_debugging.py-testpdb-set-trace-tests`

`def test_pdb_interaction_capturing_simple(self, pytester: Pytester) -> None:` · [testing/test_debugging.py:L396-L419][f1]

Verifies pytest.set_trace/pdb.set_trace interaction with IO capturing in spawned sessions.

pytest.set_trace prints 'PDB set_trace (IO-capturing turned off)' and a custom header kwarg suppresses the 'PDB set_trace' line; continuing prints 'PDB continue (IO-capturing resumed)' so captured output (hello17/hello18) appears in the final 'Captured stdout call' section — several of these are xfail(strict=False) for issue #10042. pdb.set_trace inside tests is intercepted without BdbQuit noise, and capturing resumes for later tests (test_set_trace_capturing_afterwards). Doctests under --pdb --doctest-modules show the UNEXPECTED EXCEPTION banner, can evaluate doctest locals, and quit via the '_pytest.outcomes.Exit: Quitting debugger' path (plain 'q' with -s in test_doctest_set_trace_quit) rather than BdbQuit. capsys is readable inside pdb (hello1 via capsys.readouterr()) and caplog.record_tuples is inspectable at the prompt. test_pdb_with_injected_do_debug drives --pdbcls with a pdbpp-like subclass overriding do_debug/do_continue, checking recursive 'debug' entry/exit without a spurious PDB-continue message or outcomes.Exit. test_pdb_without_capture (-s) and the heavily mocked test_pdb_continue_with_recursive_debug (parametrized over '', '-s', '-p no:capture') verify the set_trace/continue banners, the absence of a 'PDB continue' banner while _recursive_debug is elevated, and '1 passed' outcomes across capture modes.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [test_debugging.py-testpdb-outcome-tests](r7-pdb-tests.md#u-37f2e36f7344)

**Uncertainties.**

- Behavior of the xfail(strict=False) cases (capturing_simple, capturing_twice, injected_do_debug) is expected to fail on some platforms; pass/fail is not fixed by this file.

<a id="u-ab3d7a155ca5"></a>
### `test_debugging.py-testpdb-config-tests`

`def test_pdb_used_outside_test(self, pytester: Pytester) -> None:` · [testing/test_debugging.py:L786-L802][f1]

Verifies pdb configuration, hooks, and class selection.

test_pdb_used_outside_test and test_pdb_used_in_generate_tests run pytest.set_trace from a plain script / pytest_generate_tests, waiting on a break line that differs by Python version ('pytest.set_trace()' on 3.13+, 'x = 5' before). test_pdb_collection_failure_is_shown runs a subprocess and expects a NameError plus the EOF-triggered 'Exit: Quitting debugger' line. test_enter_leave_pdb_hooks_are_called (parametrized post_mortem True/False) installs conftest hooks asserting pytest_enter_pdb receives the pdb instance (mutating an attribute that pytest_leave_pdb verifies), then checks the enter/leave messages and the mode-appropriate PDB-continue banner. test_pdb_custom_cls with the custom_pdb_calls fixture asserts --pdbcls=_pytest:_CustomPdb on a collection error produces exactly ['init','reset','interaction']; test_pdb_custom_cls_without_pdb asserts --pdbcls without --pdb instantiates nothing ([]); test_pdb_custom_cls_invalid expects the argparse format error for --pdbcls=invalid; test_pdb_validate_usepdb_cls checks _validate_usepdb_cls splits on the last colon ('os.path:dirname.__name__' -> ('os.path','dirname.__name__')) without importing or validating the class; test_pdb_custom_cls_with_set_trace uses a local module class requiring a skip kwarg and set_trace, via PYTHONPATH set with monkeypatch; test_pdb_exception_chain_navigation (3.13+ only) navigates exception chains with the 'exceptions 0' command to switch frames; test_pdb_wrapped_commands_docstrings checks that continue and debug have help docstrings and no 'Undocumented commands' section exists.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61); uses: [test_debugging.py-custom-pdb-calls-fixture](r7-pdb-tests.md#u-d041030dbf19)

<a id="u-87adb3a206cc"></a>
### `test_debugging.py-testdebuggingbreakpoints`

`class TestDebuggingBreakpoints:` · [testing/test_debugging.py:L1017-L1018][f1]

Verifies breakpoint()/sys.breakpointhook integration.

test_sys_breakpointhook_configure_and_unconfigure (parametrized --pdb vs none, subprocess) installs conftest asserting sys.breakpointhook equals pytestPDB.set_trace during tests and is restored to sys.__breakpointhook__ in a cleanup. test_pdb_custom_cls uses the custom_debugger_hook fixture, deletes PYTHONBREAKPOINT, and asserts breakpoint() with --pdbcls=_pytest:_CustomDebugger records exactly ['init','set_trace'] and prints the custom marker. test_environ_custom_class (parametrized --pdb vs none, subprocess) sets PYTHONBREAKPOINT=_pytest._CustomDebugger.set_trace in conftest and asserts the hook is installed during tests and restored afterwards. test_sys_breakpoint_interception spawns a real session, quits at the Pdb prompt, and asserts 'Quitting debugger' appears without the 'reading from stdin while output' warning; test_pdb_not_altered (xfail strict=False) confirms plain pdb.set_trace still works and fails the test normally.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346), [MonkeyPatch.delenv](r6-monkeypatch-engine.md#u-7e894007c213); uses: [test_debugging.py-custom-debugger-hook-fixture](r7-pdb-tests.md#u-afa856c1534a)

<a id="u-8538f1f2ef6f"></a>
### `test_debugging.py-testtraceoption`

`class TestTraceOption:` · [testing/test_debugging.py:L1137-L1138][f1]

Verifies the --trace option, which enters pdb at the start of each test via runcall.

test_trace_sets_breakpoint steps 'c' through three passing tests, quits at the third, and asserts '2 passed', the quitting message printed once only on stdout, and no 'reading from stdin while output' warning. test_trace_with_parametrize_handles_shared_fixtureinfo parametrizes three functions (including one where 'func' is both an argument name of another test and a default kwarg) and asserts per-parameter 'args' output showing myparam/func = 1 then 2, IO-capturing suspend/resume banners per runcall, and '6 passed' overall. Both use TestPDB.flush to reap the child.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [test_debugging.py-testpdb-outcome-tests](r7-pdb-tests.md#u-37f2e36f7344)

<a id="u-44dd9f666350"></a>
### `test_debugging.py-pdb-session-edge-tests`

`def test_trace_after_runpytest(pytester: Pytester) -> None:` · [testing/test_debugging.py:L1217-L1245][f1]

Edge-case tests for PDB sessions outside the main classes.

test_trace_after_runpytest (subprocess with the pytester plugin) runs a test that itself invokes pytester.runpytest, asserting pytestPDB._saved grows to 2 during the inner run and shrinks back to 1, proving pytest_configure reentrancy. test_quit_with_swallowed_SystemExit quits pdb inside a test that swallows SystemExit, asserting the 'Exit: Quitting debugger' message and 'no tests ran'. test_pdb_suspends_fixture_capturing (parametrized capfd/capsys, xfail strict=False for #10042) asserts set_trace under -s turns off fixture capturing with a dedicated banner, evaluates 'p 40 + 2' live, resumes capturing on continue, and the fixture still reads pre/post output with exit status 0. test_pdbcls_via_local_module verifies --pdbcls import timing: an unimportable class yields a FAILURES error and ret 1, while a local mypdb.Wrapped.MyPdb works for both pdb.set_trace (set_trace_called) and --trace (runcall_called). test_raises_bdbquit_with_eoferror (xfail on 3.14+) monkeypatches input to raise EOFError without reading and asserts BdbQuit fails the test with ret 1. test_pdb_wrapper_class_is_reused asserts two set_trace calls share one --pdbcls class instance count of two instantiations of the same class.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_debugging.py
