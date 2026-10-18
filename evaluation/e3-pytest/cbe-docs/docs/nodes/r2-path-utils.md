# Filesystem & Import Path Utilities

**Capability.** Shared path and import infrastructure: module import by path with package-root resolution, numbered-directory creation with lock-based cleanup, and general path helpers (rm_rf, relative paths, safe scanning). Kept separate from consumers like cacheprovider and config.

Consult the import subtree for import_path semantics and ImportPathMismatchError, the numbered-dir subtree for cache/tmp dir lifecycle, and the helpers subtree for rm_rf/bestrelpath-style utilities used across the codebase.

**Children.**

- [Module Import by Path](r2-path-import-machinery.md) `r2-path-import-machinery` · 12 unit(s)
- [Numbered Directory Creation & Cleanup](r2-path-numbered-dir-cleanup.md) `r2-path-numbered-dir-cleanup` · 14 unit(s)
- [General Path Helpers](r2-path-general-helpers.md) `r2-path-general-helpers` · 13 unit(s)

**Depended on by.**

- [Cross-Session Cache Provider](r2-cache-provider.md) · graph-confirmed · 2 edge(s) · Cache.clear_cache and cache-directory resolution use rm_rf and resolve_from_str from the path helpers.

Parent: [Pytest Codebase](r2-pytest-root.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
