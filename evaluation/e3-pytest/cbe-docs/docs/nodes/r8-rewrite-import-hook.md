# Rewrite Import Hook and pyc Cache

**Capability.** A meta-path finder/loader (AssertionRewritingHook) that decides which modules to rewrite (mark_rewrite, _should_rewrite, _early_rewrite_bailout), executes them rewritten, and caches results atomically in pyc files (_read_pyc/_write_pyc/_write_pyc_fp/get_cache_dir/try_makedirs) with mtime/size validation.

Read this to understand module eligibility, the early-bailout fast path, and cache invalidation semantics (PYC_TAG). exec_module is the bridge into the rewriter child.

**Depends on.**

- [AssertionRewriter AST Transformation and Runtime Helpers](r8-assert-rewriter-ast.md) · graph-confirmed · 1 edge(s)
- [Pytest Framework and Test Suite](r8-pytest-root.md) · within containment · 1 edge(s)

**Depended on by.**

- [Assertion Plugin Hooks and Session Wiring](r8-assertion-plugin-hooks.md) · model-inferred · 0 edge(s)

Parent: [Assertion Rewriting](r8-assertion-rewriting.md)

## Units (20)

<a id="u-8ba94a79882d"></a>
### `AssertionRewritingHook`

`class AssertionRewritingHook(importlib.abc.MetaPathFinder, importlib.abc.Loader):` · [src/_pytest/assertion/rewrite.py:L65-L68][f1]

Import hook (meta-path finder and loader) that rewrites assert statements in test modules as they are imported during a pytest session.

It decides which modules to rewrite, replaces their spec's loader with itself, and on exec_module compiles rewritten code with a pyc cache; helper methods decide rewrite eligibility.

