"""Mechanical invariants: page caps, dead-ends, hops, line-range anchors."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path

from src.synthesis.variant_b.types import DETAIL_LINE_LIMIT, INDEX_LINE_LIMIT

_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_RANGE = re.compile(r"^L(\d+)-L(\d+)$")
_EXPLICIT = re.compile(r'<a\s+(?:id|name)="([^"]+)"')
_PROSE = re.compile(r"[A-Za-z\u4e00-\u9fff]{2,}")


def _md_files(docs_root: Path) -> list[Path]:
    return sorted(path for path in docs_root.rglob("*.md") if path.is_file())


def _rel(docs_root: Path, path: Path) -> str:
    return path.relative_to(docs_root).as_posix()


def page_line_counts(docs_root: Path) -> dict[str, int]:
    return {_rel(docs_root, path): len(path.read_text(encoding="utf-8").splitlines()) for path in _md_files(docs_root)}


def oversize_pages(docs_root: Path) -> list[dict[str, object]]:
    bad: list[dict[str, object]] = []
    for path in _md_files(docs_root):
        n = len(path.read_text(encoding="utf-8").splitlines())
        name = path.name
        limit = INDEX_LINE_LIMIT if name == "INDEX.md" else DETAIL_LINE_LIMIT
        if n > limit:
            bad.append({"page": _rel(docs_root, path), "lines": n, "limit": limit})
    return bad


def audit_index_anchors(docs_root: Path) -> dict[str, object]:
    index = docs_root / "INDEX.md"
    text = index.read_text(encoding="utf-8") if index.exists() else ""
    total = with_range = resolved = missing = 0
    broken: list[dict[str, str]] = []
    cache: dict[Path, tuple[set[str], int]] = {}
    for label, target in _LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        total += 1
        path_part, _, frag = target.partition("#")
        tgt = (docs_root / path_part).resolve() if path_part else index.resolve()
        if not tgt.exists():
            missing += 1
            broken.append({"label": label[:40], "target": target, "why": "目标文件不存在"})
            continue
        if tgt not in cache:
            body = tgt.read_text(encoding="utf-8", errors="replace")
            cache[tgt] = (set(_EXPLICIT.findall(body)), len(body.splitlines()))
        ids, n_lines = cache[tgt]
        matched = _RANGE.match(frag)
        if not matched:
            broken.append({"label": label[:40], "target": target, "why": "锚点无行区间"})
            continue
        start, end = int(matched.group(1)), int(matched.group(2))
        if start < 1 or end < start or end > n_lines:
            broken.append({"label": label[:40], "target": target, "why": "行区间越界"})
            continue
        with_range += 1
        if frag in ids:
            resolved += 1
        else:
            broken.append({"label": label[:40], "target": target, "why": "锚点 id 不存在"})
    n = max(1, total)
    return {
        "metric": "anchor_with_line_range",
        "links_total": total,
        "with_line_range": with_range,
        "anchor_resolved": resolved,
        "target_file_missing": missing,
        "rate_with_line_range": round(with_range / n, 4),
        "rate_resolved": round(resolved / n, 4),
        "broken_sample": broken[:16],
    }


def _link_targets(docs_root: Path, path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    here = path.parent
    out: list[str] = []
    for _label, target in _LINK.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path_part, _, _frag = target.partition("#")
        dest = (here / path_part).resolve() if path_part else path.resolve()
        try:
            rel = dest.relative_to(docs_root.resolve()).as_posix()
        except ValueError:
            continue
        out.append(rel)
    return out


def dead_ends(docs_root: Path) -> list[dict[str, str]]:
    pages = {_rel(docs_root, path): path for path in _md_files(docs_root)}
    children: dict[str, set[str]] = defaultdict(set)
    parents: dict[str, set[str]] = defaultdict(set)
    for rel, path in pages.items():
        for dest in _link_targets(docs_root, path):
            if dest in pages and dest != rel:
                children[rel].add(dest)
                parents[dest].add(rel)
    bad: list[dict[str, str]] = []
    for rel in pages:
        if rel != "INDEX.md" and not parents[rel]:
            bad.append({"page": rel, "why": "无上行链接"})
        if rel == "INDEX.md" and not children[rel]:
            bad.append({"page": rel, "why": "根 INDEX 无下行链接"})
        # non-leaf: a page that other pages treat as parent via directory
        # A cluster INDEX must have children; a DETAIL/PART is a leaf even if
        # it points at siblings.
        if rel.endswith("/INDEX.md") and not children[rel]:
            bad.append({"page": rel, "why": "非叶 INDEX 无下行链接"})
    return bad


def hop_distance(docs_root: Path) -> dict[str, object]:
    pages = {_rel(docs_root, path): path for path in _md_files(docs_root)}
    adj: dict[str, set[str]] = defaultdict(set)
    for rel, path in pages.items():
        for dest in _link_targets(docs_root, path):
            if dest in pages:
                adj[rel].add(dest)
    dist: dict[str, int] = {"INDEX.md": 0}
    queue = deque(["INDEX.md"])
    while queue:
        node = queue.popleft()
        for dest in adj[node]:
            if dest not in dist:
                dist[dest] = dist[node] + 1
                queue.append(dest)
    unreachable = [rel for rel in pages if rel not in dist]
    far = [rel for rel, hops in dist.items() if hops > 3]
    return {
        "pages": len(pages),
        "reachable": len(dist),
        "unreachable": unreachable,
        "over_3_hops": far,
        "max_hops": max(dist.values()) if dist else None,
    }


def density(docs_root: Path) -> dict[str, object]:
    prose = 0
    lines = 0
    oneliners = 0
    for path in _md_files(docs_root):
        for line in path.read_text(encoding="utf-8").splitlines():
            lines += 1
            if line.startswith("- [") and "：" in line:
                oneliners += 1
            if line.startswith("```"):
                continue
            prose += len(_PROSE.findall(line))
    return {
        "md_lines": lines,
        "prose_tokens": prose,
        "trace_or_toc_oneliners": oneliners,
        "pages": len(_md_files(docs_root)),
    }


def scan_docs(docs_root: Path) -> dict[str, object]:
    counts = page_line_counts(docs_root)
    return {
        "docs_root": str(docs_root),
        "page_lines": counts,
        "oversize": oversize_pages(docs_root),
        "anchors": audit_index_anchors(docs_root),
        "dead_ends": dead_ends(docs_root),
        "hops": hop_distance(docs_root),
        "density": density(docs_root),
        "n_index_pages": sum(1 for name in counts if name.endswith("INDEX.md")),
        "n_detail_pages": sum(1 for name in counts if not name.endswith("INDEX.md")),
    }
