# Report Serialization

**Capability.** JSON round-tripping of reports: _report_to_json/_report_kwargs_from_json convert __dict__ to builtin-serializable values and back, with tagged entry points pytest_report_to_serializable/from_serializable and an INTERNALERROR guard for unknown repr entry types.

Use this subtree when reports cross process boundaries. The classmethods _to_json/_from_json delegate to the module functions; _report_unserialization_failure raises the diagnostic error on unrecognized types.

**Depends on.**

- [Report Model & Rendering](r3-report-model.md) · model-inferred · 0 edge(s)

Parent: [Test & Collection Reports](r3-reports.md)

## Units (7)

<a id="u-604411dfefcd"></a>
### `BaseReport._to_json`

`def _to_json(self) -> dict[str, Any]:` · [src/_pytest/reports.py:L216-L224][f1]

Returns this report as a dict of builtin-serializable entries, delegating to _report_to_json.

Experimental.

<a id="u-decfcceb6ea5"></a>
### `BaseReport._from_json`

`def _from_json(cls, reportdict: dict[str, object]) -> Self:` · [src/_pytest/reports.py:L226-L237][f1]

Class method reconstructing a report of the invoking class from a serialized dict: converts via _report_kwargs_from_json, then instantiates cls(**kwargs).

The caller is responsible for invoking it on the correct class; nothing here validates the report type.

calls: [_report_kwargs_from_json](r3-report-serialization.md#u-98c059d36a78)

**Uncertainties.**

- If invoked on the wrong class, the converted kwargs are passed to that class's __init__ instead; failure mode not visible here.

<a id="u-299e73e18880"></a>
### `_report_to_json`

`def _report_to_json(report: BaseReport) -> dict[str, Any]:` · [src/_pytest/reports.py:L484-L491][f1]

Converts a report's __dict__ into a dict of builtin-serializable values.

longrepr handling: if it has toterminal plus reprtraceback/reprcrash attributes it is serialized structurally (reprcrash via dataclasses.asdict or None, reprtraceback with each entry converted via asdict and nested value-dicts flattened, sections kept, and a 'chain' of serialized (traceback, crash, description) tuples for ExceptionChainRepr, else chain None); if it merely has toterminal it is stringified; otherwise it is kept as-is. Afterwards, any PathLike value is converted with os.fspath, and the 'result' key is replaced by None unconditionally.

**Uncertainties.**

- serialize_exception_longrepr asserts longrepr is not None and casts to ExceptionRepr; a toterminal-bearing longrepr without reprtraceback/reprcrash would be stringified instead, so the cast path is only reached for those shapes.

<a id="u-98c059d36a78"></a>
### `_report_kwargs_from_json`

`def _report_kwargs_from_json(reportdict: dict[str, Any]) -> dict[str, Any]:` · [src/_pytest/reports.py:L557-L564][f1]

Rebuilds constructor kwargs from a serialized report dict, mutating and returning it.

When longrepr is truthy and contains 'reprcrash' and 'reprtraceback', the traceback is rebuilt by mapping each entry through deserialize_repr_entry ('ReprEntry' reconstructs optional ReprFuncArgs/ReprFileLocation/ReprLocals parts and a ReprEntry; 'ReprEntryNative' wraps lines; anything else raises via _report_unserialization_failure) and the crash via ReprFileLocation or None. A non-empty chain yields an ExceptionChainRepr of deserialized (traceback, crash, description) tuples; otherwise a plain ReprExceptionInfo; the longrepr sections are re-attached via addsection, and the reconstructed object replaces the dict's longrepr.

**Uncertainties.**

- Whether ReprEntry's constructor accepts these keyword shapes as written is not verifiable here; mismatch would raise TypeError during deserialization.

<a id="u-f1ddce2c27dd"></a>
### `_report_unserialization_failure`

`def _report_unserialization_failure( type_name: str, report_class: type[BaseReport], …` · [src/_pytest/reports.py:L240-L251][f1]

Raises RuntimeError with an INTERNALERROR-formatted message when a serialized repr entry has an unrecognized type.

Builds the multi-line message with pprint into a StringIO — type name, report class, full report dict, bug-report URL — then raises.

<a id="u-e28fb6a0e739"></a>
### `src/_pytest/reports.py:pytest_report_to_serializable`

`def pytest_report_to_serializable( report: CollectReport | TestReport, ) -> dict[str,…` · [src/_pytest/reports.py:L459-L467][f1]

Serializes a TestReport or CollectReport to a JSON-ready dict: delegates to the report's _to_json and tags the dict with '$report_type' set to the class name.

For any other input returns None (source marks this branch as possibly unreachable).

calls: [BaseReport._to_json](r3-report-serialization.md#u-604411dfefcd)

<a id="u-ab4cd6656f27"></a>
### `src/_pytest/reports.py:pytest_report_from_serializable`

`def pytest_report_from_serializable( data: dict[str, Any], ) -> CollectReport | TestR…` · [src/_pytest/reports.py:L470-L481][f1]

Deserializes a tagged dict back to a report.

Without '$report_type' it returns None. With 'TestReport' or 'CollectReport' it calls that class's _from_json; any other tag trips an `assert False` naming the unknown value.

calls: [BaseReport._from_json](r3-report-serialization.md#u-decfcceb6ea5)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/reports.py
