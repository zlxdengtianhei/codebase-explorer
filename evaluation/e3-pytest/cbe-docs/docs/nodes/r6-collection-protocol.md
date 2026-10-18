# Session and Node Protocol

**Capability.** Tests collector node semantics: initial-node parent chains, session collection protocol, item generation, custom from_parent keyword forwarding, directory-collection and collect-file hook relays, node keywords, and double collection of one file.

Use it when changing Collector/Session/Node internals or hook contracts. These tests often construct custom Collector subclasses to probe factory forwarding.

**Depends on.**

- [Test Run Invocation](r6-pytester-run.md) · graph-confirmed · 37 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 29 edge(s)

Parent: [Collection Suite](r6-test-collection.md)

## Units (10)

<a id="u-abc8958119bf"></a>
### `TestSession`

`class TestSession:` · [testing/test_collection.py:L497-L498][f1]

Session collection protocol.

test_collect_topdir parses a config from 'file.py::test_func', builds Session.from_config, and asserts perform_collect on the root nodeid returns one item whose path is the rootdir. get_reported_items extracts pytest.Item instances from pytest_collectreport hook call reports. test_collect_protocol_single_function generates items for the single-function nodeid and asserts the exact hook sequence (collectstart/make_collect_report for topdir and file, pycollect_makeitem, collectreport) and that the report contains only that item. test_collect_protocol_method shows nodeids at file, class, and method granularity all produce one item with the normalized method nodeid. test_collect_custom_nodes_multi_id adds a conftest SpecialFile yielding an extra SpecialItem and shows collecting the file nodeid produces 2 items and 2 reported items with the expected hook calls. test_collect_subdir_event_ordering and test_collect_two_commandline_args assert per-directory collectstart/report event pairs in argument order. test_serialization_byid regenerates items from a saved nodeid with matching name and path. test_find_byid_without_instance_parents confirms a class-method nodeid collects one reported item. test_collect_parametrized_order asserts parametrized ids appear in declaration order [0],[1],[2].

<a id="u-ff332212482b"></a>
### `Test_genitems`

`class Test_genitems:` · [testing/test_collection.py:L723-L724][f1]

Item generation.

test_check_collect_hashes duplicates a module file, collects 4 items from the directory, and asserts pairwise distinct identity and hash. test_example_items1 collects a module with a function, a class, and a subclass with a parametrized method, asserting item names, getmodpath values (including inherited-class paths and the '[.[' parametrized id), and getmodpath(stopatmodule=False) ending in 'module.testone'. test_classmethod_is_discovered shows a @classmethod test is collected with modpath 'TestCase.test_classmethod'. test_class_and_functions_discovery_using_glob configures python_classes=*Suite Test and python_functions=*_test test and shows glob/prefix patterns select MyTestSuite.x_test and TestCase.test_y.

<a id="u-37e5e186ae4a"></a>
### `Test_getinitialnodes`

`class Test_getinitialnodes:` · [testing/test_collection.py:L685-L686][f1]

Initial-node parent chains.

test_global_file collects x.py at the rootdir and asserts the chain is Module -> (Dir/parent) -> Session, that the Session's parent is None, and every node in listchain shares the same config. test_pkgfile places x.py with __init__.py in subdir, configures while chdir'ed into subdir, and asserts the chain Module -> Package -> Session with Session parentless, all sharing the config.

<a id="u-06a18e27127e"></a>
### `TestCollector`

`class TestCollector:` · [testing/test_collection.py:L33-L34][f1]

Verifies pytest collector-node semantics.

test_collect_versus_item asserts neither pytest.Collector nor pytest.Item subclasses the other. test_check_equality collects a module and shows two collections of test_pass are equal and hash-equal, differ from test_fail, modules, and unrelated values (3, [1,2,3]), and collecting a missing name returns None. test_getparent_and_accessors checks getparent(Module/Class/Function) resolution and that module/cls/instance/function accessors are non-None only at the correct chain depth (module has cls and instance None; class has instance None). test_getcustomfile_roundtrip registers a conftest pytest_collect_file hook returning a custom pytest.File for .xxx files and confirms re-collection of the node's nodeid yields exactly one File. test_can_skip_class_with_test_attr runs pytest on a class with __test__=False and expects 'collected 0 items'.

