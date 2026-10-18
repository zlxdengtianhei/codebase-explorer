# Capture Backends & Lifecycle

**Capability.** The CaptureBase contract and its FD-level and sys-level implementations (text and binary), the no-op backend, in-memory stream targets, the stdin guard, and MultiCapture aggregation selected by the method-name factory.

Use this subtree when working on how bytes/text are intercepted and drained via snap(). Each backend pairs a base with str/bytes snap variants; DontReadFromInput converts stdin access into a controlled error while capture is active.

**Depends on.**

- [Capture Startup & Options](r3-capture-startup.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Capture Fixtures](r3-capture-fixtures.md) · graph-confirmed · 1 edge(s)
- [Capture Coordination](r3-capture-manager.md) · graph-confirmed · 2 edge(s)
- [Capture Startup & Options](r3-capture-startup.md) · graph-confirmed · 1 edge(s)

Parent: [Output & Input Capture](r3-io-capture.md)

## Units (14)

<a id="u-6949f49c99cb"></a>
### `capture-py-captureio`

`class CaptureIO(io.TextIOWrapper):` · [src/_pytest/capture.py:L203-L204][f1]

CaptureIO is a TextIOWrapper over a fresh BytesIO with UTF-8 encoding, no newline translation, and write_through=True; it is the in-memory target for sys-level capturing.

getvalue() asserts the buffer is BytesIO and returns its bytes decoded as UTF-8. TeeCaptureIO extends it: its constructor stores a second TextIO before delegating to CaptureIO.__init__, and write(s) writes to both its own buffer (superclass) and the stored stream, returning the other stream's count; this is what makes tee-sys both capture and pass through output.

**Notes.**

- contract: TeeCaptureIO.write returns the pass-through stream's write count, not the local buffer's.

<a id="u-58afc80d4862"></a>
### `capture-py-captureresult`

`class CaptureResult(NamedTuple, Generic[AnyStr]):` · [src/_pytest/capture.py:L610-L615][f1]

CaptureResult is an immutable (out, err) pair returned by readouterr().

On Python 3.11+ (or under type checking) it is a generic final NamedTuple; otherwise it is a generic namedtuple subclass with empty __slots__. Both forms expose fields 'out' and 'err'; element type AnyStr varies by caller (str for fd/sys capture, bytes for the binary variants).

**Uncertainties.**

- Which of the two class definitions is active depends on runtime Python version, an external condition.

<a id="u-14148654269b"></a>
### `capture-py-dontreadfrominput`

`def encoding(self) -> str:` · [src/_pytest/capture.py:L223-L226][f1]

DontReadFromInput is the sys.stdin replacement while capturing; it converts any stdin access into a controlled error instead of blocking.

Read paths raise OSError('pytest: reading from stdin while output is captured!  Consider using `-s`.'): read (and its alias readline), __next__ (which calls readline, so iteration raises the same OSError, never StopIteration), and readlines. Pseudo-file operations raise io.UnsupportedOperation: fileno, flush, seek, tell, truncate, plus write and writelines on the write side. Non-failing members: encoding forwards to sys.__stdin__.encoding (asserting it is not None), isatty returns False, readable/writable/seekable return False, close is a no-op, __iter__ returns self, __enter__/__exit__ make 'with' work, and buffer returns the object itself, faking a binary buffer for callers needing the attribute.

**Notes.**

- failure: buffer returning self means binary reads through .buffer are not actually supported despite the type.

<a id="u-87dd04f5c11e"></a>
### `capture-py-encodedfile`

`def name(self) -> str: # Ensure that file.name is a string. Workaround for a Python b…` · [src/_pytest/capture.py:L189-L193][f1]

EncodedFile is a TextIOWrapper subclass exposing two compatibility properties.

'name' returns repr(self.buffer), guaranteeing a string name (workaround for a Python bug fixed in 3.7.4). 'mode' asserts the buffer has a 'mode' and returns it with any 'b' stripped, since TextIOWrapper does not expose mode but some pytest tests check it. All other behavior is inherited from TextIOWrapper wrapping the target binary temp file.

<a id="u-276c4ddffca3"></a>
### `capture-py-nocapture`

`class NoCapture(CaptureBase[str]):` · [src/_pytest/capture.py:L337-L340][f1]

NoCapture is a no-op CaptureBase[str] used when a target FD is not one of 0/1/2 or for capture method 'no'.

