# Cross-Session Cache Provider

**Capability.** Persists JSON values under .pytest_cache across sessions and builds the --lf/--ff/--nf filtering plugins on top of those cache entries, plus the cache fixture, --cache-show/--cache-clear options, and the cachedir report header. Grouped because the plugins and CLI all read/write through the single Cache object.

Use the cache fixture (Cache.get/set/mkdir) for cross-session state; LFPlugin/NFPlugin consume lastfailed/nodeids entries to reorder or deselect collection. pytest_configure wires Cache and both plugins; cacheshow short-circuits the whole session for --cache-show.

**Depends on.**

- [Ini & Option Value Access](r2-config-ini-options.md) · graph-confirmed · 8 edge(s) · Cache and the LF/NF plugins read their options via Config.getini and Config.getoption.
- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · model-inferred · 0 edge(s)
- [Filesystem & Import Path Utilities](r2-path-utils.md) · graph-confirmed · 2 edge(s) · Cache.clear_cache and cache-directory resolution use rm_rf and resolve_from_str from the path helpers.

Parent: [Pytest Codebase](r2-pytest-root.md)

## Units (19)

<a id="u-c7b89217c764"></a>
### `Cache`

`class Cache:` · [src/_pytest/cacheprovider.py:L55-L69][f1]

Cache is the object behind the `cache` fixture, persisting JSON values under a cache directory across pytest sessions.

Values live under the `v` sub-directory via `_getvaluepath` (key may contain `/`, mapping to nested paths); directories created by `mkdir` live under `d`. `__init__` stores cachedir/config and enforces internal construction via `check_ispytest`. `cache_dir_from_config` resolves the `cache_dir` ini value (default `.pytest_cache`, or under `TOX_ENV_DIR` if set) against the rootpath. `warn` emits a `PytestCacheWarning` through the config hook with stacklevel 3. `_mkdir` first ensures the cache dir and its supporting files exist, then creates the target path with parents. Trivial boundaries: `_getvaluepath` does no validation of the key.

