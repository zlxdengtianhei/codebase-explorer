# Pytest Codebase

**Capability.** pytest as a configurable, plugin-driven test framework, together with the low-level filesystem, assertion-reporting, and output infrastructure it relies on and the test corpus that pins its behavior.

Start here to orient: the config branch explains how an invocation is built, the cache/path/assertion branches provide supporting infrastructure, and the test branches record behavioral expectations. Each subtree can be read independently once the config pipeline is understood.

**Children.**

- [Package Version Metadata](r2-pkg-version.md) `r2-pkg-version` · 1 unit(s)
- [Configuration & Plugin Core](r2-config-core.md) `r2-config-core` · 0 unit(s)
- [Cross-Session Cache Provider](r2-cache-provider.md) `r2-cache-provider` · 19 unit(s)
- [Filesystem & Import Path Utilities](r2-path-utils.md) `r2-path-utils` · 0 unit(s)
- [Assertion Failure Reporting](r2-assertion-reporting.md) `r2-assertion-reporting` · 0 unit(s)
- [Terminal I/O & CLI Integration Plugins](r2-io-cli-plugins.md) `r2-io-cli-plugins` · 0 unit(s)
- [Test Corpus](r2-test-suite.md) `r2-test-suite` · 0 unit(s)

**Depends on.**

- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 220 edge(s)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 191 edge(s)
- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · within containment · 1 edge(s)

**Depended on by.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) · within containment · 18 edge(s)
- [Explanation Summary & Formatting](r2-explanation-formatting.md) · within containment · 16 edge(s)
- [Numbered Directory Creation & Cleanup](r2-path-numbered-dir-cleanup.md) · within containment · 1 edge(s)

Parent: [Configuration & Plugin Core](config-plugin-core.md)

## Units (39)

<a id="u-553e5ce7b807"></a>
### `collect_pytest_prefix-conftest`

`class pytest_something:` · [testing/example_scripts/config/collect_pytest_prefix/conftest.py:L4-L5][f1]

conftest defining an empty class named pytest_something, probing pytest's name-based collection rules: classes matching the test prefix in a conftest module should not be collected as tests.

**Uncertainties.**

- Whether pytest_something is collected or ignored is decided by upstream collection logic not present here.

<a id="u-96161f9e7350"></a>
### `create_executable-py`

`group` · [testing/freeze/create_executable.py:L1-L16][f2]

Builds a PyInstaller executable embedding a pytest runner.

The __main__ block calls pytest.freeze_includes(), turning each returned module into a --hidden-import pair, adds a --hidden-import distutils, and invokes 'pyinstaller --noconfirm ... runtests_script.py' through subprocess.check_call with shell=True. Any PyInstaller failure propagates as CalledProcessError; the script exits nonzero in that case.

**Notes.**

- side_effect: Writes build artifacts via pyinstaller and runs with shell=True command interpolation of collected names.

**Uncertainties.**

- Exact contents of pytest.freeze_includes() are defined in the pytest package, not this file.

<a id="u-64169582e0f4"></a>
### `fixture_mock_integration-py`

`def my_fixture():` · [testing/example_scripts/acceptance/fixture_mock_integration.py:L14-L17][f3]

Reproduces issue #3774 by combining unittest.mock with a function-scoped pytest fixture.

A module-level dict config starts with mykey='ORIGINAL'; the @mock.patch.dict decorator on my_fixture patches it to 'MOCKED' while the fixture body runs, so the fixture returns config['mykey'] as 'MOCKED', and test_foobar asserts that value. There is no error path in this source; the assertion is the whole check.

**Uncertainties.**

- The exact ordering of the patch exit versus fixture teardown is the behavior the script is designed to probe and is not determinable from this file alone.

<a id="u-06303cfd2b7e"></a>
### `fixtures.py-TestAutouseDiscovery`

`class TestAutouseDiscovery:` · [testing/python/fixtures.py:L1923-L1924][f4]

Tests discovery of autouse fixtures, with a class fixture that installs conftest fixtures: perfunction (autouse, uses tmp_path), arg1 (plain), perfunction2 (autouse, depends on arg1), plus fm and item accessors.

test_parsefactories_conftest asserts fm._getautousenames(item) lists exactly the two public autouse names. test_two_classes_separated_autouse confirms class-scoped autouse fixtures apply per class with independent values lists. test_setup_at_classlevel shows class-level autouse fixtures can stamp request.instance per method. test_setup_enabled_functionnode is xfail ('enabled' feature not implemented) but would test marker-driven conditional autouse activation. test_callables_nocode verifies a callable object whose __code__ is not a code object (a mock.call-like tuple subclass) does not crash discovery; the run reports 0 passed, 0 failed. test_autouse_in_conftests places a broken autouse fixture in a subdirectory conftest: tests inside that dir error at setup while the sibling directory's test passes ('1 passed 1 error'). test_autouse_in_module_and_two_classes pins ordering of module-level versus class-level autouse appends to a shared list across two classes.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917)

<a id="u-680cae1c1531"></a>
### `fixtures.py-TestAutouseManagement`

`class TestAutouseManagement:` · [testing/python/fixtures.py:L2101-L2102][f4]

