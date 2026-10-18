# Collection Tree Construction

**Capability.** src/_pytest/main.py's collector machinery: Session as root collector walks initial arguments, resolves '::'-separated collection arguments (CollectionArgument/search_pypath), creates Dir collectors per directory, skips venvs and ignored paths, dedups nodes, and dispatches per-path hook calls through FSHookProxy so only conftest-active plugins fire.

Read this to understand how filesystem paths and --pyargs names become collectors and items. perform_collect orchestrates _collect_path/collect/genitems and applies --deselect via pytest_collection_modifyitems.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (17)

<a id="u-64f8023599e4"></a>
### `CollectionArgument`

`class CollectionArgument:` · [src/_pytest/main.py:L1024-L1030][f1]

Frozen dataclass holding a resolved collection argument: `path` (the absolute filesystem path), `parts` (the `::`-separated node-name selection parts after the path), and `module_name` (the original dotted name when the argument was resolved via --pyargs, else None).

Pure value holder with no behavior.

<a id="u-195bad91faaf"></a>
### `Dir`

`class Dir(nodes.Directory):` · [src/_pytest/main.py:L495-L508][f1]

Filesystem directory collector (pytest 8.0+); the default collector for non-Package directories.

Its `from_parent` classmethod is the public constructor, forwarding parent and path through the base Collector machinery (signature differs from the base, hence the override ignore). `collect` scans entries with `scandir`: for directories, it consults `pytest_ignore_collect` only when the path is not an init path (init paths and their parents bypass the ignore check), then yields whatever `pytest_collect_directory` returns, skipping None; for files, the same ignore/initpath gate applies before yielding the collectors returned by `pytest_collect_file`. Entries that are neither directory nor file are skipped. This is how `__pycache__`, norecursedirs, and venv filtering (via pytest_ignore_collect) prune recursion.