__init__ ignores the fd, start/done/suspend/resume/writeorg all do nothing, and snap() returns EMPTY_BUFFER (''). It exists so MultiCapture and FDCaptureBase can call the lifecycle uniformly without conditionals.

<a id="u-1b3686619f19"></a>
### `CaptureBase`

`class CaptureBase(abc.ABC, Generic[AnyStr]):` · [src/_pytest/capture.py:L302-L305][f1]

Abstract generic base defining the capture lifecycle contract: __init__(fd), start, done, suspend, resume, writeorg(data), and snap() returning AnyStr, plus an EMPTY_BUFFER class constant typed per instantiation.

Every method is abstract and raises NotImplementedError, so subclasses must implement the full state machine; EMPTY_BUFFER is only a declaration here, with concrete values supplied by subclasses.

**Uncertainties.**

- EMPTY_BUFFER has no value in the base; code instantiating CaptureBase directly would fail on attribute use.

<a id="u-ff5299c393f7"></a>
### `MultiCapture`

`class MultiCapture(Generic[AnyStr]):` · [src/_pytest/capture.py:L628-L632][f1]

Aggregates optional in_/out/err CaptureBase instances and drives their lifecycle with a class-level _state (None initially) and _in_suspended flag.

start_capturing sets state 'started' then starts each present capturer. pop_outerr_to_orig snapshots via readouterr() and, for each non-empty out/err, writes it to the corresponding capturer's original stream with writeorg, returning the pair. suspend_capturing sets state 'suspended', suspends out then err, and only suspends in_ (recording _in_suspended) when the in_ flag is true. resume_capturing sets state 'started', resumes out then err, and resumes in_ only if it was suspended, clearing the flag. stop_capturing raises ValueError('was already stopped') if state is 'stopped'; otherwise marks stopped and calls done() on out, err, in_ in that order. is_started reports state == 'started' (not suspended/stopped). readouterr snaps out and err independently (empty string when absent) and wraps them in CaptureResult; each snap drains its tmpfile, so repeated calls return only new output.

