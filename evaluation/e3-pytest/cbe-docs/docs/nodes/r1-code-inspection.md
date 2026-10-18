# Python code inspection & exception rendering

**Capability.** Turns Python code objects, frames, tracebacks, and raised exceptions into structured data and terminal-renderable representations. Everything pytest prints about a failure is produced here, so Code/Frame/Traceback access, ExceptionInfo, the TerminalRepr hierarchy, and traceback formatting belong together.

Enter here to understand how an exception becomes displayed output. Use the model subtree for programmatic access to frames and tracebacks, the ExceptionInfo subtree for exception-centric APIs (exconly, match, group search), and the formatting/repr subtrees for how output is assembled. The facade unit shows the intended public imports of the package.

**Children.**

- [Code / Frame / Traceback model](r1-code-core-model.md) `r1-code-core-model` · 4 unit(s)
- [ExceptionInfo API](r1-code-exception-info.md) `r1-code-exception-info` · 9 unit(s)
- [TerminalRepr data model](r1-code-terminal-repr.md) `r1-code-terminal-repr` · 10 unit(s)
- [Traceback formatting engine](r1-code-traceback-formatting.md) `r1-code-traceback-formatting` · 12 unit(s)

**Depends on.**

- [Code / Frame / Traceback model](r1-code-core-model.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-code-inspection ` → ` r1-code-core-model `)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (1)

<a id="u-60fec36890d2"></a>
### `__init__.py module code (L1–L26)`

`module_region` · [src/_pytest/_code/__init__.py:L1-L26][f1]

Package facade re-exporting the python inspection API: it imports Code, ExceptionInfo, filter_traceback, Frame, getfslineno, Traceback, TracebackEntry from .code and getrawcode, Source from .source, then lists nine of them in __all__.

Contains no logic.

imports: [getrawcode](r6-source-introspection.md#u-d1f459143028), [Source](r6-source-introspection.md#u-e7fd6d2495da)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/__init__.py
