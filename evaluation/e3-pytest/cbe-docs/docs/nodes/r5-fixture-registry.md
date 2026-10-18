# Fixture registry and requirement closure

**Capability.** FixtureManager as the session's registry hub: parsing factories from plugins and collection nodes, registering FixtureDefs, matching definitions to nodes by baseid, computing per-item FuncFixtureInfo and transitive fixture closures, autouse/usefixtures name collection, and applying parametrized fixtures to metafuncs.

Read this for how pytest decides which fixtures apply to a given item and how parametrization variants are generated. getfixtureinfo is the entry point tying names, autouse lists and the closure together.

**Depends on.**

- [Fixture declaration API](r5-fixture-declaration.md) · model-inferred · 0 edge(s)
- [Fixture lookup error reporting](r5-fixture-lookup-errors.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Fixture listing from the command line](r5-fixture-introspection.md) · model-inferred · 0 edge(s)
- [Fixture lookup error reporting](r5-fixture-lookup-errors.md) · graph-confirmed · 1 edge(s)
- [Item reordering for high-scope fixtures](r5-fixture-ordering.md) · model-inferred · 0 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (16)

<a id="u-f0f45a635631"></a>
### `FixtureManager`

`class FixtureManager:` · [src/_pytest/fixtures.py:L1501-L1532][f1]

Registry and lookup hub for fixture definitions in a session.

The constructor stores the session and its config, creates _arg2fixturedefs (fixture name to the list of FixtureDefs with that name, order significant), _holderobjseen (dedupes parsed holder objects), seeds _nodeid_autousenames with the ini 'usefixtures' list under the empty nodeid, and registers itself in the plugin manager under 'funcmanage'. Per the class docstring, collection assembles each item's initial fixture names from ini usefixtures, autouse fixtures along the chain, usefixtures markers, and function args, then closes over dependencies. pytest_collection_modifyitems applies the parametrized-setup ordering by replacing items in place with reorder_items(items).

