"""Group-quality numbers from the published example runs (no model call, no network).

Reads ``<examples>/*/catalog.json.gz`` and ``<examples>/*/summary.json`` and computes, per
example, three numbers about the leaf groups of the module tree:

1. ``single_member_leaf_ratio``: leaf groups with exactly one unit / all leaf groups.
2. ``merges``: ``summary.json`` -> ``tree.program_merged`` when recorded; otherwise
   ``not-recorded`` and the invariant ``leaf_groups == summary.tree.leaves`` is gated.
3. ``low_cover_groups``: leaf groups where fewer than ``LOW_COVER`` of the members carry a
   word of the group's own title (in the unit id, its ``explain`` or its ``ranges[].path``).

A leaf group is a node with non-empty ``unit_ids`` that no other node names as ``parent``.

``--report`` prints the table; ``--check`` also compares with the baseline file and exits 1
when a gate fails.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXAMPLES = ROOT / "examples"
DEFAULT_BASELINE = Path(__file__).resolve().parent / "group_quality_baseline.json"

MAX_SINGLE_MEMBER_LEAF_RATIO = 0.05
MAX_LOW_COVER_GROUPS = 3
LOW_COVER = 0.20

TITLE_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]+")
STOP_WORDS = frozenset(
    "the a an and or of to for in into on by with from that this it its is are be as at not no "
    "but which what each their they".split())


def title_words(title: str) -> list[str]:
    words = (word.lower() for word in TITLE_WORD.findall(title or ""))
    return sorted({word for word in words if word not in STOP_WORDS})


def unit_text(unit_id: str, unit: dict) -> str:
    paths = [str(item.get("path") or "") for item in unit.get("ranges") or []]
    return " ".join([unit_id, str(unit.get("explain") or ""), *paths]).lower()


def leaf_groups(nodes: dict) -> tuple[list[str], list[str]]:
    """Leaf group ids, and a list of problems where ``children`` disagrees with ``parent``."""
    children: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for node_id, node in nodes.items():
        parent = node.get("parent")
        if parent:
            children.setdefault(parent, set()).add(node_id)
    problems = []
    for node_id, node in nodes.items():
        listed = node.get("children")
        if listed is not None and set(listed) != children.get(node_id, set()):
            problems.append(f"node {node_id!r}: children {sorted(listed)} but parent links give "
                            f"{sorted(children.get(node_id, set()))}")
    leaves = [node_id for node_id, node in nodes.items()
              if node.get("unit_ids") and not children.get(node_id)]
    return leaves, problems


def measure_example(example: Path) -> dict:
    catalog = json.loads(gzip.decompress((example / "catalog.json.gz").read_bytes()))
    summary = json.loads((example / "summary.json").read_text(encoding="utf-8"))
    nodes = catalog.get("nodes") or {}
    units = catalog.get("units") or {}
    leaves, problems = leaf_groups(nodes)
    single = 0
    low_cover = []
    for node_id in leaves:
        node = nodes[node_id]
        members = list(node["unit_ids"])
        if len(members) == 1:
            single += 1
        words = title_words(node.get("title") or "")
        carrying = 0
        for unit_id in members:
            text = unit_text(unit_id, units.get(unit_id) or {})
            if any(word in text for word in words):
                carrying += 1
        cover = carrying / len(members)
        if cover < LOW_COVER:
            low_cover.append({"node": node_id, "title": node.get("title") or "",
                              "members": len(members), "cover": round(cover, 2)})
    tree = summary.get("tree") or {}
    return {
        "leaf_groups": len(leaves),
        "single_member": single,
        "single_member_leaf_ratio": round(single / len(leaves), 4) if leaves else 0.0,
        "summary_leaves": tree.get("leaves"),
        "program_merged": tree.get("program_merged"),
        "low_cover_groups": low_cover,
        "problems": problems,
    }


def measure(examples: Path) -> dict[str, dict]:
    found = sorted(path for path in examples.iterdir()
                   if (path / "catalog.json.gz").is_file() and (path / "summary.json").is_file())
    return {path.name: measure_example(path) for path in found}


def _merges(value) -> str:
    return "not-recorded" if value is None else str(value)


def print_report(results: dict[str, dict]) -> None:
    header = (f"{'example':<10} {'leaf groups':>11} {'single':>6} {'ratio':>6} "
              f"{'tree.leaves':>11} {'merges':>12} {'low-cover':>9}")
    print(header)
    print("-" * len(header))
    for name, row in results.items():
        print(f"{name:<10} {row['leaf_groups']:>11} {row['single_member']:>6} "
              f"{row['single_member_leaf_ratio']:>6.2f} {str(row['summary_leaves']):>11} "
              f"{_merges(row['program_merged']):>12} {len(row['low_cover_groups']):>9}")
    total_leaves = sum(row["leaf_groups"] for row in results.values())
    total_single = sum(row["single_member"] for row in results.values())
    total_summary = sum(row["summary_leaves"] or 0 for row in results.values())
    total_low = sum(len(row["low_cover_groups"]) for row in results.values())
    ratio = total_single / total_leaves if total_leaves else 0.0
    print(f"{'total':<10} {total_leaves:>11} {total_single:>6} {ratio:>6.2f} "
          f"{total_summary:>11} {'':>12} {total_low:>9}")
    print()
    print(f"Low-cover leaf groups (cover < {LOW_COVER:.2f}):")
    lows = [(name, group) for name, row in results.items() for group in row["low_cover_groups"]]
    for name, group in lows:
        print(f"  {name}: {group['title']!r} members={group['members']} cover={group['cover']:.2f}")
    if not lows:
        print("  none")


def check(results: dict[str, dict], baseline: dict[str, dict]) -> list[str]:
    failures: list[str] = []
    print()
    print(f"{'example':<10} {'metric':<24} {'baseline':>12} {'now':>12}")
    for name in sorted(set(baseline) | set(results)):
        old, new = baseline.get(name), results.get(name)
        if new is None:
            failures.append(f"{name}: in the baseline but missing from the examples directory")
            continue
        if old is None:
            print(f"{name:<10} (new example, not in the baseline)")
            old = {}
        for metric, show in (("leaf_groups", str), ("single_member", str),
                             ("single_member_leaf_ratio", lambda v: f"{v:.2f}"),
                             ("summary_leaves", str), ("program_merged", _merges),
                             ("low_cover_groups", lambda v: str(len(v)))):
            before = show(old[metric]) if metric in old else "-"
            after = show(new[metric])
            mark = "" if before == after else "   <- changed"
            print(f"{name:<10} {metric:<24} {before:>12} {after:>12}{mark}")
        if new["single_member_leaf_ratio"] > MAX_SINGLE_MEMBER_LEAF_RATIO:
            failures.append(f"{name}: single_member_leaf_ratio {new['single_member_leaf_ratio']:.2f} "
                            f"> {MAX_SINGLE_MEMBER_LEAF_RATIO:.2f} ({new['single_member']} of "
                            f"{new['leaf_groups']} leaf groups have one unit)")
        if new["leaf_groups"] != new["summary_leaves"]:
            failures.append(f"{name}: catalog leaf_groups {new['leaf_groups']} != "
                            f"summary.json tree.leaves {new['summary_leaves']}")
        failures += [f"{name}: {problem}" for problem in new["problems"]]
    total_low = sum(len(row["low_cover_groups"]) for row in results.values())
    if total_low > MAX_LOW_COVER_GROUPS:
        failures.append(f"low_cover_groups {total_low} > {MAX_LOW_COVER_GROUPS} over all examples")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report", action="store_true", help="print the table and exit 0")
    mode.add_argument("--check", action="store_true", help="compare with the baseline; exit 1 on a regression")
    parser.add_argument("--examples", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--write-baseline", action="store_true",
                        help="with --report: write the measured numbers to the baseline file")
    args = parser.parse_args(argv)

    results = measure(args.examples)
    if not results:
        print(f"no example runs found under {args.examples}", file=sys.stderr)
        return 1
    print_report(results)
    if args.report:
        if args.write_baseline:
            frozen = {name: {key: value for key, value in row.items() if key != "problems"}
                      for name, row in results.items()}
            args.baseline.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
            print(f"\nwrote {args.baseline}")
        return 0
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    failures = check(results, baseline)
    print()
    if failures:
        print("FAIL: group-quality gates")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"OK: single_member_leaf_ratio <= {MAX_SINGLE_MEMBER_LEAF_RATIO:.2f} per example, "
          f"leaf_groups == tree.leaves, low_cover_groups <= {MAX_LOW_COVER_GROUPS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
