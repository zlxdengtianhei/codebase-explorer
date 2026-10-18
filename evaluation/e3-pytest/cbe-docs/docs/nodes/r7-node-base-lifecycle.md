# Node Base and Lifecycle

**Capability.** The Node base class and its construction/lookup machinery: NodeMeta forcing from_parent construction, path/fspath resolution (_imply_path, FSCollector.__init__, _check_initialpaths_for_relpath), marker APIs (add_marker, iter_markers, get_closest_marker), ancestor lookup (getparent), finalizer delegation, warning attribution, and failure rendering (_repr_failure_py).

Use these units when implementing a Node subclass or needing parent/marker/location services. All tree wiring goes through from_parent; Node.__init__ resolves paths and registers the node with the session.

Parent: [Collection Tree Core \(nodes.py\)](r7-collection-tree-core.md)

## Units (15)

<a id="u-fadcae42d5de"></a>
### `Node`

`class Node(abc.ABC, metaclass=NodeMeta):` · [src/_pytest/nodes.py:L128-L156][f1]

Abstract base of the collection tree: Collectors are internal nodes, Items are leaves.

Construction is blocked by NodeMeta and must go through from_parent. Beyond its constructor (separate unit) it supplies tree navigation and marker/keyword bookkeeping. ``iter_parents`` yields self then each ancestor until parent is None; ``listchain`` returns the same chain reversed, root first. ``nodeid`` is a read-only ``::``-separated address; ``__hash__`` hashes that nodeid, so identity is nodeid equality. ``__repr__`` shows class name and ``name``. ``setup``/``teardown`` are no-op hooks; ``listextrakeywords`` unions ``extra_keyword_matches`` over the whole chain; ``listnames`` maps ``listchain`` to names.

**Uncertainties.**

- fspath is declared but implemented in the legacypath plugin, so its runtime value is not observable in this file.

<a id="u-8e70554d9082"></a>
### `NodeMeta`

`class NodeMeta(abc.ABCMeta):` · [src/_pytest/nodes.py:L84-L99][f1]

Metaclass of Node that forces construction to go through from_parent.

Its ``__call__`` unconditionally raises Outcomes Failed (via ``fail``) with a deprecation message naming the class, so ``SomeNode(...)`` never builds an instance. ``_create`` is the sanctioned bypass: it invokes ``super().__call__`` (the real abc.ABCMeta construction), and on TypeError — a non-cooperative subclass constructor that rejects the injected ``parent`` kwarg — it filters kwargs to the ``__init__`` signature, emits a PytestDeprecationWarning listing the accepted keywords, and retries with only the known kwargs.

