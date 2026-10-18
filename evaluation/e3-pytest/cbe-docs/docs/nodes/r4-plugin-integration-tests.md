# Third-party plugin integration

**Capability.** Small smoke tests verifying that external plugins (pytest-bdd, django, anyio, asyncio, mock, rerunfailures) work against pytest, plus a plugin-free baseline and a minimal Django settings module used as the django plugin target.

Each file is a minimal scenario exercising one plugin's contract; rerunfailures also reuses the excinfo f/g/h raise chain for its unittest-style regression.

**Depends on.**

- [Traceback manipulation tests](r4-excinfo-traceback-model-tests.md) · graph-confirmed · 1 edge(s)

Parent: [Test suites](r4-test-suites.md)

## Units (7)

<a id="u-ec49b96ae3b9"></a>
### `bdd_wallet-py`

`def test_publish():` · [testing/plugins_integration/bdd_wallet.py:L12-L14][f1]

pytest-bdd integration scenario 'Buy fruits' from bdd_wallet.feature, bound by @scenario to test_publish.

A function-scoped wallet fixture returns a fresh Wallet class instance with amount=0. The step functions mutate that instance: the given step sets amount to 50, buying apples subtracts 1 and bananas subtracts 2, and the then step asserts amount == 47. Because each scenario gets a fresh wallet, the arithmetic only holds when all three steps run in order; the assertion fails on any other state.

**Notes.**

- contract: Step bindings match the .feature file by their given/when/then strings; the feature file itself is not in this source.

**Uncertainties.**

- bdd_wallet.feature is external to this file, so step coverage of the scenario cannot be verified.

<a id="u-9dd87adae98f"></a>
### `django_settings-py`

`group` · [testing/plugins_integration/django_settings.py:L1-L4][f2]

Minimal Django settings module exposing only SECRET_KEY = "mysecret"; serves as the settings target for the django plugin integration and has no executable behavior.

<a id="u-4f63324d1202"></a>
### `pytest_anyio_integration-py`

`async def test_sleep():` · [testing/plugins_integration/pytest_anyio_integration.py:L9-L11][f3]

AnyIO backend-agnostic async test: test_sleep is marked @pytest.mark.anyio and awaits anyio.sleep(0), verifying the anyio plugin runs coroutine tests under its parametrized backends.

**Uncertainties.**

- Backend selection for the anyio marker is provided by the anyio plugin, not this file.

<a id="u-ec1381ebadc7"></a>
### `pytest_asyncio_integration-py`

`async def test_sleep():` · [testing/plugins_integration/pytest_asyncio_integration.py:L9-L11][f4]

Asyncio plugin integration test: test_sleep is marked @pytest.mark.asyncio and awaits asyncio.sleep(0), verifying the pytest-asyncio plugin executes coroutine tests.

<a id="u-89d44342e928"></a>
### `pytest_mock_integration-py`

`def test_mocker(mocker):` · [testing/plugins_integration/pytest_mock_integration.py:L5-L6][f5]

pytest-mock integration: test_mocker receives the mocker fixture from the plugin and constructs a MagicMock through it, verifying the plugin injects a working mocker.

<a id="u-b3f843969991"></a>
### `pytest_rerunfailures_integration-py`

`class MyTestCase(unittest.TestCase):` · [testing/plugins_integration/pytest_rerunfailures_integration.py:L6-L9][f6]

unittest-style regression for issue #12424 with pytest-rerunfailures.

MyTestCase holds a class attribute first_time=True; test_fail_the_first_time checks it, and on the first run flips type(self).first_time to False and calls self.fail(), so the first execution fails and any rerun passes. The mutation is on the class, so it persists across reruns and other instances of this test class in the same session.

**Notes.**

- side_effect: Class attribute first_time is mutated on the type, not the instance.
- failure: Deliberately fails on first execution via self.fail().

**Uncertainties.**

- Whether a rerun actually occurs depends on the rerunfailures plugin configuration outside this file.

<a id="u-21ca05fad43d"></a>
### `simple_integration-py`

`def test_foo():` · [testing/plugins_integration/simple_integration.py:L7-L8][f7]

Baseline integration file with no plugins beyond parametrize: test_foo asserts True; test_bar is parametrized over range(3), producing three trivially passing cases i=0..2.

It serves as a control for plugin-integration runs.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/bdd_wallet.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/django_settings.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/pytest_anyio_integration.py
[f4]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/pytest_asyncio_integration.py
[f5]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/pytest_mock_integration.py
[f6]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/pytest_rerunfailures_integration.py
[f7]: ../../../../../../eval/pytest-5989efe/testing/plugins_integration/simple_integration.py
