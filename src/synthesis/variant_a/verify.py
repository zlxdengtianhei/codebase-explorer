"""Mechanical scans the orchestrator can re-run. No adjectives."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.synthesis.variant_a.anchors import _LINK, parse_line_fragment, split_target
from src.synthesis.variant_a.line_ranges import audit_tree
from src.synthesis.variant_a.page_tree import MAX_DETAIL_LINES


INDEX_LINE_CAP = 150
UP_RE = re.compile(r"↑")
DOWN_HINT = re.compile(r"下层|功能|PART-|DETAIL")


def load_docs(docs_root: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted(docs_root.rglob("*.md")):
        rel = path.relative_to(docs_root).as_posix()
        docs[rel] = path.read_text(encoding="utf-8")
    return docs


def page_lengths(docs: dict[str, str]) -> dict[str, object]:
    rows = []
    over_detail = []
    over_index = []
    for rel, text in sorted(docs.items()):
        n = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        rows.append({"file": rel, "lines": n})
        if rel.endswith("INDEX.md") and n > INDEX_LINE_CAP:
            over_index.append({"file": rel, "lines": n})
        if not rel.endswith("INDEX.md") and n > MAX_DETAIL_LINES:
            over_detail.append({"file": rel, "lines": n})
    return {
        "pages": rows,
        "over_index_150": over_index,
        "over_detail_400": over_detail,
        "max_lines": max((row["lines"] for row in rows), default=0),
        "ok_no_page_over_400": not over_detail,
        "ok_index_le_150": not over_index,
    }


def _internal_links(text: str) -> list[tuple[str, str]]:
    out = []
    for label, target in _LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        out.append((label, target))
    return out


def navigation(docs: dict[str, str]) -> dict[str, object]:
    """Every page has an up-link; every non-leaf has a down-link."""

    children: dict[str, set[str]] = {rel: set() for rel in docs}
    for rel, text in docs.items():
        for _label, target in _internal_links(text):
            path, _ = split_target(target)
            if not path:
                continue
            dest = str((Path(rel).parent / path))
            dest = Path(dest).as_posix()
            # normalize ..
            parts: list[str] = []
            for part in dest.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part not in (".", ""):
                    parts.append(part)
            dest = "/".join(parts)
            if dest in docs and dest != rel:
                children[rel].add(dest)
    # invert: who points at me from a shorter path (parent heuristic)
    missing_up: list[str] = []
    missing_down: list[str] = []
    for rel, text in docs.items():
        has_up = bool(UP_RE.search(text))
        if not has_up:
            missing_up.append(rel)
        is_leaf = rel.endswith("DETAIL.md") or "/PART-" in rel or rel.startswith("_unassigned/")
        if not is_leaf and not children[rel]:
            missing_down.append(rel)
    return {
        "missing_up": missing_up,
        "missing_down": missing_down,
        "ok_up": not missing_up,
        "ok_down": not missing_down,
        "out_degree": {rel: sorted(dests) for rel, dests in children.items() if dests},
    }


def hops(docs: dict[str, str]) -> dict[str, object]:
    if "INDEX.md" not in docs:
        return {"error": "no INDEX.md"}
    adj: dict[str, set[str]] = {rel: set() for rel in docs}
    for rel, text in docs.items():
        for _label, target in _internal_links(text):
            path, _ = split_target(target)
            if not path:
                continue
            dest_parts: list[str] = []
            for part in (str(Path(rel).parent / path)).replace("\\", "/").split("/"):
                if part == "..":
                    if dest_parts:
                        dest_parts.pop()
                elif part not in (".", ""):
                    dest_parts.append(part)
            dest = "/".join(dest_parts)
            if dest in docs:
                adj[rel].add(dest)
    dist = {"INDEX.md": 0}
    queue = ["INDEX.md"]
    while queue:
        cur = queue.pop(0)
        for nxt in adj[cur]:
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)
    unreachable = sorted(set(docs) - set(dist))
    over = {rel: d for rel, d in dist.items() if d > 3}
    return {
        "dist": dist,
        "unreachable": unreachable,
        "over_3_hops": over,
        "ok_le_3": not over and not unreachable,
    }


def report(docs_root: Path) -> dict[str, object]:
    docs = load_docs(docs_root)
    line = audit_tree(docs)
    lengths = page_lengths(docs)
    nav = navigation(docs)
    hop = hops(docs)
    return {
        "docs_root": str(docs_root),
        "n_pages": len(docs),
        "line_ranges": {
            "links_total": line["links_total"],
            "with_line_range": line["with_line_range"],
            "resolved": line["resolved"],
            "failed": line["failed"],
            "rate_with_line_range": line["rate_with_line_range"],
            "rate_resolved": line["rate_resolved"],
            "failed_sample": line["failed_sample"],
        },
        "links": line["links"],
        "lengths": lengths,
        "navigation": nav,
        "hops": hop,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify variant-A doc tree invariants")
    parser.add_argument("docs", help="docs root containing INDEX.md")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)
    payload = report(Path(args.docs))
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
