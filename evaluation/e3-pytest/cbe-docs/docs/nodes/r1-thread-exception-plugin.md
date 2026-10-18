# Thread exception plugin

**Capability.** Replaces threading.excepthook at pytest_configure with a hook that queues thread failure metadata, drains the deque as errors via collect_thread_exception called from trylast runtest setup/call/teardown hooks, and restores the previous hook in session cleanup.

Use this subtree for handling exceptions in threads spawned by tests. The three runtest hooks are identical wrappers around collect_thread_exception, so leftover failures surface at the earliest phase boundary. The hook annotates failures using tracemalloc_message.

**Depends on.**

- [Leaked exception reporting](r1-leaked-exception-reporting.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-thread-exception-plugin ` → ` r1-leaked-exception-reporting `)

Parent: [Leaked exception reporting](r1-leaked-exception-reporting.md)

## Units (5)

<a id="u-f1a10badbe16"></a>
### `threadexception.py:runtest-hooks`

`def pytest_runtest_setup(item: Item) -> None:` · [src/_pytest/threadexception.py:L140-L142][f1]

The three pytest_runtest_setup/call/teardown hooks are identical: each is registered trylast=True and simply calls ``collect_thread_exception(item.config)``, so exceptions captured from background threads are drained and reported between each test phase rather than only at session end.

calls: [collect_thread_exception](r1-thread-exception-plugin.md#u-44e0ba1881b5)

<a id="u-ae118c3dbca6"></a>
### `src/_pytest/threadexception.py:pytest_configure`

`def pytest_configure(config: Config) -> None:` · [src/_pytest/threadexception.py:L132-L137][f1]

Install the thread-exception capture for the session: saves the current threading.excepthook, stores a fresh deque under the thread_exceptions stash key on the config, registers a cleanup that runs ``cleanup`` (collecting leftovers and restoring the hook), and installs a functools.partial of thread_exception_hook bound to deque.append as the new global excepthook.

uses: [cleanup](r1-thread-exception-plugin.md#u-7e0e0ce37c21)

<a id="u-1753946253f1"></a>
### `thread_exception_hook`

`def thread_exception_hook( args: threading.ExceptHookArgs, /, *, append: Callable[[Th…` · [src/_pytest/threadexception.py:L92-L129][f1]

Replacement threading excepthook that queues thread failure metadata for later collection.

It computes the thread name ('<unknown>' when args.thread is None), the full formatted traceback text, and a tracemalloc allocation note up front, because thread objects may be gone by collection time; then appends a ThreadExceptionMeta(msg, cause_msg, exc_value) via the injected ``append`` callable. Any internal failure appends the exception itself (which collect_thread_exception converts to a RuntimeError) and re-raises, accepting that the exception is logged twice by design.

calls: [tracemalloc_message](r1-leaked-exception-reporting.md#u-e0457a417bb6)

<a id="u-44e0ba1881b5"></a>
### `collect_thread_exception`

`def collect_thread_exception(config: Config) -> None:` · [src/_pytest/threadexception.py:L38-L74][f1]

Drain the config-stashed deque of captured thread exceptions and surface them as errors.

Each popped item is either a BaseException — meaning the hook itself failed — turned into RuntimeError('Failed to process thread exception') chained as its __cause__, or a ThreadExceptionMeta whose msg is emitted via warnings.warn(PytUnhandledThreadExceptionWarning); when warnings are errors (e.g. -Werror) the caught warning's args are replaced with the precomputed cause_msg and __cause__ set to the original exception so tracebacks display correctly. At the end a single error is re-raised directly; multiple errors raise an ExceptionGroup. A finally block deletes locals. Note the IndexError from popping an empty deque is the loop's exit condition.

uses: [threadexception.py module code (L30–L37)][f1]; raises: [warning_types.py:warning-classes](r3-warning-types.md#u-10c8ce561005)

**Uncertainties.**

- The warning is emitted via warnings.warn, so whether it is recorded, shown, or converted to an error depends on active warning filters configured elsewhere.

<a id="u-7e0e0ce37c21"></a>
### `cleanup`

`def cleanup( *, config: Config, prev_hook: Callable[[threading.ExceptHookArgs], objec…` · [src/_pytest/threadexception.py:L77-L89][f1]

Session-cleanup that restores the previous threading.excepthook and discards the stash deque.

``collect_thread_exception`` runs first (its errors propagate), the hook is restored in an inner finally even if that raises, and the stash key is deleted in an outer finally even if restoration raised. Threads still running at teardown time are not joined, so their later exceptions are intentionally not captured.

**Notes.**

- side_effect: threading.excepthook is a process-global that is temporarily replaced for the whole session.

calls: [collect_thread_exception](r1-thread-exception-plugin.md#u-44e0ba1881b5)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/threadexception.py
