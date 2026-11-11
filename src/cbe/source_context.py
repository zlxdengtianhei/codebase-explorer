"""Multi-language source chunking and the unified graph + source context.

This module is the source-context half of the public ``cbe-context/1``
contract consumed by the generation pipeline: byte-exact source chunks plus
an optional standard ``cbe-graph/1`` analysis graph.  It turns a repository
into a byte-exact, non-overlapping partition of source chunks (functions,
classes, methods, types, module residue) and combines those chunks with a
standard graph object.

Design rules that the implementation follows:

* Chunks partition the original UTF-8 bytes exactly once.  Concatenating the
  chunks of one file in ``start_byte`` order reproduces the decoded source
  byte-for-byte.  A nested declaration is its own chunk, so a class chunk
  never repeats its method bodies; ancestor names, signatures and the full
  syntactic range stay in metadata.
* Oversized exclusive regions are split at grammar child boundaries only.
  A segment boundary is always a real syntax-tree boundary, never a character
  prefix cut.
* Unknown languages, a missing grammar package and parse failures retain their
  per-file diagnostics and use whole-file chunks for non-blank UTF-8 source.
  A UTF-8 decode failure yields ``decode_error`` and no chunks for that file;
  other files still build. Syntax errors retain grammar coverage plus a diagnostic.
* Only tree-sitter grammars do the parsing.  The glue here maps grammar node
  kinds to chunk kinds and maps byte/char/line coordinates; it does not
  re-implement any language analysis.
* Graphs are consumed, never built.  A graph whose ``source_manifest`` drifts
  from the current source is rejected with a locatable error.
"""

from __future__ import annotations

import bisect
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from cbe.grammars import (
    AMBIGUOUS_SUFFIXES,
    DEFAULT_MAX_SEGMENT_BYTES,
    MAX_FILE_BYTES,
    SCHEMA_CONTEXT,
    SCHEMA_GRAPH,
    ContextError,
    OffsetMap,
    _EXTRA_SPECS,
    _all_specs,
    _grammar_for_suffix,
    _iter_source_files,
    _make_parser,
    canonical_symbol_id,
    language_name,
    line_starts,
    sha256_bytes,
    sha256_text,
)
from cbe.declarations import _Declaration, _body_start, _extract_declarations
from cbe.graph import _prune_graph, check_graph_source


# ---------------------------------------------------------------------------
# Chunk construction
# ---------------------------------------------------------------------------


_BODY_CONTAINERS = frozenset(
    {
        "block",
        "statement_block",
        "compound_statement",
        "statement_list",
        "class_body",
        "declaration_list",
        "field_declaration_list",
        "constructor_body",
        "interface_body",
        "enum_body",
        "interface_body",
        "module",
        "program",
        "translation_unit",
        "source_file",
        "body_statement",
        "function_body",
        "protocol_body",
        "statements",
        "compilation_unit",
    }
)


def _collect_named_boundaries(root: Any) -> tuple[list[int], list[int]]:
    """Return (all named-node boundaries, statement-level boundaries).

    Statement-level boundaries are the starts/ends of nodes that sit directly
    in a body/block, so an oversized declaration prefers to cut between
    statements instead of inside an expression.  Both lists are token
    boundaries; splitting on either never cuts inside a lexeme.
    """

    all_boundaries: list[int] = [root.start_byte, root.end_byte]
    statement_boundaries: list[int] = []
    stack = [root]
    while stack:
        node = stack.pop()
        all_boundaries.append(node.start_byte)
        all_boundaries.append(node.end_byte)
        if node.type in _BODY_CONTAINERS:
            for child in node.named_children:
                statement_boundaries.append(child.start_byte)
                statement_boundaries.append(child.end_byte)
        stack.extend(node.named_children)
    return sorted(set(all_boundaries)), sorted(set(statement_boundaries))