uses: [capture-py-captureresult](r3-capture-backends.md#u-58afc80d4862)

**Uncertainties.**

- start_capturing does not check prior state; calling it twice would re-run sub-starts whose own assertions may fail — behavior of a double start is not established here.

<a id="u-cccc52c7ea58"></a>
### `FDCapture`

`class FDCapture(FDCaptureBase[str]):` · [src/_pytest/capture.py:L581-L589][f1]

FDCaptureBase[str] whose snap() asserts started/suspended, reads the tmpfile as text from position 0, then seeks and truncates (EMPTY_BUFFER '').

writeorg encodes the str as UTF-8 (source notes the original stream's encoding is not used) and writes the bytes to targetfd_save via os.write.

inherits: [FDCaptureBase](r3-capture-backends.md#u-2317c3041c06)

<a id="u-2317c3041c06"></a>
### `FDCaptureBase`

`class FDCaptureBase(CaptureBase[AnyStr]):` · [src/_pytest/capture.py:L464-L465][f1]

Base for OS-level file-descriptor capture.

__init__ first fstats the targetfd: on OSError the FD is invalid, so it opens os.devnull and dup2s that descriptor over the invalid targetfd, recording the devnull fd as targetfd_invalid; otherwise targetfd_invalid is None. It then saves the current targetfd as targetfd_save. For fd 0 the tmpfile is devnull opened as UTF-8 text and syscapture is a SysCapture(0) (so stdin reads raise the pytest OSError); otherwise the tmpfile is an EncodedFile over an unbuffered TemporaryFile, and syscapture is a SysCapture sharing that tmpfile for fds 1/2, or NoCapture for other fds. State machine mirrors SysCaptureBase with dup2 instead of sys attribute swaps: start dup2s the tmpfile over targetfd then starts syscapture; done restores targetfd_save, closes saved/invalid fds (closing the targetfd copy only when it differs from the invalid devnull fd) and syscapture/tmpfile, idempotent when already 'done'; suspend is a no-op if already suspended, else suspends syscapture and restores the saved fd; resume is a no-op if already started, else resumes syscapture and dup2s the tmpfile back. _assert_state raises AssertionError with operation, current and allowed states.

uses: [capture-py-nocapture](r3-capture-backends.md#u-276c4ddffca3), [SysCapture](r3-capture-backends.md#u-590c1e82ddae)

**Uncertainties.**

- If an exception occurs between dup operations, partial fd redirection may persist; no rollback is visible in the source.

<a id="u-5ef84b7d45ff"></a>
### `FDCaptureBinary`

`class FDCaptureBinary(FDCaptureBase[bytes]):` · [src/_pytest/capture.py:L559-L567][f1]

FDCaptureBase[bytes] whose snap() asserts started/suspended, reads the tmpfile's binary buffer from position 0 as bytes, then seeks to 0 and truncates (EMPTY_BUFFER b'').

writeorg asserts the same states and writes the raw bytes directly to targetfd_save with os.write, bypassing any encoding.

inherits: [FDCaptureBase](r3-capture-backends.md#u-2317c3041c06)

<a id="u-590c1e82ddae"></a>
### `SysCapture`

`class SysCapture(SysCaptureBase[str]):` · [src/_pytest/capture.py:L447-L450][f1]

SysCaptureBase[str] variant whose snap() returns text: asserts started/suspended, asserts the tmpfile is CaptureIO, returns getvalue() (UTF-8-decoded), then seeks and truncates the tmpfile (EMPTY_BUFFER '').

writeorg writes the str to the saved original stream and flushes it.

inherits: [SysCaptureBase](r3-capture-backends.md#u-6fbeba18f2ab)

<a id="u-6fbeba18f2ab"></a>
### `SysCaptureBase`

`class SysCaptureBase(CaptureBase[AnyStr]):` · [src/_pytest/capture.py:L362-L363][f1]

Base for capture methods that swap attributes on the sys module instead of OS file descriptors.

__init__ maps fd to 'stdin'/'stdout'/'stderr' via patchsysdict, saves the current sys attribute as _old, and if no tmpfile is given uses DontReadFromInput for stdin, otherwise a CaptureIO (or TeeCaptureIO wrapping the saved stream when tee=True). State machine with assertion guards: start (only from 'initialized') sets sys.<name> to tmpfile and state 'started'; done (allowed from any state, idempotent when already 'done') restores _old, deletes it, closes tmpfile, state 'done'; suspend (from 'started'/'suspended') restores _old, state 'suspended'; resume (from 'started'/'suspended') is a no-op if already 'started', otherwise reinstalls tmpfile and returns to 'started'. _assert_state raises AssertionError naming the operation, current state, and allowed states; repr methods render name, _old (or '<UNSET>'), state, and tmpfile.

uses: [capture-py-dontreadfrominput](r3-capture-backends.md#u-14148654269b), [capture-py-captureio](r3-capture-backends.md#u-6949f49c99cb)

**Uncertainties.**

- Graph evidence shows FDCapture* subclasses also call _assert_state with two same-named candidates (SysCaptureBase/FDCaptureBase); each class defines its own copy, which this unit documents for SysCaptureBase only.

<a id="u-519dea186f9b"></a>
### `SysCaptureBinary`

`class SysCaptureBinary(SysCaptureBase[bytes]):` · [src/_pytest/capture.py:L429-L432][f1]

SysCaptureBase[bytes] variant whose snap() drains the tmpfile as bytes: it asserts state started/suspended, seeks to 0, reads the whole binary buffer, then seeks and truncates for the next round, returning raw bytes (EMPTY_BUFFER b'').

writeorg(data: bytes) asserts the same states, flushes then writes bytes to the saved original stream's .buffer and flushes it, so binary data reaches the real stdout/stderr unchanged.

inherits: [SysCaptureBase](r3-capture-backends.md#u-6fbeba18f2ab)

<a id="u-1860a2544538"></a>
### `_get_multicapture`

`def _get_multicapture(method: _CaptureMethod) -> MultiCapture[str]:` · [src/_pytest/capture.py:L712-L723][f1]

Factory mapping a capture method name to a MultiCapture: 'fd' wraps FDCapture on fds 0/1/2; 'sys' wraps SysCapture on all three; 'no' yields a MultiCapture with all None (no-op capture); 'tee-sys' leaves in_ None and uses tee=True SysCapture on fds 1 and 2 for pass-through plus capture.

Any other value raises ValueError naming the unknown method.

calls: [MultiCapture](r3-capture-backends.md#u-ff5299c393f7); uses: [FDCapture](r3-capture-backends.md#u-cccc52c7ea58)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/capture.py
