# Class-Based Views

**Capability.** Owns View and MethodView: converting view classes into view functions via as_view, HTTP-method dispatch to same-named methods, and automatic methods inference at subclass creation.

Use this subtree for the class-based view API and its dispatch contract. The test suite pins method dispatch, HEAD handling, inheritance of methods, decorators, and init_every_request semantics.

**Children.**

- [View and MethodView Core](r2-view-core.md) `r2-view-core` · 5 unit(s)
- [View and Async Dispatch Tests](r2-view-tests.md) `r2-view-tests` · 16 unit(s)

Parent: [Flask Framework](r2-flask-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
