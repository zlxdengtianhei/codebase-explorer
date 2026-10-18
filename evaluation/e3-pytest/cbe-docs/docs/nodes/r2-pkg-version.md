# Package Version Metadata

**Capability.** Publishes the _pytest package version string.

Consult when code needs the installed pytest version. No dependencies appear in the observed graph.

Parent: [Pytest Codebase](r2-pytest-root.md)

## Units (1)

<a id="u-a88d8133ca89"></a>
### `__init__.py module code (L1–L13)`

`module_region` · [src/_pytest/__init__.py:L1-L13][f1]

Publishes the package version.

Re-exports __version__ and version_tuple from the generated ._version module; if that import raises ImportError (broken installation), falls back to __version__='unknown' and version_tuple=(0, 0, 'unknown'), which per the comment only works because version comparison elsewhere is loose.

**Uncertainties.**

- How consumers handle the 'unknown' fallback is decided outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/__init__.py
