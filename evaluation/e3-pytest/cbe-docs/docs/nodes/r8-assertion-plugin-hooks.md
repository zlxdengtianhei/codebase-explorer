# Assertion Plugin Hooks and Session Wiring

**Capability.** Registers the --assert CLI/ini options, stores per-session state (AssertionState under assertstate_key), installs the rewrite import hook during collection, wires comparison and assertion-pass callbacks around each test's protocol, and exposes register_assert_rewrite for eager marking; sessionfinish clears the hook's session reference.

Use this to see when and how rewriting is activated for a session. It delegates actual transformation and explanation rendering to the other children of assertion-rewriting.

**Depends on.**

- [Rewrite Import Hook and pyc Cache](r8-rewrite-import-hook.md) · model-inferred · 0 edge(s)
- [Typed Stash Infrastructure](r8-typed-stash.md) · model-inferred · 0 edge(s)

Parent: [Assertion Rewriting](r8-assertion-rewriting.md)

## Units (12)

<a id="u-f60db21dd8b6"></a>
### `init-py-module-residual`

`module_region` · [src/_pytest/assertion/__init__.py:L1-L25][f1]

Module-level scaffolding of the assertion package __init__: the package docstring, __future__ annotation import, stdlib imports (collections.abc.Generator, sys, typing.Any/Protocol/TYPE_CHECKING), a TYPE_CHECKING-only import of Session from _pytest.main, and imports of the rewrite, truncate, and util submodules plus assertstate_key, Config, hookimpl, Parser, and Item.

This region defines no behavior beyond making those names available to the package.

<a id="u-23cf455c6606"></a>
### `AssertionState`

`class AssertionState:` · [src/_pytest/assertion/__init__.py:L107-L110][f1]

Container stored under assertstate_key in the config stash holding the assertion plugin's per-session state.

Construction stores the requested mode (e.g. "rewrite"), obtains a named trace logger 'assertion' from config.trace.root, and initializes hook to None; install_importhook later fills hook with the installed AssertionRewritingHook.

uses: [src/_pytest/config/__init__.py][f2]

<a id="u-9f8238a9d520"></a>
### `DummyRewriteHook`

`class DummyRewriteHook:` · [src/_pytest/assertion/__init__.py:L100-L103][f1]

No-op stand-in for the rewrite import hook used when assertion rewriting is disabled or no real hook is on sys.meta_path.

Its mark_rewrite accepts any names and does nothing, so registering modules before rewriting is disabled has no effect and raises nothing.

<a id="u-3326bd7b8d0e"></a>
### `RewriteHook`

`class RewriteHook(Protocol):` · [src/_pytest/assertion/__init__.py:L96-L97][f1]

Structural protocol describing any hook that can record module names to be rewritten: it exposes a single mark_rewrite(*names: str) -> None method.

It exists to give register_assert_rewrite a type covering both the real AssertionRewritingHook and the dummy fallback.

<a id="u-553babe88423"></a>
### `install_importhook`

`def install_importhook(config: Config) -> rewrite.AssertionRewritingHook:` · [src/_pytest/assertion/__init__.py:L116-L123][f1]

Installs the assertion rewrite import hook for a session in 'rewrite' mode.

It creates an AssertionState(mode='rewrite') in the config stash, builds a rewrite.AssertionRewritingHook, inserts it at position 0 of sys.meta_path so it runs before other finders, records it as state.hook, logs the install via the assertion trace, registers a cleanup that removes the hook from sys.meta_path if still present, and returns the hook.

**Notes.**

- side_effect: Mutates sys.meta_path by inserting the hook at index 0; the registered undo removes it only if it is still present.

