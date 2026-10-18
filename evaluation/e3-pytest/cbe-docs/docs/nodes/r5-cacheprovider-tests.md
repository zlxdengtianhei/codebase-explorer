# Cache provider tests

**Capability.** Coverage for the cache plugin: directory permissions and key validation of the Cache API, warning behavior on broken caches, --lf/--ff and --nf ordering against the lastfailed key, cachedir header/show options, and README creation.

Use this to see the contractual behavior of config.cache and the --lf/--ff/--nf options, including regression cases.

**Depends on.**

- [pytest's own test suites](r5-test-suites.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r5-cacheprovider-tests ` → ` r5-test-suites `)
- [Test Run Invocation](r6-pytester-run.md) · graph-only · 106 edge(s)
- [Pytester Environment and File Setup](r6-pytester-core.md) · graph-only · 69 edge(s)

Parent: [pytest's own test suites](r5-test-suites.md)

## Units (7)

<a id="u-4bd101f4d101"></a>
### `test_cacheprovider-module-residual`

`module_region` · [testing/test_cacheprovider.py:L1-L22][f1]

File-level imports (enum, os, pathlib, shutil, typing, pytest internals) and the pytest_plugins = ('pytester',) registration enabling the pytester fixture used throughout; no executable behavior beyond that declaration.

<a id="u-1dec6f66303f"></a>
### `test_cacheprovider-new-api-tests`

`class TestNewAPI:` · [testing/test_cacheprovider.py:L23-L24][f1]

Exercises the Cache API through pytester: mkdir rejects keys containing '/', returning the created directory only for plain names; a new cache directory has the same permission bits as its parent .pytest_cache (regression #12308); cache.set raises TypeError for unserializable values, and cache.get returns the caller's default when the stored file is corrupt bytes; writes into a broken or unwritable cache path fail silently (warning filtered), while with default warning filters a failing run emits PytestCacheWarning from cacheprovider.py naming the exact path (v/cache/nodeids) with correct stacklevel.

Also verifies config.cache exists at configure and session time, the cache funcarg's get/set/TypeError semantics, and cache_dir resolution from relative paths, absolute paths, and ini values containing $env_var substitution.

**Notes.**

- condition: unwritable_cache_dir fixture chmods the cache dir to 0, skips the test if it is still writable (e.g. running as root), and restores the original mode afterwards.

**Uncertainties.**

- Exact warning deduplication and stacklevel behavior is asserted only via output patterns; the emitting implementation lives outside this file.

<a id="u-bcf4fab8e131"></a>
### `test_cacheprovider-cache-boilerplate`

`class Action(Enum):` · [testing/test_cacheprovider.py:L1281-L1285][f1]

Tests cache-directory boilerplate and value round-tripping using Cache.for_config directly.

test_gitignore (parametrized over Action.MKDIR and Action.SET, an auto-valued Enum) asserts that either operation creates .gitignore containing '# Created by pytest automatically.\n*\n' and that a pre-existing/custom .gitignore is never overwritten. test_preserve_keys_order (#9205) round-trips a dict through cache.set/get and asserts key insertion order is preserved. test_does_not_create_boilerplate_in_existing_dirs sets cache_dir to '.' and asserts v/ is created but .gitignore and README.md are not written into the pre-existing directory. test_cachedir_tag (#4278) asserts CACHEDIR.TAG bytes equal CACHEDIR_TAG_CONTENT after a set. test_clioption_with_cacheshow_and_help asserts --cache-show combined with --help exits 0.

<a id="u-6610fa1126bb"></a>
### `test_cacheprovider-reportheader-and-show`

`def test_cache_reportheader( env: Sequence[str], pytester: Pytester, monkeypatch: Mon…` · [testing/test_cacheprovider.py:L197-L209][f1]

Checks the verbose header line 'cachedir:' and the --cache-show command.

test_cache_reportheader is parametrized: with TOX_ENV_DIR set the header shows <envdir>/.pytest_cache, otherwise (after delenv) it shows the relative .pytest_cache; an external absolute cache_dir from ini is echoed verbatim in the header. test_cache_show confirms --cache-show on an empty cache prints 'cache is empty' and exits 0; after conftest populates values (my/name, my/hello, other/some) and a mkdir'd directory mydb, a bare run returns exit 5 (no tests) and --cache-show lists values with repr-ish output (notably {1:2} shown as *'1': 2) and directory entries with sizes; a glob argument '*/hello' restricts output to matching keys and directories, excluding other/some and d/mydb/world.

<a id="u-e6886672c527"></a>
### `test_cacheprovider-lastfailed-tests`

`class TestLastFailed:` · [testing/test_cacheprovider.py:L282-L283][f1]

Covers the --lf/--ff (--last-failed/--failed-first) behavior against the cache/lastfailed key.

Observed semantics asserted across these tests: failures (including import/collection errors, recorded as the file nodeid) and run failures (file::test) are stored in lastfailed; xfail and xpass are not failures, but strict xfail is; a test that previously failed but now xfails or skips removes it from lastfailed. --lf selects only previously failed items among the collected set, deselecting the rest with messages like 'rerun previous N failures (skipped M files)' or 'N known failures not in selected tests'; files with no failed tests may be skipped during collection, including nested packages; when no cached failures match, all tests run unless --lfnf none deselects everything (exit NO_TESTS_COLLECTED, and the deselected list handed to pytest_deselected must remain valid at sessionfinish). --lf does not forget failures from files not run in an invocation (cumulative workflow); removing then renaming a failed test re-collects the file; known failures given explicitly as args or inside classes are collected rather than dropping whole classes; non-Python (yaml) files are skipped. --ff reorders to run failed tests first while --lf --ff restricts to failed only. --cache-clear resets state while preserving .git inside .pytest_cache, and README.md/.gitignore boilerplate is recreated; lastfailed cache is only created when a failure exists (#1342). No 'run all' message is printed on the first --lf/--ff run (#3853). The helper get_cached_last_failed returns sorted lastfailed keys (empty list when absent); the local rlf closures set FAILIMPORT/FAILTEST env vars, run pytest, and read back the lastfailed value with default -1.

**Uncertainties.**

- test_lastfailed_with_known_failures_not_being_selected uses relative Path('pkg1/test_1.py').unlink() against the process cwd rather than pytester.path; the dependence on cwd being the pytester dir is unverified from this file alone.
- Exact filtering implementation of --lf lives in src/_pytest/cacheprovider.py, not supplied; selection semantics are inferred from asserted output only.

<a id="u-0ea6346caa6f"></a>
### `test_cacheprovider-newfirst-tests`

`class TestNewFirst:` · [testing/test_cacheprovider.py:L1139-L1140][f1]

Verifies the --nf (--new-first) option: tests are ordered newest-file-first based on mtime.

test_newfirst_usecase bumps test_1/test_1.py's mtime with os.utime, shows default alphabetical order versus --nf reversing which file runs first, and after adding a new test function to the file shows the new item ahead of existing ones even when a pytest_collection_modifyitems plugin re-sorts items (plugin's printed list confirms --nf applied its ordering before the hook). test_newfirst_parametrize extends this to parametrized tests: new parameter values from a changed file come first, and running --nf on a subset does not forget the ordering of files not collected in that run.

<a id="u-519aee83d264"></a>
### `test_cacheprovider-readme-tests`

`class TestReadme:` · [testing/test_cacheprovider.py:L1263-L1264][f1]

Asserts that .pytest_cache/README.md exists after any run, passing or failing; check_readme reads config.cache._cachedir and returns whether README.md is a file, and both tests assert it is True after runpytest.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/testing/test_cacheprovider.py
