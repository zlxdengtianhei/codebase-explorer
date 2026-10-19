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
