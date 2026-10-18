# Function Item and Execution

**Capability.** The Function item that runs one Python test: construction resolves fixtureinfo, keywords, and the request; setup fills fixtures; runtest fires pytest_pyfunc_call; instance binding creates per-function test-class instances. FunctionDefinition is a non-executable placeholder, and async functions fail with a plugin-recommendation message.

Use this subtree for how a collected function becomes a runnable item, how the request/funcargs are initialized, and how failure tracebacks are shortened. Plugin executors hook in via the trylast pytest_pyfunc_call default.

**Depends on.**

- [Collection Tree Core \(nodes.py\)](r7-collection-tree-core.md) · graph-confirmed · 1 edge(s)
- [Parametrization Machinery](r7-py-parametrization.md) · model-inferred · 0 edge(s)

Parent: [Python Test Collection and Execution](r7-python-collection.md)

## Units (18)

<a id="u-06f14dc6ae2f"></a>
### `Function`

`class Function(PyobjMixin, nodes.Item):` · [src/_pytest/python.py:L1538-L1570][f1]

Item that sets up and runs one Python test function.

__init__ stores callobj and its __self__ as _instance when given, records originalname (name without parametrize decorations, used to look the function up on the parent), extends own_markers from the function's marks plus the callspec's marks when parametrized, and updates keywords in a documented priority order (ctor keywords over function __dict__ over markers). It resolves fixtureinfo via the session fixture manager when not supplied, exposes fixturenames from the closure and creates the TopRequest. _ALLOW_MARKERS is disabled because functions handle their own markers. runtest fires the pytest_pyfunc_call hook; setup fills fixtures via the request; _traceback_filter trims tracebacks to the function's real code (get_real_func) starting at firstlineno, falling back through path-cut and filter_traceback (restoring the full traceback if filtering empties it) unless fulltrace or no _obj, and with tbstyle auto collapses middle frames to short reprs when more than two frames remain. repr_failure forces the long style when tbstyle is auto and delegates to _repr_failure_py. instance lazily binds a fresh instance when the parent is a Class; _getobj resolves the attribute on the instance or the parent object using originalname.

**Uncertainties.**

- Keyword priority semantics rely on the documented update order; exact NodeKeywords traversal is defined in nodes.py.
- repr_failure's type-ignore indicates a Liskov override whose wider contract lives in nodes.py.

<a id="u-523de5f547bc"></a>
### `Function.__init__`

`def __init__( self, name: str, parent, config: Config | None = None, callspec: CallSp…` · [src/_pytest/python.py:L1570-L1619][f1]

Builds the item: stores callobj/_instance, originalname, merges function marks, callspec marks and ctor keywords into keywords, resolves fixtureinfo (from the session fixture manager when not provided), sets fixturenames and initializes the request.

<a id="u-1211b0a13bc0"></a>
### `Function.from_parent`

`def from_parent(cls, parent, **kw) -> Self:` · [src/_pytest/python.py:L1622-L1625][f1]

Public constructor delegating to Node.from_parent with all keywords.

<a id="u-51d81608a34e"></a>
### `Function._initrequest`

`def _initrequest(self) -> None:` · [src/_pytest/python.py:L1627-L1629][f1]

Creates the empty funcargs dict and a TopRequest bound to this item.

<a id="u-df7d8c45b7a7"></a>
### `Function.function`

`def function(self):` · [src/_pytest/python.py:L1631-L1634][f1]

The underlying function with class-method binding undone via getimfunc(self.obj).

<a id="u-5b67011fbbc6"></a>
### `Function.instance`

`def instance(self):` · [src/_pytest/python.py:L1636-L1646][f1]

Returns the stored _instance; on first access when the parent is a Class, creates a fresh instance (each Function gets its own), otherwise caches None.

<a id="u-f4bbabbddce5"></a>
### `Function._getinstance`

`def _getinstance(self):` · [src/_pytest/python.py:L1648-L1653][f1]

Returns parent.newinstance() when the parent is a Class, else None.

<a id="u-2c6b739fdbac"></a>
### `Function._getobj`

`def _getobj(self):` · [src/_pytest/python.py:L1655-L1662][f1]

