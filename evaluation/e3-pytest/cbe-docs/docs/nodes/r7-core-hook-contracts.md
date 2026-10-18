# Hook Specifications

**Capability.** Declares every pytest hook signature in src/_pytest/hookspec.py, organized by lifecycle phase: initialization, collection, python item generation, the runtest protocol, report serialization/fixtures, and session/reporting/error hooks. Plugins implement these; core and third parties call them.

Use this subtree as the contract reference for what a plugin may implement at each session phase. The grouping by phase tells you when a hook fires relative to configuration, collection, execution, and reporting.

**Depended on by.**

- [Python Collection Tests](r7-collect-tests.md) · model-inferred · 0 edge(s)
- [JUnit XML Reporting](r7-junit-xml-reporting.md) · model-inferred · 0 edge(s)
- [PDB and Breakpoint Tests](r7-pdb-tests.md) · model-inferred · 0 edge(s)
- [Session Run Control Tests](r7-session-tests.md) · model-inferred · 0 edge(s)
- [Warning Handling Tests](r7-warnings-tests.md) · model-inferred · 0 edge(s)

Parent: [pytest Codebase](r7-pytest-codebase.md)

## Units (6)

<a id="u-ffa36da07d4e"></a>
### `hookspec-initialization-hooks`

`def pytest_addhooks(pluginmanager: PytestPluginManager) -> None:` · [src/_pytest/hookspec.py:L56-L71][f1]

Hook specifications for plugin registration and early configuration, all declared with the pytest hookspec marker.

pytest_addhooks, pytest_plugin_registered, pytest_addoption, and pytest_configure are historic=True: they are incompatible with hook wrappers, and conftest implementations run immediately at registration time (pytest_plugin_registered fires once per already-registered plugin, including itself). pytest_addoption registers argparse options and ini values once at startup, only for initial conftests. pytest_cmdline_parse (firstresult) returns a Config from parsed args and is only called for plugin classes passed via pytest.main's plugins argument; pytest_load_initial_conftests (not firstresult, not for conftests) loads initial conftest files before option parsing; pytest_cmdline_main (firstresult) performs the main action, whose default invokes configure hooks and the runtest loop, only for initial conftests. All bodies are docstring-only specifications; behavior comes from implementations registered by plugins.

<a id="u-f28b159c5c5d"></a>
### `hookspec-collection-hooks`

`def pytest_collection(session: Session) -> object | None:` · [src/_pytest/hookspec.py:L229-L268][f1]

Hook specifications for the collection phase, from whole-session control down to per-node callbacks.

pytest_collection (firstresult) performs collection for a session and documents the default pipeline: collectstart, make_collect_report, per-node recursion with itemcollected, collectreport, then collection_modifyitems (implementors must explicitly call pytest_deselected for filtered items), collection_finish, and setting session.items/testscollected; its return value only stops further processing. pytest_ignore_collect (firstresult) suppresses collection: True ignores the path, None defers to other plugins, False forcefully keeps the path without consulting later plugins; the legacy 'path' argument is deprecated via warn_on_impl_args. pytest_collect_directory (firstresult, 8.0) and pytest_collect_file create Collector nodes (ideally Directory/File subclasses) whose parent must be the given collector. pytest_pycollect_makemodule note lives in the python group; here pytest_make_collect_report (firstresult) wraps collector.collect() into a CollectReport. pytest_collectstart, pytest_itemcollected, pytest_collectreport, and pytest_deselected are notification hooks; pytest_deselected may be called multiple times. Per-path hooks consult only conftest files in parent directories of the target, never the target's own conftest.

<a id="u-0d716afac3fd"></a>
### `hookspec-python-item-hooks`

`def pytest_pycollect_makemodule( module_path: Path, path: LEGACY_PATH, parent ) -> Mo…` · [src/_pytest/hookspec.py:L504-L539][f1]

Hook specifications for Python test-function collection and execution setup.

pytest_pycollect_makemodule (firstresult) returns a Module collector per matching test-module path; its deprecated legacy 'path' argument warns via warn_on_impl_args. pytest_pycollect_makeitem (firstresult) lets implementations supply custom items/collectors for a named object found in a module or class, or return None to defer. pytest_pyfunc_call (firstresult) is the extension point that ultimately calls the underlying test function for a Function item. pytest_generate_tests generates multiple parametrized calls via the Metafunc helper. pytest_make_parametrize_id (firstresult) returns a user-friendly id for a parametrize value, or None when the implementation does not recognize it. All are conftest-implementable, scoped to the relevant directory and its parents.

