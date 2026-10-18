# Config exceptions and private-API guards

**Capability.** The small exception vocabulary of config handling (UsageError, PrintHelp) and the check_ispytest guard that warns when private pytest APIs are called from outside pytest.

Consult this for the error/signal types used across argument handling and for how pytest detects misuse of internal APIs.

**Depended on by.**

- [Rootdir and config-file discovery](r5-config-findpaths.md) · model-inferred · 0 edge(s)
- [Legacy path hook compatibility](r5-config-legacy-path-compat.md) · model-inferred · 0 edge(s)

Parent: [Configuration bootstrapping](r5-config-bootstrapping.md)

## Units (4)

<a id="u-4e183a5c29b3"></a>
### `UsageError`

`class UsageError(Exception):` · [src/_pytest/config/exceptions.py:L6-L8][f1]

Final Exception subclass marking errors in pytest usage or invocation; adds no behavior or state.

<a id="u-0345360997bd"></a>
### `PrintHelp`

`class PrintHelp(Exception):` · [src/_pytest/config/exceptions.py:L11-L13][f1]

Exception raised to signal that pytest should print its help and skip the remaining argument parsing and validation; carries no additional behavior.

<a id="u-35de2001b2ea"></a>
### `exceptions.py module code (L1–L5)`

`module_region` · [src/_pytest/config/exceptions.py:L1-L5][f1]

Preamble importing __future__ annotations and typing.final only; no behavior.

<a id="u-505f55ba6741"></a>
### `check_ispytest`

`def check_ispytest(ispytest: bool) -> None:` · [src/_pytest/deprecated.py:L89-L91][f2]

Guard for private pytest APIs: warns when a private class or function is called by non-internal code.

When the keyword-only ``_ispytest`` flag is False, it emits the module-level PRIVATE PytestDeprecationWarning at stacklevel=3, attributing the warning to the external caller; internal callers pass ``_ispytest=True`` and stay silent. Nothing is returned or raised today, but the module docstring notes warnings may become errors in the future.

**Uncertainties.**

- Whether stacklevel=3 attributes correctly depends on callers' fixed call depth, which is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/exceptions.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/deprecated.py
