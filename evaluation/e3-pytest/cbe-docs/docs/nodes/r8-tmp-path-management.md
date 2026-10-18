# Temporary Directory Management

**Capability.** src/_pytest/tmpdir.py owns per-session and per-test temp directories: TempPathFactory creates/numbers/cleans directories under basetemp (with retention policy and user-based naming), pytest_configure installs the factory early, the tmp_path/tmp_path_factory fixtures expose it, and the makereport hook records per-phase outcomes for cleanup decisions.

Use this to understand basetemp selection, numbered mktemp semantics, basename safety checks, and session-end retention. The tmpdir-tests child verifies these behaviors.

**Children.**

- [tmpdir and pathlib Helper Tests](r8-tmpdir-tests.md) `r8-tmpdir-tests` · 10 unit(s)

**Depended on by.**

- [Legacy py.path Compatibility Layer](r8-legacy-path-compat.md) · model-inferred · 0 edge(s)
- [pathlib and Import Mechanism Tests](r8-pathlib-tests.md) · graph-confirmed · 1 edge(s)
- [tmpdir and pathlib Helper Tests](r8-tmpdir-tests.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r8-tmpdir-tests ` → ` r8-tmp-path-management `)

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (14)

<a id="u-bfe642169624"></a>
### `TempPathFactory`

`class TempPathFactory:` · [src/_pytest/tmpdir.py:L40-L54][f1]

Factory for per-session temporary directories under a common base temp directory.

Constructed only with _ispytest=True (check_ispytest); __init__ normalizes given_basetemp with os.path.abspath (not resolve, for cross-platform reasons, per issue #4427) into _given_basetemp, stores trace, retention_count, retention_policy, and optional basetemp. from_config builds a factory from Config: reads 'tmp_path_retention_count' ini (ValueError if negative) and 'tmp_path_retention_policy' (ValueError unless all/failed/none), taking basetemp from config.option.basetemp and trace from config.trace.get('tmpdir'). mktemp creates a numbered (or plain) directory under getbasetemp(); getbasetemp lazily creates the base directory, honoring _given_basetemp or the PYTEST_DEBUG_TEMPROOT environment variable, with ownership/permission checks and retention-driven cleanup; the created _basetemp is cached for the factory's lifetime.

<a id="u-933fcbdb3de1"></a>
### `_mk_tmp`

`def _mk_tmp(request: FixtureRequest, factory: TempPathFactory) -> Path:` · [src/_pytest/tmpdir.py:L246-L251][f1]

Builds the per-test directory name from request.node.name: replaces every non-word character with '_', truncates to 30 characters (MAXVAL), and calls factory.mktemp(name, numbered=True), so repeated tests with the same (truncated) name get foo-0, foo-1, ...

directories.

calls: [TempPathFactory.mktemp](r8-tmp-path-management.md#u-a12f12d1467b)

<a id="u-7ae0e6420d68"></a>
### `get_user`

`def get_user() -> str | None:` · [src/_pytest/tmpdir.py:L199-L208][f1]

Returns getpass.getuser(), or None when that is impossible: imports getpass inside the try (import may fail in exotic environments) and catches ImportError, OSError, and KeyError (see issue #1010), returning None so callers can fall back to 'unknown'.

<a id="u-a7099b2f2aaf"></a>
### `src/_pytest/tmpdir.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/tmpdir.py:L224-L236][f1]

