# Command-Line Entry and Session Lifecycle

**Capability.** src/_pytest/main.py's top-level driver surface: registers all general/warnings/collection CLI and ini options, validates --basetemp, builds the Session via wrap_session, and runs collection and the runtest loop as hook-driven phases, with Interrupted/Failed signaling stop conditions.

Use this to trace a pytest invocation from pytest_cmdline_main through wrap_session to _main's collection and runtestloop hooks. Option registration and basetemp validation shape what the session sees.

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Units (10)

<a id="u-a08bda8be952"></a>
### `_main`

`def _main(config: Config, session: Session) -> int | ExitCode | None:` · [src/_pytest/main.py:L339-L349][f1]

Default session body run by wrap_session: fires the `pytest_collection` hook (populating session.items), then the `pytest_runtestloop` hook (running tests).

Returns ExitCode.TESTS_FAILED if session.testsfailed is nonzero, else ExitCode.NO_TESTS_COLLECTED if session.testscollected is zero, else None (wrap_session turns a falsy return into 0/OK).

uses: [src/_pytest/main.py:Session.perform_collect (2)](r8-collection-tree.md#u-71c6b6672ba8)

<a id="u-3b38c0bd4d73"></a>
### `src/_pytest/main.py:pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/main.py:L56-L248][f1]

Registers all of pytest's general, warnings, collection, and config CLI options and ini settings on the given Parser.

It creates option groups via `parser.getgroup` for "general", "pytest-warnings", "collect", and "debugconfig", adding options like `-x/--exitfirst` and `-c/--config-file` through the private `group._addoption` (needed for reserved lowercase short options) and the rest via `group.addoption`. `--basetemp` is declared with `type=validate_basetemp`, so its value is validated (rejecting empty/cwd-ancestor paths) at parse time. Ini options include `filterwarnings`, `norecursedirs` with its default pattern list, `testpaths`, `collect_imported_tests`, and `consider_namespace_packages`. No branching logic beyond option declarations; failures arise from Parser/directory_arg type conversion, not here.

uses: [validate_basetemp](r8-session-lifecycle.md#u-ca570c04e5cf); calls: [Parser.addini](r4-argparsing-parser-api.md#u-8f261b2ced78), [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

<a id="u-3de4a61c2fa5"></a>
### `src/_pytest/main.py:pytest_cmdline_main`

`def pytest_cmdline_main(config: Config) -> int | ExitCode:` · [src/_pytest/main.py:L335-L336][f1]

Hook entry point that simply delegates to wrap_session with `_main` as the body callback, returning whatever exit status the session skeleton produced.

calls: [wrap_session](r8-session-lifecycle.md#u-fee16e208abc); uses: [_main](r8-session-lifecycle.md#u-a08bda8be952)

<a id="u-bfcbd9e2675e"></a>
### `src/_pytest/main.py:pytest_collection`

`def pytest_collection(session: Session) -> None:` · [src/_pytest/main.py:L352-L353][f1]

Default `pytest_collection` hook: delegates entirely to session.perform_collect() with default arguments, which performs the collection phase and populates session.items.

calls: [src/_pytest/main.py:Session.perform_collect (2)](r8-collection-tree.md#u-71c6b6672ba8)

<a id="u-a5a9abb2b647"></a>
### `src/_pytest/main.py:pytest_runtestloop`

`def pytest_runtestloop(session: Session) -> bool:` · [src/_pytest/main.py:L356-L372][f1]

Default `pytest_runtestloop` hook: returns True immediately under `--collect-only`.

Otherwise, if collection produced failures and `continue_on_collection_errors` is not set, raises session.Interrupted with a count message (singular/plural handled). It then iterates session.items, invoking `pytest_runtest_protocol` per item with the next item as lookahead; after each item, a truthy session.shouldfail raises session.Failed, and a truthy session.shouldstop raises session.Interrupted, both aborting the loop. Returns True when the loop completes.

raises: [Interrupted](r8-session-lifecycle.md#u-17059579b102)

<a id="u-477de989a11f"></a>
### `Failed`

`class Failed(Exception):` · [src/_pytest/main.py:L479-L480][f1]

Exception signaling a stop as a failed test run (subclasses Exception).

Raised when session.shouldfail is set, causing wrap_session to record ExitCode.TESTS_FAILED.

<a id="u-17059579b102"></a>
### `Interrupted`

`class Interrupted(KeyboardInterrupt):` · [src/_pytest/main.py:L473-L476][f1]

Exception signaling that the test run was interrupted; subclasses KeyboardInterrupt so the runtime treats it as an interrupt, and sets `__module__` to "builtins" (a py3 compat choice so tracebacks render cleanly).

Raised by the runtest loop and collection-start checks with the stop reason as message.

<a id="u-fee16e208abc"></a>
### `wrap_session`

`def wrap_session( config: Config, doit: Callable[[Config, Session], int | ExitCode | …` · [src/_pytest/main.py:L276-L332][f1]

Skeleton command-line driver: constructs a Session from config, runs the session lifecycle, and returns the session's exitstatus.

Initializes `exitstatus = ExitCode.OK`, tracks an `initstate` counter (0 before configure, 1 after `_do_configure`, 2 after `pytest_sessionstart`). Inside the try: `doit(config, session)`'s truthy return becomes exitstatus (else 0). Exception order: UsageError sets USAGE_ERROR and re-raises; Failed sets TESTS_FAILED and is swallowed; KeyboardInterrupt or `exit.Exception` computes an exit status (a custom exit returncode overrides INTERRUPTED; before sessionstart the message is written to stderr) and fires the `pytest_keyboard_interrupt` hook; any other BaseException sets INTERNAL_ERROR, captures excinfo, and reports via `config.notify_exception` — if that reporting itself raises `exit.Exception`, its returncode overrides the status and it is printed, and a caught SystemExit writes a diagnostic instead. The finally block always clears excinfo (breaking a reference cycle), chdirs back to `session.startpath`, fires `pytest_sessionfinish` when initstate >= 2 (an `exit.Exception` there can override the exit status via returncode), then runs `config._ensure_unconfigure()`.

calls: [Config._do_configure](r2-config-lifecycle.md#u-dd4c3d492d72), [Config._ensure_unconfigure](r2-config-lifecycle.md#u-219ad4a29791), [Config.notify_exception](r2-config-lifecycle.md#u-762ec43ea2be)

**Uncertainties.**

- Behavior of `Session.from_config` construction failing before the try block is not covered by any handler in this function.

<a id="u-ca570c04e5cf"></a>
### `validate_basetemp`

`def validate_basetemp(path: str) -> str: # GH 7119` · [src/_pytest/main.py:L251-L259][f1]

Validates the --basetemp value as an argparse type converter, raising argparse.ArgumentTypeError with a fixed message when the path is empty, or when the given path is an ancestor of (or equal to) the current working directory.

The ancestor check runs twice: once against `Path.cwd()` compared with the absolute given path, and once comparing resolved (symlink-following) forms of both, catching cases where symlinks disguise the cwd relationship. On success it returns the original string unchanged. The nested `is_ancestor(base, query)` helper returns True on equality and otherwise checks `query in base.parents`.

group: [validate_basetemp](r8-session-lifecycle.md#u-ca570c04e5cf)

**Uncertainties.**

- The resolved-path comparison may raise OSError from Path.resolve() on broken paths; that is not handled in the visible source.

<a id="u-b313e28583d0"></a>
### `main.py module code (L1–L55)`

`module_region` · [src/_pytest/main.py:L1-L55][f1]

Imports and a TYPE_CHECKING block providing `Self` and the FixtureManager type for annotations only; no runtime behavior.

group: [src/_pytest/main.py:pytest_addoption](r8-session-lifecycle.md#u-3b38c0bd4d73)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/main.py
