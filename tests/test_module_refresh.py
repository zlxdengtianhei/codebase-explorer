from __future__ import annotations

import json
from pathlib import Path

from cbe.module_explanations import explanation_content_sha256
from cbe.module_refresh import _outbound, staged_refresh
from cbe.runner import analyze
from cbe.store import LedgerStore


def _source(name: str, marker: int = 1) -> str:
    filler = "DATA = {\n" + "".join(f"    'k{i}': {i},\n" for i in range(700)) + "}\n"
    return filler + f"\ndef {name}(x):\n    return x + {marker}\n"


def test_staged_refresh_carries_only_unchanged_independent_module(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for name in ("alpha", "beta"):
        folder = repo / name
        folder.mkdir(parents=True)
        (folder / "service.py").write_text(_source(name))
    old_run = tmp_path / "old"
    old = analyze(repo, old_run, documentation_profile="module-first-v2")
    plan = json.loads((old_run / "module_plan.json").read_text())
    gid = "module:alpha"
    assert gid in plan["groups"]
    member = next(sid for sid in plan["groups"][gid]["member_ids"] if "function" in sid)
    evidence = tmp_path / "review.txt"
    evidence.write_text("Verified alpha against frozen source.\n")
    record = {"author_id": "author-session", "summary": "Alpha returns its argument plus one.",
              "flow": "The function computes x + 1 and returns it.", "uncertainties": "",
              "key_symbols": [member], "source_refs": [{"path": "alpha/service.py", "line": 704}]}
    record["review"] = {"reviewer_id": "reviewer-session", "decision": "accepted",
        "content_sha256": explanation_content_sha256(record),
        "source_revision": old["source_revision"], "evidence_ref": str(evidence)}
    (old_run / "module_explanations.json").write_text(json.dumps({
        "source_revision": old["source_revision"], "modules": {gid: record}}))
    (repo / "beta" / "service.py").write_text(_source("beta", marker=2))
    new_run = tmp_path / "new"
    result = staged_refresh(old_run, repo, new_run)
    assert result["carried"] == [gid]
    assert (Path(LedgerStore(old_run).open()["reader_output_dir"]) / "INDEX.md").exists()
    new = LedgerStore(new_run).open()
    assert new["module_records"][gid]["state"] == "accepted"
    assert new["module_records"][gid]["record"]["review"]["source_revision"] == new["source_revision"]


def test_outbound_orders_missing_and_named_targets_without_losing_edges() -> None:
    ledger = {
        "inventory": {"symbols": {}},
        "graph": {"edges": [
            {"kind": "call", "subject_id": "f", "target_id": "target", "status": "resolved"},
            {"kind": "call", "subject_id": "f", "target_id": None, "status": "unresolved"},
        ]},
    }
    facts, _, unknown = _outbound(ledger, {"f"})
    assert len(facts) == 2
    assert {item[2] for item in facts} == {None, "target"}
    assert unknown is True


def test_staged_refresh_reuses_module_on_identical_frozen_tree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    folder = repo / "alpha"
    folder.mkdir(parents=True)
    (folder / "service.py").write_text(_source("alpha"))
    old_run = tmp_path / "old"
    old = analyze(repo, old_run, documentation_profile="module-first-v2")
    plan = json.loads((old_run / "module_plan.json").read_text())
    gid = next(gid for gid, group in plan["groups"].items() if group.get("member_ids"))
    member = next(sid for sid in plan["groups"][gid]["member_ids"] if "function" in sid)
    evidence = tmp_path / "review.txt"
    evidence.write_text("Independent review of identical frozen source.\n")
    record = {"author_id": "author-session", "summary": "Alpha returns its argument plus one.",
              "flow": "The function computes x + 1 and returns it.", "uncertainties": "",
              "key_symbols": [member], "source_refs": [{"path": "alpha/service.py", "line": 704}]}
    record["review"] = {"reviewer_id": "reviewer-session", "decision": "accepted",
        "content_sha256": explanation_content_sha256(record),
        "source_revision": old["source_revision"], "evidence_ref": str(evidence)}
    (old_run / "module_explanations.json").write_text(json.dumps({
        "source_revision": old["source_revision"], "modules": {gid: record}}))

    result = staged_refresh(old_run, repo, tmp_path / "new")
    assert result["changed_paths"] == []
    assert result["carried"] == [gid]
    assert result["invalidated"] == {}
    assert result["old_source_revision"] == result["new_source_revision"]
    assert LedgerStore(tmp_path / "new").open()["module_records"][gid]["state"] == "accepted"


def test_staged_refresh_invalidates_changed_member(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    folder = repo / "alpha"
    folder.mkdir(parents=True)
    (folder / "service.py").write_text(_source("alpha"))
    old_run = tmp_path / "old"
    old = analyze(repo, old_run, documentation_profile="module-first-v2")
    plan = json.loads((old_run / "module_plan.json").read_text())
    gid = next(gid for gid, group in plan["groups"].items() if group.get("member_ids"))
    member = next(sid for sid in plan["groups"][gid]["member_ids"] if "function" in sid)
    evidence = tmp_path / "review.txt"
    evidence.write_text("Verified original version.\n")
    record = {"author_id": "author-session", "summary": "Alpha adds one.",
              "flow": "Returns x + 1.", "uncertainties": "", "key_symbols": [member],
              "source_refs": [{"path": "alpha/service.py", "line": 704}]}
    record["review"] = {"reviewer_id": "reviewer-session", "decision": "accepted",
        "content_sha256": explanation_content_sha256(record),
        "source_revision": old["source_revision"], "evidence_ref": str(evidence)}
    (old_run / "module_explanations.json").write_text(json.dumps({
        "source_revision": old["source_revision"], "modules": {gid: record}}))
    (folder / "service.py").write_text(_source("alpha", marker=2))
    new_run = tmp_path / "new"
    result = staged_refresh(old_run, repo, new_run)
    assert result["carried"] == []
    assert result["invalidated"][gid] in {"member_symbol_changed", "member_source_changed"}
    assert LedgerStore(new_run).open()["module_records"] == {}


def test_staged_refresh_carries_accepted_facts_and_commits_covered_tasks(tmp_path: Path) -> None:
    from cbe.module_facts import _sha_json, accepted_fact

    repo = tmp_path / "repo"
    for name in ("alpha", "beta"):
        folder = repo / name
        folder.mkdir(parents=True)
        (folder / "service.py").write_text(_source(name))
    old_run = tmp_path / "old"
    analyze(repo, old_run, documentation_profile="module-first-v2")
    from cbe.module_facts import initialize as fact_initialize
    fact_initialize(old_run, batched=True)
    old_ledger = LedgerStore(old_run).open()
    alpha_sid = next(sid for sid, symbol in old_ledger["inventory"]["symbols"].items()
                     if symbol["path"] == "alpha/service.py" and symbol["kind"] == "function")
    beta_sid = next(sid for sid, symbol in old_ledger["inventory"]["symbols"].items()
                    if symbol["path"] == "beta/service.py" and symbol["kind"] == "function")
    detail = {"symbol_id": alpha_sid, "behavior": "Alpha adds one to its argument.",
              "inputs_outputs": None, "effects": None, "failures": None,
              "dependencies": None, "unresolved": None}

    def seed(current: dict) -> dict:
        current.setdefault("details", {})[alpha_sid] = detail
        current.setdefault("fact_reviews", {})[alpha_sid] = {
            "state": "source_checked", "content_sha256": _sha_json(detail),
            "author_id": "author-session", "reviewer_id": "reviewer-session",
        }
        return current

    LedgerStore(old_run).mutate(seed)
    assert accepted_fact(LedgerStore(old_run).open(), alpha_sid)

    (repo / "beta" / "service.py").write_text(_source("beta", marker=2))
    new_run = tmp_path / "new"
    result = staged_refresh(old_run, repo, new_run)
    assert result["carried_fact_count"] == 1
    new = LedgerStore(new_run).open()
    assert new["details"][alpha_sid] == detail
    review = new["fact_reviews"][alpha_sid]
    assert review["state"] == "source_checked"
    assert review["origin"] == "staged_refresh"
    assert review["prior_source_revision"] == old_ledger["source_revision"]
    assert accepted_fact(new, alpha_sid)
    assert beta_sid not in (new.get("details") or {})
    # The carried fact is never re-produced: either its whole batch task is
    # committed as satisfied, or a partial batch is claimed without it.
    from cbe.module_facts import claim
    alpha_task = next(tid for tid, task in new["tasks"].items()
                      if tid.startswith("task:fact_author:") and alpha_sid in (task.get("input_ids") or []))
    if (new["tasks"][alpha_task].get("extra") or {}).get("satisfied_by_accepted_facts"):
        assert new["tasks"][alpha_task]["state"] == "committed"
        with pytest.raises(Exception, match="accepted facts"):
            claim(new_run, alpha_task.split("task:fact_author:")[1], owner="re-producer")
    else:
        claimed = claim(new_run, alpha_task.split("task:fact_author:")[1], owner="co-author")
        packet = json.loads(Path(claimed["packet_path"]).read_text())
        assigned = {item["symbol_id"] for item in packet["assignments"]}
        assert alpha_sid not in assigned
        assert beta_sid in assigned
    # Old publication is untouched.
    assert (Path(LedgerStore(old_run).open()["reader_output_dir"]) / "INDEX.md").exists()
