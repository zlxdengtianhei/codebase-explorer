"""Build a new frozen module run while preserving the previous publication.

Reuse is deliberately narrow: identical module membership, source files,
outgoing graph/interface facts, and every resolved dependency source file.
Unknown local dependencies invalidate reuse when any enrolled source changes.
Accepted function facts carry the same way: identical symbol span in an
unchanged file keeps the fact with its review state and evidence; any change
to the symbol, its file, or its review hash leaves it behind for re-production.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cbe.module_facts import accepted_fact, initialize as fact_initialize
from cbe.module_workflow import _input_hash, _module_ids, accepted_package, initialize
from cbe.module_explanations import (
    _RECORD_KEYS, _REVIEW_KEYS, _checked_evidence_ref, _checked_module,
    _dict_with_keys, _nonempty_text, explanation_content_sha256,
)
from cbe.models import TaskRecord
from cbe.render import render
from cbe.runner import analyze
from cbe.store import LedgerStore


def _outbound(ledger: dict, members: set[str]) -> tuple[list[tuple], set[str], bool]:
    symbols = ledger["inventory"]["symbols"]
    facts: list[tuple] = []
    dependencies: set[str] = set()
    unknown = False
    for edge in ledger["graph"].get("edges") or []:
        if edge.get("subject_id") not in members:
            continue
        target = edge.get("target_id")
        facts.append((edge.get("kind"), edge.get("subject_id"), target,
                      edge.get("status"), edge.get("reason")))
        if target in symbols:
            dependencies.add(symbols[target]["path"])
        elif edge.get("status") != "external":
            unknown = True
    for relation in ledger["inventory"].get("relations") or []:
        if relation.get("subject_id") not in members:
            continue
        target = relation.get("target_id")
        extra = relation.get("extra") or {}
        facts.append((relation.get("kind"), relation.get("subject_id"), target,
                      relation.get("status"), extra.get("module"), relation.get("reason")))
        if target in symbols:
            dependencies.add(symbols[target]["path"])
        elif relation.get("status") not in {"external"}:
            unknown = True
    for edge in ledger["graph"].get("unknown_edges") or []:
        if edge.get("subject_id") in members:
            unknown = True
    # Relation fields may be absent (None) beside string values. Python cannot
    # order such tuples directly; a canonical JSON key keeps duplicate edges
    # and gives the same order for old and new frozen inventories.
    return sorted(facts, key=lambda row: json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )), dependencies, unknown


def _reusable(old: dict, new: dict, old_plan: dict, new_plan: dict,
              gid: str, changed_paths: set[str]) -> tuple[bool, str]:
    if gid not in old_plan["groups"] or gid not in new_plan["groups"]:
        return False, "module_missing"
    before, after = old_plan["groups"][gid], new_plan["groups"][gid]
    for key in ("member_ids", "children", "title", "question_answered"):
        if before.get(key) != after.get(key):
            return False, f"module_{key}_changed"
    members = set(before["member_ids"])
    old_symbols = old["inventory"]["symbols"]
    new_symbols = new["inventory"]["symbols"]
    if any(old_symbols.get(sid) != new_symbols.get(sid) for sid in members):
        return False, "member_symbol_changed"
    member_paths = {old_symbols[sid]["path"] for sid in members}
    if member_paths & changed_paths:
        return False, "member_source_changed"
    old_facts, old_dependencies, old_unknown = _outbound(old, members)
    new_facts, new_dependencies, new_unknown = _outbound(new, members)
    if old_facts != new_facts:
        return False, "outbound_contract_changed"
    if (old_dependencies | new_dependencies) & changed_paths:
        return False, "dependency_source_changed"
    if (old_unknown or new_unknown) and changed_paths:
        return False, "unknown_dependency_requires_review"
    return True, "same_evidence_and_contract"


def _historical_accepted(old: dict, plan: dict, package: dict) -> dict[str, dict]:
    """Check old acceptance metadata without requiring the old tree still exists.

    Source drift is the reason for refresh, so reading old repo files here would
    make every legitimate changed-source refresh impossible. Carried records
    receive full current-source validation against the new frozen tree below.
    """
    if package.get("source_revision") != old["source_revision"]:
        raise ValueError("historical package revision differs from old ledger")
    modules = package.get("modules")
    if not isinstance(modules, dict):
        raise ValueError("historical package modules must be an object")
    accepted: dict[str, dict] = {}
    for gid, value in modules.items():
        record = _dict_with_keys(value, _RECORD_KEYS, f"historical module {gid}")
        _checked_module(gid, plan["groups"], old["inventory"]["symbols"], old["inventory"]["files"])
        author = _nonempty_text(record["author_id"], "historical author_id").strip()
        review = _dict_with_keys(record["review"], _REVIEW_KEYS, "historical review")
        reviewer = _nonempty_text(review["reviewer_id"], "historical reviewer_id").strip()
        if reviewer == author or review["decision"] != "accepted" or review["source_revision"] != old["source_revision"]:
            raise ValueError(f"historical module review is not accepted: {gid}")
        if review["content_sha256"] != explanation_content_sha256(record):
            raise ValueError(f"historical module content hash mismatch: {gid}")
        _checked_evidence_ref(review["evidence_ref"], gid)
        accepted[gid] = record
    return accepted


def _carryable_facts(old: dict, new: dict, changed_paths: set[str]) -> dict[str, tuple[dict, dict]]:
    """Old accepted facts still bound to identical symbols in unchanged files."""
    old_symbols = old["inventory"]["symbols"]
    new_symbols = new["inventory"]["symbols"]
    carried: dict[str, tuple[dict, dict]] = {}
    for sid, detail in (old.get("details") or {}).items():
        if not isinstance(detail, dict) or not accepted_fact(old, sid):
            continue
        symbol = new_symbols.get(sid)
        if symbol is None or old_symbols.get(sid) != symbol:
            continue
        if symbol["path"] in changed_paths:
            continue
        review = (old.get("fact_reviews") or {})[sid]
        carried[sid] = (detail, review)
    return carried


def staged_refresh(old_run: Path, repo: Path, new_run: Path) -> dict[str, Any]:
    old_run, repo, new_run = Path(old_run).resolve(), Path(repo).resolve(), Path(new_run).resolve()
    if new_run.exists():
        raise ValueError("new-run must not exist; the old publication is never overwritten")
    old = LedgerStore(old_run).open()
    if (old.get("documentation_policy") or {}).get("version") != "module-first-v2":
        raise ValueError("old-run must be module-first-v2")
    old_plan = json.loads((old_run / "module_plan.json").read_text(encoding="utf-8"))
    if old.get("module_workflow_version"):
        old_package = accepted_package(old)
    else:
        path = old_run / "module_explanations.json"
        old_package = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "source_revision": old["source_revision"], "modules": {},
        }
    from cbe.module_explanations import validate_module_explanations

    accepted = _historical_accepted(old, old_plan, old_package)
    analyze(repo, new_run, documentation_profile="module-first-v2")
    new_plan = json.loads((new_run / "module_plan.json").read_text(encoding="utf-8"))
    new = LedgerStore(new_run).open()
    old_files = old["inventory"]["files"]
    new_files = new["inventory"]["files"]
    changed_paths = {
        path for path in set(old_files) | set(new_files)
        if (old_files.get(path) or {}).get("content_hash") != (new_files.get(path)).get("content_hash")
    }
    carried_facts = _carryable_facts(old, new, changed_paths)

    def carry_facts(ledger: dict) -> dict:
        for sid, (detail, review) in carried_facts.items():
            ledger.setdefault("details", {})[sid] = json.loads(json.dumps(detail))
            copied_review = json.loads(json.dumps(review))
            copied_review["origin"] = "staged_refresh"
            copied_review["prior_source_revision"] = old["source_revision"]
            ledger.setdefault("fact_reviews", {})[sid] = copied_review
        return ledger

    LedgerStore(new_run).mutate(carry_facts)
    fact_summary = fact_initialize(new_run, batched=True)
    initialize(new_run)
    outcomes = {gid: _reusable(old, new, old_plan, new_plan, gid, changed_paths)
                for gid in accepted}
    carried = {gid: record for gid, record in accepted.items() if outcomes[gid][0]}

    def mutate(ledger: dict) -> dict:
        for gid, record in carried.items():
            copy = json.loads(json.dumps(record))
            copy["review"]["source_revision"] = ledger["source_revision"]
            validate_module_explanations(ledger, new_plan, {
                "source_revision": ledger["source_revision"], "modules": {gid: copy},
            })
            ledger["module_records"][gid] = {
                "state": "accepted", "record": copy, "origin": "staged_refresh",
                "prior_source_revision": old["source_revision"], "usage": "unavailable",
            }
            for kind in ("module_author", "module_review"):
                task_id = f"task:{kind}:{gid}"
                task = TaskRecord.from_dict(ledger["tasks"][task_id])
                task.state = "committed"
                task.output_refs = [gid]
                task.input_hash = _input_hash(ledger, new_plan, gid) if kind == "module_author" else copy["review"]["content_sha256"]
                ledger["tasks"][task_id] = task.to_dict()
        return ledger

    LedgerStore(new_run).mutate(mutate)
    manifest = render(new_run)
    return {
        "old_run": str(old_run), "new_run": str(new_run),
        "old_source_revision": old["source_revision"], "new_source_revision": new["source_revision"],
        "changed_paths": sorted(changed_paths), "carried": sorted(carried),
        "invalidated": {gid: reason for gid, (ok, reason) in outcomes.items() if not ok},
        "new_pending": len(_module_ids(new_plan)) - len(carried),
        "carried_fact_count": len(carried_facts),
        "fact_tasks_satisfied_without_reproduction": fact_summary.get("satisfied_task_count"),
        "published_tokens": (manifest.get("token_budget") or {}).get("published_tokens"),
    }
