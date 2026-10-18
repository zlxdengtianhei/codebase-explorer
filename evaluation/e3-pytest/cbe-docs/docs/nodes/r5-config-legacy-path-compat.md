# Legacy path hook compatibility

**Capability.** PathAwareHookProxy wraps a pluggy HookRelay so legacy fspath-style hooks keep working alongside pathlib arguments, with _check_path validating that both views refer to the same location.

Read this to understand how pytest maintains backward compatibility for hooks taking path arguments without breaking pathlib callers.

**Depends on.**

- [Config exceptions and private-API guards](r5-config-api-guards.md) · model-inferred · 0 edge(s)

Parent: [Configuration bootstrapping](r5-config-bootstrapping.md)

## Units (3)

<a id="u-2b2f77636d4c"></a>
### `PathAwareHookProxy`

`class PathAwareHookProxy:` · [src/_pytest/config/compat.py:L34-L43][f1]

Wraps a pluggy HookRelay so that attribute access returns hook callers, replacing a fixed set of legacy hooks (per imply_paths_hooks) with wrappers that accept both pathlib and legacy path arguments.

Hooks not in the map are cached directly in __dict__; wrapped hooks are also cached, so the wrapper is built once per hook name. The wrapper warns (DeprecationWarning via HOOK_LEGACY_PATH_ARG, stacklevel=2) when the legacy argument is given; when only the legacy argument is given it asserts it is not None and derives the Path from it, when only the Path is given it derives the legacy path via legacy_path, and when both are given it validates equality with _check_path (raising ValueError on mismatch). Both values are reinserted into the kwargs and the real hook is called. The wrapper copies hook.name, hook.spec and __name__ so it can stand in for the caller.

calls: [_check_path](r5-config-legacy-path-compat.md#u-d98f73fb7c13)

**Uncertainties.**

- __getattr__ assumes the requested key exists on the hook relay; AttributeError for unknown hooks comes from the relay, not the proxy.
- The assert in fixed_hook is the only guard when path_value is None; behavior under python -O is unverified from this source.

<a id="u-d98f73fb7c13"></a>
### `_check_path`

`def _check_path(path: Path, fspath: LEGACY_PATH) -> None:` · [src/_pytest/config/compat.py:L26-L31][f1]

Validates that a legacy path and a pathlib Path refer to the same location: raises ValueError naming both values if Path(fspath) differs from path; returns silently otherwise.

<a id="u-bfb2e6008f57"></a>
### `compat.py module code (L1–L25)`

`module_region` · [src/_pytest/config/compat.py:L1-L25][f1]

Module preamble importing typing/functools/warnings, pluggy, LEGACY_PATH/legacy_path from _pytest.compat and HOOK_LEGACY_PATH_ARG, plus the module constant imply_paths_hooks mapping five hook names to (path argument, legacy fspath argument) pairs.

**Notes.**

- field: imply_paths_hooks: pytest_ignore_collect, pytest_collect_file, pytest_pycollect_makemodule, pytest_report_header, pytest_report_collectionfinish map to their pathlib and legacy-path argument names.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/compat.py
