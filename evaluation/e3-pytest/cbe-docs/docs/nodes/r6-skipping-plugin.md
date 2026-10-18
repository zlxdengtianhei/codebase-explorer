# Skip and Xfail Semantics

**Capability.** Evaluates skip/skipif and xfail marks per item and enforces the result across run phases: setup raises skips, call detects xfail outcomes, makereport rewrites reports, and the terminal status hook maps xfail outcomes.

Use it to understand when a test becomes skipped, xfailed or xpassed and how --runxfail and xfail_strict alter that. evaluate_condition is the shared evaluator for both mark families.

**Depends on.**

- [Built-in Plugins and CLI Facets](r6-builtin-plugins.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r6-skipping-plugin ` → ` r6-builtin-plugins `)

Parent: [Built-in Plugins and CLI Facets](r6-builtin-plugins.md)

## Units (10)

<a id="u-f4989abd77e6"></a>
### `Skip`

`class Skip:` · [src/_pytest/skipping.py:L161-L165][f1]

Frozen dataclass produced by evaluate_skip_marks, holding only the skip reason, defaulting to 'unconditional skip'.

<a id="u-39d48b766908"></a>
### `evaluate_condition`

`def evaluate_condition(item: Item, mark: Mark, condition: object) -> tuple[bool, str]:` · [src/_pytest/skipping.py:L88-L158][f1]

Evaluates one skipif/xfail condition, returning (result, reason).

String conditions are compiled and eval'd in a namespace containing os, sys, platform, item.config, then updated with each dict returned by the pytest_markeval_namespace hooks (a non-Mapping result raises ValueError) and, if the item has .obj, the test function's module globals. Syntax errors and any other evaluation exception are converted by fail(...) into a formatted, pytrace=False error (so fail aborts rather than returns; the returned lines are unreachable as values). Non-string conditions are bool()'d, with conversion errors likewise formatted via fail. The reason comes from mark.kwargs['reason']; if absent, string conditions use 'condition: ' + the source, while boolean conditions without a reason trigger fail('you need to specify reason=STRING ...').

uses: [evaluate_skip_marks](r6-skipping-plugin.md#u-512fcf7e9d9f)

**Uncertainties.**

- fail() raising (from _pytest.outcomes) is assumed, since this function's type says it returns a tuple on every path; its behavior lives outside this file.

<a id="u-512fcf7e9d9f"></a>
### `evaluate_skip_marks`

`def evaluate_skip_marks(item: Item) -> Skip | None:` · [src/_pytest/skipping.py:L168-L193][f1]

Returns a Skip if the item's skip/skipif marks trigger, else None.

For each skipif mark (in marker order), the conditions are mark.args unless a 'condition' keyword is present, in which case the single keyword value is used; empty conditions mean an unconditional skip with the mark's reason (default ''). Otherwise each condition is evaluated in order via evaluate_condition and the first true one returns Skip(reason). Then each plain skip mark is applied as Skip(*mark.args, **mark.kwargs); if those arguments do not fit the dataclass, the TypeError is re-raised with the hint ' - maybe you meant pytest.mark.skipif?'.

calls: [evaluate_condition](r6-skipping-plugin.md#u-39d48b766908); uses: [Skip](r6-skipping-plugin.md#u-f4989abd77e6)

<a id="u-958c472ad91f"></a>
### `evaluate_xfail_marks`

`def evaluate_xfail_marks(item: Item) -> Xfail | None:` · [src/_pytest/skipping.py:L213-L235][f1]

Returns an Xfail if any xfail mark triggers, else None.

Per mark, run (default True), strict (default from the xfail_strict ini option) and raises (default None) are read from mark kwargs; conditions follow the same convention as skipif (mark.args, or the single 'condition' keyword). Empty conditions mean unconditional xfail with the mark's reason (default ''); otherwise the first true condition (via evaluate_condition) yields Xfail(reason, run, strict, raises). Unlike skip, argument errors in constructing Xfail are not handled here.

calls: [evaluate_condition](r6-skipping-plugin.md#u-39d48b766908); uses: [evaluate_xfail_marks](r6-skipping-plugin.md#u-958c472ad91f)

<a id="u-b3e25f60a8a9"></a>
### `src/_pytest/skipping.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/skipping.py:L30-L46][f1]

Registers the --runxfail flag (store_true, default False, to report xfail tests as if unmarked) in the general group, and the xfail_strict ini option (bool, default False) that supplies the default strict parameter for xfail markers lacking an explicit one.

