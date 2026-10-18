# CallInfo and Collection

**Capability.** CallInfo wraps a single invocation's result/exception with timing; the collection path builds CollectReports for collectors and triggers interactive-exception handling.

Use this to understand how any phase invocation is captured as data and how one node is collected. collect_one_node reuses check_interactive_exception from the protocol capability.

**Depends on.**

- [Runtest Protocol](r9-runner-protocol.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Runtest Protocol](r9-runner-protocol.md) · graph-confirmed · 1 edge(s)
- [Report and CallInfo Tests](r9-tests-runner-reports.md) · model-inferred · 0 edge(s)

Parent: [Test Runner](r9-test-runner.md)

## Units (4)

<a id="u-58f50349ae1a"></a>
### `CallInfo`

`class CallInfo(Generic[TResult]):` · [src/_pytest/runner.py:L274-L291][f1]

Final dataclass holding result/exception info of one invocation ('collect', 'setup', 'call' or 'teardown'), with start/stop epoch times and duration.

Direct construction requires the private _ispytest flag (checked by check_ispytest). The result property raises AttributeError when excinfo is set (there is no valid result) and otherwise returns _result cast to TResult. `__repr__` shows either the result or the excinfo.

<a id="u-05cf9e60ee5c"></a>
### `CallInfo.from_call`

`def from_call( cls, func: Callable[[], TResult], when: Literal["collect", "setup", "c…` · [src/_pytest/runner.py:L323-L359][f1]

Class method invoking func() with no arguments and wrapping the outcome.

An Instant marks start/stop; if func raises any BaseException it is captured via ExceptionInfo.from_current, but exceptions listed in `reraise` (a type or tuple) propagate instead of being wrapped, and result becomes None on capture. Returns a CallInfo with measured times, duration, `when`, result and excinfo.

<a id="u-2c6c3b34523e"></a>
### `src/_pytest/runner.py:pytest_make_collect_report`

`def pytest_make_collect_report(collector: Collector) -> CollectReport:` · [src/_pytest/runner.py:L371-L372][f1]

Produces a CollectReport for a collector.

The inner collect() loads the Directory's conftest modules inside the CallInfo wrapper — so a conftest import failure becomes a collection error — then lists collector.collect(). The call is wrapped with reraise=(KeyboardInterrupt, SystemExit). Without excinfo the outcome is 'passed' and result is the collected nodes; for a skip (Skipped or unittest.SkipTest if loaded) the outcome is 'skipped' with longrepr (reprcrash path, lineno, message) built from a 'line'-style repr that must be an ExceptionChainRepr; otherwise 'failed', with collector.repr_failure(excinfo) as longrepr, wrapped in CollectErrorRepr if it is a bare string. The CallInfo is stashed as rep.call for collect_one_node.

calls: [Collector](r7-item-collector-types.md#u-f40d9f019e2b), [CollectReport](r3-report-model.md#u-5719d522515d)

<a id="u-27f66eb3a009"></a>
### `collect_one_node`

`def collect_one_node(collector: Collector) -> CollectReport:` · [src/_pytest/runner.py:L564-L571][f1]

Collects one node: fires pytest_collectstart, builds the CollectReport via pytest_make_collect_report, pops the stashed 'call' from the report dict, and fires pytest_exception_interact when check_interactive_exception says the collection error warrants it.

Returns the report.

calls: [check_interactive_exception](r9-runner-protocol.md#u-7ffbad734e38)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/runner.py
