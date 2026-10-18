# Type-Checking Fixtures

**Capability.** Static typing fixtures exercised by type checkers rather than at runtime: every documented view return type, a TypedDict JSON payload, a templated View subclass, and sync/async request-hook registrations.

Read these as executable documentation of accepted signatures. typing_route covers each return type via single-return views; typing_app_decorators covers hook decorator typing.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
