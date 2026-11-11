"""Regressions at the public host boundary: the derived evidence cache and the principle readings."""
import json
from pathlib import Path

from cbe import host_run, principles
from test_host_run import _drive, _repo


def test_p2_internal_edges_and_p5_threshold():
    units = {u: {} for u in ("a", "b", "c", "shared")}
    nodes = [{"id": "root", "title": "Root", "parent": None, "unit_ids": []},
             {"id": "one", "title": "One", "parent": "root", "unit_ids": ["a", "b"]},
             {"id": "two", "title": "Two", "parent": "root", "unit_ids": ["c"]},
             {"id": "infra", "title": "Infra", "parent": "root", "unit_ids": ["shared"]}]
    edges = [{"from": "a", "to": "b", "kind": "call", "count": 7},
             {"from": "a", "to": "shared", "kind": "call", "count": 2},
             {"from": "c", "to": "shared", "kind": "call", "count": 3}]
    report = principles.report({"nodes": nodes}, units, edges, {})
    rows = {r["principle"]: r for r in report["checks"]}
    assert rows["P2"]["modules"]["one"] == {"internal": 7, "external": 2, "internal_external_ratio": 3.5}
    assert rows["P5"]["shared_units"] == {}
    edges[1]["count"] = 3
    assert principles.report({"nodes": nodes}, units, edges, {})["checks"][4]["shared_units"] == {"shared": {"one": 3, "two": 3}}
    flat = {str(i): {} for i in range(31)}
    assert not principles.report({"nodes": nodes[:1]}, flat, [], {})["hierarchy"]["ok"]


def test_derived_cache_cannot_change_tree_evidence(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    path = run / "host/aggregation-inputs.json"
    cached = json.loads(path.read_text())
    first = next(iter(cached["records"].values()))
    first["summary"] = "FORGED CACHE EVIDENCE"
    path.write_text(json.dumps(cached))
    assert "FORGED CACHE EVIDENCE" not in host_run.completion_prompt(run, "tree_name_1")
