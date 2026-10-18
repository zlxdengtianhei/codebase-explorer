# caplog Capture Fixture

**Capability.** The caplog fixture object and its level/filter context managers, backed by the in-memory LogCaptureHandler and the catching_logs context manager that installs handlers on the root logger.

Read this when writing tests that inspect captured records or temporarily change levels. set_level/at_level/_force_enable_logging interact with logging.disable() caps; filtering attaches a Filter. LogCaptureHandler and catching_logs are the underlying capture mechanisms also used by the plugin core.

**Depends on.**

- [Log Formatters](r9-logging-formatters.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Plugin Lifecycle and Phase Capture](r9-logging-plugin-core.md) · graph-confirmed · 2 edge(s)

Parent: [Logging Plugin](r9-logging-plugin.md)

## Units (8)

<a id="u-7c2a746b7051"></a>
### `LogCaptureFixture`

`class LogCaptureFixture:` · [src/_pytest/logging.py:L403-L407][f1]

The caplog fixture object, constructed only via the _ispytest keyword gate (check_ispytest).

It wraps an item node whose stash holds the session's LogCaptureHandler and per-phase record dict. Read accessors expose the handler (item stash caplog_handler_key), per-phase records via get_records (stash dict .get(when, [])), ANSI-stripped handler text, the record list, (name, levelno, message) tuples, and interpolated messages; clear() delegates to handler.clear(). _finalize restores state changed by set_level: the handler level if one was saved, each logger level recorded in _initial_logger_levels, and the saved logging.disable level, clearing that saved value afterwards.

uses: [LogCaptureHandler](r9-logging-capture-fixtures.md#u-83fec58eea9a); calls: [method::check_ispytest::?][f2]

<a id="u-aac2369675fd"></a>
### `caplog`

`def caplog(request: FixtureRequest) -> Generator[LogCaptureFixture]:` · [src/_pytest/logging.py:L595-L609][f1]

Fixture factory yielding a LogCaptureFixture bound to the requesting node, and finalizing it afterwards.

It builds the fixture with _ispytest=True, yields it to the test, then calls result._finalize() so levels and logging.disable changes made via set_level are restored at teardown.

calls: [LogCaptureFixture](r9-logging-capture-fixtures.md#u-7c2a746b7051)

<a id="u-ba9d59de879d"></a>
### `LogCaptureFixture._force_enable_logging`

`def _force_enable_logging( self, level: int | str, logger_obj: logging.Logger ) -> int:` · [src/_pytest/logging.py:L495-L527][f1]

Undoes a logging.disable() cap for the requested capture level and returns the previous global disabled level.

It snapshots logger_obj.manager.disable first. If level is a string it converts via logging.getLevelName; a non-int result (unrecognized name) causes logging.disable(logging.NOTSET), un-disabling everything. If the resulting int level is not enabled on the logger, it sets logging.disable(max(level - 10, logging.NOTSET)) so exactly that severity and above become loggable. The caller is expected to restore the returned original level later.

**Notes.**

- side_effect: Mutates global logging state (logging.disable) that persists until the caller restores it.

uses: [LogCaptureFixture.set_level](r9-logging-capture-fixtures.md#u-585ee5918975), [LogCaptureFixture.at_level](r9-logging-capture-fixtures.md#u-81948d52a205)

**Uncertainties.**

- logging.getLevelName returning an int for a known name versus a lookup string for unknown names is assumed per the stdlib API; behavior for numeric strings like '20' is not shown.

<a id="u-81948d52a205"></a>
### `LogCaptureFixture.at_level`

`def at_level(self, level: int | str, logger: str | None = None) -> Generator[None]:` · [src/_pytest/logging.py:L554-L576][f1]

Context manager that temporarily sets the capture level for a logger (root by default) and the fixture handler.

It saves the logger's and handler's current levels, sets both to the requested level, calls _force_enable_logging to lift any logging.disable cap, yields, and in a finally block restores the logger level, handler level, and the original logging.disable level — so restoration occurs even if the body raises.

calls: [LogCaptureFixture._force_enable_logging](r9-logging-capture-fixtures.md#u-ba9d59de879d)

<a id="u-1f4d2b03fb76"></a>
### `LogCaptureFixture.filtering`

`def filtering(self, filter_: logging.Filter) -> Generator[None]:` · [src/_pytest/logging.py:L578-L592][f1]

Context manager that attaches a logging.Filter to the caplog handler for the duration of the with block.

It adds the filter, yields, and removes it in a finally block, so the handler is always restored even if the body raises. Adding the same filter object twice would duplicate it in the handler's filter list.

<a id="u-585ee5918975"></a>
### `LogCaptureFixture.set_level`

`def set_level(self, level: int | str, logger: str | None = None) -> None:` · [src/_pytest/logging.py:L529-L552][f1]

Sets a logger's level (root when logger is None) for the remainder of the test, also raising the handler's level.

It records the first-seen original level of the target logger in _initial_logger_levels (so repeat calls do not overwrite it), sets logger_obj.setLevel(level), and saves the handler's current level once (_initial_handler_level) before applying the new level to the handler. It then calls _force_enable_logging to lift any logging.disable cap and stores the returned disabled level only on the first call. Restoration happens later in _finalize.

calls: [LogCaptureFixture._force_enable_logging](r9-logging-capture-fixtures.md#u-ba9d59de879d); contract: [LogCaptureFixture](r9-logging-capture-fixtures.md#u-7c2a746b7051)

<a id="u-83fec58eea9a"></a>
### `LogCaptureHandler`

`class LogCaptureHandler(logging_StreamHandler):` · [src/_pytest/logging.py:L373-L376][f1]

A StreamHandler over an in-memory StringIO that also keeps a list of captured records.

emit appends the record before the superclass emit formats it into the stream. reset replaces both the records list and the stream with fresh objects, while clear empties the existing records list in place and swaps in a new StringIO. handleError re-raises the in-flight exception when logging.raiseExceptions is true (making bad log messages fail the test) and otherwise follows the default silent path.

**Notes.**

- side_effect: reset() discards object identity of both records and stream; code holding earlier references keeps seeing stale data.

<a id="u-aa1f02003ef5"></a>
### `catching_logs`

`class catching_logs(Generic[_HandlerType]):` · [src/_pytest/logging.py:L342-L347][f1]

A hand-written (non-contextmanager, for performance) context manager that temporarily installs a logging handler on the root logger.

__enter__ optionally sets the handler's level, adds it to the root logger, and if a level was given lowers the root level to min(original, level) while saving the original in orig_level; it returns the handler. __exit__ restores the root level (only when a level was given, reading self.orig_level) and removes the handler; exceptions propagate unchanged since it returns None.

**Notes.**

- failure: If __exit__ runs without a prior __enter__ having set orig_level while self.level is not None, restoring raises AttributeError; the two must be paired.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/logging.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/deprecated.py
