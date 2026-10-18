# Third-party plugin integration

**Capability.** Minimal integration tests confirming external async plugins work: pytest-trio runs @pytest.mark.trio coroutine tests on the trio kernel, and pytest-twisted supports two styles of the same deferred-based test.

Use these files as smoke tests for plugin ecosystems that alter test execution; they are intentionally tiny. Failure indicates an incompatibility with the external plugin rather than a core pytest regression. No deeper plugin behavior is asserted.

Parent: [Environment & integration tests](r1-integration-environment-tests.md)

## Units (2)

<a id="u-d374ff9b00e0"></a>
### `pytest_trio_integration-py`

`async def test_sleep():` · [testing/plugins_integration/pytest_trio_integration.py:L9-L11][f1]

Trio plugin integration test: test_sleep is marked @pytest.mark.trio and awaits trio.sleep(0), verifying the pytest-trio plugin runs coroutine tests on the trio kernel.

<a id="u-fc31330091bc"></a>
### `pytest_twisted_integration-py`

`def sleep():` · [testing/plugins_integration/pytest_twisted_integration.py:L8-L11][f2]

pytest-twisted integration with two styles of the same test.

sleep() lazily imports twisted.internet.reactor and returns deferLater(clock=reactor, delay=0), a delayed Deferred. test_inlineCallbacks is wrapped with @pytest_twisted.inlineCallbacks and yields that Deferred; test_inlineCallbacks_async is wrapped with @pytest_twisted.ensureDeferred and awaits it, verifying both plugin entry styles drive Twisted Deferreds to completion.

**Notes.**

- side_effect: Importing twisted.internet.reactor inside sleep() installs the global reactor on first call.

**Uncertainties.**

- Reactor startup/teardown behavior is managed by pytest-twisted and not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/pytest_trio_integration.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/pytest_twisted_integration.py
