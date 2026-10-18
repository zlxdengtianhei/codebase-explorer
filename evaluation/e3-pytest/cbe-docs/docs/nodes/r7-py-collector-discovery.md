# Discovery Rules and Collect Hooks

**Capability.** Name-based test discovery: PyobjMixin gives nodes Python-object access (obj, module, cls, instance, reportinfo); PyCollector applies python_files/python_classes/python_functions ini rules plus nose __test__ convention; module hooks (pytest_addoption, pytest_collect_file, pytest_collect_directory, pytest_pycollect_makeitem/makemodule) decide what becomes a collector; IGNORED_ATTRIBUTES skips builtin names.

Use this subtree to understand or override what counts as a test. The ini options registered here drive funcnamefilter/classnamefilter; _matches_prefix_or_glob_option implements prefix-then-glob matching.

**Depends on.**

- [Collection Tree Core \(nodes.py\)](r7-collection-tree-core.md) · graph-confirmed · 5 edge(s)
- [Parametrization Machinery](r7-py-parametrization.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Module, Class, and Package Collectors](r7-py-module-class-package.md) · graph-confirmed · 3 edge(s)

Parent: [Python Test Collection and Execution](r7-python-collection.md)

## Units (29)

<a id="u-135afe275fff"></a>
### `PyobjMixin`

`class PyobjMixin(nodes.Node):` · [src/_pytest/python.py:L245-L253][f1]

Mixin giving collected nodes Python-object access.

module and cls walk ancestors to the nearest Module/Class and return their obj, or None if absent; instance returns None here and is overridden by Function. obj lazily computes and caches _obj through _getobj and, when _ALLOW_MARKERS, extends own_markers from the object's marks and mirrors them into keywords (the comment assumes obj is first accessed before custom keywords are added); the setter bypasses that sync. _getobj fetches attribute self.name from parent.obj. getmodpath joins ancestor names up to the module, stripping the .py suffix and optionally including the module name; reportinfo returns (path, lineno, modpath) of obj.

inherits: [class::Node][f2]

**Uncertainties.**

- The keyword-update hack assumes obj is accessed before custom keywords are added; violating that would overwrite them.
- getmodpath relies on iter_parents ordering under unusual hierarchies.

<a id="u-7051750b2601"></a>
### `PyobjMixin._getobj`

`def _getobj(self):` · [src/_pytest/python.py:L294-L299][f1]

Default object fetch: asserts a parent exists and returns the attribute self.name of parent.obj; subclasses such as Module and Function override this.

<a id="u-b963b8929c7f"></a>
### `src/_pytest/python.py:PyobjMixin.obj`

`def obj(self):` · [src/_pytest/python.py:L275-L288][f1]

Lazy getter: returns cached _obj or computes it via _getobj; on first computation, when _ALLOW_MARKERS is set, extends own_markers with the object's unpacked marks and inserts them into keywords.

The setter form simply assigns _obj without syncing markers.

<a id="u-40b5c2c795fa"></a>
### `PyobjMixin.module`

`def module(self):` · [src/_pytest/python.py:L253-L257][f1]

Property returning the obj of the nearest Module ancestor, or None when no Module ancestor exists.

<a id="u-b0f006a4f73a"></a>
### `PyobjMixin.cls`

`def cls(self):` · [src/_pytest/python.py:L259-L263][f1]

Property returning the obj of the nearest Class ancestor, or None when no Class ancestor exists.

<a id="u-0feda4eed8d7"></a>
### `PyobjMixin.instance`

`def instance(self):` · [src/_pytest/python.py:L265-L273][f1]

Base implementation always returns None; Function overrides it to return the bound test-class instance.

<a id="u-43176b5428a3"></a>
### `PyobjMixin.getmodpath`

`def getmodpath(self, stopatmodule: bool = True, includemodule: bool = False) -> str:` · [src/_pytest/python.py:L301-L314][f1]

