"""Unit inventory: the ids a detail author must explain, with program-derived line ranges.

Ids come from the frozen ``cbe.source_context`` chunks, so the detail stage,
the graph and the query layer name the same thing. A non-empty file the
chunker left without a chunk falls back to one whole-file region.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from cbe import source_context
from cbe.checks import UNIT_KINDS
from cbe.token_budget import count_text_tokens


class SemanticError(ValueError):
    """The semantic stage cannot continue with the given input."""


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


def ensure_chunk_coverage(context: dict, repo: Path, paths: list[str]) -> dict:
    """Guarantee every non-empty requested path has a readable source chunk.

    A genuinely empty file (no bytes, or whitespace only) is known-empty: it
    gets a ``known_empty`` diagnostic and **no** chunk, so the inventory and
    render never invent a missing-grammar region or force prose for it. A
    non-empty path with no chunk is a real grammar/unsupported-language gap, so
    one whole-file region supplies a chunk and a visible ``context_fallback``
    diagnostic. Mutates and returns ``context``."""
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
            files.append({"path": path, "language": source_context.language_name(path), "sha256": digest})
        # Fallback symbol chunks historically omitted line endings and gaps.
        # Preserve exact bytes as decoded text so frozen source retrieval does
        # not need a live repository (and can verify the whole-file digest).
        file_row = next(row for row in files if row["path"] == path)
        file_row["source"] = text
        if text.strip() == "":
            diagnostics.append({"path": path, "code": "known_empty",
                                "message": "file is empty; it has no source chunk, no inventory id "
                                           "and needs no detail unit"})
            continue
        nlines = max(len(text.splitlines()), 1)
        chunks.append({"id": f"{path}::<file>", "path": path, "language": source_context.language_name(path),
                       "kind": "module_region", "name": "<file>",
                       "start_line": 1, "end_line": nlines,
                       "start_byte": 0, "end_byte": 0, "text": text,
                       "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        diagnostics.append({"path": path, "code": "context_fallback",
                            "message": "no chunk grammar output for this path; the whole-file "
                                       "fallback supplied the reading chunk"})
    return context


def inventory_for_paths(inventory: dict[str, dict], paths: Iterable[str]) -> dict[str, dict]:
    chosen = set(paths)
    return {path: inventory[path] for path in sorted(inventory) if path in chosen}
