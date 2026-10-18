# Faulthandler plugin

**Capability.** Enables Python's faulthandler against a duplicated stderr descriptor at configure time, restores it at unconfigure, supports a per-test timeout dump wrapping each runtest protocol, and cancels pending dumps before interactive control (pdb, exception interaction).

Read this to understand crash traceback dumping and the faulthandler_timeout option, plus the tests that verify enabled-state and timeout-cancel behavior across subprocess runs.

**Depends on.**

- [pytest codebase](r5-pytest-codebase.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-faulthandler-plugin ` → ` r5-pytest-codebase `)

Parent: [Runtime diagnostics and shared primitives](r5-runtime-diagnostics.md)

## Units (9)

<a id="u-652dd4fea7ba"></a>
### `src/_pytest/faulthandler.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/faulthandler.py:L26-L38][f1]

Enables the faulthandler module against a duplicated stderr descriptor stashed on the Config for later restoration.

It obtains the stderr fileno via get_stderr_fileno, and if faulthandler.is_enabled() records that fileno under fault_handler_original_stderr_fd_key so teardown can re-enable the pre-existing handler. It always dups the fileno into fault_handler_stderr_fd_key and calls faulthandler.enable on the dup, so the session writes crash tracebacks to a descriptor that survives sys.stderr being closed or patched.

**Notes.**

- side_effect: Duplicates the stderr file descriptor and stores both the original fileno (only if faulthandler was already enabled) and the dup under Config.stash keys.