<a id="u-d0bf04c6aa2b"></a>
### `TestNodeKeywords`

`class TestNodeKeywords:` · [testing/test_collection.py:L860-L861][f1]

Node keyword behavior.

test_no_under collects a module and asserts every keyword lacks a leading underscore, the module name is present, and repr includes the name. test_issue345 shows -k repr selects test___repr__ but not the failing test. test_keyword_matching_is_case_insensitive_by_default mixes mixed-case test names and markers and asserts -k with 'specifictopic', 'SPECIFICTOPIC', or 'SpecificTopic' each selects the same 4 tests, excluding the failing one. test_duplicates_handled_correctly sets module/class/item-level 'kw' (mark, mark, string) and asserts the item's keyword resolves to 'method' with no duplicate keys. test_unpacked_marks_added_to_keywords gives module mark foo, class mark bar, and function pytestmark baz, and asserts item keywords contain all three, class keywords foo and bar only, and module keywords foo only.

<a id="u-32d29b8bf465"></a>
### `TestCollectDirectoryHook`

`class TestCollectDirectoryHook:` · [testing/test_collection.py:L975-L976][f1]

pytest_collect_directory hook behavior.

test_custom_directory_example copies the customdirectory example, runs it inline expecting 2 passed, and asserts the hook fired twice: first for the rootdir with a pytest.Session parent, then for tests/ with a pytest.Dir parent. test_directory_ignored_if_none installs a wrapper hook returning None and asserts the affected directory contributes no passed or failed outcomes.

<a id="u-7fb9963a2ed0"></a>
### `TestCollectPluginHookRelay`

`class TestCollectPluginHookRelay:` · [testing/test_collection.py:L280-L281][f1]

test_pytest_collect_file registers an inline plugin whose pytest_collect_file records every file path whose name does not start with '.' (hidden files like .testmondata are ignored), creates one .abc file, and calls pytest.main(pytester.path, plugins=[Plugin()]); it asserts the hook fired exactly once with the .abc file.

calls: [pytest.main](../../catalog.json)

<a id="u-c56cb54ddb76"></a>
### `test_class_from_parent`

`def test_class_from_parent(request: FixtureRequest) -> None:` · [testing/test_collection.py:L1609-L1612][f1]

Defines MyCollector(pytest.Class) with __init__(name, parent, x) and a classmethod from_parent(parent, *, name, x) that forwards to the superclass factory, then builds an instance from the session and asserts x==10, showing Class.from_parent supports custom keyword forwarding.

<a id="u-65cea49a74b1"></a>
### `test_fscollector_from_parent`

`def test_fscollector_from_parent(pytester: Pytester, request: FixtureRequest) -> None:` · [testing/test_collection.py:L1589-L1595][f1]

Defines MyCollector(pytest.File) whose __init__ requires a keyword x (stored on the instance) and whose collect raises NotImplementedError, then constructs it via MyCollector.from_parent(parent=session, path=..., x=10) and asserts custom keyword arguments are forwarded to the constructor (pytest-cpp context #47).

<a id="u-572937834679"></a>
### `test_matchnodes_two_collections_same_file`

`def test_matchnodes_two_collections_same_file(pytester: Pytester) -> None:` · [testing/test_collection.py:L819-L857][f1]

A conftest registers Plugin2 whose pytest_collect_file returns MyFile2 for .abc files, in addition to the conftest's own hook returning MyFile1, so one .abc file is collected twice, yielding item1 and item2: a plain run shows 2 passed.

Running with the explicit nodeid '<file>::item2' collects only the second collector's item and reports 1 passed.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_collection.py
