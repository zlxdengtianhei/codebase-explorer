# Class-Based Views

**Capability.** Owns View and MethodView: converting view classes into view functions via as_view, HTTP-method dispatch to same-named methods, and automatic methods inference at subclass creation.

Use this subtree for the class-based view API and its dispatch contract. The test suite pins method dispatch, HEAD handling, inheritance of methods, decorators, and init_every_request semantics.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