calls: [get_stderr_fileno](r5-faulthandler-plugin.md#u-a712297d7e1b); uses: [Stash](r8-typed-stash.md#u-3436b55c6fc2), [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

<a id="u-cb7a8b872a28"></a>
### `src/_pytest/faulthandler.py:pytest_unconfigure`

`def pytest_unconfigure(config: Config) -> None:` · [src/_pytest/faulthandler.py:L41-L52][f1]

Restores the faulthandler state captured at configure time.

It first calls faulthandler.disable() to stop the installed dump handler. If fault_handler_stderr_fd_key is stashed it closes the duplicated descriptor and deletes the stash entry. If fault_handler_original_stderr_fd_key is stashed (set only when faulthandler was enabled before the session), it re-enables faulthandler on that original fileno and deletes the key; otherwise the pre-session disabled state is left as is.

contract: [src/_pytest/faulthandler.py:pytest_configure](r5-faulthandler-plugin.md#u-652dd4fea7ba); uses: [Stash](r8-typed-stash.md#u-3436b55c6fc2)

<a id="u-a712297d7e1b"></a>
### `get_stderr_fileno`

`def get_stderr_fileno() -> int:` · [src/_pytest/faulthandler.py:L55-L68][f1]

Returns a usable stderr file descriptor even when sys.stderr is not a real file.

It calls sys.stderr.fileno(); if that returns -1 (e.g. Twisted Logger, not FD-backed) it raises AttributeError to route into the fallback, mirroring the pytest-xdist path. On AttributeError or ValueError from fileno() (e.g. xdist's non-file monkeypatched stderr) it asserts sys.__stderr__ is not None and returns its fileno; if sys.__stderr__ were None the assertion fails and no further fallback exists.

**Notes.**

- failure: The fallback asserts sys.__stderr__ is not None, so with no usable stderr at all the function aborts via AssertionError.

<a id="u-f73371f98e13"></a>
### `src/_pytest/faulthandler.py:pytest_runtest_protocol`

`def pytest_runtest_protocol(item: Item) -> Generator[None, object, object]:` · [src/_pytest/faulthandler.py:L75-L88][f1]

Wraps each test's protocol hook with an optional faulthandler timeout.

get_timeout_config_value reads the faulthandler_timeout ini as a float. If the timeout is positive it arms faulthandler.dump_traceback_later(timeout, file=<stashed stderr dup fd>) and yields to the inner protocol; the finally block always calls cancel_dump_traceback_later() so no late dump fires after the test. If the timeout is zero or negative it simply yields and returns the inner result without arming any timer. The stashed fd comes from pytest_configure's dup, so dumps go to the stable descriptor.

**Notes.**

- field: get_timeout_config_value returns float(config.getini("faulthandler_timeout") or 0.0), so a missing/empty ini value is treated as timeout 0 (disabled).

calls: [src/_pytest/faulthandler.py:pytest_runtest_protocol](r5-faulthandler-plugin.md#u-f73371f98e13); uses: [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

**Uncertainties.**

- Whether a dump is actually written on timeout depends on faulthandler's own thread, which is outside this source.

<a id="u-15f5655ef64f"></a>
### `faulthandler-cancel-dump-traceback-later`

`def pytest_enter_pdb() -> None:` · [src/_pytest/faulthandler.py:L91-L96][f1]

Two tryfirst hook wrappers that cancel any pending faulthandler timeout dump before interactive control leaves pytest.

pytest_enter_pdb cancels before dropping into pdb; pytest_exception_interact cancels when an exception is about to be shown interactively. Both import faulthandler and call faulthandler.cancel_dump_traceback_later() unconditionally; if no dump was armed the call is a no-op on the faulthandler side.

contract: [src/_pytest/faulthandler.py:pytest_runtest_protocol](r5-faulthandler-plugin.md#u-f73371f98e13)

<a id="u-48f0fe19a2fe"></a>
### `test_faulthandler-faulthandler-enabled-state-tests`

`def test_enabled(pytester: Pytester) -> None:` · [testing/test_faulthandler.py:L11-L22][f2]

These tests exercise pytest's faulthandler plugin enabled/disabled state across subprocess runs.

test_enabled writes a test calling faulthandler._sigabrt, runs it via runpytest_subprocess, and expects '*Fatal Python error*' on stderr with a nonzero return code. setup_crashing_test is a helper writing a module whose test registers faulthandler._sigabrt via atexit, so the crash fires during interpreter shutdown. test_crash_during_shutdown_captured launches that module with -Xfaulthandler and asserts the shutdown crash is captured on stderr with nonzero ret; test_crash_during_shutdown_not_captured launches without -Xfaulthandler and asserts no fatal-error line appears while ret is still nonzero (pytest must not re-enable faulthandler it did not find enabled, issue #8260). test_disabled runs with '-p no:faulthandler' and asserts the inner test sees faulthandler.is_enabled() False, '1 passed' on stdout, ret 0. test_already_initialized_crash runs under '-X faulthandler' and still expects the fatal-error traceback dump (#8258).

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f)

**Uncertainties.**

- Whether pytest re-enables or leaves faulthandler disabled is only observed via stderr matching; the plugin's configure-time logic is outside this file.

<a id="u-c8c11077a1f3"></a>
### `test_faulthandler-get_stderr_fileno_invalid_fd`

`def test_get_stderr_fileno_invalid_fd() -> None:` · [testing/test_faulthandler.py:L155-L159][f2]

test_get_stderr_fileno_invalid_fd checks _pytest.faulthandler.get_stderr_fileno tolerates a stderr object whose fileno() is invalid (#8249).

It defines StdErrWrapper, an io.StringIO subclass mimicking twisted.logger.LoggingFile whose fileno() returns -1, installs it as sys.stderr via a pytest.MonkeyPatch.context, and asserts get_stderr_fileno() still returns 2 — the real stderr descriptor rather than the wrapper's bogus -1. The test is split into s0 (imports and the wrapper definition) and s1 (the monkeypatched assertion); StdErrWrapper.fileno is a single return of -1.

**Uncertainties.**

- How get_stderr_fileno obtains fd 2 is outside this file; only its tolerance of a -1 fileno is observed.

<a id="u-686b981dacde"></a>
### `test_timeout`

`def test_timeout(pytester: Pytester, enabled: bool) -> None:` · [testing/test_faulthandler.py:L74-L110][f2]

Tests faulthandler_timeout ini-driven traceback dumping, parametrized with enabled=True (marked skip: sometimes crashes on CI, #7022) and enabled=False.

Writes a test sleeping 1s when the CI env var is set, else 0.1s, plus an ini with faulthandler_timeout = 0.01. When enabled it passes no extra args and expects '*most recent call first*' on stderr; when disabled it passes '-p no:faulthandler' and asserts that string is absent from stderr. In both cases the run still shows '*1 passed*' and ret 0 — the timeout dump does not fail the run.

**Notes.**

- condition: The enabled=True param is skipped via pytest.mark.skip because the timeout dump sometimes crashes CI (#7022).

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-run-processes](r6-pytester-run.md#u-7cf3beaa965f)

<a id="u-f829fac005fa"></a>
### `test_cancel_timeout_on_hook`

`def test_cancel_timeout_on_hook(monkeypatch, hook_name) -> None:` · [testing/test_faulthandler.py:L113-L132][f2]

Verifies the plugin's pytest_enter_pdb and pytest_exception_interact hooks cancel any pending timeout traceback dump (pytest-faulthandler#12/#14).

Parametrized over hook_name; it imports the stdlib faulthandler and the _pytest.faulthandler plugin, monkeypatches faulthandler.cancel_dump_traceback_later with a lambda appending 1 to a local list, then fetches the named hook from the plugin and calls it directly, asserting called == [1]. If a hook failed to cancel the scheduled dump, the fake cancel would not be invoked and the assertion fails.

uses: [src/_pytest/monkeypatch.py:MonkeyPatch.setattr (2)](r6-monkeypatch-engine.md#u-7e3e8acd6062)

**Uncertainties.**

- The concrete monkeypatch.setattr overload invoked is one of three candidates; only its observable effect (attribute replaced) is relied on.
- The hooks may perform additional work beyond cancelling; only the cancellation call is asserted here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/faulthandler.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/test_faulthandler.py
