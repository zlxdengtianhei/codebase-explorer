# Code / Frame / Traceback model

**Capability.** Wraps Python code objects, live frames, and traceback chains as queryable objects exposing path, lineno, source, globals/locals, and entry-level hiding decisions; TracebackEntry depends on Frame and Frame depends on Code (resolved calls).

Use these classes when you need positional or source information about executing code or a traceback entry. Traceback is a list of TracebackEntry built by walking a TracebackType via tb_next. Hiding decisions for entries are made here and consumed by the formatting layer.

**Depended on by.**

- [ExceptionInfo API](r1-code-exception-info.md) · graph-confirmed · 2 edge(s) · ExceptionInfo walks traceback entries through the Code/Frame/Traceback model.
- [Python code inspection & exception rendering](r1-code-inspection.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-code-inspection ` → ` r1-code-core-model `)
- [TerminalRepr data model](r1-code-terminal-repr.md) · model-inferred · 0 edge(s)
- [Traceback formatting engine](r1-code-traceback-formatting.md) · graph-confirmed · 4 edge(s)

Parent: [Python code inspection & exception rendering](r1-code-inspection.md)

## Units (4)

<a id="u-b2fce7cd03e4"></a>
### `code-py-code`

`class Code:` · [src/_pytest/_code/code.py:L61-L66][f1]

Wraps a Python code object to expose its identity, name, path, and source.

Code stores the raw CodeType; from_function derives it from any callable via getrawcode. Equality compares raw code objects and __hash__ is None, so instances are unhashable. firstlineno returns co_firstlineno minus 1 (0-based). path returns '' when co_filename is empty; otherwise absolutepath(co_filename), falling back to the raw string on OSError or when the file does not exist. fullsource delegates to findsource (None if unavailable); source() builds a Source of just the code object. getargs returns the first co_varnames entries; with var=True the count is extended by the CO_VARARGS and CO_VARKEYWORDS flag bits.

uses: [src/_pytest/_code/source.py][f2]

**Uncertainties.**

- getrawcode behavior for arbitrary objects lives in _pytest._code.source and is not shown here

<a id="u-357536d1e8a9"></a>
### `code-py-frame`

`class Frame:` · [src/_pytest/_code/code.py:L130-L136][f1]

Wraps a live frame, exposing 0-based lineno, f_globals, f_locals, its Code, and the Source statement at the current line; statement returns an empty Source when fullsource is unavailable.

eval copies f_locals, overlays the keyword vars, and evals the code with the real globals, returning the result; name collisions in vars shadow frame locals only within the evaluation. repr returns saferepr of an object. getargs pairs code.getargs(var) names with f_locals values, silently skipping names missing from f_locals (KeyError path).

<a id="u-5b081f2426ff"></a>
### `code-py-traceback`

`class Traceback(list[TracebackEntry]):` · [src/_pytest/_code/code.py:L356-L359][f1]

A list of TracebackEntry objects built either by walking a TracebackType via tb_next (inner generator f in __init__) or from an iterable of entries.

cut returns a new Traceback starting at the first entry matching all given criteria: exact path string, entry not under excludepath (matched against Path parents), exact lineno, or exact code firstlineno; if no entry matches it returns self unchanged. Slicing via __getitem__ rebuilds a same-class Traceback from the sliced list; integer indexing returns the entry. filter keeps entries per a callable predicate, or, given an ExceptionInfo, keeps entries not hidden for it. recursionindex finds the first entry whose (path, id(code.raw), lineno) key already occurred with equal frozen locals (dict snapshot for the Python 3.13 f_locals proxy), returning that index or None; equality comparison of arbitrary locals can raise.

uses: [code-py-traceback-entry](r1-code-core-model.md#u-d19a56d47d86)

**Uncertainties.**

- whether cut treats a str path argument identically to Path on all platforms depends on os.fspath/str coercion shown only via str(codepath)

<a id="u-d19a56d47d86"></a>
### `code-py-traceback-entry`

`class TracebackEntry:` · [src/_pytest/_code/code.py:L192-L197][f1]

Wraps one tb entry (plus an optional repr_style override) and exposes position, source, locals, and hiding decisions for it.

lineno is tb_lineno-1; get_python_framesummary uses extract_tb(limit=1) to obtain column data. On Python <3.11 the end_lineno_relative/colno/end_colno properties return None; on 3.11+ they come from the FrameSummary, with end_lineno_relative made relative to the code's firstlineno and colno/end_colno being raw byte offsets. getsource returns the fullsource slice covering the entry's statement via getstatementrange_ast, using and updating the supplied astcache keyed by code path; on SyntaxError it falls back to just the entry's line, and returns None when fullsource is unavailable. ishidden looks up __tracebackhide__ in f_locals then f_globals, suppressing any exception from that access (non-dict namespaces from exec/eval); a callable __tracebackhide__ is invoked with the excinfo to decide. __str__ formats a File/line block, substituting '???' if reading the statement raises any non-KeyboardInterrupt exception; statement asserts fullsource is not None.

**Uncertainties.**

- exact behavior of getstatementrange_ast is defined in _pytest._code.source, not shown

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/code.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/_code/source.py
