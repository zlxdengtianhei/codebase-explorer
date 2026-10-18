# Capture primitive tests

**Capability.** Direct tests of capture internals: CaptureManager global lifecycle, FDCapture against real descriptors, the shared MultiCapture factory helpers, the teststdcapture family, CaptureIO/TeeCaptureIO, and DontReadFromInput/CaptureResult contracts, plus small test-support helpers.

These tests exercise the low-level sink objects; many module-level end-to-end tests call into the helpers defined here.

**Depends on.**

- [Capture end-to-end tests](r4-capture-endtoend-tests.md) · graph-confirmed · 6 edge(s)

**Depended on by.**

- [Capture end-to-end tests](r4-capture-endtoend-tests.md) · model-inferred · 0 edge(s)

Parent: [Capture tests](r4-test-capture-suite.md)

## Units (8)

<a id="u-6df8405153cc"></a>
### `testing-test-capture.py-testhelpers`

`def tmpfile(pytester: Pytester) -> Generator[BinaryIO]:` · [testing/test_capture.py:L974-L979][f1]

Small test-support helpers.

tmpfile is a fixture yielding a binary read/write file created from an empty pytester.makepyfile and closing it on teardown if still open. lsof_check is a context manager: it runs 'lsof -p <pid>' with a 10s timeout; if that raises OSError, UnicodeDecodeError, CalledProcessError, or TimeoutExpired it calls pytest.skip with the repr, otherwise it yields and afterwards re-runs lsof (no timeout guard on the second call) and asserts the count of 'REG' lines grew by fewer than 3, failing with the second output if file descriptors leaked. saved_fd is a context manager duplicating the given fd and, in a finally, restoring it with dup2 and closing the duplicate, guaranteeing the original fd state across a test body.

**Notes.**

- failure: lsof_check skips rather than fails when lsof is unavailable, but the post-yield lsof call has no timeout or exception guard.

<a id="u-72fa74a0d4ed"></a>
### `testing-test-capture.py-stdcapture-factories`

`def StdCaptureFD( out: bool = True, err: bool = True, in_: bool = True ) -> MultiCapt…` · [testing/test_capture.py:L33-L40][f1]

Factory helpers building MultiCapture instances over fd-level or sys-level capture sinks for tests in this file.

StdCaptureFD wraps FDCapture on fds 0/1/2, StdCapture wraps SysCapture, and TeeStdCapture wraps SysCapture with tee=True so output also passes through to the original stream. Each factory has out/err/in_ boolean flags defaulting to True; a False flag contributes None for that stream, so MultiCapture captures only the requested channels. The factories only construct the MultiCapture; capturing starts when start_capturing is called by the caller.

**Uncertainties.**

- Behavior of capture.MultiCapture, FDCapture, and SysCapture lives in _pytest/capture and is not covered by this batch.

<a id="u-e21247978cc5"></a>
### `testing-test-capture.py-testcapturemanager`

`class TestCaptureManager:` · [testing/test_capture.py:L63-L64][f1]

Tests for CaptureManager's global-capture lifecycle.

test_capturing_basic_api is parametrized over method in {no, sys, fd}: it installs an outer StdCaptureFD, starts global capturing, and asserts that suspend/read pairs return empty tuples, that after resuming and printing, method 'no' leaves sys.stdout/stderr/stdin untouched while sys/fd capture 'hello\n', always stopping the outer capture in a finally block. test_init_capturing asserts that calling start_global_capturing twice on a CaptureManager('fd') raises AssertionError. Both tests rely on unproven CaptureManager behavior in src/_pytest/capture.py.

