# Unraisable exception plugin

**Capability.** Replaces sys.unraisablehook at pytest_configure with unraisable_hook, queues UnraisableMeta/BaseException items in a config-stash deque, reports them via collect_unraisable from trylast runtest setup/call/teardown hook wrappers, and restores the previous hook in cleanup.

Use this subtree for exceptions raised during garbage collection or __del__ that Python can only report through sys.unraisablehook. Like the thread plugin, reporting happens at the last opportunity of each test phase. Cleanup guarantees the original hook is restored at session end.

Parent: [Leaked exception reporting](r1-leaked-exception-reporting.md)

## Units (5)

<a id="u-c7beb5b889f9"></a>
### `unraisableexception.py-runtest-collect-hooks`

`def pytest_runtest_setup(item: Item) -> None:` · [src/_pytest/unraisableexception.py:L151-L153][f1]

The three hook wrappers pytest_runtest_setup, pytest_runtest_call, and pytest_runtest_teardown are each registered trylast and simply call collect_unraisable(item.config), flushing any unraisable exceptions that surfaced during the preceding phase at the last opportunity in setup, call, and teardown respectively.

calls: [collect_unraisable](r1-unraisable-exception-plugin.md#u-c6880d906ec8)

<a id="u-f6b00d85d2af"></a>
### `src/_pytest/unraisableexception.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/unraisableexception.py:L143-L148][f1]

Installs the plugin at configure time: saves the current sys.unraisablehook, stores a fresh deque of UnraisableMeta/BaseException in config.stash under unraisable_exceptions, registers cleanup(config=..., prev_hook=...) as a config cleanup, and replaces sys.unraisablehook with unraisable_hook bound to the deque's append.

calls: [src/_pytest/unraisableexception.py:cleanup](r1-unraisable-exception-plugin.md#u-193a1b3bfd08), [unraisable_hook](r1-unraisable-exception-plugin.md#u-d5b865078e46)

<a id="u-d5b865078e46"></a>
### `unraisable_hook`

`def unraisable_hook( unraisable: sys.UnraisableHookArgs, /, *, append: Callable[[Unra…` · [src/_pytest/unraisableexception.py:L102-L140][f1]

Replacement for sys.unraisablehook that defers reporting.

It formats all strings eagerly — the 'Exception ignored in' summary (or the hook's err_msg), the full exception traceback, and the tracemalloc allocation message — because the underlying objects may change before collection, then appends an UnraisableMeta(msg, cause_msg, exc_value) through the injected append callable. If anything raises, it appends the exception itself and re-raises, accepting that the error will be logged twice as it should never happen.

uses: [junitxml-node-reporter](r7-junit-xml-reporting.md#u-a2459e70cff8)

**Uncertainties.**

- The graph attributes the append call to junitxml's _NodeReporter.append, but this file passes deque.append; how junitxml connects is not visible here.

<a id="u-c6880d906ec8"></a>
### `collect_unraisable`

`def collect_unraisable(config: Config) -> None:` · [src/_pytest/unraisableexception.py:L47-L83][f1]

Drains the deferred unraisable queue from the config stash and reports each item.

Plain BaseException entries (failures of the hook itself) become RuntimeError('Failed to process unraisable exception') chained to the original and collected as errors. UnraisableMeta entries trigger warnings.warn(PytestUnraisableExceptionWarning(msg)); if the warning is raised as an error (e.g. -W error), the caught warning is rewritten when exc_value exists — args replaced with cause_msg and __cause__ set to the original exception so the traceback surfaces correctly — and collected. Loop ends on IndexError from popping the deque. A single error is raised directly; multiple are raised as an ExceptionGroup('multiple unraisable exception warnings', errors); the finally block deletes the local references.

<a id="u-193a1b3bfd08"></a>
### `src/_pytest/unraisableexception.py:cleanup`

`def cleanup( *, config: Config, prev_hook: Callable[[sys.UnraisableHookArgs], object]…` · [src/_pytest/unraisableexception.py:L86-L99][f1]

Session cleanup for the unraisable plugin.

Reads the gc iteration count from the stash, defaulting to 5 (experimentally derived, per the Trio project), runs gc_collect_harder that many times because one collection may not free everything, then drains pending unraisables via collect_unraisable. The original sys.unraisablehook is restored in an inner finally, and the stash entry is deleted in an outer finally, so both happen even if collection raises.

calls: [src/_pytest/unraisableexception.py:cleanup](r1-unraisable-exception-plugin.md#u-193a1b3bfd08), [collect_unraisable](r1-unraisable-exception-plugin.md#u-c6880d906ec8)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/unraisableexception.py