def _subtract_ranges(start: int, end: int, holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    kept = [(start, end)]
    for hole_start, hole_end in sorted(holes):
        next_kept: list[tuple[int, int]] = []
        for seg_start, seg_end in kept:
            if hole_end <= seg_start or hole_start >= seg_end:
                next_kept.append((seg_start, seg_end))
                continue
            if seg_start < hole_start:
                next_kept.append((seg_start, hole_start))
            if hole_end < seg_end:
                next_kept.append((hole_end, seg_end))
        kept = next_kept
    return [(seg_start, seg_end) for seg_start, seg_end in kept if seg_end > seg_start]


def _leftover_ranges(total_bytes: int, covered: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if total_bytes <= 0:
        return []
    return _subtract_ranges(0, total_bytes, covered)


def _split_byte_span(
    start: int,
    end: int,
    all_boundaries: list[int],
    statement_boundaries: list[int],
    max_bytes: int,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Split a byte span at grammar boundaries, never inside a token.

    Everything here is in bytes, matching tree-sitter and the chunk contract.
    Returns ``(segments, oversized)``; ``oversized`` holds segments that had
    to exceed ``max_bytes`` because one indivisible grammar token does not
    fit.  The caller turns those into an explicit diagnostic instead of a
    silently over-budget chunk.
    """

    if max_bytes <= 0 or end - start <= max_bytes:
        return [(start, end)], []
    segments: list[tuple[int, int]] = []
    oversized: list[tuple[int, int]] = []
    current = start

    def choose(boundaries: list[int], limit: int) -> int | None:
        lo = bisect.bisect_left(boundaries, start)
        hi = bisect.bisect_right(boundaries, end)
        window = boundaries[lo:hi]
        index = bisect.bisect_right(window, limit) - 1
        while index >= 0:
            candidate = window[index]
            if candidate > current:
                return candidate
            index -= 1
        return None

    while current < end:
        limit = current + max_bytes
        nxt = choose(statement_boundaries, limit)
        if nxt is None:
            nxt = choose(all_boundaries, limit)
        if nxt is None:
            after = bisect.bisect_right(all_boundaries, current)
            nxt = all_boundaries[after] if after < len(all_boundaries) else end
        seg_end = min(nxt, end)
        if seg_end - current > max_bytes:
            oversized.append((current, seg_end))
        segments.append((current, seg_end))
        if seg_end >= end:
            break
        current = seg_end
    return segments, oversized


def _line_of(starts: tuple[int, ...], char_index: int) -> int:
    return bisect.bisect_right(starts, char_index)


@dataclass
class _ChunkPlan:
    path: str
    language: str
    kind: str
    name: str
    qualified_name: str
    symbol_id: str
    parent_id: str | None
    signature: str
    ancestors: tuple[str, ...]
    start_byte: int
    end_byte: int
    full_start_byte: int
    full_end_byte: int
    segment_index: int
    segment_count: int


def _plan_chunks(
    offsets: OffsetMap,
    declarations: list[_Declaration],
    root: Any,
    path: str,
    language: str,
    max_segment_bytes: int,
) -> tuple[list[_ChunkPlan], list[dict[str, Any]]]:
    total_bytes = len(offsets.raw)
    by_parent: dict[str | None, list[_Declaration]] = {}
    for decl in declarations:
        by_parent.setdefault(decl.parent_id, []).append(decl)

    # Exclusive byte ranges: full span minus the spans of direct child
    # declarations.  Union over all declarations equals the union of the
    # top-level declaration spans (no duplication).
    exclusive: dict[str, list[tuple[int, int]]] = {}
    for decl in declarations:
        holes = [(child.start_byte, child.end_byte) for child in by_parent.get(decl.symbol_id, ())]
        exclusive[decl.symbol_id] = _subtract_ranges(
            decl.start_byte, decl.exclusive_end_byte or decl.end_byte, holes)

    covered = [(decl.start_byte, decl.exclusive_end_byte or decl.end_byte)
               for decl in declarations if decl.parent_id is None]
    residual = _leftover_ranges(total_bytes, covered)

    boundaries, statement_boundaries = _collect_named_boundaries(root)
    max_bytes = max(1, int(max_segment_bytes))
    plans: list[_ChunkPlan] = []
    diagnostics: list[dict[str, Any]] = []

    def record_oversized(ranges: list[tuple[int, int]]) -> None:
        for seg_start, seg_end in ranges:
            diagnostics.append(
                {
                    "path": path,
                    "code": "oversized_token",
                    "message": (
                        f"segment [{seg_start},{seg_end}) is {seg_end - seg_start} bytes, above the "
                        f"{max_bytes}-byte target: one grammar token does not fit and no safe boundary exists"
                    ),
                }
            )

    def add_plan(decl: _Declaration, seg_start: int, seg_end: int, index: int, count: int) -> None:
        plans.append(
            _ChunkPlan(
                path=path,
                language=language,
                kind=decl.kind,
                name=decl.name,
                qualified_name=decl.qualified_name,
                symbol_id=decl.symbol_id,
                parent_id=decl.parent_id,
                signature=decl.signature,
                ancestors=decl.ancestors,
                start_byte=seg_start,
                end_byte=seg_end,
                full_start_byte=decl.start_byte,
                full_end_byte=decl.end_byte,
                segment_index=index,
                segment_count=count,
            )
        )

    for decl in declarations:
        segments: list[tuple[int, int]] = []
        oversized: list[tuple[int, int]] = []
        for rng_start, rng_end in exclusive.get(decl.symbol_id, []):
            part, over = _split_byte_span(rng_start, rng_end, boundaries, statement_boundaries, max_bytes)
            segments.extend(part)
            oversized.extend(over)
        record_oversized(oversized)
        count = len(segments)
        for index, (seg_start, seg_end) in enumerate(segments):
            add_plan(decl, seg_start, seg_end, index, count)

    for rng_start, rng_end in residual:
        segments, oversized = _split_byte_span(rng_start, rng_end, boundaries, statement_boundaries, max_bytes)
        record_oversized(oversized)
        count = len(segments)
        residual_id = canonical_symbol_id(path, "module_residual", "", rng_start)
        for index, (seg_start, seg_end) in enumerate(segments):
            plans.append(
                _ChunkPlan(
                    path=path,
                    language=language,
                    kind="module_residual",
                    name=PurePosixPath(path).name,
                    qualified_name="",
                    symbol_id=residual_id,
                    parent_id=None,
                    signature="",
                    ancestors=(),
                    start_byte=seg_start,
                    end_byte=seg_end,
                    full_start_byte=rng_start,
                    full_end_byte=rng_end,
                    segment_index=index,
                    segment_count=count,
                )
            )

    plans.sort(key=lambda item: (item.start_byte, item.end_byte))
    return plans, diagnostics


def source_signatures(path: str, source: str, language: str) -> tuple[dict[str, str], dict[tuple[str, int], str]]:
    """Full signatures by canonical ID and (qualified name, decorated start line).

    Prompt chunks intentionally cap their signatures. Published records reparse
    verified source with the same grammar and declaration boundaries, and retain
    the complete signature. No code executes. Unsupported grammars return empty
    maps, letting legacy inventory records retain their available metadata.
    """
    spec = next((s for s in _all_specs() if s.name == language), None)
    if spec is None:
        return {}, {}
    try:
        parser = _make_parser(spec)
    except (ImportError, AttributeError):
        return {}, {}
    raw = source.encode("utf-8")
    offsets = OffsetMap.from_bytes(raw)
    declarations = _extract_declarations(spec, offsets, parser.parse(raw).root_node, path)
    by_id, by_location = {}, {}
    starts = line_starts(offsets.text)
    for declaration in declarations:
        end = _body_start(declaration.node)
        if end < 0:
            value = declaration.node.child_by_field_name("value")
            if value is not None:
                end = _body_start(value)
        if end < 0:
            end = declaration.end_byte
        signature = raw[declaration.start_byte:end].decode("utf-8").strip()
        if declaration.kind != "module_region" and declaration.signature and declaration.signature not in signature:
            signature += "\n" + declaration.signature
        by_id[declaration.symbol_id] = signature
        start_line = _line_of(starts, offsets.char_of_byte(declaration.start_byte))
        by_location[declaration.qualified_name, start_line] = signature
    return by_id, by_location


def _chunk_from_plan(plan: _ChunkPlan, offsets: OffsetMap, starts: tuple[int, ...]) -> dict[str, Any]:
    text = offsets.raw[plan.start_byte:plan.end_byte].decode("utf-8")
    char_start = offsets.char_of_byte(plan.start_byte)
    char_end = offsets.char_of_byte(plan.end_byte)
    chunk_id = plan.symbol_id
    if plan.segment_count > 1:
        chunk_id = f"{chunk_id}::s{plan.segment_index}"
    return {
        "id": chunk_id,
        "path": plan.path,
        "language": plan.language,
        "kind": plan.kind,
        "name": plan.name,
        "start_line": _line_of(starts, char_start),
        "end_line": _line_of(starts, max(char_start, char_end - 1)),
        "start_byte": plan.start_byte,
        "end_byte": plan.end_byte,
        "text": text,
        "sha256": sha256_text(text),
        # --- additive metadata (DESIGN allows it; required fields keep meaning)
        "symbol_id": plan.symbol_id,
        "parent_id": plan.parent_id,
        "qualified_name": plan.qualified_name,
        "signature": plan.signature,
        "ancestors": list(plan.ancestors),
        "segment_index": plan.segment_index,
        "segment_count": plan.segment_count,
        "full_start_byte": plan.full_start_byte,
        "full_end_byte": plan.full_end_byte,
    }


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------


def _checked_chunks(
    path: str, language: str, raw: bytes, chunks: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check the frozen partition before consumers can schedule model work.

    Valid partitions pass through unchanged, including symbol identities.
    A broken partition becomes one lossless file region; never repair spans
    while retaining misleading declaration identities.
    """
    ordered = sorted(chunks, key=lambda chunk: chunk["start_byte"])
    # No grammar output is a different condition from a broken partition.
    # Keep the original diagnostic code as the reason shown to readers.
    if not chunks:
        try:
            offsets = OffsetMap.from_bytes(raw)
        except UnicodeDecodeError as exc:
            if not any(row.get("path") == path and row.get("code") == "decode_error"
                       for row in diagnostics):
                diagnostics.append({"path": path, "code": "decode_error",
                                    "message": f"UTF-8 decode failed: {exc}"})
            return []
        if not offsets.text.strip():
            # The host's ensure_chunk_coverage records known_empty without a unit.
            return []
        cause = next((row for row in diagnostics if row.get("path") == path
                      and row.get("code") in {"unsupported_language", "grammar_unavailable",
                                              "parse_error", "file_too_large"}), None)
        reason = cause["code"] if cause else "no_chunk_output"
        diagnostic_code = "context_fallback"
        message = (f"{reason}: {cause['message']}; " if cause else f"{reason}; ") + (
            "froze one whole-file source chunk; declaration-level detail is unavailable")
    else:
        reason = ""
        diagnostic_code = "source_reassembly_fallback"
        message = ""
    cursor = 0
    for chunk in ordered:
        start, end = chunk["start_byte"], chunk["end_byte"]
        if start != cursor or not start <= end <= len(raw):
            reason = f"non-contiguous chunk range [{start},{end}) at byte {cursor}"
            break
        cursor = end
    if not reason and cursor != len(raw):
        reason = f"chunk coverage ends at byte {cursor}, expected {len(raw)}"
    assembled = b"".join(chunk["text"].encode("utf-8") for chunk in ordered)
    if not reason and sha256_bytes(assembled) != sha256_bytes(raw):
        reason = "reassembled source SHA-256 differs from the input file"
    if not reason:
        return chunks

    try:
        offsets = OffsetMap.from_bytes(raw)
    except UnicodeDecodeError as exc:
        raise ContextError("source_not_reassemblable",
                           f"{path}: cannot freeze byte-exact UTF-8 source: {exc}", path=path) from exc
    diagnostics.append({
        "path": path, "code": diagnostic_code, "reason": reason,
        "message": message or (f"{reason}; CBE could not reassemble its declaration chunks; "
                               "froze one whole-file source chunk with coarser detail"),
    })
    if not raw:
        return []
    plan = _ChunkPlan(
        path=path, language=language, kind="module_residual", name=PurePosixPath(path).name,
        qualified_name="", symbol_id=canonical_symbol_id(path, "module_residual", "", 0),
        parent_id=None, signature="", ancestors=(), start_byte=0, end_byte=len(raw),
        full_start_byte=0, full_end_byte=len(raw), segment_index=0, segment_count=1,
    )
    fallback = _chunk_from_plan(plan, offsets, line_starts(offsets.text))
    if sha256_text(fallback["text"]) != sha256_bytes(raw):  # fail before any model calls
        raise ContextError("source_not_reassemblable", f"{path}: whole-file fallback SHA-256 mismatch", path=path)
    return [fallback]


def _process_source_file(
    relative: str,
    raw: bytes,
    digest: str,
    files: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    max_segment_bytes: int,
) -> None:
    spec = _grammar_for_suffix(PurePosixPath(relative).suffix)
    language = language_name(relative)

    if spec is None:
        diagnostics.append(
            {
                "path": relative,
                "code": "unsupported_language",
                "message": f"no grammar registered for suffix {PurePosixPath(relative).suffix!r}",
            }
        )
        files.append({"path": relative, "language": language, "sha256": digest})
        return

    if PurePosixPath(relative).suffix.lower() in AMBIGUOUS_SUFFIXES:
        candidates = AMBIGUOUS_SUFFIXES[PurePosixPath(relative).suffix.lower()]
        explicitly_mapped = any(".h" in extra.suffixes for extra in _EXTRA_SPECS.values())
        if spec.name == candidates[0] and not explicitly_mapped:
            diagnostics.append(
                {
                    "path": relative,
                    "code": "ambiguous_language",
                    "message": (
                        f"{PurePosixPath(relative).suffix!r} is valid in {', '.join(candidates)}; "
                        f"parsed with {spec.name}. Register a mapping or use a unique extension "
                        "to remove the ambiguity."
                    ),
                }
            )

    if len(raw) > MAX_FILE_BYTES:
        diagnostics.append(
            {
                "path": relative,
                "code": "file_too_large",
                "message": f"{len(raw)} bytes exceeds MAX_FILE_BYTES={MAX_FILE_BYTES}",
            }
        )
        files.append({"path": relative, "language": language, "sha256": digest})
        return

    files.append({"path": relative, "language": language, "sha256": digest})

    try:
        offsets = OffsetMap.from_bytes(raw)
    except UnicodeDecodeError as exc:
        diagnostics.append(
            {
                "path": relative,
                "code": "decode_error",
                "message": f"UTF-8 decode failed: {exc}",
            }
        )
        return

    try:
        parser = _make_parser(spec)
    except Exception as exc:
        diagnostics.append(
            {
                "path": relative,
                "code": "grammar_unavailable",
                "message": f"grammar {spec.module} is not importable: {exc}",
            }
        )
        return

    try:
        tree = parser.parse(raw)
    except Exception as exc:  # pragma: no cover - grammar-level failure
        diagnostics.append(
            {"path": relative, "code": "parse_error", "message": f"{type(exc).__name__}: {exc}"}
        )
        return

    root = tree.root_node
    if getattr(root, "has_error", False):
        line = root.start_point[0] + 1
        diagnostics.append(
            {
                "path": relative,
                "code": "syntax_error",
                "message": f"tree contains an ERROR node near line {line}; chunk coverage is preserved",
            }
        )

    declarations = _extract_declarations(spec, offsets, root, relative)
    plans, plan_diagnostics = _plan_chunks(
        offsets, declarations, root, relative, spec.name, max_segment_bytes
    )
    diagnostics.extend(plan_diagnostics)
    starts = line_starts(offsets.text)
    chunks.extend(_chunk_from_plan(plan, offsets, starts) for plan in plans)


def build_context(
    repo: Path | str,
    paths: list[str] | None = None,
    *,
    graph_path: Path | str | None = None,
    max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES,
) -> dict[str, Any]:
    """Freeze one source snapshot and (optionally) a matching standard graph.

    ``paths`` must be repo-relative POSIX paths.  They are validated so they
    can neither escape the repository nor follow an external symlink.
    ``graph_path`` is read and its ``source_manifest`` is checked against the
    current bytes; a mismatch raises :class:`GraphSourceMismatch`.
    """

    repo_path = Path(repo)
    if not repo_path.is_dir():
        raise ContextError("invalid_repo", f"not a directory: {repo_path}", repo=str(repo_path))

    selected, diagnostics = _iter_source_files(repo_path, paths)

    files: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    raw_sources: dict[str, bytes] = {}

    for relative in selected:
        full = repo_path / PurePosixPath(relative)
        try:
            raw = full.read_bytes()
        except OSError as exc:
            diagnostics.append({"path": relative, "code": "source_unavailable", "message": str(exc)})
            continue

        digest = sha256_bytes(raw)
        raw_sources[relative] = raw
        source_hashes[relative] = digest
        _process_source_file(
            relative, raw, digest, files, chunks, diagnostics, max_segment_bytes
        )

    by_path: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        by_path.setdefault(chunk["path"], []).append(chunk)
    chunks = [chunk for file in files for chunk in _checked_chunks(
        file["path"], file["language"], raw_sources[file["path"]],
        by_path.get(file["path"], []), diagnostics,
    )]

    graph: dict[str, Any] | None = None
    graph_status = "not_provided"
    if graph_path is not None:
        graph = _load_graph(Path(graph_path), repo_path, source_hashes)
        graph_status = "provided"

    return {
        "schema": SCHEMA_CONTEXT,
        "files": files,
        "chunks": chunks,
        "graph": graph,
        "graph_status": graph_status,
        "diagnostics": diagnostics,
    }



# ---------------------------------------------------------------------------
# Graph loading and pruning
# ---------------------------------------------------------------------------


def _load_graph(graph_path: Path, repo: Path, frozen_hashes: dict[str, str]) -> dict[str, Any]:
    if not graph_path.exists():
        raise ContextError("graph_missing", f"graph file does not exist: {graph_path}", path=str(graph_path))
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextError("graph_unreadable", f"cannot read graph {graph_path}: {exc}", path=str(graph_path)) from exc
    if not isinstance(payload, dict):
        raise ContextError("graph_schema_unsupported", "graph payload is not an object", path=str(graph_path))
    if payload.get("schema") != SCHEMA_GRAPH:
        raise ContextError(
            "graph_schema_unsupported",
            f"expected schema {SCHEMA_GRAPH!r}, got {payload.get('schema')!r}",
            path=str(graph_path),
        )
    try:
        check_graph_source(repo, payload, frozen_hashes)
    except ContextError as exc:
        # The shared check knows no file name; errors about the graph as a
        # whole name the graph file, errors about one source file keep theirs.
        if "path" not in exc.details and "paths" not in exc.details:
            exc.details["path"] = str(graph_path)
        raise
    return payload


# ---------------------------------------------------------------------------
# context_for_paths
# ---------------------------------------------------------------------------


def context_for_paths(context: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    """Select a local slice from a frozen context.  Never reads the repository.

    The slice keeps the chunks and files for the requested paths, prunes the
    graph to edges incident to those paths plus their boundary/external
    endpoints, and marks the result as partial so a consumer cannot mistake it
    for a complete relationship set.
    """

    if not isinstance(context, dict) or context.get("schema") != SCHEMA_CONTEXT:
        raise ContextError(
            "invalid_context",
            f"expected a {SCHEMA_CONTEXT!r} context object",
        )
    selected: set[str] = set()
    for raw in paths:
        candidate = PurePosixPath(str(raw))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ContextError("invalid_path", f"path escapes the context scope: {raw}", path=str(raw))
        selected.add(candidate.as_posix())

    chunks = [chunk for chunk in context.get("chunks", []) if chunk.get("path") in selected]
    files = [item for item in context.get("files", []) if item.get("path") in selected]
    diagnostics = [item for item in context.get("diagnostics", []) if item.get("path") in selected]

    return {
        "schema": SCHEMA_CONTEXT,
        "files": files,
        "chunks": chunks,
        "graph": _prune_graph(context.get("graph"), selected),
        "graph_status": context.get("graph_status", "not_provided"),
        "diagnostics": diagnostics,
        "scope": {"paths": sorted(selected), "partial": True},
    }