raises: [outcomes.py module code (L1–L13)](r4-outcomes-api.md#u-58f8b4f3406b), [warning_types.py:warning-classes](r3-warning-types.md#u-10c8ce561005)

**Uncertainties.**

- The retry in _create passes positional args ``*k`` unchanged; behavior when positional args accompany a non-cooperative constructor is not visible here.

<a id="u-dcd61aca83fe"></a>
### `Node.__init__`

`def __init__( self, name: str, parent: Node | None = None, config: Config | None = No…` · [src/_pytest/nodes.py:L156-L215][f1]

Wire a Node into the collection tree.

``name`` and ``parent`` are stored; ``config`` and ``session`` are taken from arguments or inherited from the parent, raising TypeError('config or parent must be provided') / TypeError('session or parent must be provided') when neither is available. The path is resolved with ``_imply_path``: with neither path nor fspath the parent's path is inherited; a supplied fspath triggers the NODE_CTOR_FSPATH_ARG deprecation warning (and ``_check_path`` validation when path is also given). Keywords become a NodeKeywords mapping, ``own_markers`` starts empty, extra keyword matches an empty set. ``nodeid`` is used as-is (asserting it contains no '::()') or built as parent.nodeid + '::' + name, raising TypeError('nodeid or parent must be provided') when neither is available. Finally a fresh Stash is created and aliased as the deprecated ``_store``.

**Notes.**

- side_effect: Instantiation must go through NodeMeta._create; calling Node(...) directly fails in the metaclass before this body runs.

calls: [_imply_path](r7-node-base-lifecycle.md#u-ecc047d39bf2)

<a id="u-46401c028aa9"></a>
### `Node.from_parent`

`def from_parent(cls, parent: Node, **kw) -> Self:` · [src/_pytest/nodes.py:L217-L233][f1]

Public named constructor that injects ``parent`` into the kwargs passed to ``cls._create``.

It rejects ``config`` and ``session`` keyword arguments with TypeError since those must flow through the parent, then delegates construction to the metaclass bypass, letting subclasses override from_parent and chain via super().

calls: [NodeMeta](r7-node-base-lifecycle.md#u-8e70554d9082)

<a id="u-bae899dceced"></a>
### `Node.add_marker`

`def add_marker(self, marker: str | MarkDecorator, append: bool = True) -> None:` · [src/_pytest/nodes.py:L316-L336][f1]

Attach a marker to this node at runtime.

A MarkDecorator is used directly, a string is looked up as an attribute of the global mark generator (so unknown marks raise AttributeError from the getattr), and any other type raises ValueError. The decorator is stored under its name in ``self.keywords`` and its Mark appended to ``own_markers`` (append=True) or inserted at position 0 (append=False), which changes marker lookup order for shadowing.

uses: [structures.py module code (L1–L44)][f2]

<a id="u-86150a89c844"></a>
### `Node.addfinalizer`

`def addfinalizer(self, fin: Callable[[], object]) -> None:` · [src/_pytest/nodes.py:L384-L391][f1]

Register a zero-argument callable to run when this node is finalized, by delegating to the session's current SetupState.

It only works while the node is active in the setup chain (e.g. during setup); behavior when called outside that window is determined by SetupState.addfinalizer, which is not part of this file.

uses: [method::SetupState.addfinalizer::0][f3]

**Uncertainties.**

- Failure mode when the node is not in the active setup chain depends on runner.SetupState, not shown in this file.

<a id="u-f7ae472266a7"></a>
### `Node.iter_markers`

`def iter_markers(self, name: str | None = None) -> Iterator[Mark]:` · [src/_pytest/nodes.py:L338-L344][f1]

Iterate this node's markers, closest first.

``iter_markers`` yields just the Mark objects; ``iter_markers_with_node`` yields (owning Node, Mark) pairs. Both walk ``iter_parents`` (self upward) and, for each node, its ``own_markers`` in insertion order; when ``name`` is given only marks whose ``name`` attribute equals it are yielded, otherwise all marks pass. Results are a lazy generator.

uses: [Node](r7-node-base-lifecycle.md#u-fadcae42d5de)

<a id="u-b01e79480583"></a>
### `src/_pytest/nodes.py:Node.get_closest_marker (2)`

`def get_closest_marker(self, name: str, default: Mark | None = None) -> Mark | None:` · [src/_pytest/nodes.py:L365-L372][f1]

Return the nearest marker with the given name, searching from this node outward via ``iter_markers``; ``default`` (None unless supplied) is returned when no match exists.

The two @overload stubs only refine typing: with a supplied default the return type drops the None.

calls: [Node.iter_markers](r7-node-base-lifecycle.md#u-f7ae472266a7)

<a id="u-f0c5b3d0a850"></a>
### `Node.getparent`

`def getparent(self, cls: type[_NodeType]) -> _NodeType | None:` · [src/_pytest/nodes.py:L393-L403][f1]

Find the closest ancestor (self included) that is an instance of the given node class; returns None when the chain ends without a match.

Generic over the requested type so the returned node is typed as that class.

uses: [Node](r7-node-base-lifecycle.md#u-fadcae42d5de)

<a id="u-6f5627aa244f"></a>
### `Node.warn`

`def warn(self, warning: Warning) -> None:` · [src/_pytest/nodes.py:L243-L276][f1]

Emit a warning attributed to this node's source location.

Non-Warning values raise ValueError before anything is emitted. The location comes from ``get_fslocation_from_item``; the line number is asserted non-None, incremented by one, and passed with the path to ``warnings.warn_explicit`` with category None, so the warning surfaces as if raised at the node's code location and is reported at session end unless suppressed.

calls: [get_fslocation_from_item](r7-node-base-lifecycle.md#u-113b472cf60a)

**Uncertainties.**

- warn_explicit is called with category=None; how warning category matching/suppression behaves in that case is decided by the stdlib warnings machinery, not shown here.

<a id="u-0eac6f0bd989"></a>
### `Node._repr_failure_py`

`def _repr_failure_py( self, excinfo: ExceptionInfo[BaseException], style: TracebackSt…` · [src/_pytest/nodes.py:L408-L464][f1]

Build the terminal representation of a failure for this node, applying several overrides before formatting.

A ConftestImportFailure is replaced by ExceptionInfo of its underlying cause. A Failed (fail.Exception) without pytrace forces style 'value'. A FixtureLookupError returns its own formatted repr instead of a traceback. With the ``fulltrace`` option, style becomes 'long' and no traceback filtering is applied; otherwise ``_traceback_filter`` filters the traceback and 'auto' style is upgraded to 'long'. When style is still None the ``tbstyle`` option decides ('short' or default 'long'). Locals truncation is disabled above verbosity 1, args truncation disabled above verbosity 2. Paths are shown absolute whenever os.getcwd() differs from the invocation dir (or getcwd raises OSError), avoiding misleading relative paths after CWD changes. Finally returns ``excinfo.getrepr`` with funcargs, locals/args truncation and the chosen style/filter.

uses: [Node._repr_failure_py](r7-node-base-lifecycle.md#u-0eac6f0bd989); calls: [ExceptionInfo.getrepr](r1-code-exception-info.md#u-adfe45903a4e)

<a id="u-ecc047d39bf2"></a>
### `_imply_path`

`def _imply_path( node_type: type[Node], path: Path | None, fspath: LEGACY_PATH | None…` · [src/_pytest/nodes.py:L60-L78][f1]

Resolve a Node constructor's path/fspath pair into a pathlib.Path.

If ``fspath`` is given it first warns with NODE_CTOR_FSPATH_ARG naming the node class. If ``path`` is given it is returned (after ``_check_path`` cross-checking the two when both are present); if ``path`` is None, ``fspath`` is asserted non-None and converted via ``Path(fspath)``. The emitted warning and the returned path ordering are the only observable effects.

uses: [deprecated.py module code (L1–L88)][f4], [__init__.py module code (L1–L90)][f5]; calls: [UnformattedWarning](r3-warning-types.md#u-ed063feb7bcd)

<a id="u-0171ade41f01"></a>
### `_check_initialpaths_for_relpath`

`def _check_initialpaths_for_relpath( initial_paths: frozenset[Path], path: Path ) -> …` · [src/_pytest/nodes.py:L546-L557][f1]

Compute a nodeid-relative path string for a path against the session's initial paths.

Empty string if the path itself is initial; the path relative to the first matching ancestor directory otherwise; None if no initial path matches. ``lru_cache(maxsize=1000)`` memoizes per (frozenset, path) pair, so results are shared across calls for identical inputs.

**Notes.**

- side_effect: The lru_cache keeps (initial_paths, path) keys alive up to 1000 entries across the process.

<a id="u-113b472cf60a"></a>
### `get_fslocation_from_item`

`def get_fslocation_from_item(node: Node) -> tuple[str | Path, int | None]:` · [src/_pytest/nodes.py:L480-L496][f1]

Best-effort source location of a node as (path, 0-based lineno).

Preference order: the node's ``location`` attribute, returning its first two elements; else ``obj``, located via ``getfslineno``; else the node's ``path`` (or the literal 'unknown location') with lineno -1 when no line is known.

uses: [function::getfslineno::0][f6]

<a id="u-edc79db75f55"></a>
### `FSCollector.__init__`

`def __init__( self, fspath: LEGACY_PATH | None = None, path_or_parent: Path | Node | …` · [src/_pytest/nodes.py:L563-L615][f1]

Filesystem collector construction with flexible legacy signatures.

``path_or_parent`` disambiguates: a Node becomes the parent (asserting parent was not also given), a Path becomes ``path`` (asserting path was not given). The path is normalized through ``_imply_path`` (so a legacy fspath triggers the NODE_CTOR_FSPATH_ARG deprecation warning). When no name is given it defaults to the path's final component, or the '/'-separated path relative to the parent when the parent has a different path (ValueError from relative_to keeps the bare name). With no session, the parent's session is asserted and used. The nodeid defaults to the path relative to rootpath, falling back to ``_check_initialpaths_for_relpath`` when that fails, with os separators normalized to '/'. Finally Node.__init__ is called with the resolved values.

**Notes.**

- failure: The asserts on path_or_parent/parent and path combinations and on parent presence when session is None raise AssertionError on inconsistent legacy call shapes.

calls: [_imply_path](r7-node-base-lifecycle.md#u-ecc047d39bf2), [_check_initialpaths_for_relpath](r7-node-base-lifecycle.md#u-0171ade41f01), [Node.__init__](r7-node-base-lifecycle.md#u-dcd61aca83fe)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/nodes.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/mark/structures.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/runner.py
[f4]: ../../../../../../eval/pytest-5989efe/src/_pytest/deprecated.py
[f5]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
[f6]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
