"""Regression at the public host boundary: the derived evidence cache."""
import json
from pathlib import Path

from cbe import host_run
from test_host_run import _drive, _repo


def test_derived_cache_cannot_change_tree_evidence(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    path = run / "host/aggregation-inputs.json"
    cached = json.loads(path.read_text())
    first = next(iter(cached["records"].values()))
    first["summary"] = "FORGED CACHE EVIDENCE"
    path.write_text(json.dumps(cached))
    assert "FORGED CACHE EVIDENCE" not in host_run.completion_prompt(run, "tree_name_1")
