# Warning Capture Hooks

**Capability.** Scopes warnings.catch_warnings around config, collection, and test execution via five wrapper hooks, applying filters and rendering captured warnings to text for the summary.

Use this subtree to see when warnings are captured and how they become report text. catch_warnings_for_item is the core context manager; the hooks wrap the respective phases with the right item/phase labeling.

**Depends on.**

- [Warning Categories](r3-warning-types.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Thread & Unraisable Exception Warning Tests](r3-exception-warning-tests.md) · model-inferred · 0 edge(s)
- [Warning Assertion Helpers](r3-recwarn.md) · model-inferred · 0 edge(s)

Parent: [Warning Handling](r3-warnings.md)

## Units (4)

<a id="u-66b23e3edaa5"></a>
### `warnings.py:hook-wrappers`

`def pytest_runtest_protocol(item: Item) -> Generator[None, object, object]:` · [src/_pytest/warnings.py:L85-L90][f1]

Four wrapper hooks (pytest_runtest_protocol tryfirst, pytest_collection, pytest_terminal_summary, pytest_sessionfinish, and pytest_load_initial_conftests) all follow one pattern: they wrap the wrapped hook chain in catch_warnings_for_item with the item and phase where applicable — item and 'runtest' for the protocol hook, item None with 'collect' for collection, and item None with 'config' for the summary, session-finish, and initial-conftest phases — yielding through so the inner hooks run inside the capture and returning their result.

calls: [catch_warnings_for_item](r3-warning-capture.md#u-7aa1b1ba277d)

<a id="u-7aa1b1ba277d"></a>
### `catch_warnings_for_item`

`def catch_warnings_for_item( config: Config, ihook, when: Literal["config", "collect"…` · [src/_pytest/warnings.py:L21-L71][f1]

Context manager scoping warning capture around config, collection or test execution.

Inside warnings.catch_warnings(record=record) it applies, in order: default 'always' filters for DeprecationWarning and PendingDeprecationWarning but only when the user passed no -W options (sys.warnoptions empty); the config's filterwarnings ini values and -W command-line filters via apply_warning_filters; and finally the item's filterwarnings marks (nodeid '' when item is None), each parsed by parse_warning_filter without escaping. After the wrapped block's yield — including when it raises — each captured WarningMessage, if recording, is replayed through ``ihook.pytest_warning_recorded.call_historic`` with the nodeid, the phase label ``when``, and location None.

**Notes.**

- contract: record=False skips hook replay entirely; pytest_configure uses this because the terminal reporter is done by then.

uses: [__init__.py module code (L1–L90)][f2], [Node.iter_markers](r7-node-base-lifecycle.md#u-f7ae472266a7)

<a id="u-743f793e524e"></a>
### `src/_pytest/warnings.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/warnings.py:L132-L152][f1]

Register the filterwarnings marker and keep a warning-capture context alive for config cleanup.

Inside an ExitStack it enters catch_warnings_for_item with record=False — recording is disabled because the terminal reporter has already finished by cleanup time, so this context is only useful for 'error' action filters — adds the filterwarnings marker documentation via addinivalue_line, and then registers ``stack.pop_all().close`` as a config cleanup so the capture context (and thus the non-default filters set inside it) remains active until session teardown, when it is closed and the original warning state restored.

uses: [catch_warnings_for_item](r3-warning-capture.md#u-7aa1b1ba277d)

<a id="u-ab9140c55f9e"></a>
### `warning_record_to_str`

`def warning_record_to_str(warning_message: warnings.WarningMessage) -> str:` · [src/_pytest/warnings.py:L74-L82][f1]

Render a captured warnings.WarningMessage as terminal text: warnings.formatwarning with the message string, category, filename, line number and line, followed by the tracemalloc allocation note for the message's ``source`` (empty string when none).

calls: [tracemalloc_message](r1-leaked-exception-reporting.md#u-e0457a417bb6)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/warnings.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
