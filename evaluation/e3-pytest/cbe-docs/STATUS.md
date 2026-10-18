# CBE run status

Run `7dc6f8` · status **complete** · updated 2026-10-17T22:09:29Z · review sample · jobs 2 · host api

Semantic review: mode **sample**; 1/1 reviewed by a separate reader of the source. This is independent of the deterministic structure/coverage checks and does not prove whole-map truth.

Counts: done 86

id_corrected 18

- module_38: ` testing/test_runner.py::method::BaseFunctionalTests.test_passfunction::6350 ` → ` testing/test_runner.py::method::BaseFunctionalTests.test_passfunction::6012 ` (units[10].id)
- module_38: ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue90 ` → ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue90::10919 ` (units[19].id)
- module_38: ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue1206 ` → ` testing/test_runner.py::method::BaseFunctionalTests.test_exact_teardown_issue1206::12372 ` (units[20].id)
- module_39: ` testing/test_pytester.py::function::test_parse_summary_line_always_plural::2415 ` → ` testing/test_pytester.py::function::test_parse_summary_line_always_plural::25225 ` (units[22].id)
- module_39: ` testing/test_pytester.py::function::test_parse_summary_line_always_plural::2415 ` → ` testing/test_pytester.py::function::test_parse_summary_line_always_plural::25225 ` (dispositions[testing/test_pytester.py::function::test_parse_summary_line_always_plural::25225].unit)
- module_42: ` testing/test_threadexception.py::function::test_unhandled_thread_exception_in_teardown::1089 ` → ` testing/test_threadexception.py::function::test_unhandled_thread_exception_in_teardown::2181 ` (units[46].id)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::932 ` → ` src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::33118 ` (units[27].id)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::959 ` → ` src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::34128 ` (units[28].id)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::981 ` → ` src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::34904 ` (units[29].id)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.summary_errors::1176 ` → ` src/_pytest/terminal.py::method::TerminalReporter.summary_errors::42461 ` (units[35].id)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.summary_stats::1204 ` → ` src/_pytest/terminal.py::method::TerminalReporter.summary_stats::43562 ` (units[37].id)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::932 ` → ` src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::33118 ` (dispositions[src/_pytest/terminal.py::method::TerminalReporter.pytest_sessionfinish::33118].unit)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::959 ` → ` src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::34128 ` (dispositions[src/_pytest/terminal.py::method::TerminalReporter.pytest_terminal_summary::34128].unit)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::981 ` → ` src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::34904 ` (dispositions[src/_pytest/terminal.py::method::TerminalReporter._report_keyboardinterrupt::34904].unit)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.summary_xfailures::41465 ` → ` src/_pytest/terminal.py::method::TerminalReporter.summary_xfailures::41295 ` (dispositions[src/_pytest/terminal.py::method::TerminalReporter.summary_xfailures::41465] key)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.summary_errors::1176 ` → ` src/_pytest/terminal.py::method::TerminalReporter.summary_errors::42461 ` (dispositions[src/_pytest/terminal.py::method::TerminalReporter.summary_errors::42461].unit)
- module_5: ` src/_pytest/terminal.py::method::TerminalReporter.summary_stats::1204 ` → ` src/_pytest/terminal.py::method::TerminalReporter.summary_stats::43562 ` (dispositions[src/_pytest/terminal.py::method::TerminalReporter.summary_stats::43562].unit)
- module_65: ` testing/typing_raises_group.py::function::check_multiple_exceptions_2::6039_missing ` → ` testing/typing_raises_group.py::function::check_multiple_exceptions_2::6324 ` (dispositions[testing/typing_raises_group.py::function::check_multiple_exceptions_2::6039_missing] key)

index_only_filled 0


| Task | Module | State | Attempts | Seconds | Output | Note |
|---|---|---|---:|---:|---|---|
| names |  | done | 1 | 21.0 | host/accepted/names.json |  |
| module_1 | Local Path Common Filesystem Tests | done | 2 | 234.0 | host/accepted/module_1.json |  |
| module_2 | Fixture Request and Item Reordering | done | 2 | 250.0 | host/accepted/module_2.json |  |
| module_3 | Python Collection and Test Function Discovery | done | 3 | 228.0 | host/accepted/module_3.json |  |
| module_4 | Pytester Hook Recording and FD Leak Detection | done | 1 | 268.0 | host/accepted/module_4.json |  |
| module_5 | Terminal Reporter and Output Formatting | done | 3 | 216.0 | host/accepted/module_5.json | normalized (51); id_corrected 11 |
| module_6 | Raises Exception Assertion Helpers | done | 1 | 194.0 | host/accepted/module_6.json |  |
| module_7 | Node, Warning Types, and Thread/Unraisable Hooks | done | 1 | 197.0 | host/accepted/module_7.json |  |
| module_8 | Test Runner, Reports, and Setup State | done | 2 | 176.0 | host/accepted/module_8.json |  |
| module_9 | Monkeypatch, Tmpdir, and Legacy Testdir Plugins | done | 3 | 198.0 | host/accepted/module_9.json |  |
| module_10 | Freeze Support and Hook Specifications | done | 1 | 89.0 | host/accepted/module_10.json |  |
| module_11 | PDB Debugging, Outcomes, and Unittest Integration | done | 1 | 227.0 | host/accepted/module_11.json |  |
| module_12 | Faulthandler, Logging Capture, and Stash | done | 1 | 239.0 | host/accepted/module_12.json |  |
| module_13 | Output Capture, Fixture Scope, and Setup Display | done | 2 | 210.0 | host/accepted/module_13.json |  |
| module_14 | Pathlib Utilities and Unraisable Exception Collection | done | 3 | 175.0 | host/accepted/module_14.json |  |
| module_15 | Compat Helpers, Doctest Collection, and Pastebin | done | 2 | 208.0 | host/accepted/module_15.json |  |
| module_16 | Argcomplete and Main Collection Session | done | 1 | 149.0 | host/accepted/module_16.json |  |
| module_17 | Approx Comparison API and Skip/Xfail Evaluation | done | 2 | 116.0 | host/accepted/module_17.json |  |
| module_18 | Cache Provider, Warnings Recorder, and Stepwise | done | 1 | 178.0 | host/accepted/module_18.json |  |
| module_19 | Help Config, JUnit XML Reporting, and Timing | done | 1 | 137.0 | host/accepted/module_19.json |  |
| module_20 | Code, Frame, and Traceback Entry Introspection | done | 1 | 221.0 | host/accepted/module_20.json |  |
| module_21 | IO Utilities: PrettyPrint, SafeRepr, TerminalWriter, wcwidth | done | 1 | 164.0 | host/accepted/module_21.json |  |
| module_22 | Legacy Path Checkers and Visitor Helpers | done | 2 | 174.0 | host/accepted/module_22.json |  |
| module_23 | Assertion Rewriting Import Hook and AST Transformer | done | 1 | 171.0 | host/accepted/module_23.json |  |
| module_24 | Assertion Representation, Truncation, and Utilities | done | 1 | 173.0 | host/accepted/module_24.json |  |
| module_25 | Configuration Core and Plugin Manager | done | 3 | 229.0 | host/accepted/module_25.json |  |
| module_26 | Argument Parsing and Config File Discovery | done | 5 | 126.0 | host/accepted/module_26.json |  |
| module_27 | Marks: Parametrize, Expression Matching, Structures | done | 2 | 166.0 | host/accepted/module_27.json |  |
| module_28 | Source Introspection and OS Error Mapping | done | 1 | 81.0 | host/accepted/module_28.json |  |
| module_29 | Terminal Output Functional Tests | done | 2 | 278.0 | host/accepted/module_29.json |  |
| module_30 | Pathlib Import and FNMatcher Tests | done | 3 | 124.0 | host/accepted/module_30.json |  |
| module_31 | JUnit XML Output Parsing Test Helpers | done | 1 | 146.0 | host/accepted/module_31.json |  |
| module_32 | Capture Manager and Fixture Functional Tests | done | 1 | 179.0 | host/accepted/module_32.json |  |
| module_33 | Doctest Collection and Execution Tests | done | 2 | 108.0 | host/accepted/module_33.json |  |
| module_34 | Cache Provider and Last-Failed Tests | done | 2 | 91.0 | host/accepted/module_34.json |  |
| module_35 | Unittest Integration Tests | done | 1 | 213.0 | host/accepted/module_35.json |  |
| module_36 | PDB Interaction and Postmortem Tests | done | 2 | 162.0 | host/accepted/module_36.json |  |
| module_37 | Skip and Xfail Marker Evaluation Tests | done | 1 | 121.0 | host/accepted/module_37.json |  |
| module_38 | Runner Setup State and Execution Tests | done | 3 | 175.0 | host/accepted/module_38.json | normalized (76); id_corrected 3 |
| module_39 | Pytester, Stash, and Unraisable Tests | done | 3 | 177.0 | host/accepted/module_39.json | normalized (69); id_corrected 2 |
| module_40 | Monkeypatch and Warnings Tests | done | 3 | 154.0 | host/accepted/module_40.json | normalized (50) |
| module_41 | Recwarn, Scope, and Tmpdir Tests | done | 1 | 174.0 | host/accepted/module_41.json |  |
| module_42 | Report Serialization, Stepwise, and Thread Exception Tests | done | 3 | 148.0 | host/accepted/module_42.json | normalized (49); id_corrected 1 |
| module_43 | Compat, Findpaths, Legacypath, Pastebin, and Setuponly Tests | done | 1 | 198.0 | host/accepted/module_43.json |  |
| module_44 | Faulthandler, Help Config, and Node Tests | done | 2 | 91.0 | host/accepted/module_44.json |  |
| module_45 | Code Object and Source Parsing Tests | done | 2 | 189.0 | host/accepted/module_45.json |  |
| module_46 | IO Utilities Tests: pprint, saferepr, terminalwriter, wcwidth | done | 2 | 176.0 | host/accepted/module_46.json |  |
| module_47 | Log Capture Fixture Tests | done | 1 | 112.0 | host/accepted/module_47.json |  |
| module_48 | Excinfo and Traceback Tests | done | 2 | 232.0 | host/accepted/module_48.json |  |
| module_49 | Py Library Entry Point | done | 1 | 29.0 | host/accepted/module_49.json |  |
| module_50 | Config INI Parsing and Command-Line Tests | done | 1 | 237.0 | host/accepted/module_50.json |  |
| module_51 | Assertion Rewrite Tests | done | 2 | 233.0 | host/accepted/module_51.json |  |
| module_52 | Assertion Comparison and Import Hook Tests | done | 3 | 260.0 | host/accepted/module_52.json |  |
| module_53 | Collection and Session Tests | done | 5 | 181.0 | host/accepted/module_53.json |  |
| module_54 | Mark and python path Functional Tests | done | 1 | 164.0 | host/accepted/module_54.json |  |
| module_55 | Conftest Loading, Entry Points, and Arg Parsing Tests | done | 2 | 187.0 | host/accepted/module_55.json |  |
| module_56 | Plugin Manager, Session, and Error Diff Tests | done | 9 | 191.0 | host/accepted/module_56.json |  |
| module_57 | Argcomplete, Mark Expression, and Runner XUnit Tests | done | 3 | 167.0 | host/accepted/module_57.json |  |
| module_58 | Collection, Fixture, and Mark Example Scripts | done | 1 | 211.0 | host/accepted/module_58.json |  |
| module_59 | Issue 519 Regression Example Test | done | 1 | 36.0 | host/accepted/module_59.json |  |
| module_60 | Frozen Executable Trivial Tests | done | 1 | 34.0 | host/accepted/module_60.json |  |
| module_61 | Live Logging Reporting Tests | done | 1 | 157.0 | host/accepted/module_61.json |  |
| module_62 | Log Formatter Tests | done | 2 | 55.0 | host/accepted/module_62.json |  |
| module_63 | pytest Public API Package Entry | done | 2 | 30.0 | host/accepted/module_63.json |  |
| module_64 | General Usage Acceptance Tests | done | 2 | 169.0 | host/accepted/module_64.json |  |
| module_65 | Testing Suite Conftest, Deprecation, and Typing Checks | done | 3 | 166.0 | host/accepted/module_65.json | normalized (67); id_corrected 1 |
| module_66 | Fixture Filling and Override Tests | done | 2 | 252.0 | host/accepted/module_66.json |  |
| module_67 | Metafunc Parametrize Tests | done | 1 | 268.0 | host/accepted/module_67.json |  |
| module_68 | RaisesGroup Exception Group Tests | done | 2 | 125.0 | host/accepted/module_68.json |  |
| module_69 | Module, Class, and Function Collection Tests | done | 1 | 123.0 | host/accepted/module_69.json |  |
| module_70 | Approx Comparison Tests | done | 1 | 128.0 | host/accepted/module_70.json |  |
| module_71 | Mock Decoration, Raises, and Show Fixtures Tests | done | 2 | 204.0 | host/accepted/module_71.json |  |
| module_72 | Example Script Conftests and Plugin Integration Sources | done | 3 | 124.0 | host/accepted/module_72.json |  |
| repair_66 | Fixture Filling and Override Tests | done | 2 | 303.0 | host/accepted/repair_66.json |  |
| tree |  | done | 3 | 78.0 | host/accepted/tree.json |  |
| tree_region-0001 |  | done | 1 | 226.0 | host/accepted/tree_region-0001.json |  |
| tree_region-0002 |  | done | 2 | 174.0 | host/accepted/tree_region-0002.json | normalized (11) |
| tree_region-0003 |  | done | 2 | 140.0 | host/accepted/tree_region-0003.json | normalized (2) |
| tree_region-0004 |  | done | 2 | 211.0 | host/accepted/tree_region-0004.json |  |
| tree_region-0005 |  | done | 1 | 171.0 | host/accepted/tree_region-0005.json |  |
| tree_region-0006 |  | done | 2 | 220.0 | host/accepted/tree_region-0006.json | normalized (2) |
| tree_region-0007 |  | done | 2 | 99.0 | host/accepted/tree_region-0007.json | normalized (1) |
| tree_region-0008 |  | done | 2 | 139.0 | host/accepted/tree_region-0008.json | normalized (1) |
| tree_region-0009 |  | done | 1 | 267.0 | host/accepted/tree_region-0009.json |  |
| review_66 | Fixture Filling and Override Tests | done | 1 | 67.0 | host/accepted/review_66.json |  |
| system |  | done | 5 | 56.0 | host/accepted/system.json |  |
