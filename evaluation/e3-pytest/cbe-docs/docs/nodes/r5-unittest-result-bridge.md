# unittest result-to-report translation

**Capability.** Translates unittest result callbacks into pytest reporting: add* callbacks queue ExceptionInfos via _addexcinfo, and a tryfirst pytest_runtest_makereport pops the queued excinfo into the call phase so the runner reports unittest failures/skips correctly.

Consult this to understand how an addFailure/addSkip inside unittest surfaces as the right pytest outcome.

**Depends on.**

- [Twisted trial workarounds](r5-unittest-twisted-workarounds.md) · graph-confirmed · 1 edge(s)

Parent: [unittest integration bridge](r5-unittest-bridge.md)

## Units (7)

<a id="u-d684f59e0671"></a>
### `TestCaseFunction._addexcinfo`

`def _addexcinfo(self, rawexcinfo: _SysExcInfoType) -> None:` · [src/_pytest/unittest.py:L233-L265][f1]

Converts a raw unittest exc-info tuple into a pytest ExceptionInfo and appends it to the item's _excinfo list (created via __dict__.setdefault).

First normalizes Twisted Failure inputs via _handle_twisted_exc_info. Builds ExceptionInfo.from_exc_info and touches .value and .traceback to force traceback storage (noted as problematic under trial). On TypeError from that conversion — an incompatible exception representation — it falls back: formatting the exception natively and calling fail() with a 'NOTE: Incompatible Exception Representation' prefix; if that fail() call itself raises something other than fail.Exception or KeyboardInterrupt, a second fallback calls fail() with an 'ERROR: Unknown Incompatible Exception representation' message. Either way the raised fail.Exception is caught and replaced by the current exception's excinfo; KeyboardInterrupt is always re-raised.

**Notes.**

- failure: All TypeError-based fallbacks funnel into fail.Exception which is converted to excinfo from the current exception context; KeyboardInterrupt propagates at both levels.

**Uncertainties.**

- Whether from_exc_info can raise TypeError for reasons other than tuple shape (e.g. custom exception objects) is not established.

<a id="u-1e0744747a89"></a>
### `TestCaseFunction.addError`

`def addError( self, testcase: unittest.TestCase, rawexcinfo: _SysExcInfoType ) -> None:` · [src/_pytest/unittest.py:L267-L275][f1]

unittest error callback.

If the raw exc-info's second element is an exit.Exception (accessed inside a try that swallows TypeError from malformed tuples), calls exit() with its msg, terminating the run — so pytest.exit inside a unittest test still exits pytest. Otherwise records the error via _addexcinfo.

<a id="u-1fb841a5d44d"></a>
### `TestCaseFunction.addFailure`

`def addFailure( self, testcase: unittest.TestCase, rawexcinfo: _SysExcInfoType ) -> N…` · [src/_pytest/unittest.py:L277-L280][f1]

unittest failure callback; records the failure by delegating to _addexcinfo.

<a id="u-cb0f33d01a63"></a>
### `TestCaseFunction.addSkip`

`def addSkip(self, testcase: unittest.TestCase, reason: str) -> None:` · [src/_pytest/unittest.py:L282-L286][f1]

Implements skipping: raises pytest.skip.Exception with the reason and _use_item_location=True, catches that same skip.Exception, and records the resulting current exc-info via _addexcinfo so the item reports as skipped.

<a id="u-b2b5cb5c4314"></a>
### `TestCaseFunction.addExpectedFailure`

`def addExpectedFailure( self, testcase: unittest.TestCase, rawexcinfo: _SysExcInfoTyp…` · [src/_pytest/unittest.py:L288-L297][f1]

Records an expected failure by calling xfail(str(reason)), catching the xfail.Exception, and storing the current exc-info via _addexcinfo.

<a id="u-25d14ef72a06"></a>
### `TestCaseFunction.addUnexpectedSuccess`

`def addUnexpectedSuccess( self, testcase: unittest.TestCase, reason: twisted.trial.un…` · [src/_pytest/unittest.py:L299-L311][f1]

Preserves unittest behavior by failing the test on unexpected success (explicitly not an XPASS).

Builds 'Unexpected success' plus ': <reason.reason>' when a Twisted Todo reason is supplied, calls fail(msg, pytrace=False), catches the fail.Exception, and stores the exc-info via _addexcinfo.

<a id="u-16381b405e7d"></a>
### `src/_pytest/unittest.py:pytest_runtest_makereport`

`def pytest_runtest_makereport(item: Item, call: CallInfo[None]) -> None:` · [src/_pytest/unittest.py:L367-L375][f1]

tryfirst hookimpl that bridges unittest result callbacks into pytest reporting: for TestCaseFunction items with queued _excinfo, it pops the first excinfo into call.excinfo and deletes call.result (ignoring AttributeError) so the runner reports the unittest-collected failure instead of a successful call.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/unittest.py