uses: [evaluate_xfail_marks](r6-skipping-plugin.md#u-958c472ad91f)

<a id="u-5e45ec24acd5"></a>
### `src/_pytest/skipping.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/skipping.py:L49-L57][f1]

Plugin configuration.

When --runxfail is active it monkeypatches pytest.xfail with a no-op nop function that still carries xfail.Exception as its Exception attribute, registering a config cleanup restoring the original; this makes xfail calls inside tests inert while keeping xfail-raised exceptions recognizable. Unconditionally it registers help text for the skip, skipif, and xfail markers via config.addinivalue_line. The nested nop does nothing and never raises.

uses: [src/_pytest/skipping.py:pytest_runtest_makereport](r6-skipping-plugin.md#u-c552d64de83b)

**Uncertainties.**

- Exact interaction of the nop with xfail() invoked during a test (the caller still calls xfail, which now returns None instead of raising) is implied but the raise path of the real xfail is outside this file.

<a id="u-9adca54b78fa"></a>
### `src/_pytest/skipping.py:pytest_report_teststatus`

`def pytest_report_teststatus(report: BaseReport) -> tuple[str, str, str] | None:` · [src/_pytest/skipping.py:L310-L316][f1]

Maps xfail reports to terminal status: a report carrying wasxfail yields ('xfailed', 'x', 'XFAIL') when skipped or ('xpassed', 'X', 'XPASS') when passed; any other report returns None so the normal status logic applies.

<a id="u-6f9149777dca"></a>
### `src/_pytest/skipping.py:pytest_runtest_call`

`def pytest_runtest_call(item: Item) -> Generator[None]:` · [src/_pytest/skipping.py:L253-L268][f1]

Wrapper hook around the test call.

It reuses the xfail evaluation stashed at setup, recomputing it (and storing the result) if absent — this covers marks added dynamically between phases — and raises xfail('[NOTRUN] ' + reason) when the mark is active, --runxfail is off, and run=False. The test body then runs via yield; the finally block re-checks the stash once more and refreshes the stored evaluation if it was cleared during the run, so the report phase sees current state even if the test mutated it.

calls: [evaluate_xfail_marks](r6-skipping-plugin.md#u-958c472ad91f)

**Uncertainties.**

- Whether a test can meaningfully clear xfailed_key to trigger the final re-evaluation is not shown here; the code re-evaluates only when the stash value is None.

<a id="u-c552d64de83b"></a>
### `src/_pytest/skipping.py:pytest_runtest_makereport`

`def pytest_runtest_makereport( item: Item, call: CallInfo[None] ) -> Generator[None, …` · [src/_pytest/skipping.py:L271-L307][f1]

Report-phase wrapper: receives the TestReport from yield and rewrites it per xfail state.

With --runxfail it returns the report untouched. If the call raised xfail.Exception, the report is marked skipped with rep.wasxfail set to the exception's message. Otherwise, when the report is not already skipped and an xfail is stashed: a raised exception is an expected failure — outcome 'skipped' with wasxfail set to the xfail reason — when raises is None, or the exception matches (isinstance against a type/tuple, or AbstractRaises.matches); any other exception leaves outcome 'failed'. If no exception occurred and the phase is 'call', a passing test becomes 'failed' with longrepr '[XPASS(strict)] ' + reason when strict, else 'passed' with wasxfail recording the xpass. The (possibly modified) report is returned.

uses: [evaluate_xfail_marks](r6-skipping-plugin.md#u-958c472ad91f)

**Uncertainties.**

- How rep.skipped/passed/wasxfail attributes are computed lives in _pytest.reports, outside this file.

<a id="u-7120fcba6fe5"></a>
### `src/_pytest/skipping.py:pytest_runtest_setup`

`def pytest_runtest_setup(item: Item) -> None:` · [src/_pytest/skipping.py:L242-L250][f1]

Setup-phase hook (tryfirst): raises skip.Exception with the evaluated reason if a skip/skipif mark triggers (attributed to the item's location via _use_item_location=True); otherwise stores the xfail evaluation in the item stash under xfailed_key for later phases and calls xfail('[NOTRUN] ' + reason) when the mark is active, --runxfail is off, and run=False — aborting the test as a not-run xfail.

calls: [evaluate_skip_marks](r6-skipping-plugin.md#u-512fcf7e9d9f), [evaluate_xfail_marks](r6-skipping-plugin.md#u-958c472ad91f)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/skipping.py
