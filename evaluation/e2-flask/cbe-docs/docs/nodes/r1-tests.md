# Test Suites and Fixture Apps

**Capability.** The behavioral specification of the framework: functional tests over routing, sessions, hooks, and errors; helper and config test modules; test-client behavior tests; and importable fixture applications under tests/test_apps used as CLI, blueprint, subdomain, and hello-world targets.

Use this subtree to find where a given behavior is pinned. Fixture apps are real importable packages consumed by CLI discovery, subdomain, and blueprint tests rather than tests themselves.

**Children.**

- [Functional Behavior Tests](r1-tests-functional.md) `r1-tests-functional` · 19 unit(s)
- [Helper and Resource Tests](r1-tests-helpers.md) `r1-tests-helpers` · 15 unit(s)
- [Configuration Tests](r1-tests-config.md) `r1-tests-config` · 19 unit(s)
- [Test Client Behavior Tests](r1-tests-client.md) `r1-tests-client` · 25 unit(s)
- [Fixture Applications](r1-tests-fixture-apps.md) `r1-tests-fixture-apps` · 20 unit(s)

Parent: [Flask Framework](r1-flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