group: [AssertionRewritingHook.find_spec](r8-rewrite-import-hook.md#u-a0b26fedda06), [AssertionRewritingHook.exec_module](r8-rewrite-import-hook.md#u-e00a599955f0)

**Uncertainties.**

- The class header segments (s0/s2/s11) split the class; this unit covers the class as a whole including its later segments.

<a id="u-3b31fe3f7da9"></a>
### `AssertionRewritingHook.__init__`

`def __init__(self, config: Config) -> None:` · [src/_pytest/assertion/rewrite.py:L68-L82][f1]

Stores the pytest Config and initializes rewrite-bookkeeping state.

It reads the 'python_files' ini option into fnpats; if that raises ValueError it falls back to ['test_*.py', '*_test.py']. It also initializes the session to None, empty rewritten-name and must-rewrite maps/sets, a _writing_pyc re-entrancy guard flag, a basename set seeded with 'conftest', an empty rewrite-decision cache, and _session_paths_checked=False.

<a id="u-7c5391c72eba"></a>
### `AssertionRewritingHook._early_rewrite_bailout`

`def _early_rewrite_bailout(self, name: str, state: AssertionState) -> bool:` · [src/_pytest/assertion/rewrite.py:L188-L225][f1]

Fast pre-filter to avoid expensive PathFinder lookups for modules that cannot be rewritten.

On first call with a session set, it adds the stem of each session initial path to _basenames_to_check_rewrite and sets _session_paths_checked. It returns False (do not bail out) when the module's last dotted name part is in that basename set (e.g. conftest); when any fnpat contains a directory component (full-path matching is required); when the dotted name reconstructed as a .py PurePath matches a pattern via fnmatch_ex; or when _is_marked_for_rewrite says the name is marked. Otherwise it traces and returns True, meaning skip rewriting early.

<a id="u-19f66cea15f2"></a>
### `AssertionRewritingHook._is_marked_for_rewrite`

`def _is_marked_for_rewrite(self, name: str, state: AssertionState) -> bool:` · [src/_pytest/assertion/rewrite.py:L248-L259][f1]

Cached check of whether a module name was explicitly marked for rewriting.

Consults _marked_for_rewrite_cache; on a miss it scans _must_rewrite, matching the exact name or a dotted prefix (marked + '.'), caching and returning True on match, otherwise caching and returning False.

<a id="u-3dcbccc57037"></a>
### `AssertionRewritingHook._should_rewrite`

`def _should_rewrite(self, name: str, fn: str, state: AssertionState) -> bool: # alway…` · [src/_pytest/assertion/rewrite.py:L227-L246][f1]

Decides by file path whether a module must be rewritten.

Returns True unconditionally for files named conftest.py. If a session is set and the file is an initial path (session.isinitpath of the absolute path), returns True. Otherwise returns True if the path matches any 'python_files' pattern via fnmatch_ex; as a last resort defers to _is_marked_for_rewrite for explicitly marked module names.

calls: [AssertionRewritingHook._is_marked_for_rewrite](r8-rewrite-import-hook.md#u-19f66cea15f2)

<a id="u-38bda6348989"></a>
### `AssertionRewritingHook._warn_already_imported`

`def _warn_already_imported(self, name: str) -> None:` · [src/_pytest/assertion/rewrite.py:L279-L287][f1]

Issues a PytestAssertRewriteWarning ('Module already imported so cannot be rewritten; <name>') through config.issue_config_time_warning with stacklevel=5.

<a id="u-30da032b8412"></a>
### `AssertionRewritingHook.create_module`

`def create_module( self, spec: importlib.machinery.ModuleSpec ) -> types.ModuleType |…` · [src/_pytest/assertion/rewrite.py:L141-L144][f1]

Loader create_module that returns None so Python's default module creation is used.

<a id="u-e00a599955f0"></a>
### `AssertionRewritingHook.exec_module`

`def exec_module(self, module: types.ModuleType) -> None:` · [src/_pytest/assertion/rewrite.py:L146-L186][f1]

Executes a module's code, rewriting test-file sources.

Records module name to origin path in _rewritten_names, then computes the cache dir and pyc name from the origin. Writing is skipped when sys.dont_write_bytecode is set or try_makedirs fails (traced as read-only). It tries _read_pyc for a valid cached code object; on miss it traces 'rewriting', calls _rewrite_test, and if writing is allowed sets _writing_pyc=True around _write_pyc (reset in finally) to prevent recursive rewrites, then finally exec(co, module.__dict__). The cache invariant is maintained by writing to a pid-suffixed temp file and atomically replacing, so concurrent pytest processes never observe a partial pyc.

**Notes.**

- side_effect: Records rewritten module names in _rewritten_names and may write a pyc cache file to disk.
- failure: All pyc write failures are non-fatal: _write_pyc returns False and execution proceeds with the in-memory code object.

calls: [get_cache_dir](r8-rewrite-import-hook.md#u-653818e4e6dc), [try_makedirs](r8-rewrite-import-hook.md#u-8b2acbb4d2ee), [_read_pyc](r8-rewrite-import-hook.md#u-b22c8882f0aa), [_rewrite_test](r8-rewrite-import-hook.md#u-fd1fc9511444), [_write_pyc](r8-rewrite-import-hook.md#u-c44e091d6cb1)

<a id="u-a0b26fedda06"></a>
### `AssertionRewritingHook.find_spec`

`def find_spec( self, name: str, path: Sequence[str | bytes] | None = None, target: ty…` · [src/_pytest/assertion/rewrite.py:L91-L139][f1]

Meta-path find_spec that returns a spec whose loader is this hook for modules eligible for rewriting.

Returns None immediately if a pyc write is in progress (_writing_pyc) or if _early_rewrite_bailout says the name cannot be rewritten; otherwise traces and delegates to PathFinder.find_spec. When PathFinder fails and path is provided (the --import-mode=importlib case), it tries spec_from_file_location for each path entry until one yields a spec. It returns None when the spec is missing, is a namespace package (origin None), its loader is not a SourceFileLoader, or the origin file does not exist. Otherwise _should_rewrite decides; if it declines, None is returned, else a new spec from spec_from_file_location with this hook as loader and the original submodule_search_locations.

calls: [AssertionRewritingHook._early_rewrite_bailout](r8-rewrite-import-hook.md#u-7c5391c72eba), [AssertionRewritingHook._should_rewrite](r8-rewrite-import-hook.md#u-3dcbccc57037)

**Uncertainties.**

- Effect of returning a spec with the hook as loader on the standard import machinery beyond exec_module is assumed standard PEP 451 behavior.

<a id="u-a5b526eafc80"></a>
### `AssertionRewritingHook.get_data`

`def get_data(self, pathname: str | bytes) -> bytes:` · [src/_pytest/assertion/rewrite.py:L289-L292][f1]

PEP 302 get_data: opens the given path in binary mode and returns its full contents; OSError from a missing file propagates to the caller.

<a id="u-b8709d34a3cb"></a>
### `AssertionRewritingHook.get_resource_reader`

`def get_resource_reader(self, name: str) -> TraversableResources:` · [src/_pytest/assertion/rewrite.py:L300-L306][f1]

Python >=3.10 only: returns a FileReader wrapping a SimpleNamespace whose path is the recorded origin of the named rewritten module.

Imports TraversableResources from importlib.resources.abc (3.12+) or importlib.abc, and FileReader from importlib.readers (below 3.11) or importlib.resources.readers. Assumes the name is present in _rewritten_names (KeyError otherwise).

**Uncertainties.**

- Behavior on names never passed through exec_module: _rewritten_names lookup would raise KeyError; not handled here.

<a id="u-86b2ee590866"></a>
### `AssertionRewritingHook.mark_rewrite`

`def mark_rewrite(self, *names: str) -> None:` · [src/_pytest/assertion/rewrite.py:L261-L277][f1]

Marks module/package names (plus nested modules, via prefix matching in _is_marked_for_rewrite) as needing rewriting.

For names already in sys.modules but not previously rewritten by this hook, it warns via _warn_already_imported when the module's docstring does not disable rewriting and its loader is not an instance of this hook class. Always adds names to _must_rewrite and clears the marked-for-rewrite cache so later decisions recompute.

**Notes.**

- side_effect: Mutates _must_rewrite and clears _marked_for_rewrite_cache.

calls: [AssertionRewritingHook._warn_already_imported](r8-rewrite-import-hook.md#u-38bda6348989)

<a id="u-045f3ee0d1f7"></a>
### `AssertionRewritingHook.set_session`

`def set_session(self, session: Session | None) -> None:` · [src/_pytest/assertion/rewrite.py:L84-L86][f1]

Records the current Session and resets _session_paths_checked to False so session paths are re-collected on the next early bailout check.

<a id="u-b22c8882f0aa"></a>
### `_read_pyc`

`def _read_pyc( source: Path, pyc: Path, trace: Callable[[str], None] = lambda x: None…` · [src/_pytest/assertion/rewrite.py:L363-L409][f1]

Validates and loads a pytest-written pyc for a source file, returning the code object or None.

Returns None when the pyc cannot be opened; when stat of the source or reading the 16-byte header fails (traced); when the header is short, has a wrong MAGIC_NUMBER, or nonzero flags; when the stored little-endian mtime or size does not match the source's (32-bit masked); when marshal.load raises (any exception, traced); or when the unmarshaled object is not a CodeType. Trace messages are emitted through the supplied callable (no-op by default).

<a id="u-fd1fc9511444"></a>
### `_rewrite_test`

`def _rewrite_test(fn: Path, config: Config) -> tuple[os.stat_result, types.CodeType]:` · [src/_pytest/assertion/rewrite.py:L352-L360][f1]

Reads a test file, stat()s it, parses the bytes into an AST, rewrites its assertions via rewrite_asserts with the given config, compiles the tree to a code object with dont_inherit=True, and returns (stat_result, code_object).

Parse or compile errors propagate to the caller.

calls: [rewrite_asserts](r8-assert-rewriter-ast.md#u-fde49d5e39a6)

<a id="u-c44e091d6cb1"></a>
### `_write_pyc`

`def _write_pyc( state: AssertionState, co: types.CodeType, source_stat: os.stat_resul…` · [src/_pytest/assertion/rewrite.py:L327-L349][f1]

Atomically writes the rewritten-code cache.

Writes to '<pyc>.<pid>' first via _write_pyc_fp, tracing the errno and returning False on OSError during the write; then os.replace to the final path, tracing and returning False on OSError (permissions, cache dir being a file, etc.). Returns True only when the atomic replace succeeds.

calls: [_write_pyc_fp](r8-rewrite-import-hook.md#u-dd63dabd44e5)

<a id="u-dd63dabd44e5"></a>
### `_write_pyc_fp`

`def _write_pyc_fp( fp: IO[bytes], source_stat: os.stat_result, co: types.CodeType ) -…` · [src/_pytest/assertion/rewrite.py:L309-L324][f1]

Writes a complete pyc payload to an open binary file: CPython MAGIC_NUMBER, four zero flag bytes (per PEP 552), then little-endian packed 32-bit source mtime and size (each masked to 32 bits), then marshal.dumps of the code object.

<a id="u-653818e4e6dc"></a>
### `get_cache_dir`

`def get_cache_dir(file_path: Path) -> Path:` · [src/_pytest/assertion/rewrite.py:L1204-L1215][f1]

Chooses the pyc cache directory for a source file.

When sys.pycache_prefix is set, returns prefix joined with the file's path components minus the drive/root and filename; otherwise returns the classic '<file's parent>/__pycache__'.

<a id="u-8b2acbb4d2ee"></a>
### `try_makedirs`

`def try_makedirs(cache_dir: Path) -> bool:` · [src/_pytest/assertion/rewrite.py:L1179-L1201][f1]

Attempts os.makedirs(cache_dir, exist_ok=True) and reports success.

Returns False on FileNotFoundError, NotADirectoryError, or FileExistsError (a path component is not a directory, e.g. inside a zip); on PermissionError; and on other OSError only when errno is EROFS or ENOSYS (read-only filesystems, including squashfuse_ll); any other OSError propagates. Returns True when creation succeeds or the directory already exists.

<a id="u-e3779c32aa80"></a>
### `rewrite.py module code (L1–L49)`

`module_region` · [src/_pytest/assertion/rewrite.py:L1-L49][f1]

Module header: docstring, stdlib and pytest imports, the Sentinel class, and module constants (assertstate_key StashKey, PYTEST_TAG built from cache tag and pytest version, PYC_EXT '.pyc'/'.pyo' by __debug__, PYC_TAIL, and _SCOPE_END_MARKER).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/rewrite.py
