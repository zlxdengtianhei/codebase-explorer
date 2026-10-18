# Outcome, Exit and Skip Tests

**Capability.** Behavior of control-flow exceptions (OutcomeException, pytest.exit/pytest.fail), pytest.skip and importorskip semantics including minversion, custom reasons, dev versions and exc_type warning behavior, plus PYTEST_CURRENT_TEST/PYTEST_VERSION env-var contracts and collection exit statuses.

Read this for the exact message shortening ('Skipped:'/'Failed:'), exit codes and banner output, and env-var setup/restore guarantees. The dynamic-source failure tests also live here since they guard report generation.

**Depends on.**

- [Runtest Protocol](r9-runner-protocol.md) · model-inferred · 0 edge(s)

Parent: [Runner Test Suite](r9-tests-runner.md)

## Units (29)

<a id="u-5d01c1ab384a"></a>
### `test_outcomeexception_exceptionattributes`

`def test_outcomeexception_exceptionattributes() -> None:` · [testing/test_runner.py:L602-L604][f1]

OutcomeException('test') stores its message so args[0] equals the msg attribute.

<a id="u-f343daeeb7a6"></a>
### `test_outcomeexception_passes_except_Exception`

`def test_outcomeexception_passes_except_Exception() -> None:` · [testing/test_runner.py:L607-L612][f1]

Raising OutcomeException inside try with `except Exception` re-raising NotImplementedError must let OutcomeException escape (it does not derive from Exception in a way the handler catches), so pytest.raises sees OutcomeException, not NotImplementedError.

<a id="u-8ffab5799b52"></a>
### `test-runner-test_outcome_exception_bad_msg`

`def test_outcome_exception_bad_msg() -> None:` · [testing/test_runner.py:L1187-L1190][f1]

