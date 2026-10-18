"""Regressions at the public host scheduling/submission and partition boundaries."""
import json
from pathlib import Path

import pytest

from cbe import aggregation, host_run, principles, prompts
from cbe.token_budget import count_text_tokens
from test_host_run import _answer, _drive, _repo


def drive(run, transform=lambda item, answer: answer, fail=None):
    handed, outcomes = [], []
    for _ in range(60):
        batch = host_run.next_tasks(run)["tasks"]
        if not batch:
            break
        for item in batch:
            handed.append(item["task"])
            if fail and fail(item):
                outcomes.append(host_run.submit(run, item["task"], error="simulated failure"))
            else:
                answer = transform(item, _answer(item, Path(item["prompt_file"]).read_text()))
                Path(item["output_file"]).write_text(json.dumps(answer))
                outcomes.append(host_run.submit(run, item["task"]))
    return handed, outcomes


def setup_run(tmp_path, monkeypatch, review="none"):
    monkeypatch.setenv("CBE_TREE_MAX_UNITS", "2")
    return Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review=review, jobs=8)["run_dir"])


def test_failed_reviewed_module_does_not_block_regions(tmp_path, monkeypatch):
    run = setup_run(tmp_path, monkeypatch, "all")
    state = json.loads((run / "host/state.json").read_text())
    failed = "module_" + str(len(state["modules"]))
    handed, _ = drive(run, fail=lambda item: item["task"] == failed)
    assert any(t.startswith("tree_region-") for t in handed)
    assert "tree" in handed and "system" in handed
    assert host_run.status(run)["status"] == "partial"


@pytest.mark.parametrize("length,accepted", [(59, True), (64, False)])
def test_region_id_length_checked_before_merge(tmp_path, monkeypatch, length, accepted):
    run = setup_run(tmp_path, monkeypatch)
    def transform(item, value):
        if item["task"].startswith("tree_region-"):
            value["nodes"][0]["id"] = "a" * length
        return value
    handed, outcomes = drive(run, transform)
    regions = [r for r in outcomes if r["task"].startswith("tree_region-")]
    assert regions and all(r["accepted"] == accepted for r in regions)
    if accepted:
        assert host_run.verify(run)["ok"]
        assert all(len(nid) <= 64 for nid in json.loads((run / "catalog.json").read_text())["nodes"])
    else:
        assert any("shorten id" in r.get("error", "") for r in regions)


def test_failed_merge_retains_subtrees_and_separate_failure_notes(tmp_path, monkeypatch):
    run = setup_run(tmp_path, monkeypatch)
    handed, _ = drive(run, fail=lambda item: item["task"] == "tree" or item["task"] == "tree_region-0001")
    assert "system" in handed
    index = (run / "docs/INDEX.md").read_text()
    assert "region merge is failed" in index
    assert "accepted region subtrees are retained" in index
    assert "Region `tree_region-0001` failed" in index
    assert "resume the run to retry it" not in index
    catalog = json.loads((run / "catalog.json").read_text())
    assert any(nid.startswith("r2-") for nid in catalog["nodes"])


def test_submit_checks_composed_tree_not_only_upper_tree(tmp_path, monkeypatch):
    run = setup_run(tmp_path, monkeypatch)
    def transform(item, value):
        if item["task"] == "tree":
            # Accepted subtree r1-root becomes its own parent after grafting.
            value["nodes"][0]["id"] = "r1-root"
        return value
    _, outcomes = drive(run, transform)
    merges = [r for r in outcomes if r["task"] == "tree"]
    assert merges and all(not r["accepted"] for r in merges)


def test_repair_invalidates_leased_regions(tmp_path, monkeypatch):
    run = setup_run(tmp_path, monkeypatch, "all")
    # A failed review can be retried while region leases are outstanding.
    for _ in range(30):
        batch = host_run.next_tasks(run)["tasks"]
        if any(i["task"].startswith("tree_region-") for i in batch):
            old = batch
            break
        for item in batch:
            if item["task"] == "review_1":
                host_run.submit(run, item["task"], error="review transport failure")
                continue
            Path(item["output_file"]).write_text(json.dumps(_answer(item, Path(item["prompt_file"]).read_text())))
            assert host_run.submit(run, item["task"])["accepted"]
    else:
        pytest.fail("no regions dispatched")
    host_run.retry(run, "review_1")
    item = next(i for i in host_run.next_tasks(run)["tasks"] if i["task"] == "review_1")
    Path(item["output_file"]).write_text(json.dumps({"decision": "needs_repair", "issues": ["correct detail"]}))
    assert host_run.submit(run, "review_1")["accepted"]
    item = next(i for i in host_run.next_tasks(run)["tasks"] if i["task"] == "repair_1")
    Path(item["output_file"]).write_text(json.dumps(_answer(item, Path(item["prompt_file"]).read_text())))
    assert host_run.submit(run, "repair_1")["accepted"]
    with pytest.raises(host_run.HostRunError, match="unknown task"):
        host_run.submit(run, old[0]["task"])


