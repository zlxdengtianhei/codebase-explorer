# PDB facade and wrapper classes

**Capability.** pytestPDB defers to a per-session pdb wrapper class built by _get_pdb_wrapper_class: PytestPdbWrapper customizes do_continue/do_debug/do_quit/get_stack/setup for capture awareness, recursive-debug tracking, and __tracebackhide__ filtering.

Read here to understand how a pdb session is constructed and how its commands interact with pytest's capture manager (_is_capturing) and set_trace replacement.

**Depended on by.**

- [Debugging plugin hooks](r4-debugging-pdb-plugins.md) · graph-confirmed · 2 edge(s)

Parent: [Interactive debugging](r4-debugging-module.md)

## Units (12)

<a id="u-bef0af46a492"></a>
### `pytestPDB`

`class pytestPDB:` · [src/_pytest/debugging.py:L92-L103][f1]

Pseudo-PDB facade that defers to the real pdb class.

Holds class-level state: the active plugin manager and Config, a _saved stack of prior states for restore, a _recursive_debug counter for nested debugger sessions, and a cache _wrapped_pdb_cls of the resolved (usepdb_cls, wrapper class) pair so the wrapper class is rebuilt only when the option changes. Members documented separately handle class import resolution, pdb instance creation, and set_trace.

**Uncertainties.**

- Thread safety of the class-level mutable state is not addressed in the source.

<a id="u-9726f440f365"></a>
### `pytestPDB._import_pdb_cls`

`def _import_pdb_cls(cls, capman: CaptureManager | None):` · [src/_pytest/debugging.py:L109-L146][f1]

Resolves the concrete pdb class to wrap for debugging.

If pytestPDB._config is unset (pytest.set_trace outside a test), returns plain pdb.Pdb without wrapping. Otherwise reads usepdb_cls: when set, imports modname and resolves classname by traversing dot-separated attributes; any exception becomes a UsageError naming the unimportable value. When unset, uses pdb.Pdb. The resolved class is wrapped via _get_pdb_wrapper_class and the (usepdb_cls, wrapped class) pair is cached in _wrapped_pdb_cls; subsequent calls with the same usepdb_cls return the cached wrapper directly.

**Notes.**

- side_effect: The cache is keyed only on usepdb_cls, so a changed capman between calls with the same option reuses the stale wrapper.

**Uncertainties.**

- The cache means capman changes with identical --pdbcls are not reflected; whether that matters at runtime is not established here.

<a id="u-4c27178d7e0f"></a>
### `pytestPDB._get_pdb_wrapper_class`

`def _get_pdb_wrapper_class(cls, pdb_cls, capman: CaptureManager | None):` · [src/_pytest/debugging.py:L148-L152][f1]

Builds and returns a new wrapper class subclassing the given pdb class.

The returned PytestPdbWrapper overrides several pdb commands to integrate capture and pytest hooks; the nested class is documented in its own unit.

