"""Page/token/link measurements for a rendered variant-B tree. Zero LLM."""

from __future__ import annotations

import json
from pathlib import Path

from src.budget.estimator import estimate_tokens_from_chars
from src.synthesis.variant_b.pointing import evaluate_docs, load_docs
from src.synthesis.variant_b.scan import scan_docs


def _percentile(sorted_vals: list[int], p: float) -> int | None:
    if not sorted_vals:
        return None
    idx = int(p * (len(sorted_vals) - 1))
    return sorted_vals[idx]


def measure_docs(docs_root: Path, *, repo_root: Path | None = None, ledger_path: Path | None = None) -> dict[str, object]:
    docs_root = docs_root.resolve()
    scan = scan_docs(docs_root)
    pages = sorted(p for p in docs_root.rglob("*.md") if p.is_file())
    line_counts = {p.relative_to(docs_root).as_posix(): len(p.read_text(encoding="utf-8", errors="replace").splitlines()) for p in pages}
    counts = sorted(line_counts.values())
    index_lines = {rel: n for rel, n in line_counts.items() if rel.endswith("INDEX.md")}
    pointing = evaluate_docs(load_docs(docs_root))
    doc_chars = sum(len(p.read_text(encoding="utf-8", errors="replace")) for p in pages)
    doc_tokens = estimate_tokens_from_chars(doc_chars, "markdown")
    source_tokens = None
    n_ledger_files = None
    if ledger_path and repo_root:
        ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
        files = ledger.get("files") or {}
        n_ledger_files = len(files)
        src_chars = 0
        for rel in files:
            fp = Path(repo_root) / rel
            try:
                src_chars += len(fp.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
        source_tokens = estimate_tokens_from_chars(src_chars, "python")
    ratio = None
    if source_tokens:
        ratio = round(doc_tokens / source_tokens, 4)
    return {
        "docs_root": str(docs_root),
        "n_pages": len(pages),
        "page_lines_p50": _percentile(counts, 0.5),
        "page_lines_p90": _percentile(counts, 0.9),
        "page_lines_max": counts[-1] if counts else None,
        "pages_over_400": {rel: n for rel, n in line_counts.items() if n > 400},
        "n_index_pages": len(index_lines),
        "index_lines_max": max(index_lines.values()) if index_lines else None,
        "index_over_150": {rel: n for rel, n in index_lines.items() if n > 150},
        "link_rate_resolved": scan.get("anchors", {}).get("rate_resolved"),
        "link_with_line_range": scan.get("anchors", {}).get("rate_with_line_range"),
        "max_hops": (scan.get("hops") or {}).get("max_hops"),
        "over_3_hops": (scan.get("hops") or {}).get("over_3_hops"),
        "dead_ends": scan.get("dead_ends"),
        "pointing_hit_rate": pointing.get("rate_hit"),
        "pointing_public_max_repeat": (pointing.get("public_hrefs") or {}).get("max_repeat"),
        "doc_tokens": doc_tokens,
        "source_tokens": source_tokens,
        "doc_source_token_ratio": ratio,
        "n_ledger_files": n_ledger_files,
        "scan": {
            "n_index_pages": scan.get("n_index_pages"),
            "n_detail_pages": scan.get("n_detail_pages"),
            "anchors": scan.get("anchors"),
            "hops": scan.get("hops"),
        },
    }
