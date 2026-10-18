# TestCase collection

**Capability.** pytest_pycollect_makeitem turns TestCase subclasses into UnitTestCase collectors; UnitTestCase collects test methods (honoring runTest conventions and __unittest_skip__), creates fresh instances, and registers class/method setup fixtures.

Use this to see how unittest classes enter pytest's collection tree and which items are skipped before execution.

**Depended on by.**

- [TestCaseFunction item and setup fixtures](r5-unittest-case-item.md) · graph-confirmed · 4 edge(s)

Parent: [unittest integration bridge](r5-unittest-bridge.md)

## Units (6)

<a id="u-b830e7213ecf"></a>
### `src/_pytest/unittest.py:pytest_pycollect_makeitem`

`def pytest_pycollect_makeitem( collector: Module | Class, name: str, obj: object ) ->…` · [src/_pytest/unittest.py:L52-L69][f1]

Collection hook that turns unittest.TestCase subclasses into UnitTestCase collectors.

It verifies unittest is imported, that obj is a subclass of unittest.TestCase, and that obj is not abstract; any exception in the issubclass/probe path returns None so other collectors handle the object. Concrete TestCase classes become UnitTestCase via from_parent.

**Uncertainties.**

- The broad `except Exception` also swallows errors raised by issubclass itself (e.g. non-class obj with __mro__ quirks); such objects simply fall through to None.

<a id="u-d80fa0ae9b36"></a>
### `UnitTestCase`

`class UnitTestCase(Class): # Marker for fixturemanger.getfixtureinfo() # to declare t…` · [src/_pytest/unittest.py:L72-L77][f1]

pytest collector for unittest.TestCase classes, extending python Class.

Sets nofuncargs=True as a marker so the fixture manager knows children take no funcargs. Members documented separately: newinstance, collect, and the two auto-fixture registration methods.

<a id="u-51acaa6809c6"></a>
### `UnitTestCase.collect`

`def collect(self) -> Iterable[Item | Collector]:` · [src/_pytest/unittest.py:L85-L114][f1]

Collects the TestCase's test methods into TestCaseFunction items.

If the class has a falsey __test__ attribute, yields nothing. When the class is not skipped (per _is_skipped), registers the unittest setup-method and setup-class autouse fixtures plus the standard setup_class fixture support; skipped classes get none of these. Always parses factories on a fresh dummy instance for the nodeid. Uses unittest's TestLoader to get test-case names; for each name whose attribute has a non-falsey __test__, yields a TestCaseFunction child. If nothing was found and the class defines its own runTest, an extra 'runTest' item is yielded unless the class's runTest is exactly twisted.trial's TestCase.runTest, which is not worth collecting.

calls: [_is_skipped](r5-unittest-collection.md#u-7a8374612774)

<a id="u-c081cb576d12"></a>
### `UnitTestCase.newinstance`

`def newinstance(self): # TestCase __init__ takes the method (test) name. The TestCase…` · [src/_pytest/unittest.py:L77-L83][f1]

Creates a TestCase instance by calling the collected class with the method name 'runTest'.

The comment explains this always supplies the name because some TestCase subclasses omit the default methodName parameter, while 'runTest' is the unittest no-op sentinel.

**Uncertainties.**

- If a subclass defines an actual test named 'runTest', a dummy instance built this way would run that method's name only during construction; not verified here.

<a id="u-7a8374612774"></a>
### `_is_skipped`

`def _is_skipped(obj) -> bool:` · [src/_pytest/unittest.py:L378-L380][f1]

Returns True when the object carries a truthy __unittest_skip__ attribute, i.e. was marked with @unittest.skip.

<a id="u-540e1f54876b"></a>
### `unittest.py module code (L1–L51)`

`module_region` · [src/_pytest/unittest.py:L1-L51][f1]

Module docstring, imports, the conditional ExceptionGroup import for Python < 3.11, TYPE_CHECKING-only unittest/twisted imports, and the _SysExcInfoType alias; no runtime behavior beyond imports.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/unittest.py
