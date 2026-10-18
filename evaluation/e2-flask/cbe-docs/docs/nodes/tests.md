# Test Suites and Fixture Apps

**Capability.** The behavioral specification of the framework: functional tests over routing, sessions, hooks, and errors; helper and config test modules; test-client behavior tests; and importable fixture applications used as CLI, blueprint, subdomain, and hello-world targets.

Use this subtree to find where a given behavior is pinned. Fixture apps are real importable packages consumed by CLI discovery, subdomain, and blueprint tests rather than tests themselves.

Parent: [Flask App Region](flask-app-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