Resolves the callable: getattr on the bound instance when available, else on parent.obj, using originalname so parametrized names resolve.

<a id="u-2e73c3d14e5c"></a>
### `Function._pyfuncitem`

`def _pyfuncitem(self):` · [src/_pytest/python.py:L1664-L1667][f1]

Compatibility property returning self, for pytest-2.2-style request objects.

<a id="u-8a7529e5f359"></a>
### `Function.runtest`

`def runtest(self) -> None:` · [src/_pytest/python.py:L1669-L1671][f1]

Executes the test by firing the pytest_pyfunc_call hook with this item.

<a id="u-3887af3929e3"></a>
### `Function.setup`

`def setup(self) -> None:` · [src/_pytest/python.py:L1673-L1674][f1]

Fills the fixture values via self._request._fillfixtures().

<a id="u-c39931e9df9a"></a>
### `Function._traceback_filter`

`def _traceback_filter(self, excinfo: ExceptionInfo[BaseException]) -> Traceback:` · [src/_pytest/python.py:L1676-L1703][f1]

Shortens failure tracebacks unless fulltrace is set or the function object is unavailable.

Cuts at the real function's path/firstlineno; if that changed nothing, cuts by path; if still unchanged, filters internal frames and restores the original when that empties it; then filters via excinfo. Under tbstyle auto with more than two frames, middle frames are re-rendered in short style.

**Uncertainties.**

- Whether ntraceback == traceback comparison catches all equivalences depends on Traceback equality in _code, not shown here.

<a id="u-f8d7b0d91eea"></a>
### `Function.repr_failure`

`def repr_failure( # type: ignore[override] self, excinfo: ExceptionInfo[BaseException…` · [src/_pytest/python.py:L1706-L1713][f1]

Reports failures: 'auto' tbstyle is promoted to 'long' and the rendering is delegated to Node._repr_failure_py with that style.

calls: [Node._repr_failure_py](r7-node-base-lifecycle.md#u-0eac6f0bd989)

<a id="u-ee11410928d7"></a>
### `FunctionDefinition`

`class FunctionDefinition(Function):` · [src/_pytest/python.py:L1716-L1720][f1]

Placeholder Function subclass used during _genfunctions to hold a function's name and callobj before parametrization is known; running or setting up raises RuntimeError because definitions must never execute as tests.

<a id="u-13a617d0d406"></a>
### `src/_pytest/python.py:FunctionDefinition`

`class FunctionDefinition(Function):` · [src/_pytest/python.py:L1721-L1723][f1]

Assignment alias: setup equals runtest, so a FunctionDefinition also cannot be set up.

<a id="u-e6a0a6b99b16"></a>
### `FunctionDefinition.runtest`

`def runtest(self) -> None:` · [src/_pytest/python.py:L1720-L1721][f1]

Raises RuntimeError: function definitions are not supposed to be run as tests.

<a id="u-e4fe721d1547"></a>
### `src/_pytest/python.py:pytest_pyfunc_call`

`def pytest_pyfunc_call(pyfuncitem: Function) -> object | None:` · [src/_pytest/python.py:L150-L168][f1]

Trylast default executor of a Function item.

If the test callable is an async function it fails via async_fail. Otherwise it builds kwargs from funcargs restricted to the fixture closure argnames, calls the function, and fails via async_fail if the result has __await__ or __aiter__. A non-None, non-awaitable result emits PytestReturnNotNoneWarning. Always returns True, so no later implementation runs the test.

**Notes.**

- side_effect: Any non-None return value triggers PytestReturnNotNoneWarning suggesting assert instead of return.

calls: [async_fail](r7-py-function-item.md#u-fa93a4ddc1ca)

<a id="u-fa93a4ddc1ca"></a>
### `async_fail`

`def async_fail(nodeid: str) -> None:` · [src/_pytest/python.py:L137-L147][f1]

Fails the test with a non-traceback message stating that async def functions are not natively supported and listing suitable plugins (anyio, pytest-asyncio, pytest-tornasync, pytest-trio, pytest-twisted).

The nodeid parameter is accepted but unused in the message.

**Uncertainties.**

- nodeid parameter is unused in the visible message

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/python.py