group: [PytestPdbWrapper](r4-debugging-pdb-facade.md#u-d4c2d1185262)

<a id="u-d4c2d1185262"></a>
### `PytestPdbWrapper`

`class PytestPdbWrapper(pdb_cls):` · [src/_pytest/debugging.py:L152-L156][f1]

Pdb subclass customized per pytest session; class attributes _pytest_capman (the capture manager or None) and _continued are fixed at class-creation time.

Members documented separately: do_debug, do_continue, do_quit, setup, get_stack.

<a id="u-f02db623ee6a"></a>
### `pytestPDB._get_pdb_wrapper_class.PytestPdbWrapper.do_debug`

`def do_debug(self, arg):` · [src/_pytest/debugging.py:L156-L160][f1]

Increments pytestPDB._recursive_debug around delegating to the base class's do_debug so nested debug sessions are tracked; the base docstring is copied onto this override when the base class has do_debug.

Returns the base command's result.

<a id="u-58c6fea75046"></a>
### `pytestPDB._get_pdb_wrapper_class.PytestPdbWrapper.do_continue`

`def do_continue(self, arg):` · [src/_pytest/debugging.py:L165-L189][f1]

Delegates to the base do_continue, then at the outermost debug level prints a 'PDB continue' banner and resumes IO capturing if it was active: with 'global' capturing the banner says IO-capturing resumed; with per-target capturing it names the target and resumes it; with no capturing only the banner is printed.

Always fires the pytest_leave_pdb hook with the config and this pdb instance, then sets self._continued = True so a later setup() knows to re-suspend capture. Aliased as do_c and do_cont; base docstring copied when available.

**Notes.**

- side_effect: Asserts that pytestPDB._config and _pluginmanager are not None at outermost continue; a missing config would raise AssertionError inside the pdb command.

<a id="u-8ee9348ed41d"></a>
### `pytestPDB._get_pdb_wrapper_class.PytestPdbWrapper.do_quit`

`def do_quit(self, arg): # Raise Exit outcome when quit command is used in pdb. # # Th…` · [src/_pytest/debugging.py:L196-L207][f1]

Delegates to the base do_quit (q/do_exit aliases and base docstring copied when present).

At the outermost recursive-debug level it then calls outcomes.exit('Quitting debugger'), which raises Exit so quitting pdb terminates the whole pytest run rather than producing a BdbQuit traceback; during nested debugging the exit outcome is not raised.

<a id="u-9d1368a850f6"></a>
### `pytestPDB._get_pdb_wrapper_class.PytestPdbWrapper.setup`

`def setup(self, f, tb):` · [src/_pytest/debugging.py:L215-L227][f1]

Called by pdb when re-entering a breakpoint after do_continue.

Delegates to the base setup; when the base returns False (the interaction was not exited) and self._continued is set, suspends global capture including stdin via the stored capture manager so the prompt is usable. Returns the base result.

<a id="u-53dfbe805337"></a>
### `pytestPDB._get_pdb_wrapper_class.PytestPdbWrapper.get_stack`

`def get_stack(self, f, t):` · [src/_pytest/debugging.py:L229-L236][f1]

Delegates to the base get_stack; when the frame argument f is None (post-mortem style), re-indexes to the last stack frame and walks back past any frames whose globals/local f_locals mark __tracebackhide__, so hidden frames are skipped in the initial debugger view.

**Uncertainties.**

- The hide check reads f_locals.get('__tracebackhide__'), relying on tracebackhide being local, not global-only; frames relying on module-level globals may not be skipped.

<a id="u-a8dce2d765ca"></a>
### `pytestPDB._init_pdb`

`def _init_pdb(cls, method, *args, **kwargs):` · [src/_pytest/debugging.py:L240-L277][f1]

Creates a configured pdb instance for a debugging entry point identified by `method`.

Obtains the capture manager plugin and, if present, suspends capturing including stdin. When a config exists, writes a blank terminal line and, at recursive-debug level 0, prints a header: an explicit `header` kwarg if popped from kwargs, otherwise a banner reflecting current capturing state ('global', per-target, or none) naming the method. Instantiates the wrapper class resolved via _import_pdb_cls with remaining kwargs, fires pytest_enter_pdb when a plugin manager exists, and returns the pdb instance.

**Uncertainties.**

- Whether the pop of 'header' mutating kwargs affects callers is unestablished; the dict is local to this call.

<a id="u-5ea2d6c50a0a"></a>
### `pytestPDB.set_trace`

`def set_trace(cls, *args, **kwargs) -> None:` · [src/_pytest/debugging.py:L279-L284][f1]

Replacement for pdb.set_trace: captures the caller's frame via sys._getframe().f_back, initializes the pdb instance via _init_pdb('set_trace', ...) which suspends capture and prints the banner, then arms a breakpoint on the caller's frame with _pdb.set_trace(frame).

**Uncertainties.**

- Whether sys._getframe exists on all supported implementations is assumed by the code; no fallback is present.

<a id="u-25f8fb5912dc"></a>
### `pytestPDB._is_capturing`

`def _is_capturing(cls, capman: CaptureManager | None) -> str | bool:` · [src/_pytest/debugging.py:L103-L107][f1]

Returns the CaptureManager's is_capturing() result when a capture manager is supplied, otherwise False.

Used to decide which 'capturing' header text to display.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/debugging.py