calls: [AssertionState](r8-assertion-plugin-hooks.md#u-23cf455c6606), [Config.add_cleanup](r2-config-lifecycle.md#u-6ed386e09426); imports: [src/_pytest/assertion/rewrite.py][f3]

**Uncertainties.**

- The docstring says 'raise SystemError if it fails', but the visible body contains no SystemError path; the failure condition is not established here.

<a id="u-a9b9ea51a8e6"></a>
### `pytest_addoption`

`def pytest_addoption(parser: Parser) -> None:` · [src/_pytest/assertion/__init__.py:L26-L68][f1]

Registers the assertion-debugging CLI options and ini settings on the pytest parser.

It adds a `--assert` option in the `debugconfig` group accepting `rewrite` (default) or `plain` to control assertion rewriting, plus three ini options: the boolean `enable_assertion_pass_hook` (default False, enabling the pytest_assertion_pass hook), and `truncation_limit_lines` / `truncation_limit_chars` (both defaulting to None) that override truncation thresholds. It also registers an assertions verbosity knob via Config._add_verbosity_ini using VERBOSITY_ASSERTIONS, letting a higher verbosity produce more detailed failure explanations.

calls: [Parser.addini](r4-argparsing-parser-api.md#u-8f261b2ced78), [Parser.getgroup](r4-argparsing-parser-api.md#u-e2ffc00b5f80)

<a id="u-64bc68d3e870"></a>
### `pytest_assertrepr_compare`

`def pytest_assertrepr_compare( config: Config, op: str, left: Any, right: Any ) -> li…` · [src/_pytest/assertion/__init__.py:L205-L208][f1]

Hook implementation delegating pytest_assertrepr_compare straight to util.assertrepr_compare, passing the config, operator string, and both operands; its return (list of explanation lines or None) is passed through unchanged.

calls: [assertrepr_compare](r2-explanation-formatting.md#u-28eb36a31d2c)

<a id="u-f1cdf4c4ff5d"></a>
### `pytest_collection`

`def pytest_collection(session: Session) -> None: # This hook is only called when test…` · [src/_pytest/assertion/__init__.py:L132-L139][f1]

During collection, hands the Session to the installed rewrite hook.

It reads the AssertionState from the session's config stash; only when a state exists and its hook is not None does it call hook.set_session(session). The comment notes the hook is not invoked in processes that do not collect test modules (e.g. the pytest-xdist managing process), so in those processes this function simply does nothing.

uses: [install_importhook](r8-assertion-plugin-hooks.md#u-553babe88423)

**Uncertainties.**

- Effect of set_session lives in rewrite.AssertionRewritingHook, not visible here.

<a id="u-8d49725f7bb0"></a>
### `callbinrepr`

`def callbinrepr(op, left: object, right: object) -> str | None:` · [src/_pytest/assertion/__init__.py:L152-L178][f1]

Builds the human-readable comparison string used by rewritten assertions.

It calls ihook.pytest_assertref_compare's pytest_assertrepr_compare with op/left/right and takes the first non-empty explanation list; if none, returns None. For the first result it truncates via truncate.truncate_if_required, escapes embedded newlines to literal \n and joins lines with '\n~'; when assertmode is 'rewrite' it additionally doubles '%' characters to protect later % formatting. Returns the joined string.

**Notes.**

- condition: Percent-escaping applies only when item.config.getvalue('assertmode') == 'rewrite'; 'plain' mode keeps single %.

calls: [truncate_if_required](r2-explanation-truncation.md#u-e0d4157994e6)

**Uncertainties.**

- Which hook implementations answer pytest_assertrepr_compare is not visible here; ordering depends on hook registration.

<a id="u-5171b74adf4b"></a>
### `pytest_runtest_protocol`

`def pytest_runtest_protocol(item: Item) -> Generator[None, object, object]:` · [src/_pytest/assertion/__init__.py:L142-L152][f1]

Wrapper hook around each test item's runtest protocol that installs the custom comparison and assertion-pass callbacks on the util module for the item's duration.

It saves the current (util._reprcompare, util._assertion_pass) pair, sets util._reprcompare to a callbinrepr closure and util._config to item.config, and — only if the item's hook has pytest_assertion_pass impls — sets util._assertion_pass to a closure invoking ihook.pytest_assertion_pass. It yields the protocol result in a try, and in finally restores the saved callbacks and resets util._config to None, so the module-level hooks never leak between tests.

**Notes.**

- side_effect: Temporarily mutates module-level globals in _pytest.assertion.util; guaranteed restored via finally.

uses: [src/_pytest/assertion/util.py][f4]

**Uncertainties.**

- Whether exceptions during yield leave state correct: the finally clause restores, but any hook behavior depending on _assertion_pass being None mid-test is not visible.

<a id="u-c53de13f6385"></a>
### `pytest_sessionfinish`

`def pytest_sessionfinish(session: Session) -> None:` · [src/_pytest/assertion/__init__.py:L198-L202][f1]

Clears the Session reference on the rewrite hook at session end.

Reads the AssertionState from the session's config stash and, when it exists and its hook is not None, calls hook.set_session(None) so the hook drops its session before shutdown; otherwise does nothing.

uses: [install_importhook](r8-assertion-plugin-hooks.md#u-553babe88423)

**Uncertainties.**

- set_session(None) semantics live in the rewrite hook, not visible here.

<a id="u-59c6b9232165"></a>
### `register_assert_rewrite`

`def register_assert_rewrite(*names: str) -> None:` · [src/_pytest/assertion/__init__.py:L71-L93][f1]

Marks module names so their assert statements are rewritten on a later import.

It validates that every name in *names is a str, raising TypeError naming the whole args tuple otherwise. It then searches sys.meta_path for an AssertionRewritingHook instance; if found that hook is used, otherwise a DummyRewriteHook no-op is substituted, so the call degrades silently when rewriting is not installed. Finally it calls mark_rewrite(*names) on the chosen hook; the hook itself decides how names are stored.

**Notes.**

- failure: A non-str element anywhere in *names raises TypeError with 'expected module names as *args, got ...' before any hook is touched.

calls: [DummyRewriteHook](r8-assertion-plugin-hooks.md#u-9f8238a9d520); contract: [RewriteHook](r8-assertion-plugin-hooks.md#u-3326bd7b8d0e); imports: [src/_pytest/assertion/rewrite.py][f3]

**Uncertainties.**

- The observable effect of mark_rewrite depends on rewrite.AssertionRewritingHook.mark_rewrite, whose body is not in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/__init__.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/config/__init__.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/rewrite.py
[f4]: ../../../../../../eval/pytest-5989efe/src/_pytest/assertion/util.py
