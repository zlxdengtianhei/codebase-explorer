"""Script resume accounting regressions."""
import csv
import importlib
import json

from cbe import host_run
from cbe.headless_completion import _csv_row

generator = importlib.import_module("cbe.generate")


def test_mark_result_updates_latest_duplicate(tmp_path):
    path = tmp_path / "calls.csv"
    for result in ("schema_error", "ok"):
        _csv_row(path, {"task": "module_1", "attempt": 1, "result": result})
    generator._mark_result(path, "module_1", 1, "normalized")
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["result"] for row in rows] == ["schema_error", "normalized"]


def test_resume_wall_seconds_accumulates_active_segments(tmp_path, monkeypatch):
    run = tmp_path / "run"
    (run / "host").mkdir(parents=True)
    (run / "host/state.json").write_text(json.dumps({"review": "none"}))
    (run / "summary.json").write_text(json.dumps({"wall_seconds": 100}))
    monkeypatch.setattr(host_run, "resume", lambda *a, **kw: None)
    monkeypatch.setattr(host_run, "next_tasks", lambda *a, **kw: {"tasks": []})
    monkeypatch.setattr(host_run, "mark_partial", lambda *a, **kw: None)
    monkeypatch.setattr(generator, "_delivery_problem", lambda *a: (None, ""))
    monkeypatch.setattr(host_run, "finish", lambda *a: {"status": "complete"})
    ticks = iter([10.0, 12.5])
    monkeypatch.setattr(generator.time, "monotonic", lambda: next(ticks))
    result = generator.generate(tmp_path, run, model="test/model", resume=True)
    assert result["wall_seconds"] == 102.5
    assert json.loads((run / "summary.json").read_text())["wall_seconds"] == 102.5

