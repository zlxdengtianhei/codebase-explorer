# Fixture lookup error reporting

**Capability.** FixtureLookupError and its terminal-renderable FixtureLookupErrorRepr, raised when a requested fixture cannot be resolved and rendered as a readable diagnostic.

Read this when diagnosing 'fixture not found' output. The error builds its own representation and consults the registry's factory matching while formatting suggestions.

**Depends on.**

- [Fixture registry and requirement closure](r5-fixture-registry.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Fixture registry and requirement closure](r5-fixture-registry.md) · model-inferred · 0 edge(s)
- [Request objects and scoping context](r5-fixture-request-context.md) · graph-confirmed · 4 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (2)

<a id="u-3dd83deedbc8"></a>
### `FixtureLookupError`

`class FixtureLookupError(LookupError):` · [src/_pytest/fixtures.py:L815-L819][f1]

LookupError raised when a requested fixture cannot be resolved.

The constructor records argname, the request, the fixture stack (via request._get_fixturestack) and an optional custom message. formatrepr builds the user-facing traceback: the stack starts at the requesting function and extends with each fixture in the stack; when a custom msg is present the last stack entry (the failing fixture) is dropped. For each function it tries inspect.getsourcelines; on OSError/IndexError/TypeError it emits 'source code not available', otherwise the file/line and the def line. With no custom msg it classifies the failure: if the argname is among fixtures matched to the item's parent it reports a recursive dependency, otherwise 'fixture not found', appending the sorted available fixture names and a --fixtures hint. An assert documents the assumption that a custom msg implies a non-empty fixture stack; violating it would crash because fspath is unset.

calls: [FixtureLookupErrorRepr](r5-fixture-lookup-errors.md#u-f1555652e1d1)

**Uncertainties.**

- The 'recursive dependency' classification depends on FixtureManager._matchfactories and the parent node; behavior with an item lacking a parent is guarded only by an assert.

<a id="u-f1555652e1d1"></a>
### `FixtureLookupErrorRepr`

`class FixtureLookupErrorRepr(TerminalRepr):` · [src/_pytest/fixtures.py:L882-L883][f1]

Terminal-renderable representation of a FixtureLookupError.

The constructor stores traceback lines, the error string, filename, firstlineno and argname. toterminal writes each traceback line, then the error string's first line with the fail marker and subsequent lines with the flow marker (both red), a blank line, and finally 'filename:firstlineno+1'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
