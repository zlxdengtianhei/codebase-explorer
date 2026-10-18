# Terminal Options and Status Hook

**Capability.** CLI/ini option registration for terminal reporting (including -q countdown semantics), the effective -r reportchars, and the trylast default teststatus hook driving progress output.

Use this to see which options shape output verbosity and summary categories. pytest_report_teststatus here runs after the runner's default implementation.

**Depended on by.**

- [Per-Test Progress Output](r9-terminal-progress.md) · model-inferred · 0 edge(s)
- [Summary Sections](r9-terminal-summaries.md) · model-inferred · 0 edge(s)

Parent: [Terminal Reporting](r9-terminal-reporting.md)

## Units (4)

<a id="u-bb387fa2e224"></a>
### `src/_pytest/terminal.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/terminal.py:L134-L284][f1]

Registers the terminal-reporting CLI options and ini settings.

-v/--verbose is a counting action on dest verbose; -q/--quiet uses MoreQuietAction on the same dest. Boolean options: --no-header, --no-summary, --no-fold-skipped (store_false into fold_skipped, default True), --force-short-summary, --disable-warnings, --showlocals/-l with --no-showlocals negation, --xfail-tb, --fulltrace. Value options: --verbosity (int), -r reportchars (default 'fE'), --tb style with fixed choices, --showcapture, --color, --code-highlight. It also adds the console_output_style ini (default 'progress') and the VERBOSITY_TEST_CASES verbosity ini. Lower-case short options go through the private group._addoption to bypass argparse restrictions; this is pure registration with no branching.

uses: [MoreQuietAction](r9-terminal-config.md#u-5273f21a2a0b)

<a id="u-5273f21a2a0b"></a>
### `MoreQuietAction`

`class MoreQuietAction(argparse.Action):` · [src/_pytest/terminal.py:L77-L84][f1]

argparse action implementing -q/--quiet as a countdown that also updates the legacy quiet attribute to unify verbosity handling.

__init__ delegates to argparse.Action forcing nargs=0. __call__ decrements the dest value (defaulting to 0 when absent) and increments namespace.quiet by one, so each occurrence on the command line lowers verbosity while keeping the deprecated quiet flag in sync.

<a id="u-19e5bdd30a79"></a>
### `getreportopt`

`def getreportopt(config: Config) -> str:` · [src/_pytest/terminal.py:L299-L321][f1]

Converts the raw -r reportchars option into the effective summary-category char set.

Per character: legacy aliases 'F'/'S' are lowercased; 'a' replaces the accumulated string with 'sxXEf'; 'A' with 'PpsxXEf'; 'N' empties it; any other char is appended once if absent, so a later a/A/N occurrence overrides earlier chars. Afterwards warnings handling: without --disable-warnings, 'w' is prepended if not already present; with --disable-warnings, any 'w' is removed. Returns the string.

<a id="u-5f583ee897f4"></a>
### `src/_pytest/terminal.py:pytest_report_teststatus`

`def pytest_report_teststatus(report: BaseReport) -> tuple[str, str, str]:` · [src/_pytest/terminal.py:L324-L337][f1]

trylast hook (ordered after _pytest.runner) supplying the default (category, letter, word) triple driving progress output.

Letter is '.' if report.passed, 's' if report.skipped, else 'F'. When report.when is 'collect', 'setup' or 'teardown' and outcome is 'failed', the returned category becomes 'error' and the letter 'E'. The word defaults to the upper-cased outcome.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/terminal.py
