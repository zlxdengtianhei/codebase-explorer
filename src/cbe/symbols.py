"""Unit inventory: the ids a detail author must explain, with program-derived line ranges.

Ids come from the frozen ``cbe.source_context`` chunks, so the detail stage,
the graph and the query layer name the same thing. Python files without a
chunk fall back to an AST inventory; other files to one whole-file region.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, Iterable

from cbe.checks import UNIT_KINDS
from cbe.token_budget import count_text_tokens


_LANGUAGE_BY_SUFFIX = {
    ".py": "python", ".pyi": "python", ".ts": "typescript", ".tsx": "typescript",
    ".mts": "typescript", ".cts": "typescript", ".js": "javascript", ".jsx": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".c": "c", ".h": "c", ".cc": "cpp",
    ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".rs": "rust", ".java": "java",
    ".go": "go", ".sql": "sql",
}


class SemanticError(ValueError):
    """The semantic stage cannot continue with the given input."""


def language_of(path: str) -> str:
    return _LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower(), "unknown")


def _node_span(node: ast.AST) -> list[int]:
    """Decorator-aware 1-based inclusive span; a decorated symbol starts at its
    first decorator so a segment boundary never orphans it."""
    start = node.lineno  # type: ignore[attr-defined]
    decorators = getattr(node, "decorator_list", None)
    if decorators:
        start = min(start, min(item.lineno for item in decorators))
    return [start, node.end_lineno]  # type: ignore[attr-defined]


def _python_inventory(path: str, source: str, digest: str, tokens: int) -> dict:
    rows: list[dict[str, Any]] = []
    regions: list[list[int]] = []
    region_start: int | None = None
    seen: dict[str, int] = {}

    def unique_id(name: str, start: int) -> str:
        # Two ``def reserve_run`` overloads are two real symbols; the second
        # carries its start line so no inventory id is ever duplicated.
        count = seen.get(name, 0)
        seen[name] = count + 1
        return f"{path}::{name}" if count == 0 else f"{path}::{name}@{start}"

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        tree = None
    nlines = source.count("\n") + (1 if source and not source.endswith("\n") else 0)
    for node in list(tree.body) if tree is not None else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if region_start is not None:
                regions.append([region_start, (node.lineno - 1) or region_start])
                region_start = None
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            span = _node_span(node)
            rows.append({"id": unique_id(node.name, span[0]), "name": node.name, "kind": kind,
                         "parent": None, "lines": [span]})
            if kind == "class":
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        child_span = _node_span(child)
                        qualified = f"{node.name}.{child.name}"
                        rows.append({"id": unique_id(qualified, child_span[0]),
                                     "name": qualified, "kind": "method",
                                     "parent": f"{path}::{node.name}", "lines": [child_span]})
        elif region_start is None:
            region_start = node.lineno
    if region_start is not None:
        regions.append([region_start, max(nlines, region_start)])
    if regions:
        rows.append({"id": f"{path}::<module top-level>", "name": "<module top-level>",
                     "kind": "module_region", "parent": None, "lines": regions})
    return {"tokens": tokens, "sha256": digest, "nlines": max(nlines, 1), "symbols": rows}


def _file_region_inventory(path: str, source: str, digest: str, tokens: int) -> dict:
    """Languages without an AST inventory still get one whole-file region so the
    disposition coverage check has a real id and no source is silently dropped."""
    nlines = source.count("\n") + (1 if source and not source.endswith("\n") else 0)
    rows = [{"id": f"{path}::<file>", "name": "<file>", "kind": "module_region",
             "parent": None, "lines": [[1, max(nlines, 1)]]}]
    return {"tokens": tokens, "sha256": digest, "nlines": max(nlines, 1), "symbols": rows}


def build_inventory(rows: dict[str, dict]) -> dict[str, dict]:
    """Inventory from scanned rows ``{path: {source, digest, tokens}}``.

    Python uses AST spans; every other language gets one whole-file region.
    A ``source_context`` snapshot can replace this later: see
    :func:`inventory_from_context`."""
    inventory: dict[str, dict] = {}
    for path in sorted(rows):
        row = rows[path]
        source = row.get("source") or ""
        digest = row.get("digest") or hashlib.sha256(source.encode("utf-8")).hexdigest()
        tokens = row.get("tokens") or count_text_tokens(source)
        if path.endswith((".py", ".pyi")):
            inventory[path] = _python_inventory(path, source, digest, tokens)
        else:
            inventory[path] = _file_region_inventory(path, source, digest, tokens)
    return inventory


def inventory_from_context(context: dict, paths: list[str] | None = None) -> dict[str, dict]:
    """Build the same inventory shape from a ``cbe-context/1`` snapshot.

    Chunk ids become unit ids, so the detail stage, the graph and the query
    layer all name the same thing. A chunk without a name (whole-file region)
    still yields one id. Diagnostics never turn a missing chunk into an empty
    success: a listed path with no chunks raises."""
    wanted = set(paths) if paths is not None else None
    by_path: dict[str, dict] = {}
    for chunk in context.get("chunks") or []:
        path = chunk["path"]
        if wanted is not None and path not in wanted:
            continue
        entry = by_path.setdefault(path, {"tokens": 0, "sha256": "", "nlines": 1,
                                          "symbols": []})
        if not (chunk.get("text") or "").strip():
            # A blank chunk (an empty or whitespace-only file) carries no
            # explainable detail; it must not become a unit with prose.
            continue
        name = chunk.get("name") or "<region>"
        kind = chunk.get("kind") or "module_region"
        if kind not in UNIT_KINDS:
            kind = "module_region"
        entry["symbols"].append({
            "id": chunk["id"], "name": name, "kind": kind, "parent": None,
            "lines": [[int(chunk["start_line"]), int(chunk["end_line"])]],
        })
    for row in context.get("files") or []:
        path = row["path"]
        if wanted is not None and path not in wanted:
            continue
        entry = by_path.setdefault(path, {"tokens": 0, "sha256": "", "nlines": 1,
                                          "symbols": []})
        entry["sha256"] = row.get("sha256", "")
        entry["nlines"] = max((pair[1] for sym in entry["symbols"]
                               for pair in sym["lines"]), default=1)
        entry["tokens"] = sum(count_text_tokens(chunk.get("text") or "")
                              for chunk in (context.get("chunks") or [])
                              if chunk.get("path") == path)
        # No symbols after blank chunks means the file is known-empty; the
        # catalogue still lists it, but no unit or disposition is invented.
        entry["known_empty"] = not entry["symbols"]
    if wanted is not None:
        missing = sorted(path for path in wanted if path not in by_path)
        if missing:
            raise SemanticError("source context has no chunks or file entry for: "
                                 + ", ".join(missing[:10]))
    return by_path


def inventory_ids(inventory: dict[str, dict]) -> list[str]:
    return [row["id"] for file in inventory.values() for row in file["symbols"]]


def ensure_chunk_coverage(context: dict, repo: Path, ast_inventory: dict[str, dict],
                          paths: list[str]) -> dict:
    """Guarantee every non-empty requested path has a readable source chunk.

    A genuinely empty file (no bytes, or whitespace only) is known-empty: it
    gets a ``known_empty`` diagnostic and **no** chunk, so the inventory and
    render never invent a missing-grammar region or force prose for it. A
    non-empty path with no chunk is a real grammar/unsupported-language gap, so
    the AST/file-region fallback supplies a chunk and a visible
    ``context_fallback`` diagnostic. Mutates and returns ``context``."""
    chunks = context.setdefault("chunks", [])
    files = context.setdefault("files", [])
    diagnostics = context.setdefault("diagnostics", [])
    present = {chunk["path"] for chunk in chunks}
    listed = {row["path"] for row in files}
    for path in paths:
        if path in present:
            continue
        try:
            raw = (repo / path).read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            diagnostics.append({"path": path, "code": "source_unavailable", "message": str(exc)})
            continue
        digest = hashlib.sha256(raw).hexdigest()
        if path not in listed:
            files.append({"path": path, "language": language_of(path), "sha256": digest})
        if text.strip() == "":
            diagnostics.append({"path": path, "code": "known_empty",
                                "message": "file is empty; it has no source chunk, no inventory id "
                                           "and needs no detail unit"})
            continue
        lines = text.splitlines()
        symbols = (ast_inventory.get(path) or {}).get("symbols") or []
        if not symbols:
            nlines = max(len(lines), 1)
            symbols = [{"id": f"{path}::<file>", "name": "<file>",
                        "kind": "module_region", "lines": [[1, nlines]]}]
        for symbol in symbols:
            start, end = symbol["lines"][0]
            body = "\n".join(lines[max(start - 1, 0):end])
            chunks.append({"id": symbol["id"], "path": path, "language": language_of(path),
                           "kind": symbol["kind"], "name": symbol["name"],
                           "start_line": start, "end_line": end,
                           "start_byte": 0, "end_byte": 0, "text": body,
                           "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
        diagnostics.append({"path": path, "code": "context_fallback",
                            "message": "no chunk grammar output for this path; the AST/file-region "
                                       "fallback supplied the reading chunk"})
    return context


def inventory_for_paths(inventory: dict[str, dict], paths: Iterable[str]) -> dict[str, dict]:
    chosen = set(paths)
    return {path: inventory[path] for path in sorted(inventory) if path in chosen}
