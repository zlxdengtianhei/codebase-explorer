# Leaked exception reporting

**Capability.** Captures exceptions that escape normal test flow — failures on background threads via threading.excepthook and GC-time unraisable exceptions via sys.unraisablehook — queues them per config, and drains them as errors between test phases via trylast runtest hooks, with tracemalloc supplying allocation annotations.

Use this capability to see how pytest surfaces exceptions that would otherwise vanish. Both plugins follow the same shape: install hook at configure, append metadata to a stash deque, drain in runtest hooks, restore in cleanup. The two children mirror that pattern for thread and unraisable exceptions respectively.

**Children.**

- [Thread exception plugin](r1-thread-exception-plugin.md) `r1-thread-exception-plugin` · 5 unit(s)
- [Unraisable exception plugin](r1-unraisable-exception-plugin.md) `r1-unraisable-exception-plugin` · 5 unit(s)

**Depended on by.**

- [Thread exception plugin](r1-thread-exception-plugin.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-thread-exception-plugin ` → ` r1-leaked-exception-reporting `)

Parent: [pytest codebase](r1-pytest-codebase.md)

## Units (1)

<a id="u-e0457a417bb6"></a>
### `tracemalloc_message`

`def tracemalloc_message(source: object) -> str:` · [src/_pytest/tracemalloc.py:L4-L24][f1]

Produce a tracemalloc allocation note for a source object, tolerating every degraded case.

Returns '' when the object is None or the tracemalloc module is unavailable (ImportError). With tracemalloc active and a traceback recorded for the object, returns '\nObject allocated at:' plus the formatted traceback (leading newline separates it from warning text). Otherwise returns an informational string pointing at pytest docs about enabling tracemalloc, without the leading newline.

**Uncertainties.**

- Whether a traceback is available depends on tracemalloc having been started and filtering options, decided outside this module.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/tracemalloc.py
