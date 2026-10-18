# Legacy py.path compatibility

**Capability.** Keeps the removed pylib usable via a minimal py module shim and preserves confidence in py.path.local's filesystem API through an extensive suite: a common py.path contract mixin, local-specific behavior, platform-specific and import suites, all against a canonical sample tree.

Enter here only when dealing with code that still imports py.error/py.path, or when changing py.path behavior tested by this suite. The support subtree builds the shared fixture tree; the suite subtrees pin API, platform, and import semantics. Platform-specific classes carry skip markers, so absence of failures on one OS is by design.

**Children.**

- [py.path test infrastructure](r1-local-test-support.md) `r1-local-test-support` · 4 unit(s)
- [Common py.path API suite](r1-local-commonfs-suite.md) `r1-local-commonfs-suite` · 6 unit(s)
- [Platform-specific & import suites](r1-local-platform-import-suite.md) `r1-local-platform-import-suite` · 6 unit(s)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (1)

<a id="u-d4ca81600539"></a>
### `py.py module code (L1–L15)`

`module_region` · [src/py.py:L1-L15][f1]

Provide a minimal 'py' module so code importing py.error or py.path keeps working after pylib is removed.

On import it registers the _pytest._py.error and _pytest._py.path modules in sys.modules under 'py.error' and 'py.path', and re-exports them via __all__. Per the header comment, if the real pylib is installed this file is skipped because py/__init__.py has higher precedence on sys.path.

**Notes.**

- side_effect: Importing this module mutates sys.modules by aliasing 'py.error' to _pytest._py.error and 'py.path' to _pytest._py.path.

imports: [py.py module code (L1–L15)](r1-legacy-py-path.md#u-d4ca81600539)

**Uncertainties.**

- Whether later imports of 'py' resolve to this shim depends on sys.path precedence; the header's claim that an installed pylib takes precedence is not verifiable from this source alone.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/py.py
