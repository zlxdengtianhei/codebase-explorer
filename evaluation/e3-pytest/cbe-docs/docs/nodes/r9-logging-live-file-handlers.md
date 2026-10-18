# Live and File Handlers

**Capability.** Handlers that write logs outside caplog: the live-CLI StreamHandler emitting into the TerminalReporter (or a no-op null handler), and the _FileHandler backing --log-file.

Use this to understand live output timing and the suppression of stdout/stderr capture during emission, and where file logs are written. The live handler depends on the terminal reporter, which lives in the terminal-reporting subtree.

**Depends on.**

- [Reporter Lifecycle and Collection Output](r9-terminal-reporter-core.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) · model-inferred · 0 edge(s)

Parent: [Logging Plugin](r9-logging-plugin.md)

## Units (4)

<a id="u-f39c2e7e81cb"></a>
### `_LiveLoggingStreamHandler`

`class _LiveLoggingStreamHandler(logging_StreamHandler):` · [src/_pytest/logging.py:L890-L903][f1]

StreamHandler for live logging that writes to a TerminalReporter (forced into the stream attribute despite the IO[str] typing) and temporarily disables capture while emitting.

The constructor stores the optional CaptureManager, resets the first-record flag, sets when to None, and clears the outcome-written flag. reset() clears _first_record_emitted before each test; set_when stores the phase, clears _section_name_shown, and resets _test_outcome_written only when when == 'start'. handleError suppresses errors like the other pytest handlers.

contract: [_LiveLoggingStreamHandler.emit](r9-logging-live-file-handlers.md#u-9010b9d2925a)

<a id="u-9010b9d2925a"></a>
### `_LiveLoggingStreamHandler.emit`

`def emit(self, record: logging.LogRecord) -> None:` · [src/_pytest/logging.py:L925-L942][f1]

Emits a live-log record, disabling stdout/stderr capture around the write when a CaptureManager is present (global_and_fixture_disabled) or using a nullcontext otherwise.

On the first record of a run it writes a leading newline; subsequently, during 'teardown' or 'finish' phases it writes one newline as the test outcome separator, guarded by _test_outcome_written. Before the record itself it prints a 'live log <when>' section header (sep '-', bold) once per phase when a when marker is set. Finally it delegates to the superclass emit to format and write the record.

uses: [_LiveLoggingStreamHandler](r9-logging-live-file-handlers.md#u-f39c2e7e81cb)

**Uncertainties.**

- Behavior when stream is a TerminalReporter lacking write/section is not guarded in this source; the class comment acknowledges the IO[str] mismatch.

<a id="u-4f16114a689a"></a>
### `_LiveLoggingNullHandler`

`class _LiveLoggingNullHandler(logging.NullHandler):` · [src/_pytest/logging.py:L949-L952][f1]

No-op live-logging handler installed when live logging is disabled.

reset, set_when, and handleError all do nothing, so the plugin's hook calls on log_cli_handler are safe without any live output.

<a id="u-ee6819f6cc32"></a>
### `_FileHandler`

`class _FileHandler(logging.FileHandler):` · [src/_pytest/logging.py:L882-L885][f1]

A logging.FileHandler subclass used for pytest's log file.

Its handleError override does nothing, suppressing the stdlib's stderr traceback on emit failures; the comment defers such failures to LogCaptureHandler's handling instead.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/logging.py
