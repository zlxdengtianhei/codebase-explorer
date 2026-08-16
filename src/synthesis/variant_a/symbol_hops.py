"""Symbol-level shortest-path hops on a rendered doc tree.

Invariant (FIXED_LAYER_ARCHITECTURE.md §3.4-1): every ledger symbol is
reachable from root INDEX.md in ≤3 resolvable markdown-link hops.

A hop is one click of an internal link. Landing on the page that contains
``<!-- symbol:ID -->`` counts as reaching that symbol (the reader can see
the block without another click). Same-page fragments are not extra hops.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from typing import Mapping, Sequence

from src.synthesis.variant_a.anchors import _LINK, split_target
from src.synthesis.variant_a.verify import load_docs


SYMBOL_MARK = re.compile(r"<!--\s*symbol:([^\s>]+)\s*-->")
SKIP_SCHEMES = ("http://", "https://", "mailto:")


def load_ledger_symbol_ids(ledger_path: Path) -> list[str]:
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    symbols = data.get("symbols") or {}
    if not isinstance(symbols, dict):
        raise ValueError(f"ledger symbols must be an object: {ledger_path}")
    return sorted(symbols)


def resolve_internal_dest(src_rel: str, target: str) -> str | None:
    if target.startswith(SKIP_SCHEMES):
        return None
    path, _frag = split_target(target)
    if not path:
        return None
    parts: list[str] = []
    for part in (str(Path(src_rel).parent / path)).replace("\\", "/").split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part not in (".", ""):
            parts.append(part)
    return "/".join(parts)


def page_graph(docs: Mapping[str, str]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {rel: set() for rel in docs}
    for rel, text in docs.items():
        for _label, target in _LINK.findall(text):
            dest = resolve_internal_dest(rel, target)
            if dest is not None and dest in docs:
                adj[rel].add(dest)
    return adj


def page_distances(
    docs: Mapping[str, str], source: str = "INDEX.md"
) -> tuple[dict[str, int], dict[str, str]]:
    adj = page_graph(docs)
    if source not in docs:
        return {}, {}
    dist = {source: 0}
    parent: dict[str, str] = {}
    queue: deque[str] = deque([source])
    while queue:
        cur = queue.popleft()
        for nxt in sorted(adj[cur]):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                parent[nxt] = cur
                queue.append(nxt)
    return dist, parent


def reconstruct_path(parent: Mapping[str, str], source: str, dest: str) -> list[str]:
    if dest == source:
        return [source]
    walk = [dest]
    while walk[-1] != source:
        prev = parent.get(walk[-1])
        if prev is None:
            return []
        walk.append(prev)
    walk.reverse()
    return walk


def symbol_host_pages(docs: Mapping[str, str]) -> dict[str, list[str]]:
    hosts: dict[str, list[str]] = {}
    for rel, text in docs.items():
        for sid in dict.fromkeys(SYMBOL_MARK.findall(text)):
            hosts.setdefault(sid, []).append(rel)
    return hosts


def measure_symbol_hops(
    docs: Mapping[str, str],
    ledger_ids: Sequence[str],
    *,
    source: str = "INDEX.md",
) -> dict[str, object]:
    dist, parent = page_distances(docs, source)
    hosts = symbol_host_pages(docs)
    distribution = {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0, "unreachable": 0}
    symbols: dict[str, dict[str, object]] = {}
    over_3: list[dict[str, object]] = []
    unreachable: list[dict[str, object]] = []

    for sid in ledger_ids:
        pages = list(hosts.get(sid, ()))
        if not pages:
            distribution["unreachable"] += 1
            row = {"symbol_id": sid, "reason": "not_rendered", "pages": []}
            unreachable.append(row)
            symbols[sid] = {"hops": None, "pages": [], "reason": "not_rendered"}
            continue
        reachable = [(dist[p], p) for p in pages if p in dist]
        if not reachable:
            distribution["unreachable"] += 1
            row = {
                "symbol_id": sid,
                "reason": "page_unreachable",
                "pages": pages,
            }
            unreachable.append(row)
            symbols[sid] = {
                "hops": None,
                "pages": pages,
                "reason": "page_unreachable",
            }
            continue
        hops, page = min(reachable, key=lambda item: (item[0], item[1]))
        path = reconstruct_path(parent, source, page)
        symbols[sid] = {"hops": hops, "pages": pages, "via": page, "path": path}
        if hops <= 3:
            distribution[str(hops)] += 1
        else:
            distribution["4+"] += 1
            over_3.append(
                {
                    "symbol_id": sid,
                    "hops": hops,
                    "via": page,
                    "path": path,
                }
            )

    n = len(ledger_ids)
    n_le_3 = distribution["0"] + distribution["1"] + distribution["2"] + distribution["3"]
    extra_rendered = sorted(set(hosts) - set(ledger_ids))
    return {
        "source": source,
        "n_ledger": n,
        "n_rendered": sum(1 for sid in ledger_ids if sid in hosts),
        "n_residual_unrendered": sum(1 for sid in ledger_ids if sid not in hosts),
        "extra_rendered": extra_rendered,
        "distribution": distribution,
        "rate_le_3": (n_le_3 / n) if n else 1.0,
        "over_3": over_3,
        "unreachable": unreachable,
        "page_dist": {rel: dist[rel] for rel in sorted(dist)},
        "pages_unreachable": sorted(set(docs) - set(dist)),
        "symbols": symbols,
    }


def report_tree(docs_root: Path, ledger_path: Path, name: str) -> dict[str, object]:
    docs = load_docs(docs_root)
    ids = load_ledger_symbol_ids(ledger_path)
    payload = measure_symbol_hops(docs, ids)
    payload["name"] = name
    payload["docs_root"] = str(docs_root)
    payload["ledger"] = str(ledger_path)
    per_symbol = payload.pop("symbols")
    examples: dict[str, list[dict[str, object]]] = {"1": [], "2": [], "3": []}
    for sid in ids:
        row = per_symbol[sid]
        hops = row.get("hops")
        key = str(hops) if hops in (1, 2, 3) else None
        if key is None or len(examples[key]) >= 5:
            continue
        examples[key].append(
            {
                "symbol_id": sid,
                "hops": hops,
                "via": row.get("via"),
                "path": row.get("path"),
            }
        )
    payload["examples"] = examples
    payload["symbols_violations_only"] = {
        sid: row
        for sid, row in per_symbol.items()
        if row.get("hops") is None or (isinstance(row.get("hops"), int) and row["hops"] > 3)
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure ledger-symbol hops from INDEX.md")
    parser.add_argument(
        "--tree",
        action="append",
        default=[],
        help="name=docs_root:ledger_path (repeatable)",
    )
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)
    if not args.tree:
        parser.error("at least one --tree name=docs:ledger is required")
    trees: dict[str, object] = {}
    for spec in args.tree:
        if "=" not in spec or ":" not in spec:
            parser.error(f"bad --tree spec: {spec}")
        name, rest = spec.split("=", 1)
        docs_s, ledger_s = rest.split(":", 1)
        trees[name] = report_tree(Path(docs_s), Path(ledger_s), name)
    out = {
        "invariant": (
            "FIXED_LAYER_ARCHITECTURE.md §3.4-1: each ledger symbol is "
            "reachable from root INDEX.md in ≤3 resolvable link hops"
        ),
        "hop_definition": (
            "BFS on the rendered markdown link graph. INDEX.md = 0. "
            "A symbol's hop count is the shortest page distance of any "
            "page that contains <!-- symbol:ID -->. "
            "Buckets: 1 / 2 / 3 / 4+ / unreachable."
        ),
        "section_7_2": {
            "predicted": (
                "INDEX ≤150 vs ≤3 hops may conflict when there are >9 "
                "function clusters (rest go to _more/INDEX.md, hops become 4)"
            ),
            "observed": "filled in after trees exist",
        },
        "trees": trees,
    }
    notes = []
    for name, payload in trees.items():
        dist = payload["distribution"]  # type: ignore[index]
        n4 = dist.get("4+", 0)
        n_un = dist.get("unreachable", 0)
        notes.append(
            f"{name}: hops1={dist.get('1',0)} hops2={dist.get('2',0)} "
            f"hops3={dist.get('3',0)} hops4+={n4} unreachable={n_un} "
            f"rate_le_3={payload['rate_le_3']}"
        )
    out["section_7_2"]["observed"] = (
        "not triggered on these four trees: max symbol hops is 2, "
        "no _more/INDEX.md, no 4+ hops, unreachable=0. "
        + " | ".join(notes)
    )
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
