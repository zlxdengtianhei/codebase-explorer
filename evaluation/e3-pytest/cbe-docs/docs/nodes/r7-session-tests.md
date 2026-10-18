# Session Run Control Tests

**Capability.** testing/test_session.py: item events, collection errors, -x/--maxfail stopping, deselection/ignoring, execution ordering, broken reprs in reports, sticky shouldfail/shouldstop, rootdir options, and cwd restoration around sessionfinish.

Consult for the session-level contract: what stops a run, how collection failures surface, and which output shapes reports take. TestNewSession extends SessionTests with ordering and stop-condition cases.

**Depends on.**

- [Hook Specifications](r7-core-hook-contracts.md) · model-inferred · 0 edge(s)
- [Python Test Collection and Execution](r7-python-collection.md) · model-inferred · 0 edge(s)

Parent: [pytest's Own Test Suites](r7-internal-test-suites.md)

## Units (29)

<a id="u-be6db9ad013f"></a>
### `test_session.py module code (L1–L9)`

`module_region` · [testing/test_session.py:L1-L9][f1]

Imports only (ExitCode, MonkeyPatch, Pytester, pytest); no behavior of its own.

<a id="u-ae30976fadf5"></a>
### `SessionTests`

`class SessionTests:` · [testing/test_session.py:L10-L11][f1]

Groups session-level collection/run tests: item events, import and syntax errors, -x/--maxfail stopping, broken reprs in reports, and conftest-driven file skipping; also the shared base for TestNewSession.

Members are documented individually in this batch.

<a id="u-2404534397ab"></a>
### `SessionTests.test_basic_testitem_events`

`def test_basic_testitem_events(self, pytester: Pytester) -> None:` · [testing/test_session.py:L11-L31][f1]

Checks per-item collection and outcome events for a file with one passing, two failing tests (assert and raised ValueError) and one class test.

inline_run produces outcomes: 0 skipped, 1 passed, 3 failed; the failed node-id suffixes are 'test_one_one' then 'test_other' (via a local end() helper), and exactly four pytest_itemcollected calls occurred, one per collected item including the class test.

group: [end](r7-session-tests.md#u-ca8a97d146df)

<a id="u-2bdbd1b2dd14"></a>
### `testing/test_session.py:SessionTests.test_basic_testitem_events`

`def test_basic_testitem_events(self, pytester: Pytester) -> None:` · [testing/test_session.py:L32-L41][f1]

Continuation segment of test_basic_testitem_events performing the failed-order and itemcollected assertions; behavior covered in full by the test_basic_testitem_events unit.

group: [SessionTests.test_basic_testitem_events](r7-session-tests.md#u-2404534397ab)

<a id="u-ca8a97d146df"></a>
### `end`

`def end(x):` · [testing/test_session.py:L31-L32][f1]

Nested helper returning the last '::'-separated component of a report's nodeid, used to identify failed items in the enclosing test.

<a id="u-726491ed8882"></a>
### `SessionTests.test_nested_import_error`

`def test_nested_import_error(self, pytester: Pytester) -> None:` · [testing/test_session.py:L43-L59][f1]

A test module importing 'import_fails', which itself imports the nonexistent 'does_not_work', must produce exactly one failed collection whose longrepr text mentions 'does_not_work', showing nested import failures surface as collection errors.

<a id="u-1c74046f00db"></a>
### `SessionTests.test_raises_output`

`def test_raises_output(self, pytester: Pytester) -> None:` · [testing/test_session.py:L61-L72][f1]

A test calling pytest.raises(ValueError, int, "3") fails because int('3') does not raise; exactly one failure is recorded and its crash message contains 'DID NOT RAISE'.

<a id="u-ec140bab5d36"></a>
### `SessionTests.test_syntax_error_module`

`def test_syntax_error_module(self, pytester: Pytester) -> None:` · [testing/test_session.py:L74-L79][f1]

inline_runsource on the non-Python text 'this is really not python' yields exactly one failed collection whose longrepr text contains 'not python'.

<a id="u-c3a60c23076e"></a>
### `SessionTests.test_exit_first_problem`

`def test_exit_first_problem(self, pytester: Pytester) -> None:` · [testing/test_session.py:L81-L91][f1]

With --exitfirst, two always-failing tests stop after the first: countoutcomes is failed==1 with zero passed and zero skipped, showing the run aborts before the second test.

<a id="u-f0e1f2be9603"></a>
### `SessionTests.test_maxfail`

`def test_maxfail(self, pytester: Pytester) -> None:` · [testing/test_session.py:L93-L104][f1]

With --maxfail=2 over three always-failing tests, countoutcomes is failed==2 with zero passed and zero skipped, showing the run stops at the second failure.

<a id="u-15ce1c2f6913"></a>
### `SessionTests.test_broken_repr`

`def test_broken_repr(self, pytester: Pytester) -> None:` · [testing/test_session.py:L106-L136][f1]

With a BrokenRepr1 whose __repr__ raises a custom BaseException subclass, one test that explicitly repr()s it inside pytest.raises passes (matching 'broken repr'), while an implicit failure in an assert comparing the object's attribute fails.

Outcomes are 1 passed, 0 skipped, 1 failed, and the failure's crash message contains the placeholder text '<[reprexc() raised in repr()] BrokenRepr1', showing broken reprs in failure reports are replaced, not fatal.

<a id="u-86f4ba75dcbd"></a>
### `SessionTests.test_broken_repr_with_showlocals_verbose`

`def test_broken_repr_with_showlocals_verbose(self, pytester: Pytester) -> None:` · [testing/test_session.py:L138-L160][f1]

With --showlocals -vv, a failing assertion involving an object whose __repr__ raises NotImplementedError produces one failure whose traceback has exactly one repr entry with one locals line, beginning 'x          = <[NotImplementedError() raised in repr()] ObjWithErrorInRepr' — broken reprs in local-variable display are replaced with the placeholder form.

<a id="u-5748463ac0aa"></a>
### `SessionTests.test_skip_file_by_conftest`

`def test_skip_file_by_conftest(self, pytester: Pytester) -> None:` · [testing/test_session.py:L162-L180][f1]

A conftest whose pytest_collect_file calls pytest.skip('intentional') skips collection of test files.

The test asserts a genuine pytest.skip.Exception escaping inline_run would be a failure (guarded, pragma no cover), then checks the collect reports: exactly two (Session, Dir) and the second is skipped, showing the skip at file-collection level is reported on the collection report rather than raised.

**Uncertainties.**

- Whether the conftest skip also covers nested file collection beyond the Dir level is not asserted here.

<a id="u-c143dd41551f"></a>
### `TestNewSession`

`class TestNewSession(SessionTests):` · [testing/test_session.py:L183-L184][f1]

Subclass of SessionTests adding collection-ordering and stop-condition tests (-x vs --maxfail, collect-only).

Inherited SessionTests members are documented in their own units.

<a id="u-a320abe0507e"></a>
### `TestNewSession.test_order_of_execution`

`def test_order_of_execution(self, pytester: Pytester) -> None:` · [testing/test_session.py:L184-L208][f1]

Runs seven tests appending to a shared module-level list (module-level tests then a class group sharing the same list) and asserts ordering: all 7 pass and none fail, with the class tests seeing [1,2,1,2,3], i.e. module-level tests run first, then class methods in definition order.

<a id="u-7a77d9155bd4"></a>
### `TestNewSession.test_collect_only_with_various_situations`

`def test_collect_only_with_various_situations(self, pytester: Pytester) -> None:` · [testing/test_session.py:L210-L236][f1]

With --collect-only over a directory containing test_one.py (two tests, one raising, one subclassed test class yielding 3 collected items), a syntactically invalid test_three.py, and an __init__.py: exactly 3 pytest_itemcollected calls, no runtest logreports (nothing executed), 6 matching collectstart/collectreport pairs, and exactly 1 failed collect report (the syntax-error module).

<a id="u-25dc81f0e016"></a>
### `TestNewSession.test_minus_x_import_error`

`def test_minus_x_import_error(self, pytester: Pytester) -> None:` · [testing/test_session.py:L238-L244][f1]

With -x over a directory with two unparseable test modules, collection stops after the first failed collect report: exactly one report is failed.

<a id="u-4d29ff5627bd"></a>
### `TestNewSession.test_minus_x_overridden_by_maxfail`

`def test_minus_x_overridden_by_maxfail(self, pytester: Pytester) -> None:` · [testing/test_session.py:L246-L252][f1]

With both -x and --maxfail=2 over three unparseable test modules, the maxfail limit governs collection-failure stopping: exactly two failed collect reports, showing --maxfail overrides -x.

<a id="u-6f8c12aa29e5"></a>
### `test_plugin_specify`

`def test_plugin_specify(pytester: Pytester) -> None:` · [testing/test_session.py:L255-L260][f1]

pytester.parseconfig('-p', 'nqweotexistent') raises ImportError because a named plugin that cannot be imported fails configuration parsing.

<a id="u-b0578b8eefbe"></a>
### `test_plugin_already_exists`

`def test_plugin_already_exists(pytester: Pytester) -> None:` · [testing/test_session.py:L263-L267][f1]

parseconfig('-p', 'terminal') records config.option.plugins == ['terminal'] and the full configure/unconfigure cycle (_do_configure then _ensure_unconfigure) completes without error.

<a id="u-f7d6325ebafd"></a>
### `test_exclude`

`def test_exclude(pytester: Pytester) -> None:` · [testing/test_session.py:L270-L278][f1]

Two directories each contain a syntax-error test file; with --ignore=hello --ignore=hello2 both are excluded, so only test_ok runs: return code 0 and '*1 passed*' output.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-96e61db4c8fd"></a>
### `test_exclude_glob`

`def test_exclude_glob(pytester: Pytester) -> None:` · [testing/test_session.py:L281-L293][f1]

Like test_exclude but with --ignore-glob=*h[ea]llo*, which matches hello, hello2 and hallo3 (and not sub): the three excluded directories' syntax-error files are skipped, only test_ok runs (ret 0, '*1 passed*').

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-eb03f8523c48"></a>
### `test_deselect`

`def test_deselect(pytester: Pytester) -> None:` · [testing/test_session.py:L296-L321][f1]

With a file of two plain tests, a 3-case parametrized test, and a class with two methods, three --deselect arguments remove test_a2[1], test_a2[2] and TestClass::test_c1: the run reports '*3 passed, 3 deselected*' with return code 0, and verbose output contains no lines starting with the deselected parametrized ids.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-0658e4c6d42b"></a>
### `test_sessionfinish_with_start`

`def test_sessionfinish_with_start(pytester: Pytester) -> None:` · [testing/test_session.py:L324-L339][f1]

A conftest records os.getcwd() in pytest_sessionstart and chdir's to the parent directory; pytest_sessionfinish asserts the cwd was restored, so the working directory changed during the session must be restored before sessionfinish.

Runs --collect-only expecting ExitCode.NO_TESTS_COLLECTED (the assertion in sessionfinish holds, no tests exist).

<a id="u-9849443d179c"></a>
### `test_collection_args_do_not_duplicate_modules`

`def test_collection_args_do_not_duplicate_modules(pytester: Pytester) -> None:` · [testing/test_session.py:L342-L389][f1]

Regression for #723/#3358: with one module d/test_it.py, collect-only with two node-id args ('d/test_it.py::test_1' and '::test_2') yields a single <Module test_it.py> listing each Function once (consecutive match).

The related case of passing the same directory 'd' twice with --keep-duplicates intentionally collects the module twice, showing duplication only occurs when explicitly requested.

calls: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-51f5a5434021"></a>
### `test_rootdir_option_arg`

`def test_rootdir_option_arg( pytester: Pytester, monkeypatch: MonkeyPatch, path: str …` · [testing/test_session.py:L392-L416][f1]

Parametrized over 'root', an absolute '{relative}/root', and '{environment}/root' expanded from PY_ROOTDIR_PATH.

Creates root/tests, runs with --rootdir=<variant>, and asserts the output reports the resolved rootdir as pytester.path/root, the test file path under that root, and 1 passed — all three spellings resolve to the same root directory.

calls: [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

<a id="u-8ef0040b3e02"></a>
### `test_rootdir_wrong_option_arg`

`def test_rootdir_wrong_option_arg(pytester: Pytester) -> None:` · [testing/test_session.py:L419-L423][f1]

An --rootdir pointing to a nonexistent directory produces a stderr message '*Directory *wrong_dir* not found.

Check your '--rootdir' option.*'.

<a id="u-858437a7e724"></a>
### `test_shouldfail_is_sticky`

`def test_shouldfail_is_sticky(pytester: Pytester) -> None:` · [testing/test_session.py:L426-L453][f1]

Issue #11706: a conftest pytest_sessionfinish sets session.shouldfail = False after it was set; the assignment is rejected with a warning '*session.shouldfail cannot be unset*' and the attribute stays truthy (the conftest's second assert passes).

The run with --maxfail=1 reports failed=1 and exactly one warning.

<a id="u-12d7a07edda7"></a>
### `test_shouldstop_is_sticky`

`def test_shouldstop_is_sticky(pytester: Pytester) -> None:` · [testing/test_session.py:L456-L483][f1]

Companion to the shouldfail test using --stepwise: a conftest pytest_sessionfinish sets session.shouldstop = False, which is rejected with the warning '*session.shouldstop cannot be unset*' and the attribute remains truthy; outcomes are failed=1 with one warning.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_session.py
