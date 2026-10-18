# Node API Test Suite

**Capability.** Tests of Node construction rules, diamond Item/File inheritance deprecation warnings, and node path helpers (_check_initialpaths_for_relpath, absolute paths after cwd changes).

Use this for construction-time validation contracts and relative-path computation for failure locations.

Parent: [pytest Core](r9-pytest-core.md)

## Units (4)

<a id="u-8ca075670726"></a>
### `test_nodes-node-construction-and-warning-tests`

`def test_node_from_parent_disallowed_arguments() -> None:` · [testing/test_nodes.py:L16-L20][f1]

Tests of Node construction rules and warning APIs.

test_node_from_parent_disallowed_arguments asserts nodes.Node.from_parent raises TypeError matching 'session is' when passed session=None, and TypeError matching 'config is' when passed config=None with parent None. test_node_direct_construction_deprecated asserts direct nodes.Node(None, session=None) raises OutcomeException with a message pointing to Node.from_parent and the deprecations docs URL. test_node_warn_is_no_longer_only_pytest_warnings is parametrized over (DeprecationWarning, 'deprecated') and (PytestWarning, 'pytest'): it collects items via pytester.getitems, then asserts items[0].warn(warn_type(msg)) emits a warning of that exact type matching the message fragment — Node.warn is no longer restricted to PytestWarning. test_node_warning_enforces_warning_types asserts items[0].warn(Exception('ok')) raises ValueError matching 'warning must be an instance of Warning or subclass', so non-Warning args are still rejected.

uses: [pytester-collection-helpers](r6-pytester-run.md#u-0183c0c437e7)

**Uncertainties.**

- The TypeError/OutcomeException messages are matched by regex; the exact raising code paths inside nodes.py are outside this file.

<a id="u-83153f5ef61c"></a>
### `test_nodes-subclassing-both-item-and-collector-deprecated`

`def test_subclassing_both_item_and_collector_deprecated( request, tmp_path: Path ) ->…` · [testing/test_nodes.py:L36-L47][f1]

Verifies pytest warns on diamond inheritance of Item and File, and that legacy constructors still work through from_parent.

Inside warnings.catch_warnings with simplefilter('error'), the test defines SoWrong(nodes.Item, nodes.File) — class definition itself must emit no warnings. SoWrong has a legacy __init__(fspath, parent) calling super().__init__(fspath, parent), plus collect() and runtest() raising NotImplementedError. It then wraps SoWrong.from_parent(request.session, fspath=legacy_path(tmp_path / 'broken.txt')) in pytest.warns(PytestWarning) and asserts two messages among the captured warnings: one matching '.*SoWrong.* not using a cooperative constructor.*' (legacy ctor via from_parent) and one matching '(?m)SoWrong .* should not be a collector' (Item+File diamond inheritance). If class definition raised a warning, simplefilter('error') would turn it into an exception and fail the test.

uses: [src/_pytest/compat.py][f2]

**Uncertainties.**

- Where exactly the two PytestWarnings are emitted (from_parent vs __init__) is not visible in this file; only their message texts are asserted.
- The graph's junitxml _NodeReporter.append candidate for rec.__iter__ is not clearly supported by the visible source; the iteration is over pytest.warns' recorded warnings.

<a id="u-c0bcecf89c75"></a>
### `test__check_initialpaths_for_relpath`

`def test__check_initialpaths_for_relpath() -> None:` · [testing/test_nodes.py:L101-L113][f1]

Tests nodes._check_initialpaths_for_relpath handling of directories and paths outside the initial paths.

With initial_paths = frozenset({Path.cwd()}), it asserts the function returns '' for the cwd itself, 'file' for cwd/'file' (a relative path from the initial dir, not just a dirname), and None for a nonexistent path '/outside-this-does-not-exist' outside the initial paths. It saves nothing and mutates no state; cwd is only read.

<a id="u-cd281c4eec50"></a>
### `test_failure_with_changed_cwd`

`def test_failure_with_changed_cwd(pytester: Pytester) -> None:` · [testing/test_nodes.py:L116-L140][f1]

Verifies failure lines use absolute paths when the working directory changed during the run (#6428).

It writes a test module with a private_dir fixture that creates 'ddd', chdirs into it, yields, and chdirs back on teardown; the test body then asserts False. After pytester.runpytest, it matches stdout lines '<p>: *: AssertionError' and '*1 failed in *', where p is the module path returned by makepyfile — asserting the reported path is the absolute module path despite the changed cwd at failure time.

uses: [pytester-file-factories](r6-pytester-core.md#u-42fdcb995917), [pytester-runpytest](r6-pytester-run.md#u-272699fd9346)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_nodes.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/compat.py