<a id="u-45aabc34a7c1"></a>
### `hookspec-runtest-hooks`

`def pytest_runtestloop(session: Session) -> object | None:` · [src/_pytest/hookspec.py:L627-L650][f1]

Hook specifications for the per-item runtest protocol.

pytest_runtestloop (firstresult) is the main loop after collection; its default implementation skips running when collection failed or collectonly is set, stops immediately on pytest.exit, and stops after the current item when session.shouldfail or session.shouldstop is set. pytest_runtest_protocol (firstresult) documents the default per-item order: logstart, then setup (runtest_setup wrapped in CallInfo(when="setup"), makereport, logreport, exception_interact on interactive exceptions), call only if setup passed and the setuponly option is unset, teardown (with nextitem enabling minimal finalizer teardown), then logfinish. pytest_runtest_setup runs setup() on the item and its not-yet-set-up parents including fixture setup; pytest_runtest_call's default calls item.runtest(); pytest_runtest_teardown runs finalizers and teardown on parents that need it. pytest_runtest_makereport (firstresult) creates the TestReport per phase; pytest_runtest_logstart/logfinish/logreport are notification points carrying nodeid plus a (filename, 0-based lineno, testname) location tuple relative to config.rootpath.

<a id="u-ec5feaa3e10f"></a>
### `hookspec-serialization-and-fixture-hooks`

`def pytest_report_to_serializable( config: Config, report: CollectReport | TestReport…` · [src/_pytest/hookspec.py:L825-L841][f1]

Hook specifications for report wire serialization and fixture lifecycle.

pytest_report_to_serializable (firstresult) converts a CollectReport or TestReport into a JSON-suitable dict; pytest_report_from_serializable (firstresult) restores it; both are implemented by whichever plugin performs the transport, so exact semantics depend on the caller. pytest_fixture_setup (firstresult) performs fixture setup and returns the fixture function's value; because firstresult only stops on non-None, implementations after a fixture that returns None keep being called. pytest_fixture_post_finalizer runs after fixture teardown but before the cache is cleared, so fixturedef.cached_result is still available at that moment.

<a id="u-a557ef7a305b"></a>
### `hookspec-session-reporting-and-error-hooks`

`def pytest_sessionstart(session: Session) -> None:` · [src/_pytest/hookspec.py:L922-L932][f1]

Hook specifications for session lifecycle, terminal reporting, skipping, and error/debug interaction.

Lifecycle: pytest_sessionstart fires after Session creation before collection (initial conftests only); pytest_sessionfinish fires after the whole run with the exit status about to be returned; pytest_unconfigure fires before process exit. Reporting: pytest_report_header and pytest_report_collectionfinish return header/post-collection strings (initial conftests / any conftest; lines from a plugin display before those of earlier plugins, so use trylast to appear first); pytest_report_teststatus (firstresult) returns category, shortletter, and verbose word, optionally a tuple like ("rerun", "R", ("RERUN", {"yellow": True})) for explicit styling; pytest_terminal_summary appends a terminal summary section. pytest_warning_recorded is historic and delivers captured warnings with when in {config, collect, runtest}, a nodeid (empty if not node-specific), and an optional location tuple. pytest_assertrepr_compare returns list-of-strings explanations for failing comparisons (newlines escaped, later lines indented); pytest_assertion_pass requires the enable_assertion_pass_hook ini option and clean .pyc files. pytest_markeval_namespace supplies globals for evaluating string xfail/skipif conditions at collection time. Error/debug: pytest_internalerror can return True to suppress the fallback INTERNALERROR print to sys.stderr; pytest_keyboard_interrupt handles KeyboardInterrupt/Exit; pytest_exception_interact fires for interactively handleable exceptions but not for internal ones like skip.Exception, with report being a CollectReport during collection or TestReport during runtest; pytest_enter_pdb and pytest_leave_pdb bracket pdb interactive mode. All bodies are docstring-only specifications.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/hookspec.py
