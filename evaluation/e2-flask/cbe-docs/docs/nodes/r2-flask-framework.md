# Flask Framework

**Capability.** The Flask microframework decomposed into its major capabilities: runtime contexts, CLI, configuration, blueprints, request/response objects, views, shared helpers, and the test suites and fixtures that pin their behavior.

Start here to navigate the codebase. Each subtree owns one capability; source modules are kept separate from the tests that exercise them. Edge evidence mixes resolved static calls with model-inferred relations; the latter are weaker.

**Children.**

- [Application and Request Contexts](r2-app-context-and-globals.md) `r2-app-context-and-globals` · 8 unit(s)
- [Command-Line Interface](r2-cli-system.md) `r2-cli-system` · 0 unit(s)
- [Configuration Loading](r2-configuration.md) `r2-configuration` · 10 unit(s)
- [Blueprint System](r2-blueprint-system.md) `r2-blueprint-system` · 0 unit(s)
- [Request and Response Wrappers](r2-request-response-objects.md) `r2-request-response-objects` · 14 unit(s)
- [Class-Based Views](r2-view-system.md) `r2-view-system` · 0 unit(s)
- [Shared Helpers](r2-helpers-utilities.md) `r2-helpers-utilities` · 0 unit(s)
- [Testing Support](r2-testing-support.md) `r2-testing-support` · 5 unit(s)
- [JSON Test Suite](r2-json-tests.md) `r2-json-tests` · 7 unit(s)
- [Templating Test Suite](r2-templating-tests.md) `r2-templating-tests` · 11 unit(s)
- [Logging Test Suite](r2-logging-tests.md) `r2-logging-tests` · 8 unit(s)
- [Error Handler Tests](r2-error-handling-tests.md) `r2-error-handling-tests` · 1 unit(s)
- [Type-Checking Fixtures](r2-type-check-fixtures.md) `r2-type-check-fixtures` · 4 unit(s)

**Depends on.**

- [Scaffold Registration Base](r1-scaffold-shared-base.md) · graph-only · 1 edge(s)
- [Blueprint Registration](r2-blueprint-registration.md) · within containment · 1 edge(s)

**Depended on by.**

- [Application and Request Contexts](r2-app-context-and-globals.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-app-context-and-globals ` → ` r2-flask-framework `)

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Units (1)

<a id="u-115c8d08d2f5"></a>
### `Blueprint.add_url_rule`

`def add_url_rule( self, rule: str, endpoint: str | None = None, view_func: ft.RouteCa…` · [src/flask/sansio/blueprints.py:L412-L441][f1]

Defers registration of a URL rule on the blueprint.

Raises ValueError if endpoint contains a dot or the view function's __name__ contains a dot, protecting the endpoint namespace. Records a lambda that calls state.add_url_rule with the rule, endpoint, view_func, provide_automatic_options, and remaining options; the URL prefix and endpoint name prefixing happen at registration time in BlueprintSetupState.add_url_rule.

calls: [BlueprintSetupState.add_url_rule](r2-blueprint-registration.md#u-14b96816dcf8)

**Uncertainties.**

- the recorded lambda captures provide_automatic_options explicitly, but BlueprintSetupState.add_url_rule's signature does not declare that parameter; it would flow through **options there

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/sansio/blueprints.py
