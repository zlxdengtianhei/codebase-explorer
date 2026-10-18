# CLI Entry and Test Support

**Capability.** The python -m flask entry point dispatching to the Click group, plus the app's factory methods for a test client and CLI runner, both overridable via *_class attributes and imported locally to avoid import cycles.

Use this subtree to launch the CLI or to obtain client/runner objects in tests. The classes are swappable; default implementations come from flask.testing and flask.cli.

**Depends on.**

- [FlaskGroup and App Context Commands](r2-cli-command-group.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Test Client Behavior Tests](r1-tests-client.md) · model-inferred · 0 edge(s)
- [Functional Behavior Tests](r1-tests-functional.md) · graph-only · 2 edge(s)
- [View and Async Dispatch Tests](r2-view-tests.md) · graph-only · 2 edge(s)

Parent: [Concrete WSGI Application](r1-concrete-app.md)

## Units (3)

<a id="u-d0221469d015"></a>
### `__main__.py module code (L1–L3)`

`module_region` · [src/flask/__main__.py:L1-L3][f1]

Entry point that imports main from flask.cli and calls it unconditionally at import time, so ``python -m flask`` dispatches to the Click command group.

<a id="u-b8a91912b6a5"></a>
### `Flask.test_client`

`def test_client(self, use_cookies: bool = True, **kwargs: t.Any) -> FlaskClient:` · [src/flask/app.py:L669-L725][f2]

Create a test client: uses self.test_client_class when set, otherwise imports flask.testing.FlaskClient locally.

Instantiates it with (self, self.response_class, use_cookies=use_cookies, **kwargs); kwargs are forwarded to the client constructor. Setting app.testing is documented as required for exceptions to propagate to tests rather than becoming 500 responses.

uses: [class::FlaskClient][f3]

<a id="u-42c783acd68d"></a>
### `Flask.test_cli_runner`

`def test_cli_runner(self, **kwargs: t.Any) -> FlaskCliRunner:` · [src/flask/app.py:L727-L742][f2]

Create a CLI test runner: uses self.test_cli_runner_class when set, otherwise imports FlaskCliRunner locally, constructing cls(self, **kwargs) with the app as first argument and kwargs forwarded.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/flask-85c5d93/src/flask/__main__.py
[f2]: ../../../../../../eval/flask-85c5d93/src/flask/app.py
[f3]: ../../../../../../eval/flask-85c5d93/src/flask/testing.py
