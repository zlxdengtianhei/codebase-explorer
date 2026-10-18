# Session SetupState

**Capability.** Session-scoped ordered stack that sets up collectors along the item chain and tears down exactly the nodes no longer needed, running finalizers and grouping their errors.

Read this to understand fixture/collector setup ordering, cached setup failures, and teardown_exact semantics including the None case that tears down everything. Session start/finish create and drain this stack.

**Depended on by.**

- [Runtest Protocol](r9-runner-protocol.md) · model-inferred · 0 edge(s)
- [SetupState Tests](r9-tests-runner-setupstate.md) · model-inferred · 0 edge(s)

Parent: [Test Runner](r9-test-runner.md)

## Units (5)

<a id="u-29aa083e6978"></a>
### `SetupState`

`class SetupState:` · [src/_pytest/runner.py:L422-L486][f1]

Shared per-session state managing setup/teardown of collectors along the item chain as an ordered stack (dict in insertion order).

Each entry holds the node's finalizers and, if its setup raised, the captured exception and traceback. `__init__` creates the empty stack; addfinalizer asserts the node is active (not a tuple, callable finalizer) and appends the finalizer to its list.

<a id="u-3f7d68549fa9"></a>
### `SetupState.setup`

`def setup(self, item: Item) -> None:` · [src/_pytest/runner.py:L498-L517][f1]

Sets up collectors along the chain to the item.

First asserts every stacked collector is still needed ('previous item was not torn down properly'); if a stacked collector's setup previously raised, that same exception is re-raised with its original traceback — a failed collector fails its whole subtree without retry. Then each not-yet-stacked collector from item.listchain() is pushed with [col.teardown] and col.setup() is run; a TEST_OUTCOME exception is recorded in the stack entry (exception plus traceback) and re-raised.

calls: [Node](r7-node-base-lifecycle.md#u-fadcae42d5de)

<a id="u-904baaf84443"></a>
### `SetupState.teardown_exact`

`def teardown_exact(self, nextitem: Item | None) -> None:` · [src/_pytest/runner.py:L529-L561][f1]

Tears down the stack until reaching nodes shared with nextitem (empty when nextitem is None, tearing down everything).

Pops non-shared nodes one by one, running each node's finalizers in reverse; TEST_OUTCOME from a finalizer is collected — a single one is kept as-is, multiple ones become a BaseExceptionGroup named per node. All collected exceptions are raised at the end: one directly, several as a 'errors during test teardown' BaseExceptionGroup in reverse order. When nextitem is None, asserts the stack is empty afterwards.

<a id="u-9e9f52811e07"></a>
### `src/_pytest/runner.py:pytest_sessionstart`

`def pytest_sessionstart(session: Session) -> None:` · [src/_pytest/runner.py:L106-L107][f1]

Creates the session's SetupState, storing it as session._setupstate at session start.

calls: [SetupState](r9-runner-setupstate.md#u-29aa083e6978)

<a id="u-4adf600a6c70"></a>
### `src/_pytest/runner.py:pytest_sessionfinish`

`def pytest_sessionfinish(session: Session) -> None:` · [src/_pytest/runner.py:L110-L111][f1]

At session finish, tears down the whole setup stack by calling session._setupstate.teardown_exact(None).

calls: [SetupState.teardown_exact](r9-runner-setupstate.md#u-904baaf84443)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/runner.py
