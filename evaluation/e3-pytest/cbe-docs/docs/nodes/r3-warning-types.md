# Warning Categories

**Capability.** Defines PytestWarning and its subclasses (all resetting __module__ to 'pytest'), UnformattedWarning for runtime-formattable messages, and warn_explicit_for to warn at a definition site.

Use this subtree for the public warning classes that appear in filterwarnings entries and output. It has no capture logic; it is the vocabulary the capture layer and users refer to.

**Depended on by.**

- [Warning Assertion Helpers](r3-recwarn.md) · model-inferred · 0 edge(s)
- [Warning Capture Hooks](r3-warning-capture.md) · model-inferred · 0 edge(s)

Parent: [Warning Handling](r3-warnings.md)

## Units (3)

<a id="u-10c8ce561005"></a>
### `warning_types.py:warning-classes`

`class PytestWarning(UserWarning):` · [src/_pytest/warning_types.py:L13-L16][f1]

All pytest warning categories subclass PytestWarning (itself a UserWarning) and reset ``__module__`` to 'pytest' so they appear as pytest.* in output.

Specializations: PytestDeprecationWarning also subclasses DeprecationWarning (so default filters that ignore DeprecationWarning apply), PytestRemovedIn9Warning narrows it to pytest 9 removals, and PytestExperimentalApiWarning also subclasses FutureWarning. Most concrete categories are @final and carry only docstrings: PytestAssertRewriteWarning, PytestCacheWarning, PytestConfigWarning, PytestCollectionWarning, PytestReturnNotNoneWarning, PytestUnknownMarkWarning, PytestUnraisableExceptionWarning, PytestUnhandledThreadExceptionWarning, PytestFDWarning. PytestExperimentalApiWarning additionally offers the classmethod ``simple(apiname)`` producing a ready-made message '<apiname> is an experimental api that may change over time'.

<a id="u-ed063feb7bcd"></a>
### `UnformattedWarning`

`class UnformattedWarning(Generic[_W]):` · [src/_pytest/warning_types.py:L120-L132][f1]

A deferred warning: a dataclass holding a PytestWarning subclass and a str template, meant for messages that can only be formatted at runtime (e.g. with the node or argument names).

``format(**kwargs)`` substitutes the template and instantiates the category, returning the fully formed warning instance.

<a id="u-f4a9063e0bd7"></a>
### `warn_explicit_for`

`def warn_explicit_for(method: FunctionType, message: PytestWarning) -> None:` · [src/_pytest/warning_types.py:L144-L166][f1]

Warn at a function's definition site for code written before the problem was known (e.g. legacy hook marking).

It reads the function's first line number, source file, module and globals, then calls warnings.warn_explicit using the module's ``__warningregistry__`` (created via setdefault if absent) so per-module suppression semantics apply. Under -Werror, warning-as-error raises and the location would be lost, so any raised Warning is re-raised as a new instance of the same type with ' at filename:lineno' appended and no chained cause.

**Uncertainties.**

- Only exceptions that are Warning instances are augmented; other escapes from warn_explicit propagate unmodified.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/warning_types.py
