# Assertion Rewriting

**Capability.** Owns pytest's transparent assertion introspection: rewriting assert statements at import time into instrumented code that captures intermediate values, and producing human-readable failure explanations. Plugin wiring, the import hook, and the AST engine belong together because the plugin exists only to activate and feed the engine.

Read this subtree to understand how plain asserts yield detailed reports. The plugin-hooks child manages session lifecycle and mode; the import-hook child decides which modules are rewritten and caches pycs; the rewriter child is the AST transformation core.

**Children.**

- [Assertion Plugin Hooks and Session Wiring](r8-assertion-plugin-hooks.md) `r8-assertion-plugin-hooks` · 12 unit(s)
- [Rewrite Import Hook and pyc Cache](r8-rewrite-import-hook.md) `r8-rewrite-import-hook` · 20 unit(s)
- [AssertionRewriter AST Transformation and Runtime Helpers](r8-assert-rewriter-ast.md) `r8-assert-rewriter-ast` · 35 unit(s)

Parent: [Pytest Framework and Test Suite](r8-pytest-root.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