calls: [reorder_items](r5-fixture-ordering.md#u-ae43a2b63b8b)

<a id="u-3d1ec655f99f"></a>
### `FixtureManager._register_fixture`

`def _register_fixture( self, *, name: str, func: _FixtureFunc[object], nodeid: str | …` · [src/_pytest/fixtures.py:L1716-L1770][f1]

Construct a FixtureDef and insert it into the registry.

Builds the FixtureDef from name, func, nodeid, scope, params, ids and autouse (passing _autouse for the deprecation path). Location-less fixtures (from external plugins) are inserted after existing location-less entries but before located ones, so plugin fixtures override conftests; located fixtures are appended. An autouse fixture name is additionally recorded under its nodeid (or '' for global) in _nodeid_autousenames.

calls: [FixtureDef](r5-fixture-lifecycle.md#u-9674c75d4866)

<a id="u-f10c5c5beb21"></a>
### `src/_pytest/fixtures.py:FixtureManager.parsefactories (2)`

`def parsefactories( self, node_or_obj: nodes.Node | object, nodeid: str | NotSetType …` · [src/_pytest/fixtures.py:L1787-L1851][f1]

Collect fixture definitions from a collection node or plain object.

When nodeid is NOTSET the argument must be a node: its underlying object is the holder and its nodeid sets visibility; otherwise the object itself is the holder and the given nodeid (possibly None for global) applies. Each holder object is parsed only once (_holderobjseen). For class or module holders the type itself is scanned to avoid triggering descriptors; otherwise the instance's type is used. For every attribute whose value on the type is a FixtureFunctionDefinition, the fixture name is the marker's explicit name or the attribute name; the attribute is then fetched from the instance (falling back to the type-level value with AttributeError when a renamed fixture cannot be found on a module), the wrapped function extracted, and _register_fixture called with the marker's scope/params/ids/autouse. Attribute access on the type is via safe_getattr, so raising descriptors are skipped.

calls: [FixtureManager._register_fixture](r5-fixture-registry.md#u-3d1ec655f99f)

<a id="u-f5f4e139b022"></a>
### `FixtureManager.pytest_plugin_registered`

`def pytest_plugin_registered(self, plugin: _PluggyPlugin, plugin_name: str) -> None: …` · [src/_pytest/fixtures.py:L1583-L1605][f1]

Parse fixtures of each newly registered plugin, assigning visibility.

For conftest plugins (name ends with 'conftest.py') the conftest path comes from plugin_name (chosen over plugin.__file__ for correct case/normalization, issue #11816); its parent directory relative to rootpath becomes the nodeid, with '.', path errors, or the root itself collapsing to '' — non-conftest plugins get nodeid None (global visibility). Then parsefactories(plugin, nodeid) registers the plugin's fixtures.

calls: [src/_pytest/fixtures.py:FixtureManager.parsefactories (2)](r5-fixture-registry.md#u-f10c5c5beb21)

<a id="u-74db93c21948"></a>
### `FixtureManager.getfixturedefs`

`def getfixturedefs( self, argname: str, node: nodes.Node ) -> Sequence[FixtureDef[Any…` · [src/_pytest/fixtures.py:L1853-L1871][f1]

Return the FixtureDefs for a name that apply to a node.

A KeyError on _arg2fixturedefs returns None — no fixture with this name exists anywhere; otherwise the registered defs are filtered through _matchfactories and returned as a tuple, which is empty when definitions exist but none is visible to the node. This None-vs-empty distinction drives the two FixtureLookupError cases in the request resolution.

calls: [FixtureManager._matchfactories](r5-fixture-registry.md#u-981f0e2a96c9)

<a id="u-c2364ca443d7"></a>
### `FixtureManager.getfixtureclosure`

`def getfixtureclosure( self, parentnode: nodes.Node, initialnames: tuple[str, ...], i…` · [src/_pytest/fixtures.py:L1625-L1656][f1]

Compute the transitive fixture-name closure for an item plus the fixturedefs for every name in it.

Starting from initialnames, repeatedly scans the closure and, for each name not in ignore_args and not yet resolved, looks up getfixturedefs; non-empty results are stored in arg2fixturedefs and the closest definition's own argnames are appended to the closure. The loop stops when a pass adds nothing. Afterwards the closure is sorted by the scope of each name's closest fixturedef (missing names count as Function scope), descending, so wider-scoped fixtures initialize first; the closure and map are returned.

calls: [FixtureManager.getfixturedefs](r5-fixture-registry.md#u-74db93c21948)

<a id="u-981f0e2a96c9"></a>
### `FixtureManager._matchfactories`

`def _matchfactories( self, fixturedefs: Iterable[FixtureDef[Any]], node: nodes.Node )…` · [src/_pytest/fixtures.py:L1873-L1879][f1]

Yield the fixturedefs whose baseid is among the nodeids of the node's parents.

Collects all ancestor nodeids into a set, then filters the given fixturedefs by membership, implementing conftest-style visibility (empty baseid matches everything since '' is a prefix of every chain that includes the root).

**Uncertainties.**

- Whether '' baseid matches nodes whose chain omits the root nodeid is not proven from this file.

<a id="u-f48168522704"></a>
### `FixtureManager.getfixtureinfo`

`def getfixtureinfo( self, node: nodes.Item, func: Callable[..., object] | None, cls: …` · [src/_pytest/fixtures.py:L1547-L1581][f1]

Compute the FuncFixtureInfo for an item.

If the item has a function and does not set nofuncargs, argnames come from getfuncargnames (class-aware for methods), otherwise empty. Initial names are the de-duplicated union of autouse names along the node chain, usefixtures names, and argnames. Direct (non-indirect) parametrize args are excluded via _get_direct_parametrize_args and passed as ignore_args to getfixtureclosure, whose closure and arg2fixturedefs are returned inside a new FuncFixtureInfo.

calls: [FixtureManager.getfixtureclosure](r5-fixture-registry.md#u-c2364ca443d7), [deduplicate_names](r5-fixture-registry.md#u-9088c01d90da)

<a id="u-33076d658922"></a>
### `FuncFixtureInfo`

`class FuncFixtureInfo:` · [src/_pytest/fixtures.py:L313-L344][f1]

Static fixture-requirement record for an item known at collection time.

Holds argnames requested as function parameters, initialnames (argnames plus usefixtures and autouse), the transitive names_closure, and name2fixturedefs mapping each closure name to applicable FixtureDefs ordered furthest-to-closest. Dynamic getfixturevalue dependencies are deliberately excluded. Uses __slots__ and is a frozen dataclass; prune_dependency_tree is its only behavior.

<a id="u-855e63ca15f8"></a>
### `FuncFixtureInfo.prune_dependency_tree`

`def prune_dependency_tree(self) -> None:` · [src/_pytest/fixtures.py:L344-L369][f1]

Recompute names_closure from initialnames and name2fixturedefs, only ever shrinking it and preserving original order.

A working set seeded with initialnames is walked: a name joins the closure only if it was already in the old closure (dropping new dependencies such as the pseudo 'request' of direct-param fixtures) and, when it has fixturedefs, the closest definition's argnames are enqueued. names_closure is finally rewritten in place, sorted by position in the old closure, so the result is a subset. Direct parametrization can shadow fixtures, which is why this pruning exists.

<a id="u-e0654ec508be"></a>
### `FixtureManager._getautousenames`

`def _getautousenames(self, node: nodes.Node) -> Iterator[str]:` · [src/_pytest/fixtures.py:L1607-L1612][f1]

Yield autouse fixture names visible to a node.

Walks node.listchain() and yields the names recorded in _nodeid_autousenames for each ancestor nodeid, so autouse fixtures from wider scopes are inherited.

<a id="u-ac864561b8c1"></a>
### `FixtureManager._getusefixturesnames`

`def _getusefixturesnames(self, node: nodes.Item) -> Iterator[str]:` · [src/_pytest/fixtures.py:L1614-L1623][f1]

Yield fixture names from the node's usefixtures markers, node-by-node via iter_markers_with_node.

A usefixtures marker without arguments produces no names and warns with a PytestWarning naming the nodeid; the names of each marker's args are yielded in order.

<a id="u-64a53c9a9ef2"></a>
### `_get_direct_parametrize_args`

`def _get_direct_parametrize_args(node: nodes.Node) -> set[str]:` · [src/_pytest/fixtures.py:L1476-L1492][f1]

Collect parametrize argument names that a node parametrizes directly, so they are not mistaken for fixtures.

Iterates the node's 'parametrize' markers; those without a truthy 'indirect' kwarg have their argument names parsed via ParameterSet._parse_parametrize_args and accumulated into the returned set. Indirect parametrization is excluded because indirect args are still fixture names.

<a id="u-9088c01d90da"></a>
### `deduplicate_names`

`def deduplicate_names(*seqs: Iterable[str]) -> tuple[str, ...]:` · [src/_pytest/fixtures.py:L1495-L1498][f1]

De-duplicate names across several iterables while preserving first-occurrence order, returning a tuple.

Uses dict.fromkeys over the chained sequences because plain sets do not keep insertion order.

<a id="u-bdcc628fbd1a"></a>
### `src/_pytest/fixtures.py:FixtureManager.pytest_generate_tests`

`def pytest_generate_tests(self, metafunc: Metafunc) -> None:` · [src/_pytest/fixtures.py:L1672-L1710][f1]

Apply parametrized fixtures to a metafunc, generating test variants.

For each name in metafunc.fixturenames: names without fixturedefs are skipped (they will fail at setup if not parametrized elsewhere); names the test itself parametrizes (its own parametrize marks, checked via the nested get_parametrize_mark_argnames helper) are skipped so the test's parametrization wins. Otherwise fixturedefs are walked from closest to furthest: the first with params is applied via metafunc.parametrize(indirect=True, with the def's scope and ids) and the loop breaks; a def that does not itself request the overridden name breaks too; only when an overriding fixture requests its super fixture does the search continue for a parametrized super fixture (#1953).

calls: [Metafunc.parametrize](r7-py-parametrization.md#u-8c79ced9d8b3)

<a id="u-bc876a4a750d"></a>
### `pytest_sessionstart`

`def pytest_sessionstart(session: Session) -> None:` · [src/_pytest/fixtures.py:L119-L120][f1]

Create the session's FixtureManager at session start.

Assigns a new FixtureManager(session) to session._fixturemanager, making fixture registration available for the whole run; runs once per session via the pytest_sessionstart hook.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
