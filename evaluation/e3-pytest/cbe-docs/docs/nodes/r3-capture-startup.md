# Capture Startup & Options

**Capability.** Registering the --capture/-s options and installing global capture during startup, including platform-specific stdio workarounds so capture does not corrupt Windows/libedit streams.

Use this subtree for early-session behavior: option registration and the pytest_load_initial_conftests hook that applies stdio workarounds and starts global capture before conftests load.

**Depends on.**

- [Capture Backends & Lifecycle](r3-capture-backends.md) · graph-confirmed · 1 edge(s)
- [Capture Coordination](r3-capture-manager.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Capture Backends & Lifecycle](r3-capture-backends.md) · model-inferred · 0 edge(s)

Parent: [Output & Input Capture](r3-io-capture.md)

## Units (3)

<a id="u-533b46382224"></a>
### `src/_pytest/capture.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/capture.py:L49-L65][f1]

Registers the --capture option (choices fd|sys|no|tee-sys, default 'fd') in the 'general' parser group plus a private -s short option storing the constant 'no' into the same 'capture' destination.

Registration only; parsing is delegated to the parser.

calls: [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

<a id="u-178712d83b07"></a>
### `pytest_load_initial_conftests`

`def pytest_load_initial_conftests(early_config: Config) -> Generator[None]:` · [src/_pytest/capture.py:L155-L180][f1]

Early hook applying stdio workarounds and installing global capture before conftest loading.

When the parsed capture method is 'fd' it runs the Windows console workaround on sys.stdout; then it always applies colorama and readline workarounds. It builds a CaptureManager for the method, registers it as plugin 'capturemanager', and adds capman.stop_global_capturing as a config cleanup for final shutdown. Conftest loading is yielded while global capture is active; the finally clause suspends capture, and on any BaseException the captured out/err are replayed to real sys.stdout/sys.stderr before re-raising, so early failures remain visible.

uses: [CaptureManager](r3-capture-manager.md#u-a88cc981e1b7); calls: [Config.add_cleanup](r2-config-lifecycle.md#u-6ed386e09426)

**Uncertainties.**

- Ordering of the exception-path sys.stdout.write against output already written outside capture is not determinable here.

<a id="u-5cc27f2fbb69"></a>
### `capture-py-startup-workarounds`

`def _colorama_workaround() -> None:` · [src/_pytest/capture.py:L68-L80][f1]

Groups three startup workarounds so I/O capture does not corrupt Windows/libedit stdio handling.

_colorama_workaround imports colorama only when sys.platform starts with 'win32', swallowing ImportError so colorama binds to console handles before capture redirects them. _readline_workaround imports readline unconditionally, swallowing ImportError, so libedit-based readline attaches to the real stdio handles before capture; it cannot check readline.backend because importing it already performs the fix. _windowsconsoleio_workaround(stream) returns immediately on non-Windows, on PyPy, when stream lacks a 'buffer' attribute, or when the buffer's raw is not io._WindowsConsoleIO. Otherwise its inner _reopen_stdio dups each std stream's fileno and wraps it in a TextIOWrapper preserving encoding/errors/newlines/line_buffering, choosing buffering=0 only when the buffer has no 'raw' and mode starts with 'w'; then sys.stdin ('rb'), sys.stdout ('wb') and sys.stderr ('wb') are rebound so the console handles closed by FDCapture's dup2 are not the ones Python writes through.

**Notes.**

- side_effect: _windowsconsoleio_workaround permanently rebinds sys.stdin/stdout/stderr to freshly duped descriptors.

calls: [pytest_load_initial_conftests](r3-capture-startup.md#u-178712d83b07)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/capture.py
