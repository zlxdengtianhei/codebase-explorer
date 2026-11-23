"""Program readings for the must-link merging, without a model call.

usage: python evaluation/mustlink_readings.py REPO [REPO ...] [--topic tooltip] [--json PATH]

The leaf layer groups units the program hands it, and it hands one task a chunk of
candidates (``layers.leaf_chunks``). Two units in different chunks can never be grouped.
This script measures what the merging changes on a real repository, before and after it:

* candidate groups: the hint the author sees, one per program group;
* groups above the group ceiling (12 members): the author has to divide them again;
* units whose path or name holds a topic word, and how many candidate groups they fall
  in (the "one feature, how many pages" reading);
* declaration/implementation pairs (``mustlink``), and the share in one candidate.

It builds the source context and the inventory with the packaged product modules, so it
needs the tree-sitter grammars and no API key. It feeds ``skeleton`` no graph edges and
no model prose, because both belong to a run: a real run's numbers are higher (more
edges, written summaries). What is comparable is the same repository measured the same
way before and after the change.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cbe import batching, layers, mustlink, skeleton, source_context, symbols  # noqa: E402

DECL_IMPL = "declaration/implementation"


def units_of(repo: Path) -> dict:
    """One unit per inventory symbol: the shape ``skeleton`` and ``layers`` read."""
    files = batching.scan(repo)
    selected = [item.path for item in files]
    context = source_context.build_context(repo, selected)
    inventory = symbols.inventory_from_context(context, selected)
    units = {}
    for path, row in inventory.items():
        for symbol in row["symbols"]:
            units[symbol["id"]] = {"id": symbol["id"], "kind": symbol["kind"], "summary": "",
                                   "ranges": [{"path": path, "lines": symbol["lines"]}]}
    return units


def _groups(nodes: list[dict]) -> list[list[str]]:
    return [sorted(node["unit_ids"]) for node in nodes if node.get("unit_ids")]


def _topic_units(units: dict, topic: str) -> list[str]:
    """Units whose path or symbol name holds the topic word."""
    word = topic.lower()
    out = []
    for uid in units:
        pieces = uid.split("::")
        text = (pieces[0] + " " + (pieces[2] if len(pieces) > 2 else "")).lower()
        if word in text:
            out.append(uid)
    return sorted(out)


def _topic_groups(groups: list[list[str]], topic_units: list[str]) -> int:
    wanted = set(topic_units)
    return sum(1 for group in groups if wanted & set(group))


def _pair_share(groups: list[list[str]], pairs: list[tuple[str, str]]) -> tuple[int, int]:
    home = {uid: index for index, group in enumerate(groups) for uid in group}
    inside = sum(1 for a, b in pairs if home.get(a) is not None and home.get(a) == home.get(b))
    return inside, len(pairs)


def _size_share(groups: list[list[str]], ceiling: int) -> dict:
    sizes = [len(group) for group in groups]
    return {"groups": len(groups), "groups_above_ceiling": sum(1 for size in sizes if size > ceiling),
            "largest": max(sizes, default=0)}


def _topic_groups(groups: list[list[str]], wanted: set[str]) -> int:
    return sum(1 for group in groups if wanted & set(group))


def _topic_concentration(groups: list[list[str]], wanted: set[str]) -> float | None:
    """Share of the topic's units in its largest candidate group: one feature, one place."""
    if not wanted:
        return None
    best = max((len(wanted & set(group)) for group in groups), default=0)
    return round(best / len(wanted), 3)


def _sets_across(groups: list[list[str]], sets: list[list[str]]) -> tuple[int, float]:
    """How many linked sets one candidate group cannot hold, and their mean spread."""
    spreads = []
    for units in sets:
        wanted = set(units)
        spreads.append(sum(1 for group in groups if wanted & set(group)))
    return sum(1 for spread in spreads if spread > 1), round(sum(spreads) / len(spreads), 2) if spreads else 0.0


def _chunks_split(units: dict, groups: list[list[str]], sets: list[list[str]]) -> int:
    chunks = layers.leaf_chunks(units, groups, [])
    return sum(1 for group in sets
               if sum(1 for chunk in chunks if set(chunk["members"]) & set(group)) > 1)


def read_repo(repo: Path, topic: str) -> dict:
    if not repo.is_dir():
        return {"repo": str(repo), "error": "not a directory"}
    units = units_of(repo)
    if not units:
        return {"repo": str(repo), "error": "no units: no supported language in this repository"}
    counted = mustlink.links(units, [])
    before = _groups(skeleton.build(units, [])["nodes"])
    planned = layers.leaf_plan(units, [])
    after = planned["candidates"]
    pairs = list(counted["pairs"])
    linked_sets = planned["linked"] + planned["oversized"]
    wanted = set(_topic_units(units, topic))
    before_inside, pair_count = _pair_share(before, pairs)
    after_inside, _ = _pair_share(after, pairs)
    return {
        "repo": str(repo), "units": len(units), "topic": topic,
        "before": {**_size_share(before, layers.MAX_GROUP),
                   "topic_units": len(wanted),
                   "topic_groups": _topic_groups(before, wanted),
                   "topic_concentration": _topic_concentration(before, wanted),
                   "pairs_in_one_candidate": before_inside, "pairs": pair_count,
                   "share": round(before_inside / pair_count, 3) if pair_count else None,
                   "chunks": len(layers.leaf_chunks(units, before, [])),
                   "linked_sets_across_candidates": _sets_across(before, linked_sets)[0],
                   "linked_sets_mean_candidates": _sets_across(before, linked_sets)[1],
                   "linked_sets_split_by_chunking": _chunks_split(units, before, linked_sets)},
        "after": {**_size_share(after, layers.MAX_GROUP),
                  "topic_units": len(wanted),
                  "topic_groups": _topic_groups(after, wanted),
                  "topic_concentration": _topic_concentration(after, wanted),
                  "pairs_in_one_candidate": after_inside, "pairs": pair_count,
                  "share": round(after_inside / pair_count, 3) if pair_count else None,
                  "chunks": len(layers.leaf_chunks(units, after, planned["linked"])),
                  "linked_sets_across_candidates": _sets_across(after, linked_sets)[0],
                  "linked_sets_mean_candidates": _sets_across(after, linked_sets)[1],
                  "linked_sets_split_by_chunking": 0},
        "mustlink": {"families": counted["families"], "skipped": counted["skipped"],
                     "linked_sets": len(linked_sets),
                     "linked_sets_above_ceiling": len(planned["oversized"])},
        "note": "no graph edges and no model prose: compare the same repository across a change, "
                "not against a full run",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repos", nargs="+", type=Path)
    parser.add_argument("--topic", default="tooltip")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    rows = [read_repo(repo, args.topic) for repo in args.repos]
    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        if "error" in row:
            print(f"{row['repo']}: {row['error']}")
            continue
        print(f"\n{Path(row['repo']).name}: {row['units']} units, links {row['mustlink']['families']}")
        print(f"  before: {row['before']}")
        print(f"  after:  {row['after']}")
        print(f"  linked sets: {row['mustlink']['linked_sets']} kept whole, "
              f"{row['mustlink']['linked_sets_above_ceiling']} above the {layers.MAX_GROUP}-member ceiling, "
              f"skipped {row['mustlink']['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
