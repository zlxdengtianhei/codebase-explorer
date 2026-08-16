"""EV-14 document budget: doc tokens / source tokens.

Token estimate matches ev's layer_invariants_oracle.py: len(chars) // 4.
Out of [0.15, 0.30] is FLAG, not BLOCK (FIXED_LAYER_ARCHITECTURE.md §3.4-5 / §7.4).

Navigation overhead = tokens of every non-root INDEX.md / total doc tokens.
That is the per-page cost of the nested tree (EV-19 progressive disclosure).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CHARS_PER_TOKEN = 4
BUDGET_LO, BUDGET_HI = 0.15, 0.30
SKIP_DIR_NAMES = {".venv", "node_modules", ".git", "__pycache__", ".codebase-analysis"}


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def _iter_files(root: Path, suffix: str) -> list[Path]:
    out: list[Path] = []
    for path in sorted(root.rglob(f"*{suffix}")):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        out.append(path)
    return out


def measure_budget(docs_root: Path, src_root: Path) -> dict[str, object]:
    doc_files = _iter_files(docs_root, ".md")
    src_files = _iter_files(src_root, ".py")
    doc_rows = []
    doc_tokens = 0
    sub_index_tokens = 0
    root_index_tokens = 0
    leaf_tokens = 0
    n_sub_index = 0
    for path in doc_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens = estimate_tokens(text)
        rel = path.relative_to(docs_root).as_posix()
        doc_rows.append({"file": rel, "chars": len(text), "tokens": tokens})
        doc_tokens += tokens
        if path.name == "INDEX.md":
            if rel == "INDEX.md":
                root_index_tokens = tokens
            else:
                n_sub_index += 1
                sub_index_tokens += tokens
        else:
            leaf_tokens += tokens
    src_tokens = 0
    src_chars = 0
    for path in src_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        src_chars += len(text)
        src_tokens += estimate_tokens(text)
    ratio = (doc_tokens / src_tokens) if src_tokens else 0.0
    in_range = BUDGET_LO <= ratio <= BUDGET_HI
    nav_share = (sub_index_tokens / doc_tokens) if doc_tokens else 0.0
    return {
        "docs_root": str(docs_root),
        "src_root": str(src_root),
        "doc_files": len(doc_files),
        "src_files": len(src_files),
        "doc_tokens": doc_tokens,
        "src_tokens": src_tokens,
        "src_chars": src_chars,
        "ratio": round(ratio, 4),
        "range": [BUDGET_LO, BUDGET_HI],
        "verdict": "PASS" if in_range else "FLAG",
        "token_rule": f"len(chars)//{CHARS_PER_TOKEN}",
        "nav": {
            "n_sub_index": n_sub_index,
            "sub_index_tokens": sub_index_tokens,
            "root_index_tokens": root_index_tokens,
            "leaf_tokens": leaf_tokens,
            "share_of_docs": round(nav_share, 4),
        },
        "doc_pages": doc_rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure EV-14 doc/src token budget")
    parser.add_argument(
        "--tree",
        action="append",
        default=[],
        help="name=docs_root:src_root (repeatable)",
    )
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)
    if not args.tree:
        parser.error("at least one --tree name=docs:src is required")
    trees: dict[str, object] = {}
    for spec in args.tree:
        if "=" not in spec or ":" not in spec:
            parser.error(f"bad --tree spec: {spec}")
        name, rest = spec.split("=", 1)
        docs_s, src_s = rest.split(":", 1)
        trees[name] = {"name": name, **measure_budget(Path(docs_s), Path(src_s))}
    compare: dict[str, object] = {}
    pairs = (("docs_flask", "docs_flask_clus"), ("docs_httpx", "docs_httpx_clus"))
    for old_name, new_name in pairs:
        if old_name in trees and new_name in trees:
            old, new = trees[old_name], trees[new_name]
            compare[f"{new_name}_minus_{old_name}"] = {
                "ratio_delta": round(new["ratio"] - old["ratio"], 4),
                "doc_tokens_delta": new["doc_tokens"] - old["doc_tokens"],
                "nav_share_delta": round(
                    new["nav"]["share_of_docs"] - old["nav"]["share_of_docs"], 4
                ),
                "n_sub_index_delta": new["nav"]["n_sub_index"] - old["nav"]["n_sub_index"],
            }
    out = {
        "invariant": (
            "FIXED_LAYER_ARCHITECTURE.md §3.4-5 / EV-14: "
            "doc_tokens / src_tokens ∈ [0.15, 0.30]; out of band is FLAG not BLOCK"
        ),
        "token_rule": f"len(chars)//{CHARS_PER_TOKEN} (same as ev layer_invariants_oracle.py)",
        "nav_definition": (
            "navigation overhead = tokens of every INDEX.md except the root "
            "INDEX.md, divided by total doc tokens"
        ),
        "src_skip_dirs": sorted(SKIP_DIR_NAMES),
        "trees": trees,
        "compare": compare,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