Registers two ini options: 'tmp_path_retention_count' with default 3 (how many sessions' tmp_path directories are kept per policy) and 'tmp_path_retention_policy' with default 'all' (all/failed/none controlling which tmp_path directories are kept based on test outcome).

<a id="u-012e3ea62226"></a>
### `src/_pytest/tmpdir.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/tmpdir.py:L211-L221][f1]

Creates the session TempPathFactory early so plugins can use it at configure time.

Wraps config in a MonkeyPatch registered via config.add_cleanup(mp.undo), builds TempPathFactory.from_config(config, _ispytest=True), and setattr's it on config as _tmp_path_factory (raising=False), so it is removed by the cleanup along with the attribute record.

calls: [TempPathFactory](r8-tmp-path-management.md#u-bfe642169624); uses: [MonkeyPatch](r6-monkeypatch-engine.md#u-3cde513da82a)

<a id="u-90399e4c8779"></a>
### `src/_pytest/tmpdir.py:pytest_runtest_makereport`

`def pytest_runtest_makereport( item: Item, call ) -> Generator[None, TestReport, Test…` · [src/_pytest/tmpdir.py:L304-L312][f1]

Wrapper hookimpl (tryfirst) around report creation: obtains the TestReport from the wrapped call, asserts rep.when is not None, then records item.stash.setdefault(tmppath_result_key, {})[rep.when] = rep.passed, so the tmp_path fixture can later decide per-phase whether the test's call phase passed.

Returns the report unchanged.

contract: [tmp_path](r8-tmp-path-management.md#u-fee0ae1b62c7)

<a id="u-e385fd731a07"></a>
### `src/_pytest/tmpdir.py:pytest_sessionfinish`

`def pytest_sessionfinish(session, exitstatus: int | ExitCode):` · [src/_pytest/tmpdir.py:L279-L301][f1]

Session-end cleanup.

Reads the factory from session.config._tmp_path_factory and its _basetemp; if _basetemp is None (never created), returns immediately. If exitstatus == 0, policy is 'failed', and the user did not supply --basetemp (_given_basetemp is None), it removes the base temp tree with rmtree(basetemp, ignore_errors=True) — best effort, ignoring leaked resources or permission errors. Regardless of policy or exit status (as long as basetemp exists and is a directory), it then calls cleanup_dead_symlinks(basetemp) to drop dead symlinks left by retained directories.

uses: [TempPathFactory.getbasetemp](r8-tmp-path-management.md#u-9bff6cf31e64), [src/_pytest/tmpdir.py:pytest_runtest_makereport](r8-tmp-path-management.md#u-90399e4c8779)

**Uncertainties.**

- cleanup_dead_symlinks semantics (which links count as dead) are defined in _pytest.pathlib, outside this batch.

<a id="u-fee0ae1b62c7"></a>
### `tmp_path`

`def tmp_path( request: FixtureRequest, tmp_path_factory: TempPathFactory ) -> Generat…` · [src/_pytest/tmpdir.py:L254-L276][f1]

Per-test fixture yielding a unique temporary directory from _mk_tmp (sanitized, truncated node name, numbered under basetemp).

After the test finishes, it applies the retention policy: it reads tmp_path_factory._retention_policy and request.node.stash[tmppath_result_key] (a dict of phase -> passed set by pytest_runtest_makereport); if the policy is 'failed' and the 'call' phase passed (missing entry defaults to True, so e.g. setup/teardown-only failures still count as passing for retention), it removes the directory with rmtree(path, ignore_errors=True), best-effort. Finally it deletes the stash entry regardless of policy, so subsequent phases see no stale results.

calls: [_mk_tmp](r8-tmp-path-management.md#u-933fcbdb3de1); contract: [src/_pytest/tmpdir.py:pytest_runtest_makereport](r8-tmp-path-management.md#u-90399e4c8779)

**Uncertainties.**

- Behavior when tmppath_result_key is missing from the stash (e.g. makereport hook blocked) is not guarded here; the direct stash lookup would raise KeyError.

<a id="u-30eefc26d77c"></a>
### `tmp_path_factory`

`def tmp_path_factory(request: FixtureRequest) -> TempPathFactory:` · [src/_pytest/tmpdir.py:L239-L243][f1]

Session-scoped fixture returning request.config._tmp_path_factory, the TempPathFactory attached by pytest_configure.

If configure did not run or the attribute was removed, this raises AttributeError; creation is deliberately not done here per the comment.

contract: [src/_pytest/tmpdir.py:pytest_configure](r8-tmp-path-management.md#u-012e3ea62226)

<a id="u-4eae4f79c566"></a>
### `TempPathFactory.__init__`

`def __init__( self, given_basetemp: Path | None, retention_count: int, retention_poli…` · [src/_pytest/tmpdir.py:L54-L75][f1]

Requires _ispytest=True or raises via check_ispytest.

If given_basetemp is None stores None, else stores Path(os.path.abspath(str(given_basetemp))) — absolute but not resolved, deliberately (see #4427 and bpo-25012). Stores trace, retention_count, retention_policy directly, and basetemp (pre-set base, normally None).

<a id="u-7db7dd52b4b4"></a>
### `TempPathFactory._ensure_relative_to_basetemp`

`def _ensure_relative_to_basetemp(self, basename: str) -> str:` · [src/_pytest/tmpdir.py:L109-L113][f1]

Normalizes basename with os.path.normpath, then checks that (getbasetemp()/basename).resolve().parent equals getbasetemp(); if not — i.e. the name escapes or is not normalized relative to basetemp — raises ValueError('{basename} is not a normalized and relative path').

Note it calls getbasetemp(), which can create the base directory as a side effect of this validation.

<a id="u-ddacdfa8ad50"></a>
### `TempPathFactory.from_config`

`def from_config( cls, config: Config, *, _ispytest: bool = False, ) -> TempPathFactory:` · [src/_pytest/tmpdir.py:L77-L107][f1]

Classmethod building a factory from pytest configuration.

Requires _ispytest=True. Reads ini 'tmp_path_retention_count', converts to int, raises ValueError('tmp_path_retention_count must be >= 0...') if negative; reads 'tmp_path_retention_policy' and raises ValueError if it is not 'all', 'failed', or 'none'. Returns cls(given_basetemp=config.option.basetemp, trace=config.trace.get('tmpdir'), retention_count=count, retention_policy=policy, _ispytest=True).

calls: [TempPathFactory](r8-tmp-path-management.md#u-bfe642169624)

<a id="u-9bff6cf31e64"></a>
### `TempPathFactory.getbasetemp`

`def getbasetemp(self) -> Path:` · [src/_pytest/tmpdir.py:L139-L196][f1]

Returns the cached base temp directory, creating it on first use.

If _basetemp is set, returns it unchanged. If _given_basetemp was provided, it deletes any existing directory with rm_rf, recreates it with mode 0o700, and resolves it — a user-specified basetemp is always wiped, so its prior contents do not survive. Otherwise: temproot is PYTEST_DEBUG_TEMPROOT or tempfile.gettempdir(), resolved; user is get_user() or 'unknown'; rootdir is temproot/pytest-of-{user}, created with mode 0o700 exist_ok=True; on OSError (likely illegal characters from getuser) it retries with 'pytest-of-unknown'. If get_user_id() returns a uid, it stats rootdir and raises OSError if not owned by the current user ('not owned by the current user. Fix this and try again.'), and chmods away group/other permission bits (mode & ~0o077) for privacy and to fix historical 0o755. Retention: keep = _retention_count, or 0 if policy is 'none'; the base is created via make_numbered_dir_with_cleanup(prefix='pytest-', root=rootdir, keep=keep, lock_timeout=LOCK_TIMEOUT, mode=0o700), which per its name also prunes older numbered dirs beyond keep. Caches and traces the result; assertion guards that basetemp is not None.

uses: [TempPathFactory.from_config](r8-tmp-path-management.md#u-ddacdfa8ad50)

**Uncertainties.**

- Exact pruning/symlink behavior of make_numbered_dir_with_cleanup and rm_rf lives in _pytest.pathlib, not in this batch.

<a id="u-a12f12d1467b"></a>
### `TempPathFactory.mktemp`

`def mktemp(self, basename: str, numbered: bool = True) -> Path:` · [src/_pytest/tmpdir.py:L115-L137][f1]

Creates a new managed directory under getbasetemp().

basename must pass _ensure_relative_to_basetemp (ValueError on absolute/escaping/unnormalized names). If numbered is False it creates basetemp/basename with mkdir(mode=0o700), which raises FileExistsError on a second call with the same name; if True (default) it creates make_numbered_dir(root=basetemp, prefix=basename, mode=0o700), yielding foo-0, foo-1, ... with numbers greater than any existing one, and traces ('mktemp', p). Returns the new Path.

calls: [TempPathFactory._ensure_relative_to_basetemp](r8-tmp-path-management.md#u-7db7dd52b4b4), [TempPathFactory.getbasetemp](r8-tmp-path-management.md#u-9bff6cf31e64)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/tmpdir.py
