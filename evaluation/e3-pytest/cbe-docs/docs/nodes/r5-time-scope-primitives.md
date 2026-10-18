# Timing and scope primitives

**Capability.** Shared value types: Instant/Duration for precise perf_counter-based elapsed time with a test-friendly MockTiming dataclass, and the ordered Scope enum underlying fixture scoping.

Use these primitives whenever code needs elapsed time or scope comparisons. setuponly and fixture setup both consume Scope; pytest's own tests use MockTiming to control time.

**Depended on by.**

- [Fixture setup display plugin](r5-setuponly-display.md) · model-inferred · 0 edge(s)

Parent: [Runtime diagnostics and shared primitives](r5-runtime-diagnostics.md)

## Units (4)

<a id="u-313e6e0ed7df"></a>
### `Instant`

`class Instant:` · [src/_pytest/timing.py:L24-L43][f1]

Frozen dataclass representing a point in time with two internally initialized fields: wall-clock time via time.time() and a perf_counter tick.

elapsed() returns a Duration from this instant to a fresh Instant, and as_utc() converts the recorded wall time to a UTC datetime. Both field defaults use lambdas so a patched _pytest.timing.time/perf_counter (e.g. via MockTiming) is honored. elapsed and as_utc are folded here.

<a id="u-e6c0f31e6168"></a>
### `Duration`

`class Duration:` · [src/_pytest/timing.py:L52-L59][f1]

Frozen dataclass pairing a start and stop Instant; its read-only seconds property subtracts the perf_counter ticks for precise elapsed seconds rather than wall-clock difference.

Used as the result of Instant.elapsed. The seconds property is folded here.

<a id="u-3489c6e24187"></a>
### `timing-mocktiming`

`def sleep(self, seconds: float) -> None:` · [src/_pytest/timing.py:L80-L81][f1]

Dataclass letting pytest's own tests control time deterministically.

It holds a static _current_time (defaulting to the timestamp of 2020-05-22 14:20:50); sleep(seconds) advances that stored time without real delay, and time() returns it. patch(monkeypatch) imports _pytest.timing and replaces its sleep, time, and perf_counter bindings with these methods, so pytest code reading timing functions observes the fake clock; perf_counter is mapped to the same static time, meaning measured durations are only what sleep advanced. Covers sleep, time, and patch.

contract: [Instant](r5-time-scope-primitives.md#u-313e6e0ed7df)

<a id="u-046837a5b5a3"></a>
### `Scope`

`class Scope(Enum):` · [src/_pytest/scope.py:L21-L42][f2]

Enum of fixture scopes ordered lower to higher: Function, Class, Module, Package, Session, decorated @total_ordering.

next_lower returns the member one index below in _SCOPE_INDICES, raising ValueError for Function as the lower-most scope; next_higher returns the member one index above, raising ValueError for Session as the upper-most. __lt__ compares member indices, giving total ordering Function < Class < Module < Package < Session. from_user converts a user-supplied scope name: Scope(scope_name) raises ValueError for unknown names, which is converted into a pytest.fail with message '<descr> [from <where> ]got an unexpected scope value '<name>'' (where omitted when None) and pytrace=False; on success the Scope is returned. Module-level _ALL_SCOPES lists members in definition order, _SCOPE_INDICES maps each to its index, and HIGH_SCOPES lists all scopes except Function.

uses: [src/_pytest/outcomes.py][f3]

**Uncertainties.**

- fail() aborts via pytest's outcome mechanism; its exact control-flow effect lives outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/timing.py
[f2]: ../../../../../../eval/pytest-5989efe/src/_pytest/scope.py
[f3]: ../../../../../../eval/pytest-5989efe/src/_pytest/outcomes.py