def test_partition_keeps_flask_shaped_files_balanced():
    # 294 units, including the two files formerly split 7/7 and 24/3.
    sizes = [14, 27] + [11] * 23
    units = {f"pkg/f{f}.py::u{i}": {"id": f"pkg/f{f}.py::u{i}",
             "summary": "A capability with sufficiently descriptive evidence. " * 5,
             "ranges": [{"path": f"pkg/f{f}.py"}]} for f, size in enumerate(sizes) for i in range(size)}
    render = lambda rows, edges: prompts.tree_prompt(rows, sorted({r["path"] for u in rows.values() for r in u["ranges"]}), edges)
    total = count_text_tokens(render(units, []))
    regions = aggregation.partition(units, [], aggregation.Limits(300, int(total * .96)), render)
    assert len(regions) == 2
    assert abs(len(regions[0]["unit_ids"]) - len(regions[1]["unit_ids"])) <= 27
    homes = {}
    for region in regions:
        for uid in region["unit_ids"]:
            path = uid.split("::")[0]
            assert homes.setdefault(path, region["id"]) == region["id"]


def test_merge_budget_failure_is_explicit_and_preserves_regions(tmp_path, monkeypatch):
    run = setup_run(tmp_path, monkeypatch)
    def transform(item, value):
        if item["task"].startswith("tree_region-"):
            root = value["nodes"][0]
            value["nodes"].extend({**root, "id": f"n{i}", "parent": "root", "unit_ids": [],
                                   "capability": "Long accepted capability. " * 40} for i in range(20))
        return value
    # Region prompts fit; accepted answers make the upper input exceed budget.
    monkeypatch.setenv("CBE_TREE_MAX_TOKENS", "4000")
    handed, _ = drive(run, transform)
    state = json.loads((run / "host/state.json").read_text())
    assert state["tasks"]["tree"]["status"] == "failed"
    assert "exceeds token budget" in state["tasks"]["tree"]["errors"][-1]
    assert "system" in handed
    assert "accepted region subtrees are retained" in (run / "docs/INDEX.md").read_text()


def test_p2_internal_edges_and_p5_threshold(monkeypatch):
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
    monkeypatch.setenv("CBE_TREE_MAX_GRAIN", "5")
    six = {str(i): {} for i in range(6)}
    assert not principles.report({"nodes": nodes[:1]}, six, [], {})["hierarchy"]["ok"]


def test_partition_respects_prompt_render_resource_budget():
    units = {f"pkg/f{f}.py::u{i}": {"id": f"pkg/f{f}.py::u{i}", "summary": "Owns a capability.",
             "ranges": [{"path": f"pkg/f{f}.py"}]} for f in range(100) for i in range(10)}
    calls = 0
    def bounded_render(rows, edges):
        nonlocal calls
        calls += 1
        if calls > 100:
            raise RuntimeError("prompt rendering resource budget exhausted")
        return prompts.tree_prompt(rows, [], edges)
    regions = aggregation.partition(units, [], aggregation.Limits(50, 8000), bounded_render)
    assert len(regions) == 20
    assert {uid for r in regions for uid in r["unit_ids"]} == set(units)


def test_default_budget_handles_indivisible_large_file(monkeypatch):
    monkeypatch.delenv("CBE_TREE_MAX_TOKENS", raising=False)
    monkeypatch.delenv("CBE_TREE_MAX_UNITS", raising=False)
    units = {f"large.py::u{i}": {"id": f"large.py::u{i}", "summary": "Measured evidence. " * 70,
             "ranges": [{"path": "large.py"}]} for i in range(200)}
    render = lambda rows, edges: prompts.tree_prompt(rows, ["large.py"], edges)
    tokens = count_text_tokens(render(units, []))
    assert 32000 < tokens < 64000
    assert aggregation.partition(units, [], aggregation.Limits.configured(), render) == []


def test_derived_cache_cannot_change_tree_evidence(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    path = run / "host/aggregation-inputs.json"
    cached = json.loads(path.read_text())
    first = next(iter(cached["records"].values()))
    first["summary"] = "FORGED CACHE EVIDENCE"
    path.write_text(json.dumps(cached))
    assert "FORGED CACHE EVIDENCE" not in host_run.completion_prompt(run, "tree")