OutcomeException validates its input (#5578): constructing it with a function instead of a string raises TypeError with a two-line message stating a string was expected and suggesting a mark may have been intended.

<a id="u-74b83019e176"></a>
### `test_pytest_exit`

`def test_pytest_exit() -> None:` · [testing/test_runner.py:L615-L618][f1]

pytest.exit('hello') raises pytest.exit.Exception and the captured excinfo reports errisinstance of that exception class.

<a id="u-04d56fdd0fd8"></a>
### `test_pytest_exit_msg`

`def test_pytest_exit_msg(pytester: Pytester) -> None:` · [testing/test_runner.py:L628-L638][f1]

A conftest pytest_configure calling pytest.exit('oh noes') makes runpytest emit 'Exit: oh noes' on stderr.

<a id="u-d093b49c9101"></a>
### `test_pytest_exit_returncode`

`def test_pytest_exit_returncode(pytester: Pytester) -> None:` · [testing/test_runner.py:L651-L679][f1]

pytest.exit('some exit msg', 99) in a test prints an exit banner on stdout, leaves stderr empty after _strip_resource_warnings, and sets return code 99.

A second run exits during pytest_sessionstart (code 98): the banner also appears on stdout, but stderr additionally contains the line 'Exit: during_sessionstart' after filtering.

<a id="u-378f7dc0da70"></a>
### `_strip_resource_warnings`

`def _strip_resource_warnings(lines): # Assert no output on stderr, except for unrelia…` · [testing/test_runner.py:L641-L648][f1]

Helper filtering stderr lines: drops lines starting with 'Exception ignored in:' or 'ResourceWarning' so tests can assert stderr emptiness despite unreliable ResourceWarnings (issue 5088).

<a id="u-390a3beb5b02"></a>
### `test_pytest_fail`

`def test_pytest_fail() -> None:` · [testing/test_runner.py:L621-L625][f1]

pytest.fail('hello') raises pytest.fail.Exception whose exconly(tryshort=True) starts with 'Failed', confirming failed-message shortening.

<a id="u-301b1c12c5ad"></a>
### `test_pytest_fail_notrace_collection`

`def test_pytest_fail_notrace_collection(pytester: Pytester) -> None:` · [testing/test_runner.py:L698-L710][f1]

Calling pytest.fail(..., pytrace=False) at module import/collection time prints 'hello' without the traceback source line 'def some_internal_function()'.

<a id="u-02e60bb3cb14"></a>
### `test_pytest_fail_notrace_non_ascii`

`def test_pytest_fail_notrace_non_ascii(pytester: Pytester) -> None:` · [testing/test_runner.py:L713-L728][f1]

pytest.fail with a non-ascii message ('oh oh: ☺', pytrace=False) prints the test name and the message intact on stdout, without the 'def test_hello' source line.

<a id="u-bd90ec0db9c8"></a>
### `test_pytest_fail_notrace_runtest`

`def test_pytest_fail_notrace_runtest(pytester: Pytester) -> None:` · [testing/test_runner.py:L682-L695][f1]

pytest.fail(..., pytrace=False) during a test and its teardown prints only the messages 'world' and 'hello' on stdout with no source lines such as 'def teardown_function'.

<a id="u-4670677c1076"></a>
### `test_exception_printing_skip`

`def test_exception_printing_skip() -> None:` · [testing/test_runner.py:L753-L760][f1]

Catching pytest.skip('hello') and rendering via ExceptionInfo.from_current().exconly(tryshort=True) yields a string starting with 'Skipped', verifying skip-message shortening.

<a id="u-3ab50b842b2d"></a>
### `test-runner-test_importorskip`

`def test_importorskip(monkeypatch) -> None:` · [testing/test_runner.py:L763-L766][f1]

pytest.importorskip semantics: 'sys' resolves to the sys module; a nonexistent module triggers a skip whose report reprcrash.path points at the calling file (test_runner), proving the skip is attributed to the actual caller.

Malformed names ('x y z', 'x=y') raise SyntaxError. A pre-seeded module with __version__ '1.3' skips when minversion='1.3.1' but is returned for minversion='1.3'. A spurious skip escaping the body fails the test with the captured excinfo.

<a id="u-2d6406ee3e45"></a>
### `TestImportOrSkipExcType`

`class TestImportOrSkipExcType:` · [testing/test_runner.py:L801-L804][f1]

Tests for #11523 covering when importorskip warns about a module that exists but raises ImportError on import, depending on the exc_type argument.

<a id="u-8a6d29330fd5"></a>
### `TestImportOrSkipExcType.test_no_warning`

`def test_no_warning(self) -> None: # An attempt on a module which does not exist will…` · [testing/test_runner.py:L804-L813][f1]

Importing a nonexistent module skips without capturing any warning under simplefilter('always').

<a id="u-293ffa62c7f4"></a>
### `TestImportOrSkipExcType.test_import_error_with_warning`

`def test_import_error_with_warning(self, pytester: Pytester) -> None: # Create a modu…` · [testing/test_runner.py:L815-L829][f1]

A module present on sys.path whose import raises ImportError for another reason: importorskip still skips but emits exactly one PytestDeprecationWarning about the future behavior change.

<a id="u-6e56e0a6d35d"></a>
### `TestImportOrSkipExcType.test_import_error_suppress_warning`

`def test_import_error_suppress_warning(self, pytester: Pytester) -> None: # Same as t…` · [testing/test_runner.py:L831-L843][f1]

Same import-failure scenario but with exc_type=ImportError passed to importorskip: the skip occurs and no warning is captured, showing exc_type suppresses the deprecation warning.

<a id="u-a1104c4c6997"></a>
### `TestImportOrSkipExcType.test_warning_integration`

`def test_warning_integration(self, pytester: Pytester) -> None:` · [testing/test_runner.py:L845-L865][f1]

End-to-end: a test using importorskip on a module that raises ImportError reports on stdout the message about the module being found but failing import, the original ImportError text, and the summary '1 skipped, 1 warning'.

<a id="u-01fd98eb3528"></a>
### `test_importorskip_custom_reason`

`def test_importorskip_custom_reason(pytester: Pytester) -> None:` · [testing/test_runner.py:L896-L909][f1]

With reason='just because' given to module-level importorskip and -ra, the custom reason appears in the short summary alongside 'collected 0 items / 1 skipped'.

<a id="u-e19e8e65cc42"></a>
### `test_importorskip_dev_module`

`def test_importorskip_dev_module(monkeypatch) -> None:` · [testing/test_runner.py:L868-L878][f1]

With a fake 'mockmodule' of version '0.13.0.dev-43290', importorskip(minversion='0.12.0') returns the module (dev versions compare correctly); a missing module 'mockmodule1' with minversion='0.14.0' skips.

A spurious skip fails the test.

<a id="u-5532c09939fa"></a>
### `test_importorskip_module_level`

`def test_importorskip_module_level(pytester: Pytester) -> None:` · [testing/test_runner.py:L881-L893][f1]

importorskip at module import level must skip the whole module's collection: runpytest reports 'collected 0 items / 1 skipped'.

<a id="u-ede36b307786"></a>
### `test_importorskip_imports_last_module_part`

`def test_importorskip_imports_last_module_part() -> None:` · [testing/test_runner.py:L796-L798][f1]

pytest.importorskip('os.path') returns the last module part, identical to os.path.

<a id="u-7a8a79caf69a"></a>
### `test-runner-test_makereport_getsource_dynamic_code`

`def test_makereport_getsource_dynamic_code( pytester: Pytester, monkeypatch: MonkeyPa…` · [testing/test_runner.py:L979-L987][f1]

Failure-report source extraction must survive dynamically generated code: inspect.findsource is monkeypatched to raise IndexError for objects named 'foo'.

A fixture named foo requesting a missing fixture makes the run report, without INTERNALERROR, that fixture 'missing' was not found and the test_fix line — showing the IndexErrors from findsource are contained.

<a id="u-df44fc959a76"></a>
### `test_makereport_getsource`

`def test_makereport_getsource(pytester: Pytester) -> None:` · [testing/test_runner.py:L966-L976][f1]

A failure on an `else:` branch (with an unreachable `if False: pass`) must be reported with the 'else: assert False' source line and must not trigger INTERNALERROR.

<a id="u-1890cafd8d3e"></a>
### `test-runner-test_store_except_info_on_error`

`def test_store_except_info_on_error() -> None:` · [testing/test_runner.py:L1012-L1017][f1]

On item failure, pytest_runtest_call stores the exception on sys (last_type IndexError, last_value IndexError with args ('TEST',), last_traceback set, plus last_exc on Python >= 3.12) and clears them on the next successful run, so afterwards none of those attributes exist.

A fake item class with a class-var raise_error toggles failure vs success.

**Uncertainties.**

- runtest is invoked through the runner despite the object not being a real Item, relying on duck typing of the hook implementation.

<a id="u-72f47e643b6e"></a>
### `test_current_test_env_var`

`def test_current_test_env_var(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_runner.py:L1048-L1077][f1]

PYTEST_CURRENT_TEST is set during fixture setup, the test call, and fixture teardown, with values '<nodeid> (setup|call|teardown)' recorded via a shared list injected on sys; after the in-process run it must be removed from os.environ.

**Uncertainties.**

- Injection via monkeypatch.setattr(sys, 'pytest_current_test_vars', ..., raising=False) means the child code reads the list through the same in-process sys module.

<a id="u-bf587f5b0ad9"></a>
### `test_pytest_version_env_var`

`def test_pytest_version_env_var(pytester: Pytester, monkeypatch: MonkeyPatch) -> None:` · [testing/test_runner.py:L1202-L1216][f1]

With PYTEST_VERSION preset to 'old version', an in-process run sees os.environ['PYTEST_VERSION'] equal to pytest.__version__ inside the test (pytest overwrites it) and, after the run, the outer environment is restored to 'old version'.

**Uncertainties.**

- Restoration relies on monkeypatch's in-process teardown interplay with pytest's own env handling.

<a id="u-effb96b5d11a"></a>
### `test_pytest_cmdline_main`

`def test_pytest_cmdline_main(pytester: Pytester) -> None:` · [testing/test_runner.py:L912-L927][f1]

Runs the generated file as a script; its __main__ block calls pytest.cmdline.main([__file__]) in a subprocess, which must exit 0 for the contained passing test.

**Uncertainties.**

- Behavior depends on subprocess execution not visible here.

<a id="u-2a825be70732"></a>
### `test_pytest_no_tests_collected_exit_status`

`def test_pytest_no_tests_collected_exit_status(pytester: Pytester) -> None:` · [testing/test_runner.py:L731-L750][f1]

Exit-status contract for collection: no tests at all gives 'collected 0 items' and NO_TESTS_COLLECTED; one passing test gives OK; one test fully deselected via -k still reports 'collected 1 item' with '1 deselected' and NO_TESTS_COLLECTED.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_runner.py
