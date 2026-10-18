# JUnit XML Reporting

**Capability.** The junitxml plugin (src/_pytest/junitxml.py): CLI/ini option declaration, session-lifecycle wiring of the LogXML reporter, per-node <testcase> construction with XML-safe escaping, and user-facing record_* fixtures for properties and attributes.

Use this subtree to understand --junitxml output composition and to hook custom data into the report via record_property/record_testsuite_property. Static edges show node-reporter and the record fixtures both funnel into logxml, with shared helpers for param validation and xunit2 warnings.

**Depends on.**

- [Hook Specifications](r7-core-hook-contracts.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Plugin and Utility Unit Tests](r7-misc-unit-tests.md) · graph-confirmed · 2 edge(s)

Parent: [pytest Codebase](r7-pytest-codebase.md)

## Units (13)

<a id="u-18079b7c231f"></a>
### `src/_pytest/junitxml.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/junitxml.py:L376-L420][f1]

Declares the junitxml CLI and ini options: --junitxml/--junit-xml storing the report path (validated by filename_arg) and --junitprefix/--junit-prefix for classname prefixes, plus ini entries junit_suite_name (default 'pytest'), junit_logging (no|log|system-out|system-err|out-err|all, default 'no'), junit_log_passing_tests (bool, default True), junit_duration_report (total|call, default 'total'), and junit_family (legacy|xunit1|xunit2, default 'xunit2').

Purely declarative.

<a id="u-f83e853fd1d9"></a>
### `src/_pytest/junitxml.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/junitxml.py:L423-L437][f1]

Creates and registers the XML reporter when --junitxml is active.

Skips entirely on worker nodes (config has workerinput, i.e. xdist workers) to avoid opening the log there. Otherwise reads all five ini values and stores a constructed LogXML under xml_key, then registers it with the plugin manager so its hooks run.