Tests when and in what order autouse fixtures run.

test_autouse_conftest_mid_directory: an autouse fixture in a mid-tree package conftest applies to tests in subdirectories. test_funcarg_and_setup: a module-scoped autouse fixture depending on a module-scoped fixture creates the dependency first (values [1,2]) and caches across tests. test_uses_parametrized_resource: an autouse fixture depending on a parametrized fixture triggers two instantiations. test_session_parametrized_function: a function-scoped autouse fixture filtering by request.function records one append per session-scoped parameter. test_class_function_parametrization_finalization: combined class- and function-scoped parametrization produces finalizers in order fin_a1..fin_b2 for each of two classes, read from the conftest module after unconfigure. test_scope_ordering pins autouse setup order module→class→function ([1,3,2]); test_parametrization_setup_teardown_ordering pins class-scoped parametrize cycles completing (setup/step/teardown per parameter) before the next; test_ordering_autouse_before_explicit shows autouse fixtures run before explicitly requested same-scope fixtures; test_ordering_dependencies_torndown_first (issue 226, parametrized over with/without params on both fixtures) asserts dependency teardown order fin2 then fin1 regardless of parametrization. test_reordering_catastrophic_performance (issue 12355) runs a module-scoped 26-parameter parametrization three times and asserts 3 passes without slowdown.

<a id="u-2c4d431dc6c3"></a>
### `fixtures.py-TestContextManagerFixtureFuncs`

`class TestContextManagerFixtureFuncs:` · [testing/python/fixtures.py:L3863-L3864][f4]

Tests generator (yield) fixtures.

test_simple: setup code runs before the test body, the yielded value is injected, and teardown code runs after each test, even when the test fails (output shows setup/test2/teardown). test_scoped: a module-scoped yield fixture sets up once and tears down after the last consuming test. test_setup_exception: an exception before the yield produces an error referencing the pytest.fail('setup') call with '1 error' and no test run. test_teardown_exception: an exception after the yield lets the test pass but reports '1 passed 1 error' with the teardown failure. test_yields_more_than_one: a fixture yielding twice produces a 'fixture function' error; the output pattern '*test_yields*:2*' matches line 2 of the generated test file — the decorator/definition line of the fixture — which is the failure-surface line this source supports, not a yield line. test_custom_name: @pytest.fixture(name='meow') registers the fixture under the custom name and the test consumes it.

<a id="u-b5e19a568639"></a>
### `fixtures.py-TestErrors`

`class TestErrors:` · [testing/python/fixtures.py:L3482-L3483][f4]

Error-surface tests.

test_subfactory_missing_funcarg and test_setupfunc_missing_funcarg (autouse variant) both produce a non-zero exit with output pointing at 'def gen(qwe123):' and 'fixture qwe123 not found', one collection/setup error. test_issue498_fixture_finalizer_failing: a function-scoped fixture whose finalizer raises KeyError produces teardown errors for each test while all three tests still pass ('3 pass 2 errors'), and a third test confirms each test got a distinct fixture instance. test_cached_exception_doesnt_get_longer (issue 12204): a session-scoped fixture raising is cached; the test asserts three failures occur and that the second and third failure tracebacks have the same number of lines, i.e., the cached exception's representation does not accumulate per reuse.

<a id="u-3de09086896d"></a>
### `fixtures.py-TestFillFixtures`

`class TestFillFixtures:` · [testing/python/fixtures.py:L133-L135][f4]

End-to-end tests of fixture resolution, extension, and overriding using example files (pytester_example_path 'fixtures/fill_fixtures') or inline pytester projects.

Key behaviors asserted: an unknown fixture argument fails collection with a 'fixture ... not found' message listing available fixtures (test_funcarg_lookupfails, test_funcarg_lookup_error, which also checks no INTERNAL traceback appears); a recursive fixture dependency reports 'recursive dependency involving fixture'; direct setup via item.session._setupstate.setup fills funcargs with the declared values (test_funcarg_basic). Fixture extension/override precedence is covered across layers: module vs class, conftest vs module, conftest vs conftest in subdirectories, plugin vs conftest, and plugin vs plugin in loading order; parametrized fixtures overridden by non-parametrized ones collapse to one test, while the reverse yields 3 parametrized runs; autouse fixtures overridden by parametrized conftest fixtures reproduce issue 1601. Several tests pin that an overriding fixture can request the higher-level parametrized fixture and that request.param equals the parametrize value even with indirect parametrization (issue 1953 variants). test_autouse_fixture_plugin covers autouse fixtures from plugins lacking baseid; test_fixture_excinfo_leak asserts sys.exc_info() is clean inside fixture and test execution.