Builds the dotted path of this node relative to its containing module by walking iter_parents.

Module nodes contribute a name with the .py extension stripped; when stopatmodule is true the walk stops at the module, including the module name only if includemodule. Parts are reversed and joined with dots.

<a id="u-a5a45d64c215"></a>
### `PyobjMixin.reportinfo`

`def reportinfo(self) -> tuple[os.PathLike[str] | str, int | None, str]: # XXX caching?` · [src/_pytest/python.py:L316-L320][f1]

Returns (path, lineno, modpath) for reporting: file position of obj via getfslineno and its dotted module-relative path via getmodpath.

<a id="u-586f91f1d412"></a>
### `PyCollector`

`class PyCollector(PyobjMixin, nodes.Collector, abc.ABC):` · [src/_pytest/python.py:L343-L344][f1]

Abstract collector implementing pytest's name-based discovery rules over Python objects.

funcnamefilter/classnamefilter match names against the python_functions/python_classes ini options (prefix or glob) via _matches_prefix_or_glob_option, which short-circuits on startswith and only runs the costlier fnmatch when the option contains glob metacharacters. isnosetest accepts objects whose __test__ is exactly True (deliberately strict to avoid truthy custom __getattr__). istestfunction accepts static/classmethods by unwrapping __func__ and requires the callable to have no fixture marker; istestclass additionally rejects abstract classes. collect iterates obj.__dict__ (plus each MRO base's __dict__ for classes) in definition order, skipping IGNORED_ATTRIBUTES, deduplicating names across dicts, optionally skipping functions/classes imported from other modules when collect_imported_tests is off, and dispatching each entry through ihook.pytest_pycollect_makeitem; results are returned in reverse-MRO order so inherited nodes precede subclass nodes. _genfunctions builds a FunctionDefinition, a Metafunc, and runs pytest_generate_tests hooks (plus module/class-level pytest_generate_tests methods); with no calls it yields a single Function, otherwise it prunes the fixture dependency tree and yields one Function per callspec named name[id].

inherits: [PyobjMixin](r7-py-collector-discovery.md#u-135afe275fff), [class::Collector][f2]; calls: [PyCollector._genfunctions](r7-py-collector-discovery.md#u-352fbf2a6b33)

**Uncertainties.**

- Whether dict mutation during collect's list() copy can drop entries added mid-iteration is unguarded beyond the copy.
- _genfunctions calls cls().pytest_generate_tests, instantiating the class, whose side effects are not visible here.

<a id="u-352fbf2a6b33"></a>
### `PyCollector._genfunctions`

`def _genfunctions(self, name: str, funcobj) -> Iterator[Function]:` · [src/_pytest/python.py:L441-L488][f1]

Generates the Function items for one collected function.

It resolves the enclosing module object and class object (None if absent), builds a FunctionDefinition to obtain fixtureinfo, and constructs a Metafunc. Module- and class-level pytest_generate_tests callables are collected as extra methods (note: it instantiates the class via cls() to fetch the bound method) and the pytest_generate_tests hook is called with call_extra; these fill metafunc._calls. With no calls it yields a single plain Function. Otherwise it recomputes direct parameter indices, prunes the fixture dependency tree (direct parametrizations may shadow fixtures), and yields one Function per CallSpec2, named name[callspec.id] when the id list is nonempty, with keywords {callspec.id: True} and originalname set to the undecorated name.

uses: [PyCollector.istestclass](r7-py-collector-discovery.md#u-a30c9a4f2c56); calls: [Node.getparent](r7-node-base-lifecycle.md#u-f0c5b3d0a850)

**Uncertainties.**

- cls().pytest_generate_tests instantiates the test class; its construction side effects are not visible here.
- Behavior when a class-level pytest_generate_tests is inherited from an unrelated base is not established.

<a id="u-9c88b1837a0d"></a>
### `PyCollector.collect`

`def collect(self) -> Iterable[nodes.Item | nodes.Collector]:` · [src/_pytest/python.py:L390-L439][f1]

Enumerates candidate attributes of the underlying object and yields collected nodes.

If obj has __test__ falsy it returns nothing. It reads obj.__dict__ (avoiding random getattrs) and, for classes, each MRO base's __dict__; entries already seen are skipped so subclass overrides win. IGNORED_ATTRIBUTES are skipped, and when collect_imported_tests is off on a Module, functions/classes whose __module__ differs from the module's own name are skipped. Each remaining entry goes through ihook.pytest_pycollect_makeitem; None results are dropped, lists are extended, single nodes appended. Dict-order is preserved per class, and the per-class lists are concatenated in reversed order so inherited (MRO-earlier) nodes come first.

<a id="u-b96f1f9a22fc"></a>
### `PyCollector.funcnamefilter`

`def funcnamefilter(self, name: str) -> bool:` · [src/_pytest/python.py:L344-L345][f1]

True when the name matches the python_functions ini prefixes/globs.

<a id="u-6fc0d13321bf"></a>
### `PyCollector.classnamefilter`

`def classnamefilter(self, name: str) -> bool:` · [src/_pytest/python.py:L356-L357][f1]

True when the name matches the python_classes ini prefixes/globs.

<a id="u-2f5135b83840"></a>
### `PyCollector.isnosetest`

`def isnosetest(self, obj: object) -> bool:` · [src/_pytest/python.py:L347-L354][f1]

True when obj has a __test__ attribute that is exactly True (nose @istest convention); strict identity avoids treating truthy custom __getattr__ results as tests.

<a id="u-a30c9a4f2c56"></a>
### `PyCollector.istestclass`

`def istestclass(self, obj: object, name: str) -> bool:` · [src/_pytest/python.py:L368-L373][f1]

True when the name passes classnamefilter or obj passes isnosetest, and obj is not abstract.

<a id="u-2918b04f7387"></a>
### `PyCollector.istestfunction`

`def istestfunction(self, obj: object, name: str) -> bool:` · [src/_pytest/python.py:L359-L366][f1]

True when the name passes funcnamefilter or the object passes isnosetest and, after unwrapping staticmethod/classmethod via __func__, the object is callable and carries no fixture marker.

Otherwise False.

<a id="u-8344c32f6cae"></a>
### `PyCollector._matches_prefix_or_glob_option`

`def _matches_prefix_or_glob_option(self, option_name: str, name: str) -> bool:` · [src/_pytest/python.py:L375-L388][f1]

Checks the given ini option entries against a name: startswith match first; fnmatch only when the option looks like a glob (*, ?

or [) to keep the hot path cheap. Returns True on any match, else False.

<a id="u-48558d6976cb"></a>
### `python.py module code (L1–L82)`

`module_region` · [src/_pytest/python.py:L1-L82][f1]

Module header of python.py: docstring and stdlib/pytest-internal imports only, with a TYPE_CHECKING-only Self import.

No runtime behavior.

<a id="u-11d0910a7fbb"></a>
### `python.py module code (L320–L326)`

`module_region` · [src/_pytest/python.py:L320-L326][f1]

Defines IGNORED_ATTRIBUTES, a frozenset of builtin attribute names (dir of a bare ModuleType, extra module keys like __builtins__/__file__/__cached__, and dir of an empty class and instance) that are pre-ignored during collection so the makeitem hook is not called for them.

The temporary _EmptyClass is deleted afterwards.

<a id="u-c45c8bb1d479"></a>
### `python.py module code (L327–L342)`

`module_region` · [src/_pytest/python.py:L327-L342][f1]

Computes the IGNORED_ATTRIBUTES frozenset union (see region ::11618 description); purely a constant definition.

<a id="u-1e905a2fdb45"></a>
### `_EmptyClass`

`class _EmptyClass:` · [src/_pytest/python.py:L327-L327][f1]

Bare class used only as a template to compute default class/instance attribute names for IGNORED_ATTRIBUTES.

<a id="u-4ae5e8edf4a7"></a>
### `src/_pytest/python.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/python.py:L83-L109][f1]

Registers the ini options that drive Python test discovery: python_files (default test_*.py and *_test.py), python_classes (Test), python_functions (test), all args-typed, plus the boolean disable_test_id_escaping_and_forfeit_all_rights_to_community_support.

Collectors and ID generation later read these via config.getini, so changing them changes what is collected and how IDs are escaped.

calls: [Parser.addini](r4-argparsing-parser-api.md#u-8f261b2ced78)

<a id="u-45fe4b2ad5ea"></a>
### `src/_pytest/python.py:pytest_collect_file`

`def pytest_collect_file(file_path: Path, parent: nodes.Collector) -> Module | None:` · [src/_pytest/python.py:L185-L197][f1]

File collection hook for .py files.

If the path is not a session initial path, it must match the python_files ini patterns or None is returned; initial paths bypass the pattern filter. Matching .py files yield a Module created through the session hook proxy's pytest_pycollect_makemodule. Non-.py files always yield None.

calls: [path_matches_patterns](r7-py-collector-discovery.md#u-dcb0458372cd)

<a id="u-dcb0458372cd"></a>
### `path_matches_patterns`

`def path_matches_patterns(path: Path, patterns: Iterable[str]) -> bool:` · [src/_pytest/python.py:L200-L202][f1]

Returns True when the path matches any of the given glob patterns via fnmatch_ex.

<a id="u-6279465c335c"></a>
### `src/_pytest/python.py:pytest_collect_directory`

`def pytest_collect_directory( path: Path, parent: nodes.Collector ) -> nodes.Collecto…` · [src/_pytest/python.py:L171-L182][f1]

Directory collection hook: returns a Package collector when the directory contains __init__.py, otherwise None.

If the __init__.py existence check raises PermissionError, returns None so unreadable directories are skipped instead of aborting collection.

uses: [Package](r7-py-module-class-package.md#u-9b1314e683f6)

<a id="u-17447557fb65"></a>
### `src/_pytest/python.py:pytest_pycollect_makemodule`

`def pytest_pycollect_makemodule(module_path: Path, parent) -> Module:` · [src/_pytest/python.py:L205-L206][f1]

Creates a Module collector node for the given file path under the given parent collector.

<a id="u-80d71e4085af"></a>
### `src/_pytest/python.py:pytest_pycollect_makeitem`

`def pytest_pycollect_makeitem( collector: Module | Class, name: str, obj: object ) ->…` · [src/_pytest/python.py:L209-L242][f1]

Trylast fallback deciding what an unclaimed attribute becomes (asserts the collector is a Class or Module).

If obj is a class, an istestclass match yields a Class node; otherwise nothing. If obj is a candidate function, it is normalized by unwrapping __func__ (mock) and functools wrappers; when no real function can be obtained, a PytestCollectionWarning is issued with warn_explicit and nothing is collected. When __test__ is not False, generator functions abort with fail ('yield' allowed in fixtures, not tests) while normal functions yield their parametrized Function items via _genfunctions. Returns None when nothing matches.

**Notes.**

- failure: Generator test functions abort collection with fail() rather than being skipped.

calls: [PyCollector._genfunctions](r7-py-collector-discovery.md#u-352fbf2a6b33), [PyCollector.istestclass](r7-py-collector-discovery.md#u-a30c9a4f2c56)

<a id="u-c4260d122653"></a>
### `hasinit`

`def hasinit(obj: object) -> bool:` · [src/_pytest/python.py:L842-L846][f1]

True when obj has an __init__ different from object.__init__.

<a id="u-826e98137a90"></a>
### `hasnew`

`def hasnew(obj: object) -> bool:` · [src/_pytest/python.py:L849-L853][f1]

True when obj has a __new__ different from object.__new__.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/python.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/nodes.py
