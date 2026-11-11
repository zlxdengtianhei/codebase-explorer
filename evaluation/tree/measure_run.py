"""Readings of one finished run's tree: nodes, empty nodes, titles, entry page size, naming calls.

Evaluation tool, not part of the installed package.   usage: python measure_run.py RUN_DIR
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def measure(run: Path) -> dict:
    tree = json.loads((run / "host/accepted/tree.json").read_text(encoding="utf-8"))
    nodes = tree["nodes"]
    kids = defaultdict(list)
    for node in nodes:
        if node["parent"]:
            kids[node["parent"]].append(node["id"])
    by_id = {n["id"]: n for n in nodes}
    empty = [n["id"] for n in nodes if not n["unit_ids"] and not kids[n["id"]]]
    sibling_dups = sum(sum(1 for c in Counter(_norm(by_id[k]["title"]) for k in ks).values() if c > 1)
                       for ks in kids.values())
    titles = Counter(_norm(n["title"]) for n in nodes)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    state = json.loads((run / "host/state.json").read_text(encoding="utf-8"))
    rows = [r for r in csv.DictReader((run / "calls.csv").open(encoding="utf-8"))
            if r["task"].startswith("tree_")]
    events = [json.loads(line) for line in (run / "host/events.jsonl").read_text(encoding="utf-8").splitlines()]
    rejects = [e for e in events if e["event"] == "reject" and str(e.get("task", "")).startswith("tree_")]
    depth = {}

    def walk(nid, d):
        depth[nid] = d
        for k in kids[nid]:
            walk(k, d + 1)

    walk(next(n["id"] for n in nodes if n["parent"] is None), 0)
    index_text = (run / "docs/INDEX.md").read_text(encoding="utf-8")
    return {
        "nodes": len(nodes), "leaves": sum(1 for n in nodes if n["unit_ids"]), "depth": max(depth.values()),
        "empty_nodes": len(empty), "same_parent_duplicate_titles": sibling_dups,
        "tree_wide_duplicate_titles": sum(1 for c in titles.values() if c > 1),
        "program_made_title_nodes": sum(1 for n in nodes if n.get("note")),
        "index": summary["tree"]["index"], "index_lines": index_text.count("\n"),
        "no_maintenance_navigation": "Maintenance navigation" not in index_text,
        "naming_tasks": sorted(t for t, row in state["tasks"].items() if row["kind"] in ("tree_name", "tree_top")),
        "tree_calls": len(rows), "tree_prompt_tokens": sum(int(r["input_tokens"] or 0) for r in rows),
        "tree_output_tokens": sum(int(r["output_tokens"] or 0) for r in rows),
        "tree_cache_tokens": sum(int(r["cache_tokens"] or 0) for r in rows),
        "tree_calls_by_task": dict(Counter(r["task"] for r in rows)),
        "rejected_calls": len(rejects), "rejected_reasons": [e.get("error", "")[:200] for e in rejects],
        "status": state["status"], "verify_ok": state["verify"]["ok"],
    }


if __name__ == "__main__":
    print(json.dumps(measure(Path(sys.argv[1])), indent=2, ensure_ascii=False))