uses: [Pytester.copy_example](r6-pytester-core.md#u-c15c0894e320), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

**Uncertainties.**

- Exact error-message wording of the fixture machinery is only asserted via fnmatch patterns in the embedded example files, whose contents are not in this batch

<a id="u-2a4e68ea702b"></a>
### `fixtures.py-TestFixtureManagerParseFactories`

`class TestFixtureManagerParseFactories:` · [testing/python/fixtures.py:L1683-L1684][f4]

Tests the fixture manager's parsefactories through a fixture that writes a conftest exposing fm (request._fixturemanager) and item (request._pyfuncitem).

test_parsefactories_evil_objects_issue214 confirms objects with hostile __getattr__/__call__ do not break collection. test_parsefactories_conftest asserts each conftest fixture resolves via fm.getfixturedefs to exactly one definition whose func matches the name. test_parsefactories_conftest_and_module_and_class asserts three layered definitions of 'hello' in order conftest, module, class. test_parsefactories_relative_node_ids uses a package/subpackage layout where 'one' resolves to 1 then 2, and re-runs from a different cwd with a relative path ('..') still passing both tests. Package tests: test_package_xunit_fixture checks package-level setup_module/teardown_module append and clear shared values so each package's test sees only its own marker; test_package_fixture_complex verifies package-scoped and package-scoped-autouse yield fixtures in a package conftest with ordering assertions on shared values. test_collect_custom_items collects a copied example with custom item types via runpytest('foo').

<a id="u-4629a1571a11"></a>
### `fixtures.py-TestFixtureMarker`

`class TestFixtureMarker:` · [testing/python/fixtures.py:L2375-L2376][f4]

Tests @pytest.fixture parametrization, scoping, and lifecycle.

Parametrization: params multiply tests (3 params + result test = 4; cross-product with @parametrize gives 9); overriding a parametrized fixture via parametrize accepts string, list, or tuple arg-name forms (issue 979 regression); module/class parametrized fixtures yield separated value sequences ([1,1,2,2]) with per-parameter lifecycles and finalizer ordering verified through shared lists. Scope: module scope caches across tests and classes (values appended once); a session-scoped fixture calling pytest.skip skips dependents while later tests observe exactly one setup (three variants, including two chained fixtures where the dependent never runs); a session fixture shared across two modules is created once (reqs == [1]). Scope mismatch: a session fixture depending on a function-scope one (directly, dynamically via getfixturevalue on an already-computed fixture, or via redefinition) yields ScopeMismatch errors with source line pointers. Dynamic scope: a callable scope consulted with the fixture name and config returns 'function' or 'session' (--extend-scope option), changing caching so the second run has 1 passed/1 failed; an invalid returned scope reports "got an unexpected scope value". Ordering tests use console_output_style=classic and pin exact -v output for session→module parametrization interleaving across two modules, plugin-registered fixtures with autouse (flavor×encap), class ordering with function params (TestClass2 a-1..b-2 then TestClass), and a precise 36-entry create/fin event sequence showing higher-scope fixtures outliving function-scope ones (test_parametrize_separated_order_higher_scope_first). Class-scoped autouse classmethod fixtures tear down in reverse (values popped 2 then 1). Further: overridden fixture finalizers still run (test_fixture_finalizer with subdir override); class-scope fixtures apply across plain module tests; request.param is clean per parametrize iteration; finalizers of function-scoped parametrized fixtures run between iterations ([1,fin1,2,fin2] twice); finalizer order on parametrization holds at session/function/module scopes (issue 246); class-scope parametrization tears down per class (issue 396); autouse setup finalizers sequence per parameter; @pytest.fixture-decorated test_ functions are not collected as tests; explicit ids label parametrized runs ('alpha','beta') for both return and yield fixtures; and PYTHONHASHSEED changes do not alter collected test IDs (12 identical output lines across two subprocess runs).

<a id="u-f8cbdcc3cefa"></a>
### `fixtures.py-TestFixtureUsages`

`class TestFixtureUsages:` · [testing/python/fixtures.py:L1221-L1222][f4]

Broad coverage of fixture usage semantics.

Basic chaining and caching: fixtures receive other fixtures (test_receives_funcargs); a function-scoped fixture requested by a module-scoped fixture triggers ScopeMismatch errors with 'Requesting fixture stack' details (two variants, including one where the test itself requests the narrower fixture); an unknown scope string reports "got an unexpected scope value 'functions'"; parameters lacking __eq__ semantics (raising or returning a falsy-raising object) do not break parametrization under function or session scope. test_funcarg_parametrized_and_used_twice shows parametrized values instantiate once per parameter. Error surfaces: a fixture depending on a missing name produces a stacked error listing both fixture definitions; a class used as a fixture factory fails collection once. usefixtures: class-level marker runs a class-scoped fixture once and sets request.cls attributes; an empty usefixtures() warns 'without arguments has no effect' (issue 12439); ini-file usefixtures works; --markers shows the usefixtures help. test_request_instance_issue203 asserts self is request.instance in class fixtures. Iterator params are consumed at decoration time producing [1,2,10,20] ordering. test_setup_functions_as_fixtures (issues 517/3094) shows xunit setup hooks run inside session-scoped autouse fixture lifetimes. test_parameterized_fixture_caching (issue 12600) uses unique list objects and a session-scoped fixture to assert exactly two cache misses, i.e., no re-instantiation per test. test_unwrapping_pytest_fixture and test_fixture_wrapped_looks_liked_wrapped_function verify the fixture wrapper exposes _get_wrapped_function (returning bound methods or functions) and propagates __doc__.

<a id="u-cc5c4b6437d1"></a>
### `fixtures.py-TestParameterizedSubRequest`

`class TestParameterizedSubRequest:` · [testing/python/fixtures.py:L3992-L3993][f4]

Tests error reporting when request.getfixturevalue requests a parametrized fixture without an active parameter.

All four tests build a params=[0,1,2] fixture 'fix_with_param' and request it via getfixturevalue either from another fixture (test_call_from_fixture, yielding a setup error) or directly from the test (test_call_from_test, test_external_fixture with a conftest-defined fixture, and test_non_relative_path with the fixture in a separate, sys.path-inserted directory, all yielding failures). The error message includes 'The requested fixture has no parameter defined for test:', the test node id, the defining file and line, and a 'Requested here:' pointer. test_non_relative_path additionally changes cwd and reruns with an explicit --rootdir and the tests directory, asserting the message now points at the absolute fix.py path and the absolute test file location; both variants end with '1 failed'.

<a id="u-a9e755ceba33"></a>
### `fixtures.py-TestRequestBasic`

`class TestRequestBasic:` · [testing/python/fixtures.py:L679-L680][f4]

Tests TopRequest and FixtureRequest behavior.

test_request_attributes builds an item and checks request.function/keywords/module/cls/config and that repr contains the test name; test_request_attributes_method checks req.cls and req.instance for a class-based test; test_request_contains_funcarg_arg2fixturedefs verifies _arg2fixturedefs holds the fixture definition with matching argname. test_getfixturevalue runs item setup directly and asserts: unknown names raise FixtureLookupError; repeated getfixturevalue calls return cached values; funcargs is populated including 'request'. Finalizer tests: addfinalizer callbacks run only at teardown_exact (test_request_addfinalizer); finalizers registered before a failing setup still run (failing_setup variants, including module scope where both finalizers pop values); a partially failed setup makes the whole module collection fail ('1 error'); exceptions from multiple finalizers are deferred and re-raised as an ExceptionGroup naming the subrequest fixture, in declared-finalizer reverse order with values [3,2,1] (issue 2440). test_getfixturevalue_recursive shows a shadowing fixture calling getfixturevalue on the conftest-level same-name fixture; test_getfixturevalue_teardown documents that getfixturevalue dependencies do not affect teardown ordering (resource is torn down before inner). test_request_garbage (skipped on pypy, xfail under xdist) runs in a subprocess with gc.DEBUG_SAVEALL to assert no PseudoFixtureDef leaks; test_request_fixturenames and its dynamic-fixture regression assert the public fixture-name list; test_setupdecorator_and_xunit pins autouse setup ordering module→function→class→method; test_fixtures_sub_subdir_normalize_sep checks --fixtures output for subdir conftests; test_show_fixtures_color_yes checks ANSI-colored output; test_setupcontext_no_param asserts autouse setup requests see no request.param under parametrization.

uses: [class::TopRequest][f5], [pytester-inline-run](r6-pytester-run.md#u-2e2ff834e74d)

<a id="u-3f7a9c99ad09"></a>
### `fixtures.py-TestRequestMarking`

`class TestRequestMarking:` · [testing/python/fixtures.py:L1150-L1151][f4]

Tests marker application and access through the request.

test_applymarker constructs TopRequest objects, asserts applymarker(pytest.mark.xfail) and applymarker(pytest.mark.skipif) add the corresponding entries to item.keywords, and that applymarker(42) raises ValueError. test_accesskeywords runs an inline test whose fixture returns request.keywords, checking a statically applied @pytest.mark.XYZ is visible and unrelated keys are absent. test_accessmarker_dynamic applies a class-scoped autouse fixture calling request.applymarker(pytest.mark.XYZ('hello')), asserting both class tests observe the dynamic marker via their keywords fixture.

<a id="u-b8f3aa38d9f0"></a>
### `fixtures.py-TestRequestScopeAccess`

`class TestRequestScopeAccess:` · [testing/python/fixtures.py:L3430-L3441][f4]

Parametrized at class level via pytestmark over (scope, ok, error) combinations: session-scope requests may access only session/config-level attributes (path, class, function, module raise AttributeError); module scope adds module and path; class scope adds cls; function scope can access all.

test_setup exercises this via an autouse fixture and test_funcarg via an explicitly requested fixture; both generated snippets assert hasattr for allowed names, expect AttributeError via getattr for forbidden ones, and confirm request.session and request.config always exist. Each variant run must report 1 passed.

<a id="u-ea841b3684cf"></a>
### `fixtures.py-TestRequestSessionScoped`

`class TestRequestSessionScoped:` · [testing/python/fixtures.py:L1136-L1137][f4]

Verifies that session-scoped requests raise AttributeError with the message '<name> not available in session-scoped context' when accessing path or module.

The class defines a session-scoped fixture returning the request itself; the single test is parametrized over the two attribute names and asserts via pytest.raises with a matching message, using getattr to trigger the lookup.

<a id="u-31e8c9b9e039"></a>
### `fixtures.py-TestScopeOrdering`

`class TestScopeOrdering:` · [testing/python/fixtures.py:L4187-L4190][f4]

Pins that request.fixturenames is ordered by scope (session→package→module→class→function) with autouse and same-scope fixtures ordered root-first, then declared order (issues 2405 and related).

test_func_closure_module_auto runs two semantically identical variants (env-selected 'mark' via pytestmark usefixtures, or 'autouse') asserting ['m1','f1']; an unknown/missing variant env falls back to 'mark' with a warning in the generated module. test_func_closure_with_native_fixtures additionally runs the tests and compares declared closure order (s1 my_tmp_path_factory p1 m1 f1 f2 my_tmp_path) against actual execution order recorded via a monkeypatched pytest.FIXTURE_ORDER list, showing dependency-driven reordering (my_tmp_path executes before f1). test_func_closure_module, test_func_closure_scopes_reordered, test_func_closure_same_scope_closer_root_first (conftest/sub-conftest/test module autouse ordering p_sub, m_conf, m_sub, m_test, then f1), and test_func_closure_all_scopes_complex (s1 p1 m1 m2 c1 f2 f1) each construct TopRequest on the first collected Function and assert the exact fixturenames list. test_parametrized_package_scope_reordering (issue 12328) uses --setup-plan to show a package-scoped parametrized fixture groups both test modules per parameter before tearing down. test_multiple_packages builds two sibling packages with package-scoped yield fixtures over a shared values list, asserting each package's setup/teardown bracket only its own tests. test_class_fixture_self_instance (issue 2270) registers a plugin class whose fixture asserts self is the plugin instance and returns its attribute.

uses: [class::TopRequest][f5]

<a id="u-24c4e51f45bf"></a>
### `fixtures.py-TestShowFixtures`

`class TestShowFixtures:` · [testing/python/fixtures.py:L3571-L3572][f4]

Tests the --fixtures output.

test_funcarg_compat asserts --funcargs maps to option.showfixtures; test_show_help combines --fixtures with --help successfully. Basic listings include built-in tmp_path/tmp_path_factory with scope annotations and source paths in both normal and -v modes. test_show_fixtures_testmodule: module fixtures with docstrings are listed (arg1 with 'hello world') while underscore-prefixed _arg0 is hidden. test_show_fixtures_conftest lists conftest fixtures whether or not a test module exists (parametrized). Docstring rendering tests assert trimming of surrounding whitespace/blank lines and preservation of internal indentation, including when the first line starts unindented, and inside classes; source line numbers in the header point at the fixture definition line. test_show_fixtures_different_files (issue 833) asserts fixtures from each collected file are shown under separate 'fixtures defined from <file>' headers. test_show_fixtures_with_same_name lists both conftest and module definitions of arg1 with their distinct docstrings. test_fixture_disallow_twice asserts applying @pytest.fixture twice to a function raises ValueError immediately at decoration time.

<a id="u-6586668caec9"></a>
### `fixtures.py-getfuncargnames-tests`

`def test_getfuncargnames_functions():` · [testing/python/fixtures.py:L20-L23][f4]

Verifies getfuncargnames argument extraction across callable shapes.

For plain functions: no args yields an empty tuple, one positional arg yields ('arg',), and parameters with defaults are dropped (h yields ('arg1',), j yields ('arg1','arg2')). For methods: self is excluded regardless of positional-only markers, keyword-only markers, or combinations (k with positional-only self yields ('arg1','arg2')). For staticmethods, the test passes cls=A so the wrapped function's args are returned without a self drop; the inherited-staticmethod case confirms this works through subclassing (B.static with cls=B). For functools.partial bound as a class attribute (and its staticmethod-wrapped variant), the call passes name='test_ok' and expects the partial's remaining parameters ('arg1','arg2') since i is keyword-bound. The partial-on-Python-<3.13 case is skipped on 3.13+, where partial becomes a method descriptor and would emit FutureWarning; the wrapped-partial behavior is instead covered by the staticmethod_partial test. All bodies raise NotImplementedError, so only signature inspection is exercised.

uses: [function::getfuncargnames](../../catalog.json)

**Uncertainties.**

- Exact failure behavior when getfuncargnames cannot resolve a callable is not exercised here

<a id="u-7bf4a627def0"></a>
### `fixtures.py-module-level-test-functions`

`def test_call_fixture_function_error():` · [testing/python/fixtures.py:L4566-L4569][f4]

Module-level tests covering API errors, ordering, and regression cases.

test_call_fixture_function_error: calling a fixture-decorated function directly raises pytest.fail.Exception (issue 4545). test_fixture_double_decorator: double @pytest.fixture in a collected file yields one error with 'ValueError: @pytest.fixture is being applied more than once to the same function'; test_fixture_class: decorating a class yields one collection error. test_fixture_param_shadowing (issue 5036): a direct @parametrize on 'arg' shadows the identically named fixture (only test_direct runs with [1]), the fixture-based test runs per fixture parameter [a,b], and indirect parametrize still multiplies by its own param (4 passed total). test_fixture_named_request: a fixture named 'request' errors with a reserved-word message pointing at the defining line. test_indirect_fixture_does_not_break_scope (issue 570): session-scoped indirect fixtures instantiate in the parametrized grouping order, verified by an exact instantiation list. test_fixture_parametrization_nparray (skipped without numpy): numpy linspace params yield 10 passes. test_fixture_arg_ordering (issues 6540/6492): same-scope fixtures instantiate in declaration order when combined. test_yield_fixture_with_no_value: a yield fixture whose yield never runs errors with 'ValueError: custom did not yield a value' and ExitCode.TESTS_FAILED. test_deduplicate_names: deduplicate_names preserves first-occurrence order ('abacd'→'abcd'; extended tuple deduplicated). test_staticmethod_classmethod_fixture_instance (issue 12065): static/class-method tests receive a fresh instance where setup_method and an autouse fixture have run (3 passed). test_scoped_fixture_caching: class-scoped yield fixture sets up once and tears down after the class. test_scoped_fixture_caching_exception: a class-scoped fixture raising has its finalizer run once despite cached failure (xfail-marked dependents). test_scoped_fixture_teardown_order (issue 1489) and test_subfixture_teardown_order (issue 12135): teardowns occur in reverse setup order when later tests re-request cached scoped fixtures, without re-scheduling finalizers; exact global-order lists are asserted. test_parametrized_fixture_scope_allowed (issue 13248): scope='function' in parametrize does not block session-scoped fixture dependency resolution. test_pytest_fixture_setup_and_post_finalizer_hook: pytest_fixture_setup/pytest_fixture_post_finalizer hooks fire for both the tests/ conftest and the root conftest in that order, around the fixture and test, verified by -s output patterns.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346); calls: [function::deduplicate_names][f5]

<a id="u-1f98d12dd273"></a>
### `generate_folders-py`

`def generate_folders(root, elements, *more_numbers):` · [testing/example_scripts/perf_examples/collect_stats/generate_folders.py:L15-L26][f6]

Generates a tree of test files for collection-performance measurement.

Module level reads template_test.py bytes as TEST_CONTENT and builds an argparse parser taking zero-or-more integers. generate_folders recurses: with more_numbers non-empty it creates, for each i in range(elements), a zero-padded folder foo_<i> under root (mkdir on an existing folder raises), writes TEST_CONTENT as __init__.py inside, and recurses with the remaining numbers; once numbers are exhausted it writes TEST_CONTENT to test_<i>.py files directly under root. The __main__ block runs generate_folders(HERE, *(args.numbers or (10, 100))), so no arguments yields a 10x100 tree.

calls: [path-localpath-fs-ops](r6-path-fs.md#u-7a1651f068dd); contract: [template_test-py](r7-misc-examples.md#u-339860a12060)

**Uncertainties.**

- Zero-padding format of folder and test names (fill widths) is inferred from the f-string usage and not further verifiable here.

<a id="u-fa7228b56a07"></a>
### `package_infinite_recursion-conftest`

`def pytest_ignore_collect(collection_path):` · [testing/example_scripts/collect/package_infinite_recursion/conftest.py:L5-L6][f7]

conftest whose pytest_ignore_collect hook returns False unconditionally, so no collection path is ever ignored from this file; collection proceeds normally, supporting the infinite-recursion regression scenario.

<a id="u-ba0e1244c6c5"></a>
### `pathlib.py-register-cleanup-lock-removal`

`def register_cleanup_lock_removal( lock_path: Path, register: Any = atexit.register )…` · [src/_pytest/pathlib.py:L263-L269][f8]

register_cleanup_lock_removal registers a lock-removal callback via the supplied register function (atexit.register by default) and returns its result.

The callback captures the lock path and PID as default arguments; at call time it returns without touching the lock if the current PID differs (forked child), otherwise unlinks the lock file and suppresses any OSError. The nested cleanup_on_exit and the split function segments implement exactly this callback and registration.

uses: [PytestPluginManager.register](r2-config-plugin-manager.md#u-ab6cdde49ec4)

**Uncertainties.**

- The graph shows a call from the s1 segment into PytestPluginManager.register, but this file only shows the default atexit.register; whether a plugin manager registrar is passed is not visible here.

<a id="u-78d240d1756e"></a>
### `runtests_script-py`

`group` · [testing/freeze/runtests_script.py:L1-L14][f9]

Entry point frozen into the executable: when run as __main__, imports pytest and exits with sys.exit(pytest.main()), delegating the process exit code to the pytest run of whatever arguments the frozen environment supplies.

**Uncertainties.**

- The arguments pytest.main() receives depend on the frozen environment and are not visible here.

<a id="u-066911b3d9de"></a>
### `set-comparators`

`def _compare_eq_set( left: AbstractSet[Any], right: AbstractSet[Any], highlighter: _H…` · [src/_pytest/assertion/util.py:L429-L438][f10]

Set-oriented comparison helpers built on _set_one_sided_diff.

_compare_eq_set reports extra items on both sides ('Extra items in the left set:' / 'right set:' with each item repr'd via saferepr through the highlighter). _compare_gte_set delegates to a one-sided diff of right-minus-left (items in right that make '>=' fail) and _compare_lte_set to left-minus-left analog for '<='; _compare_gt_set and _compare_lt_set wrap those respectively, and when the underlying diff is empty they return ['Both sets are equal'] instead of an empty list — the explanation for 'left > right' failing when the sets are actually equal. _set_one_sided_diff computes set1 - set2 and appends a header plus one highlighted saferepr line per extra item, returning an empty list when the difference is empty.

**Notes.**

- condition: For '>=', items listed come from right-minus-left because a right-only extra item is what breaks left >= right.

calls: [set-comparators](r2-pytest-root.md#u-066911b3d9de)

**Uncertainties.**

- _compare_gt_set/_compare_lt_set accept and ignore a verbose parameter; verbose never changes their output.

<a id="u-785b38f87501"></a>
### `test_1.py`

`def func(msg):` · [testing/example_scripts/warnings/test_group_warnings_by_message_summary/test_1.py:L9-L10][f11]

Same warning-emitting pattern as the non-summary sibling, scaled up: func(msg) raises UserWarning; test_foo and test_bar are parametrized over range(20) emitting 'foo' and 'bar', and test_foo_1 emits 'foo' once.

All tests pass; module-level func is also importable, which test_2 in the same package reuses.

<a id="u-d82d3d056098"></a>
### `test_compare_dataclasses.py`

`def test_dataclasses() -> None:` · [testing/example_scripts/dataclasses/test_compare_dataclasses.py:L7-L8][f12]

Verifies that pytest assertion rewriting reports dataclass field comparisons.

Inside test_dataclasses a local @dataclass SimpleDataObject defines field_a: int and field_b: str; two instances are built with equal field_a but different field_b, and 'assert left == right' intentionally fails, exercising how the rewritten comparison renders dataclass contents.

**Uncertainties.**

- The batch shows the assert, not the pytest hook that formats the failure; how the output is rendered lies outside this source.

<a id="u-516ad480a9fa"></a>
### `test_compare_dataclasses_field_comparison_off.py`

`def test_dataclasses_with_attribute_comparison_off() -> None:` · [testing/example_scripts/dataclasses/test_compare_dataclasses_field_comparison_off.py:L7-L8][f13]

Checks dataclass comparison when a field is excluded via field(compare=False).

The local SimpleDataObject marks field_b as non-comparing, so two instances differing only in field_b compare equal; the final 'assert left == right' passes, demonstrating that compare=False suppresses field_b in the generated __eq__.

<a id="u-b8d7a49f0495"></a>
### `test_compare_dataclasses_with_custom_eq.py`

`def test_dataclasses() -> None:` · [testing/example_scripts/dataclasses/test_compare_dataclasses_with_custom_eq.py:L7-L8][f14]

Exercises dataclass equality with a user-defined __eq__ that delegates to super().

The local SimpleDataObject overrides __eq__ to call the dataclass-generated implementation; instances differing in field_b therefore still compare unequal, and 'assert left == right' fails, testing assertion rewriting against custom __eq__ rather than the default object identity path.

<a id="u-cfc36778ecdc"></a>
### `test_compare_two_different_dataclasses.py`

`def test_comparing_two_different_data_classes() -> None:` · [testing/example_scripts/dataclasses/test_compare_two_different_dataclasses.py:L7-L8][f15]

Verifies that distinct dataclass types never compare equal even with matching field values.

Inside the test, SimpleDataObjectOne and SimpleDataObjectTwo share the same field layout; left (One) and right (Two) hold equal data, yet 'assert left != right' passes because dataclass __eq__ also compares class identity. The comparison-overlap type-ignore comment silences mypy for the intentional cross-type comparison.

<a id="u-7c6d3d51b179"></a>
### `test_extend_fixture_conftest_module.py`

`def spam(spam):` · [testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_module/test_extend_fixture_conftest_module.py:L7-L9][f16]

Demonstrates a module-level fixture extending a conftest fixture of the same name.

The module's spam(spam) receives the conftest-provided 'spam' and returns 'spamspam'; test_spam(spam) then asserts the doubled value, so the test passes only when the override chain (conftest first, module second) resolves in that order.

<a id="u-428fc2342cf8"></a>
### `test_funcarg_lookup_classlevel.py`

`class TestClass:` · [testing/example_scripts/fixtures/fill_fixtures/test_funcarg_lookup_classlevel.py:L7-L8][f17]

Verifies class-level fixture lookup and instance identity.

TestClass.something is a fixture returning request.instance, the instance of the test class being run; test_method(something) asserts something is self, which holds only when the fixture is resolved from the class and the requesting test is an instance method of TestClass.

<a id="u-1da70f140279"></a>
### `test_getfixturevalue_dynamic.py`

`def dynamic():` · [testing/example_scripts/fixtures/test_getfixturevalue_dynamic.py:L7-L9][f18]

Checks how dynamically resolved fixtures appear in request.fixturenames.

Fixture a calls request.getfixturevalue("dynamic") at setup time, and b depends on a; test(b, request) asserts the exact order request.fixturenames == ["b", "request", "a", "dynamic"], so the example passes only when the dynamically fetched 'dynamic' is appended after statically declared dependencies. dynamic itself returns None.

calls: [FixtureRequest](r5-fixture-request-context.md#u-e8edbc928469)

<a id="u-14580cbdce1b"></a>
### `test_pprint.py-dataclass-fixtures`

`class EmptyDataclass:` · [testing/io/test_pprint.py:L18-L20][f19]

Three tiny @dataclass fixtures provide empty, single-field, and two-field instances used as PrettyPrinter inputs; they carry no behavior beyond the generated dataclass constructor and repr.

<a id="u-8f6d64d0aa18"></a>
### `test_unittest_asyncio.py`

`class AsyncArguments(IsolatedAsyncioTestCase):` · [testing/example_scripts/unittest/test_unittest_asyncio.py:L10-L11][f20]

Exercises IsolatedAsyncioTestCase with async test methods and teardown accounting.

AsyncArguments defines asyncTearDown appending to the module-level teardowns list; test_something_async awaits a local addition(2, 2) coroutine and asserts the sum is 4 (passes), test_something_async_fails asserts the same sum is 3 (fails), and the synchronous test_teardowns asserts len(teardowns) == 2, which holds only if exactly the two async tests ran their asyncTearDown before it executes.

**Uncertainties.**

- Each test method defines its own local addition, so the call addition(2, 2) in the graph is ambiguous between them; behavior is identical either way.
- test_teardowns depends on execution ordering of the three tests, which the file itself does not enforce.

<a id="u-59f8a608b275"></a>
### `test_unittest_plain_async.py`

`class Test(unittest.TestCase):` · [testing/example_scripts/unittest/test_unittest_plain_async.py:L7-L8][f21]

Shows the failure mode of declaring an async method on a plain unittest.TestCase: Test.test_foo is a coroutine function whose body is 'assert False'.

A stock unittest runner cannot await it, so the assertion may never execute and the outcome depends on how the runner handles a returned un-awaited coroutine.

**Uncertainties.**

- Whether test_foo is reported as failing, passing, or warning is decided by runner coroutine handling outside this file.

<a id="u-481f94097d33"></a>
### `truncate-py-module-residual`

`module_region` · [src/_pytest/assertion/truncate.py:L1-L18][f22]

Header of truncate.py: module docstring describing default truncation at terminal lines unless assertions verbosity >= 2 or CI, plus imports (util, Config, Item) and the constants DEFAULT_MAX_LINES = 8, DEFAULT_MAX_CHARS = 640, and USAGE_MSG = "use '-vv' to show" used by truncation messaging.

<a id="u-748323ffaa84"></a>
### `type-predicates`

`def issequence(x: Any) -> bool:` · [src/_pytest/assertion/util.py:L121-L122][f10]

Small type-classification helpers used to choose comparison strategies in _compare_eq_any and assertrepr_compare.

issequence matches collections.abc.Sequence excluding str; istext matches str; isdict matches dict; isset matches set or frozenset; isnamedtuple matches a tuple exposing a non-None _fields; isdatacls matches objects with __dataclass_fields__; isattrs matches objects with __attrs_attrs__; all return bools from isinstance/getattr checks with no side effects. isiterable is different: it attempts iter(obj) and returns True when iteration succeeds and the object is not a str, returning False on any Exception raised by iter, so objects with broken __iter__ are treated as non-iterable rather than propagating the error.

<a id="u-770d7415ac50"></a>
### `util-py-module-residual`

`class _HighlightFunc(Protocol):` · [src/_pytest/assertion/util.py:L41-L42][f10]

Header of util.py: module docstring, imports (collections.abc views, os, pprint, dataclasses deferred in functions, typing, unicodedata.normalize, _pytest.outcomes, _pytest._code, the _io pprint/saferepr helpers, Config), and three module-level hook globals: _reprcompare (comparison hook invoked by the assertion rewriter), _assertion_pass (populated per-test by pytest_runtest_protocol when the assertion-pass hook is enabled), and _config (the current item's Config during a test).

These globals are the channel through which the rewrite module reaches the plugin hooks; all default to None.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/config/collect_pytest_prefix/conftest.py
[f2]: ../../../../../../eval/pytest-5989efe/testing/freeze/create_executable.py
[f3]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/acceptance/fixture_mock_integration.py
[f4]: ../../../../../../eval/pytest-5989efe/testing/python/fixtures.py
[f5]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
[f6]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/perf_examples/collect_stats/generate_folders.py
[f7]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/collect/package_infinite_recursion/conftest.py
[f8]: ../../../../../../eval/pytest-5989efe/src/_pytest/pathlib.py
[f9]: ../../../../../../eval/pytest-5989efe/testing/freeze/runtests_script.py
[f10]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/util.py
[f11]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/warnings/test_group_warnings_by_message_summary/test_1.py
[f12]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_dataclasses.py
[f13]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_dataclasses_field_comparison_off.py
[f14]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_dataclasses_with_custom_eq.py
[f15]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/dataclasses/test_compare_two_different_dataclasses.py
[f16]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_extend_fixture_conftest_module/test_extend_fixture_conftest_module.py
[f17]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/fill_fixtures/test_funcarg_lookup_classlevel.py
[f18]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/fixtures/test_getfixturevalue_dynamic.py
[f19]: ../../../../../../eval/pytest-5989efe/testing/io/test_pprint.py
[f20]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_unittest_asyncio.py
[f21]: ../../../../../../eval/pytest-5989efe/testing/example_scripts/unittest/test_unittest_plain_async.py
[f22]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/truncate.py
