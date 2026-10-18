# Capture Fixtures

**Capability.** Per-test fixtures (capsys, capsysbinary, capfd, capfdbinary, capteesys) that hand a CaptureFixture to tests, choosing backend and text/bytes mode and precedence over global capture.

Use this subtree for the user-facing capture API. Each fixture follows the same set/start/yield/close/unset lifecycle through CaptureFixture, which delegates to CaptureManager and the MultiCapture selected for it.

**Depends on.**

- [Capture Backends & Lifecycle](r3-capture-backends.md) · graph-confirmed · 1 edge(s)
- [Capture Coordination](r3-capture-manager.md) · graph-confirmed · 10 edge(s)

Parent: [Output & Input Capture](r3-io-capture.md)

## Units (6)

<a id="u-0cd7ba3c92b4"></a>
### `CaptureFixture`

`class CaptureFixture(Generic[AnyStr]):` · [src/_pytest/capture.py:L916-L920][f1]

Per-test capture object behind capsys/capsysbinary/capfd/capfdbinary.

__init__ enforces internal construction via check_ispytest, stores the CaptureBase subclass, the SubRequest, and an optional config dict of extra constructor kwargs, with no active capture and empty buffers taken from the capture class's EMPTY_BUFFER. _start lazily builds a MultiCapture with in_=None and out/err from captureclass(1, **config)/captureclass(2, **config), then starts it; repeated calls do nothing once started. close() flushes pending capture back to the original streams via pop_outerr_to_orig, accumulates it into _captured_out/_captured_err, stops the capture, and clears it. readouterr returns accumulated buffered out/err plus any new snapshot from the live capture, then resets both buffers to EMPTY_BUFFER, so each call returns only output since the previous call. _suspend/_resume suspend/resume the fixture's own MultiCapture when present; _is_started reports whether the MultiCapture exists and is in 'started' state. disabled() is a context manager that resolves the 'capturemanager' plugin from the request's config and delegates to its global_and_fixture_disabled(), suspending both global and fixture capture inside the with block.

uses: [CaptureManager](r3-capture-manager.md#u-a88cc981e1b7), [capture-py-captureresult](r3-capture-backends.md#u-58afc80d4862)

**Uncertainties.**

- The config dict's accepted keys depend on the captureclass constructors (e.g. tee=True for SysCapture); other keys would surface as constructor errors not visible here.

<a id="u-51bff11e094c"></a>
### `capsys`

`def capsys(request: SubRequest) -> Generator[CaptureFixture[str]]:` · [src/_pytest/capture.py:L999-L1024][f1]

Fixture enabling text capture of sys.stdout/sys.stderr writes.

It fetches the capturemanager plugin, creates a CaptureFixture(SysCapture), registers it with the manager (which fails if another capture fixture is active), starts it, yields the fixture to the test, then closes it (flushing pending capture back to the originals) and unregisters it, so global capture resumes afterwards.

uses: [CaptureFixture](r3-capture-fixtures.md#u-0cd7ba3c92b4); calls: [CaptureManager](r3-capture-manager.md#u-a88cc981e1b7)

<a id="u-cefcc82ca52e"></a>
### `capsysbinary`

`def capsysbinary(request: SubRequest) -> Generator[CaptureFixture[bytes]]:` · [src/_pytest/capture.py:L1062-L1087][f1]

Fixture enabling bytes capture of sys.stdout/sys.stderr: same set/start/yield/close/unset lifecycle as capsys but with CaptureFixture(SysCaptureBinary), so readouterr() returns bytes in out/err.

uses: [CaptureFixture](r3-capture-fixtures.md#u-0cd7ba3c92b4)

<a id="u-29b4163dbadd"></a>
### `capfd`

`def capfd(request: SubRequest) -> Generator[CaptureFixture[str]]:` · [src/_pytest/capture.py:L1090-L1115][f1]

Fixture enabling text capture at the OS file-descriptor level (fds 1 and 2), so output from subprocesses is also captured: same set/start/yield/close/unset lifecycle as capsys but with CaptureFixture(FDCapture); readouterr() returns text.

uses: [CaptureFixture](r3-capture-fixtures.md#u-0cd7ba3c92b4)

<a id="u-714173978b8b"></a>
### `capfdbinary`

`def capfdbinary(request: SubRequest) -> Generator[CaptureFixture[bytes]]:` · [src/_pytest/capture.py:L1118-L1144][f1]

Fixture enabling bytes capture at the OS file-descriptor level (fds 1 and 2): same lifecycle as capfd but with CaptureFixture(FDCaptureBinary); readouterr() returns bytes.

uses: [CaptureFixture](r3-capture-fixtures.md#u-0cd7ba3c92b4)

<a id="u-9317d6d08c26"></a>
### `capteesys`

`def capteesys(request: SubRequest) -> Generator[CaptureFixture[str]]:` · [src/_pytest/capture.py:L1027-L1059][f1]

Fixture enabling simultaneous text capture and pass-through of sys.stdout/sys.stderr: identical lifecycle to capsys but builds the CaptureFixture with config={'tee': True}, so the underlying SysCapture writes to a TeeCaptureIO that mirrors output to the real stream while also capturing it, respecting the global --capture setting.

uses: [CaptureFixture](r3-capture-fixtures.md#u-0cd7ba3c92b4)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/capture.py
