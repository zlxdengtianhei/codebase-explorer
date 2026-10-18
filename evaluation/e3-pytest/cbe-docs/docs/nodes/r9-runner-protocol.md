# Runtest Protocol

**Capability.** The per-item hook chain: pytest_runtest_protocol delegates to runtestprotocol, which runs setup/call/teardown via call_and_report, maintains PYTEST_CURRENT_TEST, and decides interactive-exception handling.

Read this to follow phase-by-phase execution of a single item and where reports originate. check_interactive_exception and show_test_item support the protocol; durations reporting and default teststatus are separate config capabilities.

**Depends on.**

- [CallInfo and Collection](r9-runner-callinfo-collect.md) · graph-confirmed · 1 edge(s)
- [Runner Options and Status Defaults](r9-runner-config-durations.md) · model-inferred · 0 edge(s)
- [Session SetupState](r9-runner-setupstate.md) · model-inferred · 0 edge(s)
- [Reporter Lifecycle and Collection Output](r9-terminal-reporter-core.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [CallInfo and Collection](r9-runner-callinfo-collect.md) · graph-confirmed · 1 edge(s)
- [Outcome, Exit and Skip Tests](r9-tests-runner-outcome-skip.md) · model-inferred · 0 edge(s)
- [Runtest Protocol Functional Tests](r9-tests-runner-protocol.md) · model-inferred · 0 edge(s)
- [Report and CallInfo Tests](r9-tests-runner-reports.md) · model-inferred · 0 edge(s)

Parent: [Test Runner](r9-test-runner.md)

## Units (10)

<a id="u-f0c22eb857e2"></a>
### `src/_pytest/runner.py:pytest_runtest_protocol`

`def pytest_runtest_protocol(item: Item, nextitem: Item | None) -> bool:` · [src/_pytest/runner.py:L114-L119][f1]

Runs the full runtest protocol for one item: emits logstart, delegates to runtestprotocol, emits logfinish, and returns True.

calls: [runtestprotocol](r9-runner-protocol.md#u-375c8a992da0)

<a id="u-375c8a992da0"></a>
### `runtestprotocol`

`def runtestprotocol( item: Item, log: bool = True, nextitem: Item | None = None ) -> …` · [src/_pytest/runner.py:L122-L147][f1]

Executes setup/call/teardown for one item and returns the list of reports.

If the item was re-run without an active request (as pytest-rerunfailures does), _initrequest is re-invoked. Reports the setup phase; only when setup passed, show_test_item is called under --setupshow and the call phase is reported (skipped under --setuponly). When session.shouldfail or shouldstop is set, nextitem is forced to None so teardown of the whole stack happens for correct fixture-teardown error reporting; teardown is always reported. Afterwards item._request is reset to False and funcargs to None.

calls: [call_and_report](r9-runner-protocol.md#u-4fa5f34e240c)

<a id="u-4fa5f34e240c"></a>
### `call_and_report`

`def call_and_report( item: Item, when: Literal["setup", "call", "teardown"], log: boo…` · [src/_pytest/runner.py:L230-L253][f1]

Runs one runtest phase and reports it.

Selects the item hook for 'setup', 'call' or 'teardown' (any other value asserts). Reraise always includes Exit, and additionally KeyboardInterrupt unless --usepdb is active (so pdb gets to handle it); the hook is executed inside CallInfo.from_call. The resulting CallInfo goes through pytest_runtest_makereport; with log=True the report is logged; when check_interactive_exception is true, pytest_exception_interact fires. Returns the TestReport.

calls: [CallInfo.from_call](r9-runner-callinfo-collect.md#u-05cf9e60ee5c), [check_interactive_exception](r9-runner-protocol.md#u-7ffbad734e38)

<a id="u-7ffbad734e38"></a>
### `check_interactive_exception`

`def check_interactive_exception(call: CallInfo[object], report: BaseReport) -> bool:` · [src/_pytest/runner.py:L256-L268][f1]

Decides whether a call's exception deserves interactive handling: False when nothing was raised, when the report carries 'wasxfail' (expected failure/skip), or when the exception is Skipped or BdbQuit (control-flow); True otherwise.

<a id="u-07ffadcf7f8e"></a>
### `src/_pytest/runner.py:pytest_runtest_setup`

`def pytest_runtest_setup(item: Item) -> None:` · [src/_pytest/runner.py:L162-L164][f1]

Setup-phase hook: updates PYTEST_CURRENT_TEST to the setup stage, then sets up collectors along the item's chain via the session's SetupState.

calls: [_update_current_test_var](r9-runner-protocol.md#u-72231f120987), [SetupState.setup](r9-runner-setupstate.md#u-3f7d68549fa9)

<a id="u-a54afbd0793b"></a>
### `src/_pytest/runner.py:pytest_runtest_call`

`def pytest_runtest_call(item: Item) -> None:` · [src/_pytest/runner.py:L167-L188][f1]

Call-phase hook: updates PYTEST_CURRENT_TEST, clears sys.last_type/last_value/last_traceback (and last_exc on 3.12+, tolerating missing attributes), then runs item.runtest().

If the call raises an Exception, the exception's info is stored into sys.last_* for postmortem debugging — the traceback stored skips this frame via tb_next — and the exception is re-raised.

calls: [Item](r7-item-collector-types.md#u-8388b852e250)

**Uncertainties.**

- BaseExceptions raised in the call do not populate sys.last_*; only the `except Exception` branch does.

<a id="u-bd309469ab2f"></a>
### `src/_pytest/runner.py:pytest_runtest_teardown`

`def pytest_runtest_teardown(item: Item, nextitem: Item | None) -> None:` · [src/_pytest/runner.py:L191-L194][f1]

Teardown-phase hook: updates PYTEST_CURRENT_TEST to 'teardown', tears down the setup stack up to nextitem, then removes PYTEST_CURRENT_TEST by passing None.

calls: [SetupState.teardown_exact](r9-runner-setupstate.md#u-904baaf84443)

<a id="u-ba5b20997112"></a>
### `src/_pytest/runner.py:pytest_runtest_makereport`

`def pytest_runtest_makereport(item: Item, call: CallInfo[None]) -> TestReport:` · [src/_pytest/runner.py:L367-L368][f1]

Default makereport hook: builds the TestReport for an item's call via TestReport.from_item_and_call.

calls: [TestReport.from_item_and_call](r3-report-model.md#u-d1f941732e5b)

<a id="u-72231f120987"></a>
### `_update_current_test_var`

`def _update_current_test_var( item: Item, when: Literal["setup", "call", "teardown"] …` · [src/_pytest/runner.py:L197-L211][f1]

Maintains PYTEST_CURRENT_TEST.

With a `when`, sets the variable to '<nodeid> (<when>)', replacing NUL bytes with '(null)' since environment values cannot contain them; with when=None, pops the variable from the environment.

<a id="u-1f90386c5d37"></a>
### `show_test_item`

`def show_test_item(item: Item) -> None:` · [src/_pytest/runner.py:L150-L159][f1]

Prints the test item's nodeid and used fixtures to the terminal writer (under --setupshow): blank line, indented nodeid, and a sorted '(fixtures used: ...)' suffix when the item has fixturenames.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/runner.py