calls: [junitxml-logxml](r7-junit-xml-reporting.md#u-d7533d07dbab); contract: [src/_pytest/junitxml.py:pytest_addoption](r7-junit-xml-reporting.md#u-18079b7c231f)

<a id="u-72aa408c0e89"></a>
### `src/_pytest/junitxml.py:pytest_unconfigure`

`def pytest_unconfigure(config: Config) -> None:` · [src/_pytest/junitxml.py:L440-L444][f1]

Tears down the XML reporter at session end: if a LogXML is present in the config stash, deletes the stash entry and unregisters it from the plugin manager.

No action when junitxml was not configured.

<a id="u-d7533d07dbab"></a>
### `junitxml-logxml`

`def __init__( self, logfile, prefix: str | None, suite_name: str = "pytest", logging:…` · [src/_pytest/junitxml.py:L459-L490][f1]

JUnit XML reporting plugin object implementing pytest hooks to build the report.

__init__ expands user/env vars in the log path, normalizes it to an absolute path, stores options (prefix, suite name, logging mode, duration mode, family, log_passing_tests), initializes per-status counters, reporter registries keyed by (nodeid, workernode), ordered reporter list, global properties, open call-phase reports for teardown-failure handling, and a counter of double-fail tests; a 'legacy' family is remapped to 'xunit1'. pytest_runtest_logreport is the core dispatcher: passed reports only produce testcase content during call phase; failed call reports open a testcase, append a failure, and are tracked in open_reports (captured output written immediately when log_passing_tests is off), while failed setup/teardown append an error — a failed teardown matching a pending open report first finalizes that testcase and counts a double-fail so the schema allows a new testcase; skipped reports append skip info; durations are always updated, and on teardown the captured output is written and the testcase finalized, removing it from open_reports when matched. Other hooks: collect reports create testcases for failed/skipped collection; internal errors create a synthetic 'pytest internal' testcase; session start records a timing.Instant; session finish creates the log directory (with exist_ok to avoid races), computes test count as passes+failures+skips+errors minus double-fails, writes the XML declaration, a <testsuite> node with stats, wall-clock duration, local ISO timestamp and hostname, global properties, and each reporter's testcase wrapped in <testsuites>. Helpers finalize (moves user_properties onto the reporter and permanently finalizes it, popping it from the registry), node_reporter (caches per (nodeid, workernode); TODO notes it breaks with --dist=each), add_stats, _opentestcase, update_testcase_duration (accumulates duration when report_duration is 'total' or matches the report phase), pytest_terminal_summary (prints the output file path), and add_global_property/_get_global_properties_node (session-level properties with name type-check and XML escaping) are folded here.

**Notes.**

- failure: finalize pops the (nodeid, workernode) key before checking the reporter, so an unknown report would raise KeyError from dict.pop before the None guard is reached.
- field: open_reports tracks failed call reports until their teardown arrives so a teardown error can be reported as a separate testcase per the JUnit schema.

uses: [junitxml-node-reporter](r7-junit-xml-reporting.md#u-a2459e70cff8), [Instant](r5-time-scope-primitives.md#u-313e6e0ed7df); calls: [junitxml-bin-xml-escape](r7-junit-xml-reporting.md#u-e12a60ef002c), [_check_record_param_type](r7-junit-xml-reporting.md#u-1dae0013d36c)

**Uncertainties.**

- the dispositions of suite_start attribute and count semantics across xdist interlacing are inferred from the code path; interlaced worker ordering beyond the documented xdist case is not proven
- node_reporter's TODO acknowledges broken behavior with --dist=each; exact failure mode is not derivable here

<a id="u-a2459e70cff8"></a>
### `junitxml-node-reporter`

`def __init__(self, nodeid: str | TestReport, xml: LogXML) -> None:` · [src/_pytest/junitxml.py:L87-L95][f1]

Builds one JUnit <testcase> element for a node id or report, accumulating attributes, duration, custom properties, and child result nodes.

__init__ copies stats/family hooks from the owning LogXML and starts duration at 0. record_testreport mangles the nodeid into classname/name parts (optionally prefixed), fills file/line/url when present, restores any user-defined attributes, then for families other than xunit1 filters attributes down to those permitted by families[family]['testcase']. write_captured_output skips output for passed tests when log_passing_tests is off or logging is 'no', and depending on junit_logging ('log', 'system-out', 'system-err', 'out-err', 'all') emits <system-out>/<system-err> nodes with 80-char centered headers around captured log/stdout/stderr. Result appenders distinguish failure modes: append_failure reports an unexpected pass of xfail-marked tests as 'skipped', otherwise uses reprcrash message or str(longrepr); append_error frames the reason as failing on setup or teardown; append_skipped handles xfail reason stripping ('reason: ' prefix) versus skip reasons ('Skipped: ' prefix) with file:line details, and for non-xfail skips also writes captured output. finalize serializes to XML, clears the instance __dict__, and replaces to_xml with a constant-returning lambda so later serialization still yields the finished element. Trivial appenders (append, add_property, add_attribute, make_properties_node, to_xml, _add_simple, _prepare_content, _write_content, append_pass, append_collect_error, append_collect_skipped) are folded here.

**Notes.**

- side_effect: finalize() destroys the reporter's instance state and permanently replaces its to_xml with a constant lambda.

uses: [junitxml-logxml](r7-junit-xml-reporting.md#u-d7533d07dbab); calls: [junitxml-bin-xml-escape](r7-junit-xml-reporting.md#u-e12a60ef002c), [mangle_test_address](r7-junit-xml-reporting.md#u-f0160cbca68b)

**Uncertainties.**

- append_skipped asserts report.longrepr is a tuple for non-xfail skips; behavior with other shapes is unproven
- record_testreport references families[self.family]['testcase']; a family absent from that dict would raise KeyError, not observed here

<a id="u-e12a60ef002c"></a>
### `junitxml-bin-xml-escape`

`def repl(matchobj: re.Match[str]) -> str:` · [src/_pytest/junitxml.py:L48-L53][f1]

Escapes characters that are illegal in XML documents into visible '#xNN' markers rather than true XML entities, so consumers see the original code point.

The regex whitelists tab, newline, carriage return, printable ASCII 0x20-0x7E, and large Unicode ranges, deliberately excluding DEL (0x7F). The inner repl formats matched code points as two hex digits for values <= 0xFF and four digits otherwise. Input is converted with str(arg); the inner repl function is folded here.

<a id="u-25d4e8acc1a0"></a>
### `merge_family`

`def merge_family(left, right) -> None:` · [src/_pytest/junitxml.py:L64-L71][f1]

Merges attribute-family dicts by intersecting keys of left and right and concatenating their list values.

For each key present in both dicts it requires the left value to be a list, raising TypeError otherwise, then stores the concatenation in result and finally updates left with it. Keys only in one dict are ignored. Used at module level to build the xunit1 family from base and legacy attribute sets.

<a id="u-f0160cbca68b"></a>
### `mangle_test_address`

`def mangle_test_address(address: str) -> list[str]:` · [src/_pytest/junitxml.py:L447-L455][f1]

Converts a node id into classname parts for the JUnit classname/name attributes.

It splits off any bracketed parameters, splits the remainder on '::', converts the leading file path to a dotted module path, strips a trailing '.py', then reattaches the bracket parameters to the last name. Returns the list of name parts.

<a id="u-54155c18c223"></a>
### `junitxml-record-property-fixture`

`def append_property(name: str, value: object) -> None:` · [src/_pytest/junitxml.py:L293-L294][f1]

Fixture returning a callable that records (name, value) user properties on the calling test node, exposed to reporters such as the JUnit XML output.

It first warns via _warn_incompatibility_with_xunit2 when the active family is xunit2-like. The returned append_property simply appends the tuple to request.node.user_properties; values are XML-encoded later by the reporter. This unit covers both the fixture and its inner function.

calls: [_warn_incompatibility_with_xunit2](r7-junit-xml-reporting.md#u-f2435d9e0ae5)

<a id="u-ebd1423c89a1"></a>
### `junitxml-record-testsuite-property-fixture`

`def record_func(name: str, value: object) -> None:` · [src/_pytest/junitxml.py:L365-L368][f1]

Session-scoped fixture returning a callable that records a <property> under the root <testsuite>, compatible with xunit2.

record_func begins as a validating no-op (so calls are harmless when --junitxml was not given) that type-checks the name argument; when a LogXML is stashed it is replaced by xml.add_global_property so values actually land in the report. Covers the fixture and its inner record_func.

calls: [_check_record_param_type](r7-junit-xml-reporting.md#u-1dae0013d36c); uses: [junitxml-logxml](r7-junit-xml-reporting.md#u-d7533d07dbab)

<a id="u-afdbdcf814bc"></a>
### `junitxml-record-xml-attribute-fixture`

`def add_attr_noop(name: str, value: object) -> None:` · [src/_pytest/junitxml.py:L315-L316][f1]

Experimental fixture that would set extra XML attributes on the calling test's testcase tag, but first warns unconditionally with PytestExperimentalApiWarning.

After the xunit2 incompatibility warning, it defaults to a no-op callable; only when a LogXML is registered in the config stash does it return the relevant node reporter's add_attribute so calls actually mutate testcase attributes. Covers the fixture and its add_attr_noop inner function.

**Notes.**

- side_effect: Using the fixture always emits an experimental-API warning, regardless of junit_family.

calls: [junitxml-logxml](r7-junit-xml-reporting.md#u-d7533d07dbab)

<a id="u-1dae0013d36c"></a>
### `_check_record_param_type`

`def _check_record_param_type(param: str, v: str) -> None:` · [src/_pytest/junitxml.py:L328-L334][f1]

Validates that a record fixture parameter is a string; sets __tracebackhide__ so pytest's traceback filtering hides this frame, and raises TypeError with a message naming the parameter and the offending type when the check fails.

Returns nothing on success.

<a id="u-f2435d9e0ae5"></a>
### `_warn_incompatibility_with_xunit2`

`def _warn_incompatibility_with_xunit2( request: FixtureRequest, fixture_name: str ) -…` · [src/_pytest/junitxml.py:L261-L273][f1]

Shared helper emitting a PytestWarning about fixtures incompatible with modern junit families.

It reads the LogXML registered under xml_key from the config stash; if present and its family is neither 'xunit1' nor 'legacy', it warns on the current node that the named fixture is incompatible and recommends those families. When no XML log is configured it does nothing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/junitxml.py
