# JUnit XML reporting tests

**Capability.** End-to-end tests of LogXML output: a run_and_parse fixture with schema validation, DomDocument/DomNode wrappers for XML navigation, coverage of Python and non-Python item reporting, escaping, xdist, and the plugin's configure-once behavior.

Use this to learn the expected shape of generated JUnit XML and the helper vocabulary (run_and_parse, assert_attr) used to assert on it.

**Depends on.**

- [pytest codebase](r5-pytest-codebase.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-junitxml-tests ` → ` r5-pytest-codebase `)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 69 edge(s)

Parent: [pytest's own test suites](r5-test-suites.md)

## Units (12)

<a id="u-420a07f27eb9"></a>
### `schema`

`def schema() -> xmlschema.XMLSchema:` · [testing/test_junitxml.py:L28-L33][f1]

Session-scoped fixture returning an xmlschema.XMLSchema built from the bundled junit-10.xsd file.

calls: [path-localpath-readwrite](r6-path-fs.md#u-4e0de7f2e479)

<a id="u-331f38af5634"></a>
### `run_and_parse`

`def run_and_parse(pytester: Pytester, schema: xmlschema.XMLSchema) -> RunAndParse:` · [testing/test_junitxml.py:L55-L63][f1]

Fixture returning a RunAndParse bound to the current pytester and schema, so tests can run pytest and get a parsed DomDocument; family sets junit_family and 'xunit2' additionally schema-validates.

uses: [RunAndParse](r5-junitxml-tests.md#u-9c33be8d791e)

<a id="u-9c33be8d791e"></a>
### `RunAndParse`

`class RunAndParse:` · [testing/test_junitxml.py:L36-L37][f1]

Callable helper that runs pytest with a --junitxml option, validates xunit2 output against the XSD, and returns the run result plus a DomDocument wrapper of the parsed XML.

**Uncertainties.**

- Whether xml_path always exists when family is falsy is not guarded here; minidom.parse would fail on a missing file, but that path is not exercised in this file.

<a id="u-1443b75e94e0"></a>
### `DomDocument`

`class DomDocument:` · [testing/test_junitxml.py:L78-L81][f1]

Wrapper around a minidom document or element exposing tag-based lookup and child navigation for tests; finders return DomNode wrappers or None, and get_first_by_tag/get_unique_child raise or assert when the shape does not match.

**Notes.**

- failure: get_first_by_tag raises LookupError(tag) when no element matches; get_unique_child asserts len(children)==1, failing with AssertionError otherwise.
- failure: find_nth_by_tag catches IndexError from items[n] and returns None.
- contract: children filters childNodes to minidom.Element instances, so text nodes are skipped.

<a id="u-0760aee753e9"></a>
### `DomNode`

`class DomNode(DomDocument):` · [testing/test_junitxml.py:L122-L125][f1]

DomDocument subclass wrapping a minidom.Element that adds attribute access via __getitem__ (raising KeyError when absent), a repr equal to the element's XML, delegated assert_attr, text from the first child text node, and the tagName.

**Notes.**

- failure: text asserts the first child node is minidom.Text, so an element without a leading text node fails that assertion.

inherits: [DomDocument](r5-junitxml-tests.md#u-1443b75e94e0); calls: [assert_attr](r5-junitxml-tests.md#u-eab7f2fd1303)

<a id="u-eab7f2fd1303"></a>
### `assert_attr`

`def assert_attr(node: minidom.Element, **kwargs: object) -> None:` · [testing/test_junitxml.py:L66-L69][f1]

Assertion helper comparing a minidom element's attributes to keyword expectations: values are stringified, missing attributes read as None, and inequality fails the test with hidden traceback.

<a id="u-5cf3cc4ca901"></a>
### `TestJunitHelpers`

`class TestJunitHelpers:` · [testing/test_junitxml.py:L153-L156][f1]

Coverage tests for the DomDocument/DomNode helpers using a small inline two-item XML document; verifies unique-child lookup, attribute assertion failures, KeyError and LookupError paths, and repr equal to the serialized element.

<a id="u-e89e043507a5"></a>
### `TestPython`

`class TestPython:` · [testing/test_junitxml.py:L198-L199][f1]

End-to-end tests of LogXML report generation for Python tests, each running pytest via run_and_parse and asserting on the produced JUnit XML.

Both xunit1 and xunit2 families are parametrized for most tests, with xunit2 additionally schema-validated by the fixture. Key checked behaviors: testsuite counts (errors/failures/skipped/tests) for pass/fail/skip/xfail/xpass mixes including fixture errors and strict xpass producing a failure with '[XPASS(strict)]' message; hostname from platform.node(); ISO timestamp between run start and end; testcase time under mocked timing (sum of setup/teardown/test sleeps, 7.0) and under junit_duration_report where the 'total' mode yields 3.0 while 'call' yields the injected 1.0. Error and failure messages follow the observed formats: setup errors as 'failed on setup with "ValueError: ..."', teardown as 'failed on teardown with ...', call failures as 'Exception: ...'; a call failure plus teardown error produces two distinct testcase nodes, one failure and one error. Skip messages appear as skipped nodes with type 'pytest.skip' for pytest.skip, mark.skip and skipif; marked skips do not capture output. classname encodes module (with --junitprefix prepended), nested directories as dotted paths, and 'pytest'/'internal' with message 'internal error' for conftest protocol errors. junit_logging controls captured content: 'log' adds warnings to system-out (info excluded), 'system-out'/'system-err' add the respective streams, 'out-err'/'all' both, 'no' none; xfail output appears exactly once per enabled stream; failing tests still capture stdout/stderr, and setup/teardown output is merged without duplication. Escape/encoding cases (unicode in failures, binary comparison chars) assert the XML stays parseable.

**Uncertainties.**

- test_timing_function depends on the mock_timing fixture defined outside this file; its exact mocking behavior is not visible here.
- test_assertion_binchars only runs the scenario and prints the XML, asserting nothing beyond a successful run.

<a id="u-3240995ea66c"></a>
### `TestNonPython`

`class TestNonPython:` · [testing/test_junitxml.py:L1031-L1032][f1]

Verifies JUnit reporting for non-Python collect items: a conftest collects .xyz files into a custom Item whose runtest raises and whose repr_failure returns a custom message; the XML then shows one failing testcase named after the file with that message.

<a id="u-e21404c81a9c"></a>
### `test-junitxml-module-level-tests`

`def test_nullbyte(pytester: Pytester, junit_logging: str) -> None: # A null byte cann…` · [testing/test_junitxml.py:L1061-L1080][f1]

Module-level tests covering LogXML construction, escaping, record_* fixtures, xdist behavior, and suite-level features.

XML sanitization: test_nullbyte and test_nullbyte_replace assert null bytes never appear raw in junit.xml and are emitted as #x00/#x0 escapes only when junit_logging=system-out; test_invalid_xml_escape checks bin_xml_escape maps control and surrogate code points to #xHH/#xHHHH escapes while 0x9, 0xA, 0x20 pass through unchanged. Path handling: test_logxml_path_expansion checks ~ and $HOME expansion in LogXML logfile (with HOME monkeypatched), test_logxml_changingdir that the XML path resolves before a test os.chdir, test_logxml_makedir that parent directories are created, and test_logxml_check_isdir that a directory argument errors with '--junitxml must be a filename'. Name escaping tests cover parametrized names with \x00 and 'double::colon' for functions and methods. test_unicode_issue368 drives LogXML._opentestcase directly with a fake BaseReport through failure/collect-error/skip/xfail appends and finishes the session, exercising unicode longreprs. record_property tests assert <properties><property> nodes (order preserved, duplicates allowed, present on both the failed and error testcase when teardown also fails) and normal terminal output; record_xml_attribute sets testcase attributes but warns as experimental. test_record_fixtures_without_junitxml shows both fixtures are harmless without --junitxml; test_record_fixtures_xunit2 shows both drop values under junit_family=xunit2 with an incompatibility warning; test_record_testsuite_property writes testsuite-level properties (later value overwritten shown as second node), works when junit is disabled, and raises TypeError for a non-string name. xdist tests (skipped without xdist) verify overlapping report handling and deduplication when the same file runs twice. test_root_testsuites_tag and test_set_suite_name check the testsuites root, its name from junit_suite_name (default 'pytest' when empty). test_global_properties and test_url_property drive LogXML directly, asserting one <properties> with the added global properties and the report url attribute on the testcase. Skip-reason escaping tests assert '#x1B'-escaped ANSI and '1 <> 2' content in skipped nodes; test_escaped_setup_teardown_error checks escape sequences in error message and text. junit_log_passing_tests=False suppresses system-out/system-err for passing tests but still records them for failing tests according to junit_logging.

**Uncertainties.**

- test_record_fixtures_xunit2 builds expected_lines twice; only the incompatibility message list is actually matched, so the experimental-feature line appended for record_xml_attribute is dead code in this test.
- test_fancy_items_regression expects testcase classnames derived from the conftest file; the exact classname mapping for custom collectors is asserted empirically rather than derived here.

<a id="u-27485ced4755"></a>
### `test_dont_configure_on_workers`

`def test_dont_configure_on_workers(tmp_path: Path) -> None:` · [testing/test_junitxml.py:L1001-L1004][f1]

Verifies junitxml.pytest_configure registers exactly once: a FakeConfig (self-referential pluginmanager/option, real Stash, xmlpath in tmp) first configures as a non-worker, then setting FakeConfig.workerinput = None makes a second configure a no-op, keeping the recorded call count at 1.

**Uncertainties.**

- Behavior of the real pytest_configure (skip condition, what is registered) lives in _pytest/junitxml and is not visible here.

<a id="u-1a42c967beb6"></a>
### `test_mangle_test_address`

`def test_mangle_test_address() -> None:` · [testing/test_junitxml.py:L993-L998][f1]

Checks mangle_test_address turns 'a/my.py.thing.py::Class::method::[a-1-::]' into ['a.my.py.thing','Class','method','[a-1-::]'], converting the path portion to dotted form while leaving the parametrized tail intact.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_junitxml.py