calls: [testing-test-capture.py-stdcapture-factories](r4-capture-mechanism-tests.md#u-72fa74a0d4ed)

**Uncertainties.**

- Whether read_global_capture consumes buffers or accumulates is defined in src/_pytest/capture.py, not here.

<a id="u-99a788f15890"></a>
### `testing-test-capture.py-testfdcapture`

`class TestFDCapture:` · [testing/test_capture.py:L1002-L1003][f1]

Direct tests of capture.FDCapture against a real file descriptor, mostly via the tmpfile fixture.

test_simple shows that snap() before start() raises AssertionError, done() closes the capture, and after start() an os.write to the fd is returned verbatim by snap(); test_simple_many repeats it ten times and test_simple_many_check_open_files wraps that loop in lsof_check with an open tmpfile to assert no fd leak. test_simple_fail_second_start asserts start() after done() raises AssertionError. test_stderr and test_stdin apply FDCapture to fds 2 and 0 directly: stderr prints are captured, and reading stdin yields empty bytes. test_writeorg checks snap returns only data written while capturing while writeorg(str) sends text to the ORIGINAL fd, verified by re-reading the file after done(). test_simple_resume_suspend, inside saved_fd(1), verifies fd and sys-level writes are interleaved in snap order ('hello' + 'whatever'), that suspend() drops subsequent writes (snap empty), resume() recaptures, suspend after done() raises AssertionError, and that repr shows _state='done' with an '<UNSET>' _old on the chained SysCapture. test_capfd_sys_stdout_mode asserts the capfd fixture leaves sys.stdout.mode without 'b'.

calls: [testing-test-capture.py-testhelpers](r4-capture-mechanism-tests.md#u-6df8405153cc)

**Uncertainties.**

- FDCapture's internal dup/dup2/tmpfile mechanics are in src/_pytest/capture.py; state-machine rules are inferred from the assertions here.

<a id="u-05fed620d866"></a>
### `testing-test-capture.py-teststdcapture-family`

`class TestStdCapture:` · [testing/test_capture.py:L1106-L1109][f1]

Sys-level capture tests shared across three subclasses via the captureclass staticmethod and the getcapture context manager, which constructs the class with kwargs, starts capturing, and always stops in finally.

Inherited behavior: sys.stdout/sys.stderr writes are split into out/err by readouterr (which consumes buffers, so a second read returns only new output); readouterr returns a CaptureResult with .out/.err attributes; unicode prints round-trip; stopping twice raises ValueError; replacing sys.stdout/sys.stderr with fresh CaptureIO objects mid-capture does not affect already-captured data, and the originals are restored on exit (assignment via print to the swapped objects is invisible); nested captures isolate their output (cap1 sees only pre-nesting output, cap2 its own); out=False or err=False disables the respective channel; stdin is restored after capture and, by default, replaced with a null stream whose read raises OSError. TestTeeStdCapture overrides only test_capturing_error_recursive: with tee=True the outer capture also sees the inner capture's passthrough output, so cap1 reads 'cap1\ncap2\n' while cap2 reads only 'cap2\n'. TestStdCaptureFD switches captureclass to StdCaptureFD and adds fd-level tests: test_simple_only_fd (subprocess: os.write to fd 1 captured on failure), test_intermingling asserting fd writes and sys writes appear in call order ('123'/'abc' after flushes), and test_many running StdCaptureFD start/stop ten times inside lsof_check.

uses: [testing-test-capture.py-stdcapture-factories](r4-capture-mechanism-tests.md#u-72fa74a0d4ed); calls: [testing-test-capture.py-testhelpers](r4-capture-mechanism-tests.md#u-6df8405153cc)

<a id="u-9f71f83bf35b"></a>
### `testing-test-capture.py-testcaptureio`

`class TestCaptureIO:` · [testing/test_capture.py:L877-L878][f1]

Unit tests for capture.CaptureIO and capture.TeeCaptureIO.

For CaptureIO: write then getvalue returns the text; writing bytes raises TypeError while a unicode str writes fine; and the underlying .buffer accepts bytes, which getvalue exposes as text ('foo\r\n' round-trips), covering the issue-1407 text-io-wrapper case. TeeCaptureIO is tested as a subclass mirroring CaptureIO's contract, additionally asserting that writes appear in the wrapped io.StringIO target: both getvalue() results are equal after writing 'hello', and the bytes-vs-str TypeError rule holds. The TestTeeCaptureIO class inherits from TestCaptureIO, overriding both named tests and inheriting test_write_bytes_to_buffer unchanged.

inherits: [testing-test-capture.py-testcaptureio](r4-capture-mechanism-tests.md#u-9f71f83bf35b)

**Uncertainties.**

- CaptureIO/TeeCaptureIO implementations are in src/_pytest/capture.py, outside this batch.

<a id="u-02956f86192d"></a>
### `testing-test-capture.py-dontreadfrominput-captureresult`

`def test_dontreadfrominput() -> None:` · [testing/test_capture.py:L918-L941][f1]

Contract tests for two capture primitives.

test_dontreadfrominput builds a DontReadFromInput and enumerates its contract: buffer is the object itself, isatty is False, read/readlines/__next__ raise OSError, and fileno/flush/seek/tell/truncate/write/writelines raise UnsupportedOperation, while readable/seekable/writable are False, encoding is a str; close() and using it as a context manager are harmless. test_captureresult checks CaptureResult('out','err') as a namedtuple-like value: length 2, .out/.err, tuple unpacking and indexing, equality with equal instances and plain tuples and inequality otherwise, hash equal to the tuple's, tuple ordering comparisons, count/index (index of a missing element raises ValueError), iteration, and _replace.

<a id="u-d747b77e5901"></a>
### `testing-test-capture.py-invalid-fd-tests`

`class TestStdCaptureFDinvalidFD:` · [testing/test_capture.py:L1283-L1284][f1]

Tests capturing behavior when the target fd is already closed.

test_stdcapture_fd_invalid_fd spawns a subprocess (with its own StdCaptureFD copy) where each test closes fd 1, 2, or 0 first, then builds a MultiCapture for just that channel and asserts the repr matches "<FDCapture N oldfd=* _state='initialized' tmpfile=*>"; the stdout and stderr variants also capture os.writes after start and read them back — all three pass, proving closed-fd capture works by reallocating the fd. test_fdcapture_invalid_fd_with_fd_reuse uses saved_fd(1), closes fd 1, then FDCaptureBinary(1): start makes fd 1 valid again, suspend/resume behavior accumulates 'started resumed' in snap, and after done() writing fd 1 raises OSError. test_fdcapture_invalid_fd_without_fd_reuse does the same against fd 2 while both 1 and 2 are saved and closed, giving the same start/suspend/resume/done lifecycle and OSError after done.

calls: [testing-test-capture.py-testhelpers](r4-capture-mechanism-tests.md#u-6df8405153cc)

**Uncertainties.**

- Whether FDCapture deliberately reuses the freed fd number or merely opens the tmpfile into it is decided in src/_pytest/capture.py.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_capture.py