calls: [Cache._ensure_cache_dir_and_supporting_files](r2-cache-provider.md#u-076713cac7a0), [Cache](r2-cache-provider.md#u-c7b89217c764)

<a id="u-9a4fd3fa6b8f"></a>
### `Cache.for_config`

`def for_config(cls, config: Config, *, _ispytest: bool = False) -> Cache:` · [src/_pytest/cacheprovider.py:L76-L86][f1]

Creates the session Cache: resolves the configured cache dir, and clears the cached directories/values sub-directories when the `--cache-clear` option is set and the directory exists.

Returns a Cache built with internal-construction validation; calling without `_ispytest=True` raises.

calls: [Cache.clear_cache](r2-cache-provider.md#u-b889b5a2c7ff), [Cache](r2-cache-provider.md#u-c7b89217c764)

<a id="u-076713cac7a0"></a>
### `Cache._ensure_cache_dir_and_supporting_files`

`def _ensure_cache_dir_and_supporting_files(self) -> None:` · [src/_pytest/cacheprovider.py:L203-L246][f1]

Idempotently creates the cache directory with its README.md, .gitignore, and CACHEDIR.TAG files.

Fast-returns if the cachedir already exists. Otherwise it creates the parent, builds everything inside a temporary sibling directory with permissions set to 0o777 minus the current umask (umask read non-atomically via set/reset), writes the three files with exclusive-create mode 'x', then renames the temp dir to the final location. If the rename loses a race with another concurrent pytest, the OSError is swallowed when errno is ENOTEMPTY or EEXIST (Windows FileExistsError maps to EEXIST) and the temp dir is cleaned up; any other errno re-raises. On a winning rename it re-creates an empty directory at the temp path so TemporaryDirectory cleanup does not complain.

**Uncertainties.**

- Concurrent-process behavior on errnos other than ENOTEMPTY/EEXIST is unhandled by design and propagates.

<a id="u-7701a22ff520"></a>
### `Cache.mkdir`

`def mkdir(self, name: str) -> Path:` · [src/_pytest/cacheprovider.py:L129-L148][f1]

Returns a persistent directory path under the cache's `d` prefix, creating it (and the cache dir) if missing.

Raises ValueError if `name` contains a path separator (`/`), so callers get one flat directory per name.

calls: [Cache](r2-cache-provider.md#u-c7b89217c764)

<a id="u-765de9866ae4"></a>
### `Cache.get`

`def get(self, key: str, default):` · [src/_pytest/cacheprovider.py:L153-L170][f1]

Returns the JSON-deserialized value stored for `key`, or `default` when the file is missing, unreadable, or contains invalid JSON — both ValueError (json) and OSError (I/O, missing file) fall back to `default`; no other exception types are handled.

<a id="u-125d7c893a21"></a>
### `Cache.set`

`def set(self, key: str, value: object) -> None:` · [src/_pytest/cacheprovider.py:L172-L201][f1]

Writes `value` as UTF-8 JSON (indent=2, non-ASCII preserved) to the path for `key`.

On OSError while creating the parent directory it emits a cache warning 'could not create cache path' and returns without writing; on OSError while opening for write it emits 'cache could not write path' instead of raising. Serialization itself is not wrapped, so a non-JSON-serializable value raises from json.dumps.

calls: [Cache](r2-cache-provider.md#u-c7b89217c764)

**Uncertainties.**

-  Whether json.dumps failure can leave a partially written file is not determinable here; serialization happens before the file is opened.

<a id="u-b889b5a2c7ff"></a>
### `Cache.clear_cache`

`def clear_cache(cls, cachedir: Path, _ispytest: bool = False) -> None:` · [src/_pytest/cacheprovider.py:L88-L98][f1]

Removes the `d` and `v` sub-directories of the given cachedir when each exists, via `rm_rf`; leaves other cache content untouched.

Guarded by `check_ispytest`.

calls: [rm_rf](r2-path-general-helpers.md#u-679a90fd83e0)

<a id="u-e8c7ac7bfe07"></a>
### `LFPlugin`

`class LFPlugin:` · [src/_pytest/cacheprovider.py:L319-L322][f1]

Implements the --lf/--ff options by tracking failed nodeids in the `cache/lastfailed` cache entry.

`__init__` sets `active` when `--lf` or `--ff` is given, loads lastfailed, initializes counters/status fields, and — only for `--lf` — computes `_last_failed_paths` and registers LFPluginCollWrapper. `pytest_runtest_logreport` maintains lastfailed: a passed call-phase report or any skipped report removes the nodeid; a failed report sets it True. `pytest_collectreport` treats passed/skipped outcomes as collection success: a previously failed collector is removed and its contained items are all marked failed; a failed collection marks the collector failed. `pytest_report_collectionfinish` returns the status line when active at verbosity >= 0. `pytest_sessionfinish` persists lastfailed back to the cache unless `--cache-show` is active or the process is an xdist worker (workerinput attribute), and only when the saved entry differs. Folded methods' state transitions are the core of the class; pytest_collection_modifyitems has its own unit.

uses: [Cache.get](r2-cache-provider.md#u-765de9866ae4), [LFPluginCollWrapper](r2-cache-provider.md#u-daa0083c1a4d)

<a id="u-46bf32522c79"></a>
### `LFPlugin.get_last_failed_paths`

`def get_last_failed_paths(self) -> set[Path]:` · [src/_pytest/cacheprovider.py:L338-L347][f1]

Maps each nodeid in lastfailed to a filesystem path (part before the first `::`, relative to rootpath), collects those paths plus all their parents, and returns only entries that currently exist on disk.

Nonexistent historical paths silently drop out.

<a id="u-5cdb9c582a1c"></a>
### `LFPlugin.pytest_collection_modifyitems`

`def pytest_collection_modifyitems( self, config: Config, items: list[nodes.Item] ) ->…` · [src/_pytest/cacheprovider.py:L369-L419][f1]

Wrapper hook that reorders or deselects items for --lf/--ff.

Inactive: returns unchanged. With lastfailed entries, items split into previously failed and passed; with --lf only the failed run and the passed are deselected via pytest_deselected; with --ff failed items are moved to the front keeping all. When no previously failed items match the selection, nothing is deselected and the status reports 'known failures not in selected tests'. With empty lastfailed, behavior depends on `--lfnf`: 'none' deselects every item and empties `items`, 'all' (default) leaves them. Skipped-file counts are appended to the status message.

**Uncertainties.**

- Wrapper tryfirst ordering against other modifyitems hooks is not visible here.

<a id="u-daa0083c1a4d"></a>
### `LFPluginCollWrapper`

`class LFPluginCollWrapper:` · [src/_pytest/cacheprovider.py:L249-L250][f1]

Collection-time companion of LFPlugin implementing --lf ordering and filtering, registered as 'lfplugin-collwrapper' only when `--lf` is active.

Its wrapper hook inspects the collector type. For Session or Directory collectors it sorts results so items whose path is in `_last_failed_paths` come first (stable sort, reverse=True on the membership key). For File collectors whose path was previously failed, when no failure has yet been seen it first checks whether any result nodeid is in `lastfailed`: if none, the report is returned unmodified; otherwise it registers LFPluginCollSkipfiles as 'lfplugin-collskip' and sets `_collected_at_least_one_failure`. It then filters the results in place, keeping items whose nodeid is in lastfailed, items on initial paths given on the command line, and all sub-collectors. File collectors not in `_last_failed_paths` are untouched.

uses: [LFPluginCollSkipfiles](r2-cache-provider.md#u-43d7c21b56cd); calls: [Session](r8-collection-tree.md#u-ec1f807fa46d)

**Uncertainties.**

- Interaction ordering with other wrapper hooks is not visible here.

<a id="u-43d7c21b56cd"></a>
### `LFPluginCollSkipfiles`

`class LFPluginCollSkipfiles:` · [src/_pytest/cacheprovider.py:L301-L302][f1]

Registered lazily by LFPluginCollWrapper; its hook makes collection of File collectors whose path was not previously failed appear as a passed, empty CollectReport so --lf skips those files without re-collecting them.

It increments `_skipped_files` for the status line and returns None (normal processing) for anything else, including non-File collectors.

calls: [CollectReport](r3-report-model.md#u-5719d522515d)

<a id="u-e5098218665f"></a>
### `NFPlugin`

`class NFPlugin:` · [src/_pytest/cacheprovider.py:L432-L435][f1]

Implements --nf (new-first) using the `cache/nodeids` cache entry.

`__init__` activates on the newfirst option and loads cached nodeids into a set. The collection hook, when active, partitions items into never-cached ('new') and known ones, orders each group by file mtime descending via `_get_increasing_order` (which stats each item path), concatenates new-first, and adds the new nodeids to the cache set; when inactive it still records all collected nodeids so future --nf runs know them. `pytest_sessionfinish` writes the sorted nodeid set back unless `--cache-show`, an xdist worker (workerinput attribute), or `--collect-only` mode is active.

uses: [Cache.set](r2-cache-provider.md#u-125d7c893a21)

**Uncertainties.**

- _get_increasing_order calls item.path.stat(); behavior on missing files (e.g. deleted between collection and ordering) is not guarded here.

<a id="u-d44832ca84d5"></a>
### `cache`

`def cache(request: FixtureRequest) -> Cache:` · [src/_pytest/cacheprovider.py:L554-L567][f1]

Fixture returning the session Cache so tests can call cache.get/cache.set; asserts config.cache is not None.

<a id="u-a94c72cae19a"></a>
### `cacheshow`

`def cacheshow(config: Config, session: Session) -> int:` · [src/_pytest/cacheprovider.py:L586-L625][f1]

Implements `--cache-show`: prints the cachedir path and returns 0; if the cachedir does not exist prints 'cache is empty' and returns.

Uses the optional glob argument (default '*') to list value files under the `v` prefix sorted, printing each key's pretty-printed value, or 'contains unreadable content, will be ignored' when cache.get falls back to the sentinel (invalid JSON/unreadable). Then lists files under the `d` prefix with their sizes if that directory exists. Returns 0.

**Uncertainties.**

- Which __iter__ the glob filter uses is ambiguous in graph evidence; behavior read directly from the rglob expression.

<a id="u-effe74889082"></a>
### `src/_pytest/cacheprovider.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/cacheprovider.py:L478-L536][f1]

Registers the general-group options --lf/--last-failed, --ff/--failed-first, --nf/--new-first, --cache-show (append with optional glob argument), --cache-clear, and --lfnf/--last-failed-no-failures (choices all/none, default all).

Also defines the `cache_dir` ini setting whose default is `.pytest_cache`, placed under `TOX_ENV_DIR` when that environment variable is set.

<a id="u-0ea3ffd87987"></a>
### `pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode | None:` · [src/_pytest/cacheprovider.py:L539-L544][f1]

Intercepts `--cache-show` runs (unless `--help` was also given): it imports wrap_session and runs cacheshow as the whole session, returning its result; otherwise returns None so normal command-line handling proceeds.

calls: [cacheshow](r2-cache-provider.md#u-a94c72cae19a)

<a id="u-86da7c6e14b8"></a>
### `pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/cacheprovider.py:L547-L551][f1]

tryfirst configure hook that creates the session Cache (honoring --cache-clear), assigns it to config.cache, and registers the LFPlugin and NFPlugin unconditionally (they no-op when their options are inactive).

calls: [Cache.for_config](r2-cache-provider.md#u-9a4fd3fa6b8f); uses: [class::LFPlugin::11097][f1], [class::NFPlugin::15734][f1]

<a id="u-ebb7303567f7"></a>
### `pytest_report_header`

`def pytest_report_header(config: Config) -> str | None:` · [src/_pytest/cacheprovider.py:L570-L583][f1]

Adds a 'cachedir: ...' header line when verbosity > 0 or the cache_dir ini differs from the default `.pytest_cache`.

Displays the path relative to rootpath when possible; ValueError from relative_to (path outside root) falls back to the absolute path. Returns None (no header) otherwise.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/cacheprovider.py
