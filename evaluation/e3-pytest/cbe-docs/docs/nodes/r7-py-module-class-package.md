# Module, Class, and Package Collectors

**Capability.** The container collectors for Python code: Module imports and collects a test file (importtestmodule turns every import failure into CollectError), Class guards against custom __init__/__new__ and collects methods, Package collects directories with __init__.py. Each registers xunit setup/module/class/function teardown as autouse fixtures via _call_with_optional_argument.

Read here for import-mode semantics, collection-error messages, __init__-first package ordering, and how setup_module/setup_class/setup_method/setup_function are adapted into fixtures. Package.setup runs the package init's module-level setup immediately with a teardown finalizer.

**Depends on.**

- [Collection Tree Core \(nodes.py\)](r7-collection-tree-core.md) · model-inferred · 0 edge(s)
- [Discovery Rules and Collect Hooks](r7-py-collector-discovery.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [Python Collection Tests](r7-collect-tests.md) · model-inferred · 0 edge(s)

Parent: [Python Test Collection and Execution](r7-python-collection.md)

## Units (28)

<a id="u-ff2e44fe1b77"></a>
### `Module`

`class Module(nodes.File, PyCollector):` · [src/_pytest/python.py:L547-L550][f1]

File collector for a Python test module.

Its _getobj imports the module via importtestmodule. collect first registers the xunit setup fixtures and asks the fixture manager to parse factories for this module, then defers to PyCollector.collect for the attribute walk. The xunit helpers: _register_setup_module_fixture looks up setUpModule/setup_module and tearDownModule/teardown_module (skipping attributes already marked as fixtures) and, if either exists, registers an autouse module-scoped fixture that calls setup before the yield and teardown after, passing the module object with optional-argument calling. _register_setup_function_fixture similarly wraps setup_function/teardown_function in an autouse function-scoped fixture whose body yields immediately when request.instance is not None (letting setup_method handle it), otherwise calls setup with the function before the yield and teardown after.

calls: [importtestmodule](r7-py-module-class-package.md#u-1a2dcd1cd401); inherits: [PyCollector](r7-py-collector-discovery.md#u-586f91f1d412)

<a id="u-a52b789dc052"></a>
### `Module._getobj`

`def _getobj(self):` · [src/_pytest/python.py:L550-L551][f1]

Imports and returns the module object for this collector's path via importtestmodule.

<a id="u-c6b3d30c852a"></a>
### `Module.collect`

`def collect(self) -> Iterable[nodes.Item | nodes.Collector]:` · [src/_pytest/python.py:L553-L557][f1]

Registers the module/function xunit setup fixtures, parses factories for this module into the session fixture manager, then returns PyCollector.collect's results.

<a id="u-f0835b0e1d96"></a>
### `Module._register_setup_module_fixture`

`def _register_setup_module_fixture(self) -> None:` · [src/_pytest/python.py:L559-L576][f1]

Looks up setUpModule/setup_module and tearDownModule/teardown_module on the module (non-fixture attributes only); if both are absent returns without registering anything.

<a id="u-eab7cf748963"></a>
### `src/_pytest/python.py:Module._register_setup_module_fixture`

`def _register_setup_module_fixture(self) -> None:` · [src/_pytest/python.py:L582-L591][f1]

Registers the generator above as an autouse, module-scoped fixture named _xunit_setup_module_fixture_<module __name__> on this nodeid.

<a id="u-4016944c67fc"></a>
### `xunit_setup_module_fixture`

`def xunit_setup_module_fixture(request) -> Generator[None]:` · [src/_pytest/python.py:L576-L582][f1]

Body of the registered autouse module fixture: calls setup_module (if present) with the module via optional-argument dispatch, yields, then calls teardown_module (if present).

<a id="u-f75aac67a850"></a>
### `Module._register_setup_function_fixture`

`def _register_setup_function_fixture(self) -> None:` · [src/_pytest/python.py:L593-L607][f1]

Looks up setup_function and teardown_function (non-fixture only); returns early if both are missing.

<a id="u-69b051d95d83"></a>
### `src/_pytest/python.py:Module._register_setup_function_fixture`

`def _register_setup_function_fixture(self) -> None:` · [src/_pytest/python.py:L618-L627][f1]

Registers the generator above as an autouse, function-scoped fixture named _xunit_setup_function_fixture_<module __name__> on this nodeid.

<a id="u-a5393b835e7d"></a>
### `xunit_setup_function_fixture`

`def xunit_setup_function_fixture(request) -> Generator[None]:` · [src/_pytest/python.py:L607-L618][f1]

Body of the registered function-scoped fixture: when request.instance is not None it yields and returns (delegating to setup_method); otherwise it calls setup_function (if present) with the function, yields, then calls teardown_function.

<a id="u-83a743c15644"></a>
### `Class`

`class Class(PyCollector):` · [src/_pytest/python.py:L736-L739][f1]

Collector for test methods and nested classes in a Python class.

from_parent is the public constructor (obj passed through keywords). newinstance returns a fresh instance of the class. collect refuses to collect when __test__ is falsy, or when the class defines __init__ or __new__ (comparing against object's own), emitting a PytestCollectionWarning naming the reason and the parent nodeid, and returns nothing. Otherwise it registers the class- and method-scoped xunit setup fixtures, asks the fixture manager to parse factories from a fresh instance (so self-dependent fixtures resolve), and defers to PyCollector.collect for the attribute walk. _register_setup_class_fixture wraps setup_class/teardown_class (non-fixture only) in an autouse class-scoped fixture: it resolves the underlying function via getimfunc and calls it with request.cls before and after the yield. _register_setup_method_fixture wraps setup_method/teardown_method in an autouse function-scoped fixture that binds them to request.instance and calls with request.function around the yield. Neither registers anything when both counterparts are absent.

inherits: [PyCollector](r7-py-collector-discovery.md#u-586f91f1d412); calls: [hasinit](r7-py-collector-discovery.md#u-c4260d122653)

<a id="u-b25f65449ac6"></a>
### `Class.collect`

`def collect(self) -> Iterable[nodes.Item | nodes.Collector]:` · [src/_pytest/python.py:L747-L774][f1]

Guards collection: empty when __test__ is falsy; empty with a PytestCollectionWarning when the class has a custom __init__ or __new__ (checked by hasinit/hasnew, warning cites parent nodeid).

Otherwise registers the setup fixtures, parses factories from a fresh instance, and returns PyCollector.collect's results.

uses: [Node.warn](r7-node-base-lifecycle.md#u-6f5627aa244f)

<a id="u-d354f0eb7522"></a>
### `Class.from_parent`

`def from_parent(cls, parent, *, name, obj=None, **kw) -> Self: # type: ignore[override]` · [src/_pytest/python.py:L739-L742][f1]

Public constructor delegating to Node.from_parent with name and obj keywords.

<a id="u-c16e226ecb07"></a>
### `Class.newinstance`

`def newinstance(self):` · [src/_pytest/python.py:L744-L745][f1]

Returns a fresh instance of the collected class by calling self.obj().

<a id="u-ad1d31de1e5d"></a>
### `Class._register_setup_class_fixture`

`def _register_setup_class_fixture(self) -> None:` · [src/_pytest/python.py:L776-L788][f1]

Finds setup_class/teardown_class (skipping fixture-marked attributes); returns early when both are absent.

<a id="u-8f24d3be0a56"></a>
### `src/_pytest/python.py:Class._register_setup_class_fixture`

`def _register_setup_class_fixture(self) -> None:` · [src/_pytest/python.py:L796-L805][f1]

Registers the generator as an autouse, class-scoped fixture named _xunit_setup_class_fixture_<qualname> on this nodeid.

<a id="u-19c3fb55e18c"></a>
### `xunit_setup_class_fixture`

`def xunit_setup_class_fixture(request) -> Generator[None]:` · [src/_pytest/python.py:L788-L796][f1]

Body of the class-scoped fixture: resolves setup/teardown functions via getimfunc and calls each with request.cls around the yield, only when present.

<a id="u-3e33a0434338"></a>
### `Class._register_setup_method_fixture`

`def _register_setup_method_fixture(self) -> None:` · [src/_pytest/python.py:L807-L821][f1]

Finds setup_method/teardown_method (non-fixture only); returns early when both are absent.

<a id="u-6f9ebf3833d5"></a>
### `src/_pytest/python.py:Class._register_setup_method_fixture`

`def _register_setup_method_fixture(self) -> None:` · [src/_pytest/python.py:L830-L839][f1]

Registers the generator as an autouse, function-scoped fixture named _xunit_setup_method_fixture_<qualname> on this nodeid.

<a id="u-60d7dde3f0c7"></a>
### `xunit_setup_method_fixture`

`def xunit_setup_method_fixture(request) -> Generator[None]:` · [src/_pytest/python.py:L821-L830][f1]

Body of the function-scoped fixture: binds setup/teardown to request.instance via getattr and calls each with request.function around the yield.

<a id="u-9b1314e683f6"></a>
### `Package`

`class Package(nodes.Directory):` · [src/_pytest/python.py:L630-L645][f1]

Directory collector for Python packages (directories with __init__.py), inheriting from nodes.Directory since 8.0.

__init__ resolves the session from the parent and forwards all arguments (several, like config/session/nodeid, accepted but unused, kept for compatibility). setup imports the package's __init__.py, calls setup_module/setUpModule immediately via optional-argument dispatch, and registers a finalizer calling teardown_module/tearDownModule; it deliberately does not use fixtures because autouse package fixtures are not invoked automatically. collect scans the directory with __init__.py sorted first (then by name); directories are skipped when pytest_ignore_collect says so (unless an init path with parents), else delegated to pytest_collect_directory; files are skipped the same way (without parents) and delegated to pytest_collect_file, yielding results.

calls: [importtestmodule](r7-py-module-class-package.md#u-1a2dcd1cd401)

**Uncertainties.**

- Whether setup's finalizer ordering relative to other package finalizers matters is not visible here.

<a id="u-49f84d9012ed"></a>
### `Package.__init__`

`def __init__( self, fspath: LEGACY_PATH | None, parent: nodes.Collector, # NOTE: foll…` · [src/_pytest/python.py:L645-L665][f1]

Constructor: resolves session from parent.session and forwards fspath/path/parent/config/session/nodeid to the Directory constructor; config, session and nodeid parameters are accepted but unused for compat.

<a id="u-a9772ffef9c6"></a>
### `Package.collect`

`def collect(self) -> Iterable[nodes.Item | nodes.Collector]: # Always collect __init_…` · [src/_pytest/python.py:L685-L687][f1]

Yields collectors for the package directory, always starting with __init__.py.

<a id="u-9e9fb2b87ac1"></a>
### `src/_pytest/python.py:Package.collect`

`def collect(self) -> Iterable[nodes.Item | nodes.Collector]: # Always collect __init_…` · [src/_pytest/python.py:L688-L710][f1]

Iterates scandir with the __init__-first sort key.

For directories: skipped when pytest_ignore_collect declines them unless the path is an init path (with_parents=True), else yields pytest_collect_directory's collector if any. For files: skipped on ignore unless an init path, else yields all collectors from pytest_collect_file.

<a id="u-915bd9db91d4"></a>
### `src/_pytest/python.py:sort_key`

`def sort_key(entry: os.DirEntry[str]) -> object:` · [src/_pytest/python.py:L687-L688][f1]

Sort key giving __init__.py precedence (False sorts first) and ordering remaining entries by name.

<a id="u-fea9eb0b3f2d"></a>
### `Package.setup`

`def setup(self) -> None:` · [src/_pytest/python.py:L667-L683][f1]

Imports the package __init__.py, runs its setup_module/setUpModule (optional-argument call) right away, and registers a partial of the teardown_module call via self.addfinalizer; no fixture is used (autouse package fixtures are not called automatically).

uses: [TopRequest](r5-fixture-request-context.md#u-e83ca79a5b8f)

<a id="u-1a2dcd1cd401"></a>
### `importtestmodule`

`def importtestmodule( path: Path, config: Config, ): # We assume we are only called o…` · [src/_pytest/python.py:L491-L544][f1]

Imports a test module file honoring --import-mode, consider_namespace_packages and the root path, converting every failure mode into Collector.CollectError: SyntaxError becomes a short exception repr; ImportPathMismatchError becomes a hint-laden message about __pycache__/duplicate basenames; ImportError becomes a message with the traceback filtered by filter_traceback only when verbosity is below 2 (otherwise exconly when no traceback remains); skip.Exception re-raises when allow_module_level is true, otherwise becomes an explanatory CollectError about module-level skip.

On success it calls pluginmanager.consider_module(mod) and returns the module.

**Uncertainties.**

- The exact import_path failure surface beyond the four caught exception types is defined in _pytest.pathlib, not here.

<a id="u-c78154b72b54"></a>
### `_call_with_optional_argument`

`def _call_with_optional_argument(func, arg) -> None:` · [src/_pytest/python.py:L713-L722][f1]

Invokes a setup/teardown callable with the given argument only if it accepts one: reads co_argcount and decrements it for bound methods; a nonzero count calls func(arg), zero calls func().

**Uncertainties.**

- Relies on func having __code__; C-implemented callables would raise AttributeError (not handled here).

<a id="u-36c45b136988"></a>
### `_get_first_non_fixture_func`

`def _get_first_non_fixture_func(obj: object, names: Iterable[str]) -> object | None:` · [src/_pytest/python.py:L725-L733][f1]

Returns the first named attribute that exists and is not itself marked as a fixture (via getfixturemarker), preventing a double call; None when no candidate qualifies.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/python.py