group: [Dir](r8-collection-tree.md#u-195bad91faaf); uses: [Session](r8-collection-tree.md#u-ec1f807fa46d)

**Uncertainties.**

- Which plugin handles `pytest_collect_file`/`pytest_collect_directory` is plugin-manager resolved; the source shows only the ihook dispatch with multiple hook candidates.

<a id="u-d24c9ae8df26"></a>
### `FSHookProxy`

`class FSHookProxy:` · [src/_pytest/main.py:L458-L459][f1]

Lazy proxy that exposes hook callers with certain plugins removed.

`__init__` stores the plugin manager and the set of plugins to remove. Any attribute access via `__getattr__` creates (once, caching in `__dict__`) a `pm.subset_hook_caller(name, remove_plugins=remove_mods)`, so hooks fired through the proxy exclude those plugins. Cache-on-first-access means each hook name resolves to one stable caller per proxy.

<a id="u-ec1f807fa46d"></a>
### `Session`

`class Session(nodes.Collector):` · [src/_pytest/main.py:L547-L562][f1]

Root collector of the collection tree, also registered on the plugin manager under the name "session" so its hookimpls (collectstart, runtest_logreport, collectreport) fire.

`__init__` builds the node with empty name/nodeid at config.rootpath, initializes counters (`testsfailed`, `testscollected`), stop flags, a collection trace logger, empty initial-path sets, notfound/initial-parts lists, a collector-to-report cache, the items list, and a `_bestrelpath_cache` rooted at rootpath for cheap relative path formatting. Class attributes alias Interrupted/Failed so `session.Interrupted`/`session.Failed` work; `_setupstate` and `_fixturemanager` are annotated but set externally (by runner and fixtures sessionstart hooks). The shouldstop/shouldfail property setters enforce one-way semantics: attempting to reset a previously set flag to False warns with PytestWarning and ignores the assignment, because the runner assumes a set flag means definite stop.

uses: [Interrupted](r8-session-lifecycle.md#u-17059579b102), [Failed](r8-session-lifecycle.md#u-477de989a11f), [_bestrelpath_cache](r8-collection-tree.md#u-edac9fd75e4c); group: [Session](r8-collection-tree.md#u-ec1f807fa46d)

<a id="u-edac9fd75e4c"></a>
### `_bestrelpath_cache`

`class _bestrelpath_cache(dict[Path, str]):` · [src/_pytest/main.py:L483-L489][f1]

A dict subclass acting as a memoizing relative-path cache: keyed by Path, valued by the best-relative-path string from a fixed base path (a dataclass field).

On a missing key, `__missing__` computes `bestrelpath(self.path, path)`, stores it, and returns it, so repeated lookups avoid recomputing the relatively slow bestrelpath call. Used by Session for displaying node locations relative to rootpath.

<a id="u-7d3bd364a653"></a>
### `_in_venv`

`def _in_venv(path: Path) -> bool:` · [src/_pytest/main.py:L375-L393][f1]

Detects whether the given path is the root of a virtual environment: True if `pyvenv.cfg` (PEP 405) or `conda-meta/history` (conda regression guard) exists as a file directly under it.

Any OSError raised by the file checks (e.g. permission errors) is swallowed and yields False.

**Uncertainties.**

- Whether existence of either marker file truly implies a usable environment root is a heuristic inherited from the docstring; only the file checks are observable.

<a id="u-bc3f885ca9df"></a>
### `src/_pytest/main.py:pytest_collect_directory`

`def pytest_collect_directory( path: Path, parent: nodes.Collector ) -> nodes.Collecto…` · [src/_pytest/main.py:L434-L437][f1]

Default `pytest_collect_directory` hook: unconditionally creates a Dir collector under the given parent for the given path.

Returning the Dir (never None) means every directory reached during collection gets one unless a `pytest_ignore_collect` hook already vetoed it.

calls: [Dir](r8-collection-tree.md#u-195bad91faaf)

<a id="u-57a76068e198"></a>
### `src/_pytest/main.py:pytest_collection_modifyitems`

`def pytest_collection_modifyitems(items: list[nodes.Item], config: Config) -> None:` · [src/_pytest/main.py:L440-L455][f1]

Default `pytest_modifyitems` hook implementing `--deselect`: builds a tuple of deselect node-id prefixes; returns immediately when none.

Otherwise partitions items into those whose nodeid `startswith` any prefix (deselected) and the rest, then if any were deselected fires the `pytest_deselected` hook and rewrites `items[:]` in place to only the remaining items, so callers holding the same list see the change.

calls: [Config.getoption](r2-config-ini-options.md#u-957f13292f77)

<a id="u-3a1dcae63310"></a>
### `src/_pytest/main.py:pytest_ignore_collect`

`def pytest_ignore_collect(collection_path: Path, config: Config) -> bool | None:` · [src/_pytest/main.py:L396-L431][f1]

Default `pytest_ignore_collect` hook deciding whether a candidate path should be skipped during collection; returns True to ignore, None to allow (None lets later hooks decide).

Checks in order: any `__pycache__` path is ignored; the conftest-provided `collect_ignore` path list plus `--ignore` option paths (each absolutized) cause ignoring on exact membership; conftest `collect_ignore_glob` plus `--ignore-glob` option patterns cause ignoring on fnmatch of the path string; unless `--collect-in-virtualenv` is set, a path detected as a venv root by `_in_venv` is ignored; and for directories, matching any `norecursedirs` ini pattern via `fnmatch_ex` causes ignoring (file paths skip this check). Conftest lists are fetched relative to the collection path's parent, so entries resolve against that directory.

calls: [_in_venv](r8-collection-tree.md#u-7d3bd364a653), [Config._getconftest_pathlist](r2-config-ini-options.md#u-ab8d07df0c0d), [Config.getini](r2-config-ini-options.md#u-22f06e7bb7ce)

<a id="u-03b1ae1e56bd"></a>
### `resolve_collection_argument`

`def resolve_collection_argument( invocation_path: Path, arg: str, *, as_pypath: bool …` · [src/_pytest/main.py:L1033-L1104][f1]

Parses a command-line collection argument like `pkg/tests/test_foo.py::TestClass::test_foo` into a CollectionArgument.

It splits at the first `[` so a parametrization bracket attaches to the last name part (e.g. `test_foo[param]`), then splits the remainder on `::` into path and parts. When `as_pypath` (--pyargs) is set, the path portion is looked up as a module via `search_pypath`; on success the found filesystem path is used and `module_name` records the original dotted name. The path is joined with the invocation directory and absolutized. Failure paths: a nonexistent path raises UsageError with a message that, for pypath mode, hints at a missing `__init__.py`; selection parts combined with a directory path raise UsageError (message differs per pypath mode: package vs directory). Otherwise returns the frozen CollectionArgument.

calls: [search_pypath](r8-collection-tree.md#u-c8bd1c24b038); uses: [CollectionArgument](r8-collection-tree.md#u-64f8023599e4)

**Uncertainties.**

- `safe_exists` semantics (e.g. handling of broken symlinks) come from _pytest.pathlib and are not visible here.

<a id="u-c8bd1c24b038"></a>
### `search_pypath`

`def search_pypath( module_name: str, *, consider_namespace_packages: bool = False ) -…` · [src/_pytest/main.py:L988-L1021][f1]

Resolves a dotted module name via `importlib.util.find_spec`, returning None on AttributeError (name looks like a package but is a filename), ImportError (missing module), or ValueError (not a module name), or when the spec is None.

For a simple module (no submodule_search_locations or an empty list) it returns `spec.origin`, the module's file path. For packages: with `consider_namespace_packages` it returns the first submodule search location (also chosen when the package has no physical origin, e.g. an empty-location namespace package); without that flag, a None origin (namespace package) yields None, otherwise the dirname of the origin (the package directory). Returns a string path or None.

**Uncertainties.**

- Whether returning the first search location for namespace packages with multiple locations is sufficient is acknowledged in a comment as documentation-based; only single-entry behavior is observable here.

<a id="u-47215393ae0e"></a>
### `Session._collect_one_node`

`def _collect_one_node( self, node: nodes.Collector, handle_dupes: bool = True, ) -> t…` · [src/_pytest/main.py:L834-L845][f1]

Collects one collector node with dedup: when the node is already in the session's collection cache and handle_dupes is True, returns the cached CollectReport and True (duplicate).

Otherwise calls `collect_one_node(node)`, caches its report, and returns it with False. The returned duplicate flag lets callers skip re-reporting or re-expansion of already-collected nodes.

<a id="u-fbe5871fee3a"></a>
### `Session._collect_path`

`def _collect_path( self, path: Path, path_cache: dict[Path, Sequence[nodes.Collector]…` · [src/_pytest/main.py:L707-L736][f1]

Creates collectors for one path of an initial argument, memoized by the supplied path_cache so repeated paths return identical collector tuples.

Directories get a collector via the ihook `pytest_collect_directory` (hook proxy for the parent path) or an empty tuple if it returns None; files get whatever `pytest_collect_file` returns; anything else (broken symlink or missing path) yields an empty tuple. Results are stored in the cache before returning.

**Uncertainties.**

- Which plugins handle the collect hooks is plugin-manager resolved (multiple candidates in the graph).

<a id="u-d0b16a7a20b4"></a>
### `Session.collect`

`def collect(self) -> Iterator[nodes.Item | nodes.Collector]: # This is a cache for th…` · [src/_pytest/main.py:L847-L966][f1]

Generator that walks each initially requested collection argument and yields the matched nodes (collectors or items).

For each argument it builds a root-down path list: for plain paths, all parents still within confcutdir are prepended; for `--pyargs` module arguments, only parents whose stems match the dotted module name are prepended. It then works a stack of (node, remaining parts): when parts are exhausted the node is yielded and the initial part is marked matched; non-collector nodes with parts remaining are discarded. The Session level collects its path part directly via `_collect_path` (avoiding recursion); other collectors go through `_collect_one_node` — dedup is disabled when a single file path part remains so command-line duplicate files are still collected twice — and a failed (non-passed) report is reported via the node's ihook when first seen, then prunes that branch. Matching compares the next Path part against node.path, with a Windows fallback to os.path.samefile for short-path mismatches that additionally requires link-ness to agree (avoiding duplicate matches of linked files, #12039); name parts match node.name either exactly or ignoring a `[...]` parametrization suffix. When nothing in an initial part matched, `(argpath::names, unmatched_collectors)` is appended to `self._notfound` for perform_collect to turn into a UsageError.

calls: [Session._collect_path](r8-collection-tree.md#u-fbe5871fee3a), [Session._collect_one_node](r8-collection-tree.md#u-47215393ae0e), [PytestPluginManager._is_in_confcutdir](r2-config-plugin-manager.md#u-8030a7e104e3)

**Uncertainties.**

- os.path.samefile behavior on Windows short paths is relied on but not verifiable from this source.
- The exact ihook plugin handling pytest_collect_file for a given path is plugin-manager resolved (multiple hook candidates).

<a id="u-041a9ade5adc"></a>
### `Session.genitems`

`def genitems(self, node: nodes.Item | nodes.Collector) -> Iterator[nodes.Item]:` · [src/_pytest/main.py:L968-L985][f1]

Recursively expands a collector or yields a single item, emitting collection reports.

For an Item, fires `pytest_itemcollected` and yields it. For a Collector, reads `--keep-duplicates`; dedup handling applies only to nodes that are File instances, so non-file collectors always handle dupes. Calls `_collect_one_node`: a duplicate result is silently skipped (return) unless keepduplicates is set; a passed report causes recursion into `genitems` for each sub-node; a non-duplicate node gets its report fired via its ihook regardless of pass/fail, ensuring failed imports surface as collect reports.

calls: [Session._collect_one_node](r8-collection-tree.md#u-47215393ae0e)

<a id="u-e7f68fdf4b39"></a>
### `Session.gethookproxy`

`def gethookproxy(self, fspath: os.PathLike[str]) -> pluggy.HookRelay: # Optimization:…` · [src/_pytest/main.py:L690-L705][f1]

Returns the hook relay to use for a given path: fetches the conftest modules active at that path via the plugin manager, computes which globally-registered conftest plugins are NOT active there, and if any exist wraps an FSHookProxy (which removes those plugins from each hook caller) in a PathAwareHookProxy; otherwise, when all conftest plugins are active, returns the config's normal hook relay directly.

calls: [PytestPluginManager._getconftestmodules](r2-config-plugin-manager.md#u-c646f5477aac); uses: [FSHookProxy](r8-collection-tree.md#u-d24c9ae8df26)

<a id="u-71c6b6672ba8"></a>
### `src/_pytest/main.py:Session.perform_collect (2)`

`def perform_collect( self, args: Sequence[str] | None = None, genitems: bool = True )…` · [src/_pytest/main.py:L748-L832][f1]

Runs the whole collection phase for the session and returns collected items (or collectors when genitems=False).

Defaults args to config.args; resets `_notfound`, `_initial_parts`, `_collection_cache`, and `self.items` at start and again in the finally block. For each argument, resolves it via `resolve_collection_argument` (honoring `--pyargs` and the namespace-packages ini) and records its path plus all parents in the initial-path frozensets. Then collects the session node itself, reports it, and: if any arguments were not found, raises UsageError with per-argument messages listing the collectors searched; if genitems is False, returns the raw collector result leaving session.items empty; otherwise recursively expands each collected node into `self.items`. Fires `pytest_collection_modifyitems` (which applies --deselect), and in the finally block always fires `pytest_collection_finish`; `testscollected` is updated only when genitems is True. `check_pending` on the plugin manager runs before modifyitems and can raise on unregistered hook implementations.

calls: [resolve_collection_argument](r8-collection-tree.md#u-03b1ae1e56bd), [Session.genitems](r8-collection-tree.md#u-041a9ade5adc); uses: [Session._collect_one_node](r8-collection-tree.md#u-47215393ae0e)

**Uncertainties.**

- Exact failure order between check_pending and UsageError paths depends on upstream hook implementations not shown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/main.py
