"""Print one JSON row of readings for a finished CBE run.

    python readings.py <run-dir> [--wall SECONDS] [--passes N] [--verify] [--name NAME] [--cost FILE]

Everything comes from files in the run directory (summary.json, calls.csv,
catalog.json).  `--wall` is the sum of the wall-clock seconds of every
`cbe generate` command that built the run (a resume is a second command);
`--passes` is how many commands that was.  `--verify` runs `cbe host verify`.

Definitions
  requests       rows in calls.csv, rate-limit waits excluded
  rate_limited   rows in calls.csv with result `rate_limited` (waits inside one call)
  rejected       answers the program refused and asked again: rows whose result is
                 neither `ok` nor `rate_limited`
  reasks         rows with attempt >= 2 (counted once per repeated attempt)
  prompt_tokens  provider input tokens plus cached tokens (host path: input, cache-write and cache-read
                 tokens of the subagent transcripts, from `cbe host cost`; requests are the subagent runs
                 and refusals the `reject` lines of progress.log)
  index_tokens   tokens of docs/INDEX.md as measured by the run (summary tree.index.tokens)
  empty_nodes    tree nodes with no unit in their own subtree
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def _subtree_units(nodes: dict, name: str, memo: dict) -> int:
    if name not in memo:
        node = nodes[name]
        memo[name] = len(node.get("unit_ids") or []) + sum(
            _subtree_units(nodes, child, memo) for child in node.get("children") or [])
    return memo[name]


def readings(run: Path, wall: float | None = None, passes: int | None = None, verify: bool = False,
             name: str | None = None, cost: Path | None = None) -> dict:
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    catalog = json.loads((run / "catalog.json").read_text(encoding="utf-8"))
    calls_file = run / "calls.csv"
    calls = []
    if calls_file.exists():
        with calls_file.open(newline="", encoding="utf-8") as handle:
            calls = list(csv.DictReader(handle))
    rate_limited = sum(1 for row in calls if row["result"] == "rate_limited")
    answers = [row for row in calls if row["result"] != "rate_limited"]
    rejected = sum(1 for row in answers if row["result"] != "ok")
    reasks = sum(1 for row in answers if int(row["attempt"]) >= 2)
    nodes = catalog["nodes"]
    memo: dict = {}
    empty = sum(1 for name in nodes if _subtree_units(nodes, name, memo) == 0)
    source = summary["source_tokens"]
    prompt = (summary.get("input_tokens") or 0) + (summary.get("cache_tokens") or 0)
    output = summary.get("output_tokens") or 0
    if cost is not None:  # host path: no calls.csv; usage comes from `cbe host cost` output
        totals = json.loads(cost.read_text(encoding="utf-8"))
        prompt = sum(totals["totals"][key] for key in ("input_tokens", "cache_write_tokens", "cache_read_tokens"))
        output = totals["totals"]["output_tokens"]
        progress = (run / "progress.log").read_text(encoding="utf-8").splitlines()
        rejected = sum(1 for line in progress if " reject " in line)
        reasks = rejected
        answers = [None] * totals["subagent_runs"]
    tree = summary.get("tree") or {}
    row = {
        "name": name or run.name,
        "status": summary["status"],
        "model": summary.get("model"),
        "files": summary["source_files"],
        "source_tokens": source,
        "modules": summary.get("modules"),
        "units": summary.get("units"),
        "requests": len(answers),
        "rate_limited_rows": rate_limited,
        "rejected": rejected,
        "reasks": reasks,
        "prompt_tokens": prompt,
        "input_tokens": summary.get("input_tokens") if cost is None else totals["totals"]["input_tokens"],
        "cache_tokens": summary.get("cache_tokens") if cost is None else
        totals["totals"]["cache_write_tokens"] + totals["totals"]["cache_read_tokens"],
        "output_tokens": output,
        "prompt_per_source": round(prompt / source, 2) if source else None,
        "output_per_source": round(output / source, 3) if source else None,
        "index_tokens": (tree.get("index") or {}).get("tokens"),
        "nodes": tree.get("nodes"),
        "leaves": tree.get("leaves"),
        "empty_nodes": empty,
        "program_made_titles": tree.get("program_made_titles"),
        "naming_tasks": tree.get("naming_tasks"),
        "unexplained": summary.get("unexplained_count"),
        "pending": len(summary.get("pending") or []),
        "failed": len(summary.get("failed") or []),
        "context_fallback": summary.get("context_fallback_count"),
        "usage_complete": summary.get("usage_complete") if cost is None else not totals.get("usage_unknown"),
        "wall_seconds": wall,
        "passes": passes,
        "first_pass_complete": (passes == 1) if passes is not None else None,
    }
    if verify:
        out = subprocess.run([sys.executable, "-m", "cbe", "host", "verify", "--run-dir", str(run)],
                             capture_output=True, text=True, check=False)
        try:
            result = json.loads(out.stdout)
            row["verify_ok"] = bool(result.get("ok"))
            row["verify_failed_checks"] = [c["check"] for c in result.get("checks", []) if not c.get("ok")]
        except json.JSONDecodeError:
            row["verify_ok"] = False
            row["verify_failed_checks"] = ["verify output is not JSON: " + out.stderr[:200]]
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--wall", type=float)
    ap.add_argument("--passes", type=int)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--name")
    ap.add_argument("--cost", type=Path, help="host path: JSON printed by `cbe host cost`")
    args = ap.parse_args()
    print(json.dumps(readings(args.run_dir, args.wall, args.passes, args.verify, args.name, args.cost), ensure_ascii=False))


if __name__ == "__main__":
    main()
