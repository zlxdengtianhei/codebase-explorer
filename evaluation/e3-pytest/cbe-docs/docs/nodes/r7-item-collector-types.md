# Collector and Item Types

**Capability.** Defines the two structural specializations of Node: Collector (tree-building node whose collect() returns children) and Item (leaf representing one test invocation), including Item construction invariants and the diamond-inheritance warning for classes that mix both.

Consult when writing a custom collector or item subclass. Item.__init__ passes name/parent positionally for plugin compatibility and initializes report/user-properties storage.

Parent: [Collection Tree Core \(nodes.py\)](r7-collection-tree-core.md)

## Units (4)

<a id="u-f40d9f019e2b"></a>
### `Collector`

`class Collector(Node, abc.ABC):` · [src/_pytest/nodes.py:L499-L506][f1]

Abstract base for tree-building nodes whose ``collect()`` returns child Items/Collectors; ``collect`` is abstract and raises NotImplementedError.

Nested ``CollectError`` signals collection problems with a custom message. ``repr_failure`` overrides the Node version: a CollectError is rendered as just str(exc.args[0]) unless ``fulltrace`` is set; otherwise the ``tbstyle`` option is honored but 'auto' is downgraded to 'short' (Node's base defaults 'auto' to 'long'). ``_traceback_filter`` cuts the traceback to entries at this collector's path; if cutting removed nothing, it instead excludes the pytest install dir (tracebackcutdir), then applies the standard filter and returns the filtered traceback; without a ``path`` attribute the raw traceback is returned.

**Notes.**

- contract: repr_failure deliberately drops the style= parameter of the base method (flagged as a Liskov violation in-source).

calls: [Node._repr_failure_py](r7-node-base-lifecycle.md#u-0eac6f0bd989)

<a id="u-8388b852e250"></a>
### `Item`

`class Item(Node, abc.ABC):` · [src/_pytest/nodes.py:L655-L663][f1]

Abstract leaf node representing one test invocation (a function may yield several items).

``runtest`` is abstract and raises NotImplementedError('runtest must be implemented by Item subclass'). ``add_report_section`` appends (when, key, content) to ``_report_sections`` only when content is non-empty. ``reportinfo`` defaults to (self.path, None, ''); ``location`` is a cached_property that absolutizes the reportinfo path, converts it via the session to a rootpath-relative string, asserts the name is a str, and caches the (relfspath, lineno, testname) triple so later reads reuse the first result. ``nextitem`` is a class attribute defaulting to None.

uses: [Item](r7-item-collector-types.md#u-8388b852e250)

**Uncertainties.**

- session._node_location_to_relpath behavior is defined outside this file.

<a id="u-60faf76128e8"></a>
### `Item.__init__`

`def __init__( self, name, parent=None, config: Config | None = None, session: Session…` · [src/_pytest/nodes.py:L663-L690][f1]

Item construction: passes name and parent positionally (deliberately, to keep plugins subclassing both pytest.Item and pytest.File working) plus config/session/nodeid and any extra kwargs to Node.__init__, then initializes ``_report_sections`` as an empty list, ``user_properties`` as an empty list of (name, value) tuples, and runs the diamond-inheritance warning check.

**Notes.**

- side_effect: Extra **kw are forwarded to Node.__init__, which accepts fspath/path; a legacy fspath therefore triggers the same deprecation warning.

calls: [Node.__init__](r7-node-base-lifecycle.md#u-dcd61aca83fe)

<a id="u-8a02948e4bc9"></a>
### `Item._check_item_and_collector_diamond_inheritance`

`def _check_item_and_collector_diamond_inheritance(self) -> None:` · [src/_pytest/nodes.py:L692-L719][f1]

Warn once per class when an Item subclass also inherits from a Collector.

A ``_pytest_diamond_inheritance_warning_shown`` attribute is set on the class (a deliberate hack) so repeat instantiations return early without warning. Otherwise the names of direct bases that are Collector subclasses are joined, and if any exist a PytestWarning naming the class, its collector bases, and docs/links is emitted.

**Notes.**

- side_effect: Sets an attribute on the user's class, permanently suppressing the warning for that class.

raises: [warning_types.py:warning-classes](r3-warning-types.md#u-10c8ce561005)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/nodes.py
