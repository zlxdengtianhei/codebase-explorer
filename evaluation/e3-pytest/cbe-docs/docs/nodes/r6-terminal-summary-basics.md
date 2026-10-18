# Summary, Warnings and Misc Reporting

**Capability.** Tests the short-test-summary and warnings-summary sections: reportchars and aliases via addopts, CI-dependent truncation, --force-short-summary, -vv full reprs, collection-error sections, pytest_terminal_summary hook output, and --traceconfig.

Use it for flag-driven presence/absence and truncation of summary lines and the warnings sections emitted around them.

**Depends on.**

- [Patch Engine and Undo Journal](r6-monkeypatch-engine.md) · graph-confirmed · 6 edge(s)

Parent: [Terminal Reporting Suite](r6-test-terminal.md)

## Units (18)

<a id="u-e52fb2527cc5"></a>
### `test_collecterror`

`def test_collecterror(pytester: Pytester) -> None:` · [testing/test_terminal.py:L2740-L2754][f1]

A module raising SyntaxError at import with -ra reports 'collected 0 items / 1 error', an ERRORS section, the SyntaxError line, a short summary ERROR entry, the 'Interrupted: 1 error during collection' banner, and exit '1 error'.

<a id="u-89caeb7bf38b"></a>
### `test_no_summary_collecterror`

`def test_no_summary_collecterror(pytester: Pytester) -> None:` · [testing/test_terminal.py:L2757-L2760][f1]

--no-summary suppresses the ERRORS section even with a collection error.

<a id="u-51297d8b2410"></a>
### `test_fail_extra_reporting`

`def test_fail_extra_reporting( pytester: Pytester, monkeypatch, use_ci: bool, expecte…` · [testing/test_terminal.py:L1223-L1248][f1]

Parametrized over CI env: with CI=true the short summary shows the full 900-char assertion message ('- AssertionError: this_failed' repeated), otherwise it is truncated with 't...'; COLUMNS is fixed to 80.

A -rN run must not show a short summary at all.

<a id="u-56dcbb7165ca"></a>
### `test_fail_reporting_on_pass`

`def test_fail_reporting_on_pass(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1251-L1254][f1]

-rf on an all-passing run shows no short test summary.

<a id="u-d23ab45816bf"></a>
### `test_pass_extra_reporting`

`def test_pass_extra_reporting(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1257-L1262][f1]

Default runs show no summary for passes; adding -rp prints the short summary with a PASS line.

<a id="u-94ebd6092e71"></a>
### `test_pass_reporting_on_fail`

`def test_pass_reporting_on_fail(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1265-L1268][f1]

-rp on a failing run shows no summary (only failures matter by default).

<a id="u-58713d732e8a"></a>
### `test_pass_output_reporting`

`def test_pass_output_reporting(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1271-L1308][f1]

Passing tests' captured output is hidden by default; with -rPp a '= PASSES =' section shows the passing test's captured stdout plus setup and teardown sections, and the short summary lists both passing tests including the one with no output.

<a id="u-0cf363a87888"></a>
### `test_force_short_summary`

`def test_force_short_summary(monkeypatch: MonkeyPatch, pytester: Pytester) -> None:` · [testing/test_terminal.py:L2685-L2699][f1]

--force-short-summary keeps truncation even under -vv: a multiline repeated string asserts as 'a\na\na\na...' in the summary.

<a id="u-64257bd9e3d2"></a>
### `test_short_summary_with_verbose`

`def test_short_summary_with_verbose( monkeypatch: MonkeyPatch, pytester: Pytester ) -…` · [testing/test_terminal.py:L2619-L2653][f1]

With running_on_ci monkeypatched to False: default verbosity truncates a 200+200-char assertion message in the short summary ('assert AAA...'); with -vv the full both-sides message is printed untruncated.

<a id="u-b4ec2a92add4"></a>
### `test_full_sequence_print_with_vv`

`def test_full_sequence_print_with_vv( monkeypatch: MonkeyPatch, pytester: Pytester ) …` · [testing/test_terminal.py:L2656-L2682][f1]

With -vv, entire repr sequences (a 10-element list and dict) appear untruncated in the short summary lines.

<a id="u-cf93be3fa16a"></a>
### `test_fdopen_kept_alive_issue124`

`def test_fdopen_kept_alive_issue124(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1731-L1747][f1]

Xfailed when os.dup is unavailable.

Two tests keep a duplicate stdout file object alive across tests and close it later; both must pass, verifying capfd does not break on held fds.

<a id="u-ee698cfb268d"></a>
### `test_terminal_summary`

`def test_terminal_summary(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1768-L1785][f1]

A conftest pytest_terminal_summary writing a section, a line, and the exitstatus renders 'hello' section, 'world', and 'exitstatus: 5' (NO_TESTS_COLLECTED).

<a id="u-83864873ffe7"></a>
### `test_terminal_summary_warnings_are_displayed`

`def test_terminal_summary_warnings_are_displayed(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1788-L1822][f1]

Warnings raised inside pytest_terminal_summary produce a second '= warnings summary (final) =' section after the short test summary; the test-time warning appears exactly once, the warnings-summary banner appears twice, and no 'None' line leaks.

<a id="u-86135dc31942"></a>
### `test_terminal_summary_warnings_header_once`

`def test_terminal_summary_warnings_header_once(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1825-L1847][f1]

Without a conftest warning, only one warnings-summary section appears (emitted before the short summary); the test warning is shown once and no 'None' line appears.

<a id="u-d63ddcf5ff0a"></a>
### `test_terminal_no_summary_warnings_header_once`

`def test_terminal_no_summary_warnings_header_once(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1850-L1862][f1]

With --no-summary neither the warnings summary nor the short test summary sections appear.

<a id="u-4092d55d75f0"></a>
### `test_terminalreporter_reportopt_addopts`

`def test_terminalreporter_reportopt_addopts(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1459-L1475][f1]

With ini addopts=-rs, the running TerminalReporter obtained in-test has opt 'skipped' enabled and 'qwe' not, proving addopts reportchars are applied to the reporter's option state.

<a id="u-05131b84d465"></a>
### `testing/test_terminal.py:test_traceconfig`

`def test_traceconfig(pytester: Pytester) -> None:` · [testing/test_terminal.py:L1502-L1505][f1]

--traceconfig prints an 'active plugins' section; exit code is NO_TESTS_COLLECTED.

<a id="u-235dbf626968"></a>
### `test_via_exec`

`def test_via_exec(pytester: Pytester) -> None:` · [testing/test_terminal.py:L2763-L2768][f1]

A test defined via exec() shows verbose output with '<- <string>' origin annotation and passes.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_terminal.py
