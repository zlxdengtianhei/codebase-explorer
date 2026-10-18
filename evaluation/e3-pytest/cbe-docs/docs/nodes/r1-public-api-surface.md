# Public pytest API surface

**Capability.** The pytest module namespace: re-exports the stable public API from internal _pytest submodules so user code and plugins import everything from 'pytest' rather than internals.

Use this unit to see which names are declared public. Adding a public API requires routing through this facade; importing _pytest internals directly is unsupported for users. Its contents are declarations only, with behavior owned by the corresponding capability subtrees.

**Depends on.**

- [pytest codebase](r1-pytest-codebase.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-public-api-surface ` → ` r1-pytest-codebase `)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (1)

<a id="u-bbcdcae30a33"></a>
### `__init__.py module code (L1–L180)`

`module_region` · [src/pytest/__init__.py:L1-L180][f1]

Re-export the public pytest API from internal _pytest submodules as the 'pytest' module namespace.

It imports roughly 85 names spanning fixtures, config, hooks, outcomes, collection classes, reporting, warnings, and pytester utilities; aliases MARK_GEN as 'mark', imports pytestPDB as '__pytestPDB', and binds 'set_trace' to '__pytestPDB.set_trace'. The '__all__' list enumerates the public surface, so 'from pytest import *' exposes exactly those names; names imported here remain accessible as attributes regardless. The '# PYTHON_ARGCOMPLETE_OK' marker comment enables argcomplete discovery. All imports execute at module import time, so a failure inside any _pytest import propagates and blocks 'import pytest'.

**Uncertainties.**

- Names reachable via imported objects but absent from __all__ may still be importable as pytest attributes; __all__ governs only star-imports, and this file does not prove any stricter hiding.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/pytest/__init__.py
