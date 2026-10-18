# Pytester self-tests

**Capability.** Tests of the pytester testing utility itself: HookRecorder construction and bookkeeping, LineMatcher, inline_run sys.modules snapshotting, SysModulesSnapshot/SysPathsSnapshot restore semantics, subprocess runs (timeout, plugins, --runpytest subprocess), RunResult outcome accounting, and makefile/makepyfile behaviors.

Consult this to see the expected semantics of pytester's own API. Tests are grouped by the utility feature they pin.

**Depends on.**

- [Request objects and scoping context](r5-fixture-request-context.md) · graph-confirmed · 1 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 33 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 30 edge(s)

Parent: [pytest's own test suites](r5-test-suites.md)

## Units (27)

<a id="u-3bd8e2dc9ef5"></a>
### `test_pytester.py-make-hook-recorder`

`def test_make_hook_recorder(pytester: Pytester) -> None:` · [testing/test_pytester.py:L22-L31][f1]

Exercises HookRecorder failure and collect bookkeeping built on an item's pluginmanager via Pytester.make_hook_recorder.

The recorder starts with no failures. A fake failed report (class rep) fed twice through pytest_runtest_logreport is returned by getfailures both times, so repeated getfailures calls do not drain state. A skipped report (rep2) is fed, then a collect report (rep3, forced to failed) produced via pytester.getmodulecol and pytest_make_collect_report is fed through pytest_collectreport. listoutcomes yields no passed, one skipped, one failed; countoutcomes matches; getfailedcollections has one entry. After recorder.unregister() and recorder.clear(), feeding rep3 again and calling getfailures raises ValueError. An always-true condition precedes an xfail noting these internal recorder tests need refactoring.

calls: [pytester-core](r6-pytester-core.md#u-f18f003077f1), [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7)

**Uncertainties.**

- Whether the ValueError after unregister/clear stems from hook unregistration or cleared recorder state cannot be determined from this file

<a id="u-9dfef1d5c0d8"></a>
### `test_pytester.py-make-holder`

`def make_holder():` · [testing/test_pytester.py:L169-L170][f1]

Builds two hook-spec holders used to parameterize test_hookrecorder_basic: a class whose methods pytest_xyz and pytest_xyz_noarg are specs, and a module created via type(os)("api") with same-named functions attached.

Both expose identical hook names and signatures so add_hookspecs behavior can be compared for class-based and module-based specs.

<a id="u-de8144428739"></a>
### `test_hookrecorder_basic`

`def test_hookrecorder_basic(holder) -> None:` · [testing/test_pytester.py:L190-L202][f1]

Registers the parameterized holder (class or module specs) on a fresh PytestPluginManager and wraps it in a HookRecorder constructed with _ispytest=True.

Firing pm.hook.pytest_xyz(arg=123) is recorded; popcall("pytest_xyz") returns a call with arg 123 and _name "pytest_xyz". Popping a never-fired hook name raises pytest.fail.Exception. Firing pytest_xyz_noarg and popping it succeeds, so zero-argument hooks are recorded too.

uses: [src/_pytest/pytester.py][f2]

**Uncertainties.**

- HookRecorder constructor and popcall internals live in src/_pytest/pytester.py and are outside this source

<a id="u-52fe8a8885b1"></a>
### `test_pytester.py-linematcher`

`def test_linematcher_with_nonlist() -> None:` · [testing/test_pytester.py:L474-L495][f1]

LineMatcher behavior tests.

Only list, tuple and str line inputs are valid: fnmatch_lines/re_match_lines raise TypeError naming the invalid type for set, dict, and Source arguments to fnmatch_lines/re_match_lines, while _getlines converts Source to its lines and passes sets/dicts through. On match failure fnmatch_lines and re_match_lines raise pytest.fail.Exception with a structured message: an 'exact match' section for earlier matched lines, a 'nomatch' section listing remaining candidates, and a final 'remains unmatched' line; consecutive=True changes the wording to 'no consecutive match'. The no_*_line methods assert absence: calling them with a pattern that does match raises with a nomatch report (calling twice shows no accumulated buffer), while a genuinely non-matching pattern passes; after a successful fnmatch_lines, no_fnmatch_line('*') fails reporting the first remaining line. str(LineMatcher) joins its lines with newlines.

<a id="u-46c32ca7725e"></a>
### `test_pytester.py-inline-run-cleanup`

`class TestInlineRunModulesCleanup:` · [testing/test_pytester.py:L219-L220][f1]

Verifies that Pytester.inline_run snapshots and restores sys.modules so modules imported during a run are cleaned up, with controlled exceptions.

spy_factory builds a SysModulesSnapshotSpy whose __init__ records itself in a class-level instances list, stores the preserve argument, and wraps a real SysModulesSnapshot; its restore() increments a counter before delegating. Tests monkeypatch this spy into the _pytest.pytester module to observe inline_run. One test proves a test module is re-imported across two inline_run calls: after rewriting it, the second run fails, so its module was not left cached. Another asserts exactly one snapshot is created and restored once, sys.modules equals the original dict, and every module object retains its original identity. The preserve test checks the predicate itself: 'black_knight' is not preserved while 'zope', 'zope.interface', and 'zopelicious' are. The last test imports a module from a syspathinsert-ed directory, mutates its attribute inside the run, and asserts the change (data == 42) survives, so external imports are not reverted.

calls: [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d); uses: [src/_pytest/pytester.py][f2], [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062)

<a id="u-a15a49e58524"></a>
### `test_pytester.py-sys-modules-snapshot`

`class TestSysModulesSnapshot:` · [testing/test_pytester.py:L304-L307][f1]

Tests SysModulesSnapshot restore semantics over sys.modules using a class-level key 'my-test-module'.

test_remove_added: a module added after the snapshot is removed by restore, returning sys.modules to the original dict. test_add_removed: a module present at snapshot time but deleted afterwards is re-added by restore. test_restore_reloaded: a module replaced with a different object after the snapshot is restored to the original object. test_preserve_modules: with preserve(name) returning True for key[0], key[1] and 'some-other-key', restoring keeps the replaced objects for the preserved keys while reverting the non-preserved key[2]; since the test also rewrites 'original' entries for the preserved keys, equality with original still holds. test_preserve_container: when sys.modules itself is replaced by a new dict after the snapshot, restore writes the original contents back into the replacement dict in place, so sys.modules is the replacement but equals the original content.

uses: [src/_pytest/pytester.py][f2], [MonkeyPatch.setitem](r6-monkeypatch-engine.md#u-0494ec708f24)

<a id="u-ab667f3fa7dd"></a>
### `test_pytester.py-sys-paths-snapshot`

`class TestSysPathsSnapshot:` · [testing/test_pytester.py:L367-L371][f1]

Tests SysPathsSnapshot restore semantics, parametrized over sys.path and sys.meta_path (the other attribute is left untouched in both cases).

test_restore replaces the target list via monkeypatch, performs deletions, insertion, in-place replacement and append until it matches the transformed expected sequence, then asserts restore returns the very same list object (identity) with the original contents, and the other path list unchanged. test_preserve_container asserts that when the whole attribute is swapped for a fresh list after snapshotting, restore refills that new list in place: sys.path/sys.meta_path is the new object holding the original contents, and the other attribute object and contents are untouched. The static path helper generates the dummy entry names used by both tests.

uses: [src/_pytest/pytester.py][f2], [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062)

<a id="u-af13f284a58b"></a>
### `test_pytester.py-subprocess-basic`

`def test_pytester_subprocess(pytester: Pytester) -> None:` · [testing/test_pytester.py:L413-L415][f1]

Basic runpytest_subprocess and argument-handling checks.

A plain passing test run in a subprocess must return exit code 0, and so must a run without a timeout option. Passing a non-ASCII -k expression (Hebrew letters) collects no tests, yielding ExitCode.NO_TESTS_COLLECTED rather than an argument error.

<a id="u-df107bb3ee7e"></a>
### `test_pytester.py-run-timeout`

`def test_pytester_run_with_timeout(pytester: Pytester) -> None:` · [testing/test_pytester.py:L449-L459][f1]

Timeout behavior of runpytest_subprocess.

With timeout=120 a passing run must return OK and complete in under the timeout, measured via _pytest.timing.Instant elapsed. With timeout=1 a test that sleeps 10 seconds must cause pytester.TimeoutExpired to be raised by runpytest_subprocess.

<a id="u-5c12e24ef0fd"></a>
### `test_pytester.py-subprocess-plugins`

`def test_pytester_subprocess_with_string_plugins(pytester: Pytester) -> None:` · [testing/test_pytester.py:L839-L845][f1]

runpytest_subprocess plugin-argument validation.

String plugin names (pytester.plugins = ["pytester"]) are accepted and the subprocess run completes with NO_TESTS_COLLECTED. Non-string plugin objects trigger ValueError matching 'plugins as objects is not supported' when runpytest_subprocess is invoked; MyPlugin is a bare class instantiated for this purpose.

<a id="u-f0809b6095ff"></a>
### `test_pytester_subprocess_via_runpytest_arg`

`def test_pytester_subprocess_via_runpytest_arg(pytester: Pytester) -> None:` · [testing/test_pytester.py:L418-L436][f1]

A generated test, itself run inprocess with -p pytester and --runpytest subprocess, spawns a grandchild pytest subprocess that asserts its pid differs from its parent's; success proves the --runpytest subprocess option routes the nested run to a separate process.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-f6de64040cef"></a>
### `test_pytester.py-runresult-xfail`

`def test_runresult_assertion_on_xfail(pytester: Pytester) -> None:` · [testing/test_pytester.py:L118-L132][f1]

Three tests pin RunResult outcome accounting for xfail variants.

A non-strict xfail test that fails yields xfailed=1 with ret 0. A non-strict xfail test that passes yields xpassed=1 with ret 0. Under xfail(strict=True), a passing test is counted as failed=1 and the return code is nonzero, so strict unexpected passes are treated as failures.

<a id="u-448a656ec8c9"></a>
### `test_pytester.py-assert-outcomes-optional`

`def test_pytester_assert_outcomes_warnings(pytester: Pytester) -> None:` · [testing/test_pytester.py:L807-L820][f1]

Two tests show assert_outcomes checks only explicitly passed outcome kinds.

A run emitting a warning asserts passed=1, warnings=1, but a later assert_outcomes(passed=1) without warnings succeeds — warnings are not checked unless requested. Likewise a -k filtered run asserts passed=1, deselected=1, and a subsequent assert_outcomes(passed=1) without deselected also succeeds.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-d17eafcd1b40"></a>
### `test_assert_outcomes_after_pytest_error`

`def test_assert_outcomes_after_pytest_error(pytester: Pytester) -> None:` · [testing/test_pytester.py:L296-L301][f1]

Runs pytest with an unrecognized argument so no terminal summary is produced.

Calling result.assert_outcomes then raises ValueError matching 'Pytest terminal summary report not found', the contract asserted via pytest.raises; the requested outcomes are irrelevant because parsing fails first.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-361613cd3cb6"></a>
### `test_pytester_outcomes_with_multiple_errors`

`def test_pytester_outcomes_with_multiple_errors(pytester: Pytester) -> None:` · [testing/test_pytester.py:L740-L759][f1]

Two tests request a fixture that raises, producing two errors.

assert_outcomes(errors=2) and parseoutcomes() both report exactly {'errors': 2}, so errors aggregate across tests and parseoutcomes returns only the observed nouns.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-24663f425ca3"></a>
### `test_parse_summary_line_always_plural`

> **ID corrected by CBE.** CBE changed the unit ID from ` testing/test_pytester.py::function::test_parse_summary_line_always_plural::2415 ` to the inventory ID ` testing/test_pytester.py::function::test_parse_summary_line_always_plural::25225 `. The model wrote this body under the wrong ID; it may be inaccurate.

`def test_parse_summary_line_always_plural() -> None:` · [testing/test_pytester.py:L762-L788][f1]

Pins RunResult.parse_summary_nouns (#6505): singular nouns in the terminal summary line are always returned pluralized.

'1 failed, 1 passed, 1 warning, 1 error' yields keys failed/passed/warnings/errors with count 1; '2 warnings, 2 errors' yields 2 for those keys, so counts map to plural keys regardless of the summary's grammatical number.

uses: [src/_pytest/pytester.py][f2]

**Uncertainties.**

- The correct inventory id for this symbol is ...::test_parse_summary_line_always_plural::25225; the ::2415 id appears to collide with test_parseconfig, so the disposition key may mismatch the program's expectation

<a id="u-9c21de7fe8ef"></a>
### `test_run_result_repr`

`def test_run_result_repr() -> None:` · [testing/test_pytester.py:L721-L737][f1]

Constructs RunResult objects directly and pins repr formatting.

A known exit code 1 renders as the symbolic ExitCode.TESTS_FAILED, an unknown code 99 renders as the bare number; both include line counts of stdout and stderr and a two-decimal duration ('0.50s').

<a id="u-b25997ab8667"></a>
### `test_pytester.py-makepyfile-encoding`

`def test_makepyfile_unicode(pytester: Pytester) -> None:` · [testing/test_pytester.py:L205-L206][f1]

Two tests cover Pytester.makepyfile content encoding.

A lone U+FFFD replacement-character string must be accepted without encoding errors. UTF-8-encoded bytes containing 'São Paulo' (#2738) must round-trip: the created file's read_bytes includes the encoded source.

<a id="u-537e4cec335c"></a>
### `test_makefile_joins_absolute_path`

`def test_makefile_joins_absolute_path(pytester: Pytester) -> None:` · [testing/test_pytester.py:L791-L794][f1]

Passing an absolute path (as a string key) to makepyfile yields the file at that location with '.py' appended; the returned path equals pytester.path/absfile.py, so absolute basenames are joined rather than treated as relative names.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-5235c07c522d"></a>
### `test_pytester_makefile_dot_prefixes_extension_with_warning`

`def test_pytester_makefile_dot_prefixes_extension_with_warning( pytester: Pytester, )…` · [testing/test_pytester.py:L797-L804][f1]

Calling pytester.makefile with an extension like 'foo.bar' that starts with a dot-less first component raises ValueError with the message directing the caller to use '.foo.bar' instead, so multi-dot extensions must be given with a leading dot.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-b5c9f08c0172"></a>
### `test_pytester.py-popen-stdin`

`def test_popen_stdin_pipe(pytester: Pytester) -> None:` · [testing/test_pytester.py:L644-L655][f1]

Pytester.popen stdin modes.

With stdin=subprocess.PIPE the caller feeds bytes through proc.communicate(input=...) and the child echoes them as ['input', '2ndline'] with empty stderr and returncode 0. With stdin as a bytes payload popen itself supplies the pipe, so communicate() takes no input and the same output is produced. In a nested run, stdin=None leaves the pipe unclosed (avoiding 'ValueError: flush of closed file' from communicate), the child reading empty stdin prints a blank line then 'stdout' with 'stderr' on stderr and returncode 0; this inner test is wrapped so it does not hang under pytest -s.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-9f2798a2b051"></a>
### `test_run_stdin`

`def test_run_stdin(pytester: Pytester) -> None:` · [testing/test_pytester.py:L614-L641][f1]

Exercises Pytester.run stdin handling with subprocess-style stdin values.

A child that sleeps one second before reading stdin raises pytester.TimeoutExpired whether stdin is subprocess.PIPE or a bytes payload, when timeout is 0.1. Without a timeout, the same child with bytes stdin returns output lines ['input', '2ndline'], empty stderr, and ret 0, so bytes stdin is delivered intact and fully consumed.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f)

<a id="u-4ae73288e0ed"></a>
### `test_spawn_uses_tmphome`

`def test_spawn_uses_tmphome(pytester: Pytester) -> None:` · [testing/test_pytester.py:L701-L718][f1]

Checks that the pytester environment propagates into spawned processes.

At fixture setup HOME equals pytester.path, and a custom variable set via pytester._monkeypatch is visible. A generated test asserts both os.environ values inside a child launched with pytester.spawn_pytest; child.wait() must be 0, with the captured output included in the assertion message on failure.

calls: [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f), [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-3796fad31dd8"></a>
### `test_parseconfig`

`def test_parseconfig(pytester: Pytester) -> None:` · [testing/test_pytester.py:L77-L80][f1]

Calls pytester.parseconfig() twice and asserts the returned config objects are distinct, so each call must construct a fresh configuration rather than return a cached one.

calls: [pytester-parseconfig](r6-pytester-run.md#u-4da6110e81d7)

<a id="u-b781483b71af"></a>
### `test_pytester_runs_with_plugin`

`def test_pytester_runs_with_plugin(pytester: Pytester) -> None:` · [testing/test_pytester.py:L83-L92][f1]

A generated test file declares pytest_plugins = "pytester" and its inner test uses the pytester fixture, proving the plugin loads inside a nested inprocess run; runpytest must report exactly passed=1.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-8f78e0a36065"></a>
### `test_pytester_with_doctest`

`def test_pytester_with_doctest(pytester: Pytester) -> None:` · [testing/test_pytester.py:L95-L115][f1]

Verifies the pytester fixture works inside doctests, where request.function used to be None.

A package sub/ contains a doctest module that fetches the fixture, creates a file, and asserts its path ends with basetemp/sub.t-doctest0/sub.py with os.sep normalized to '/'. runpytest with -p pytester and --doctest-modules on that file must exit 0.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-3355b6658288"></a>
### `test_pytest_addopts_before_pytester`

`def test_pytest_addopts_before_pytester(request, monkeypatch: MonkeyPatch) -> None:` · [testing/test_pytester.py:L608-L611][f1]

Sets PYTEST_ADDOPTS via monkeypatch before requesting the pytester fixture, then asserts the variable is gone from os.environ.

This shows the pytester fixture clears PYTEST_ADDOPTS at setup time so environment options do not leak into nested runs.

calls: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469); uses: [MonkeyPatch.setenv](r6-monkeypatch-engine.md#u-3bcdaba77d61)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_pytester.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/pytester.py
