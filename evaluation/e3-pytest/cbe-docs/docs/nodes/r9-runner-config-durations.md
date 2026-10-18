# Runner Options and Status Defaults

**Capability.** Registers --durations/--durations-min, implements the durations terminal summary, and supplies the default setup/teardown teststatus categories.

Use this for the --durations reporting contract and for the base pytest_report_teststatus implementation that the terminal reporter later overrides as trylast.

**Depended on by.**

- [Runtest Protocol](r9-runner-protocol.md) · model-inferred · 0 edge(s)
- [Reporter Lifecycle and Collection Output](r9-terminal-reporter-core.md) · model-inferred · 0 edge(s)

Parent: [Test Runner](r9-test-runner.md)

## Units (3)

<a id="u-918d8a594ec4"></a>
### `src/_pytest/runner.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/runner.py:L50-L68][f1]

Registers the --durations (int) and --durations-min (float) options in a 'terminal reporting' group placed after 'general'; both default to None.

--durations-min's help notes the effective default is 0.005, or 0.0 with -vv.

calls: [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

<a id="u-b2af4d5a6f1e"></a>
### `src/_pytest/runner.py:pytest_terminal_summary`

`def pytest_terminal_summary(terminalreporter: TerminalReporter) -> None:` · [src/_pytest/runner.py:L71-L103][f1]

Implements the --durations report of the slowest setup/test phases.

Returns early if --durations is unset; durations_min defaults to 0.005, or 0.0 at verbosity >= 2. Collects all reports having a `duration` from the terminal reporter's stats; returns early if none. Sorts descending by duration, prints a 'slowest durations' (or 'slowest N durations' with dlist truncated to N) separator, then writes one line per report. On the first report below durations_min it writes a message about hidden durations — appending 'Use -vv to show these durations' only when durations_min was not given explicitly — and stops.

calls: [TerminalReporter.write_line](r9-terminal-progress.md#u-52343aa4eaa7), [TerminalReporter](r9-terminal-reporter-core.md#u-8d4b8f445ae8)

<a id="u-20814e5190cb"></a>
### `src/_pytest/runner.py:pytest_report_teststatus`

`def pytest_report_teststatus(report: BaseReport) -> tuple[str, str, str] | None:` · [src/_pytest/runner.py:L214-L223][f1]

Default teststatus hook for setup and teardown phases: a failed report maps to category 'error'/'E'/'ERROR', a skipped one to 'skipped'/'s'/'SKIPPED', anything else to empty strings.

For other phases (e.g. call) it returns None, deferring to other hook implementations.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/runner.py
