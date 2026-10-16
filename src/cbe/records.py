"""Published records: one authority for prose, source identity and graph evidence."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from cbe.symbols import SemanticError


def summary_sentence(unit: dict) -> str:
    """Use the author's optional sentence, or the first explanation sentence."""
    summary = unit.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    text = (unit.get("explain") or "").strip()
    match = re.search(r"[.!?](?=\s|$)|[。！？]", text)
    return text[:match.end()] if match else text.split("\n", 1)[0]


def frozen_sources(context: dict, paths: list[str] | None = None) -> dict[str, str]:
    """Reassemble and SHA-256-check every selected frozen file before returning.

    Chunks are exclusive UTF-8 byte slices, not whole declarations. Concatenating
    them by byte offset recovers original bytes (including CRLF). The whole-file
    digest also rejects missing, duplicated, overlapping or tampered chunks.
    """
    files = {row["path"]: row for row in context.get("files") or []}
    selected = sorted(files if paths is None else set(paths))
    sources = {}
    for path in selected:
        if path not in files:
            raise SemanticError(f"no frozen source file: {path}")
        parts = sorted((c for c in context.get("chunks") or [] if c["path"] == path),
                       key=lambda c: c.get("start_byte", 0))
        raw = b"".join(c.get("text", "").encode("utf-8") for c in parts)
        if hashlib.sha256(raw).hexdigest() != files[path].get("sha256"):
            raise SemanticError(f"frozen source digest mismatch: {path}; no code printed")
        sources[path] = raw.decode("utf-8")
    return sources


def build_records(units: dict, dispositions: dict, inventory: dict, ranges: dict,
                  sources: dict[str, str], languages: dict[str, str],
                  context: dict | None, graph: dict | None) -> tuple[dict, dict]:
    """Return unit and inventory-symbol records, keeping original evidence verbatim."""
    from cbe.source_context import source_signatures
    from cbe.graph import graph_state

    chunks = {c["id"]: c for c in (context or {}).get("chunks") or []}
    signatures = {path: source_signatures(path, text, languages.get(path, "unknown"))
                  for path, text in sources.items()}
    symbols = {}
    for path, entry in inventory.items():
        for symbol in entry["symbols"]:
            sid = symbol["id"]
            chunk = chunks.get(sid, {})
            declaration = chunk.get("symbol_id", sid)
            by_id, by_name = signatures.get(path, ({}, {}))
            signature = by_id.get(declaration, by_name.get(symbol["name"],
                                  chunk.get("signature") or ""))
            symbols[sid] = {"id": sid, "kind": symbol["kind"], "name": symbol["name"],
                            "file": path, "signature": signature,
                            "ranges": [{"path": path, "lines": symbol["lines"]}]}

    def resolve(sid):
        return sid if sid in units else (dispositions.get(sid) or {}).get("unit")

    reverse = defaultdict(list)
    for uid, unit in units.items():
        for relation in unit.get("relations") or []:
            target = resolve(relation.get("target"))
            if target in units:
                reverse[target].append({"source": uid, **relation})

    # Coordinates belong to exclusive chunks. Never assign a caller merely
    # because its enclosing declaration spans the call's line.
    blocks = defaultdict(list)
    starts = {}
    for path, text in sources.items():
        raw = text.encode("utf-8")
        starts[path] = (raw, [0] + [i + 1 for i, b in enumerate(raw) if b == 10])
    for sid, chunk in chunks.items():
        if sid in symbols:
            blocks[chunk["path"]].append(chunk)

    def at(path, line, column=None):
        if path not in starts or not isinstance(line, int) or line < 1:
            return None
        raw, offsets = starts[path]
        if line > len(offsets):
            return None
        point = offsets[line - 1]
        if column is None:
            while point < len(raw) and raw[point] in b" \t":
                point += 1
        elif isinstance(column, int) and column >= 1:
            end = offsets[line] if line < len(offsets) else len(raw)
            text = raw[point:end].decode("utf-8")
            if column > len(text) + 1:
                return None
            point += len(text[:column - 1].encode("utf-8"))
        else:
            return None
        for chunk in blocks[path]:
            if chunk.get("start_byte", -1) <= point < chunk.get("end_byte", -1):
                return chunk["id"]
        return None

    graph_nodes = {n["id"]: n for n in (graph or {}).get("nodes") or []}
    node_symbols = {}
    for nid, node in graph_nodes.items():
        owner = graph_nodes.get(node.get("owner"), node)
        node_symbols[nid] = at(owner.get("path"), owner.get("start_line"))
    outgoing, incoming = defaultdict(list), defaultdict(list)
    for edge in (graph or {}).get("edges") or []:
        source = graph_nodes.get(edge.get("source"), {})
        caller = (at(edge.get("path") or source.get("path"), edge.get("line"), edge.get("column"))
                  if edge.get("kind") == "call" else node_symbols.get(edge.get("source")))
        callee = node_symbols.get(edge.get("target"))
        evidence = {**edge, "source_symbol": caller, "target_symbol": callee}
        if caller:
            outgoing[caller].append(evidence)
        if callee:
            incoming[callee].append(evidence)
    availability = graph_state(graph)[0]
    for sid, symbol in symbols.items():
        symbol.update(graph_state=availability, outgoing=outgoing[sid], incoming=incoming[sid])

    records = {}
    for uid, unit in units.items():
        members = list(dict.fromkeys(([uid] if uid in symbols else []) +
                                     (unit.get("members") or []) +
                                     [sid for sid, d in dispositions.items() if d.get("unit") == uid]))
        signature_rows = [{"id": sid, "signature": symbols[sid]["signature"]}
                          for sid in members if sid in symbols]
        record = {**unit, "id": uid, "summary": summary_sentence(unit),
                  "ranges": ranges[uid], "signatures": signature_rows,
                  "signature": next((r["signature"] for r in signature_rows if r["signature"]), ""),
                  "members": unit.get("members") or [], "folded_members": [m for m in members if m != uid],
                  "reverse_relations": reverse[uid], "graph_state": availability}
        for direction, edges in (("outgoing", outgoing), ("incoming", incoming)):
            unique = {}
            for sid in members:
                for edge in edges[sid]:
                    unique[edge["id"]] = edge
            record[direction] = list(unique.values())
        node_ids = {edge.get(endpoint) for direction in ("outgoing", "incoming")
                    for edge in record[direction] for endpoint in ("source", "target")}
        record["graph_nodes"] = [graph_nodes[nid] for nid in sorted(node_ids - {None}) if nid in graph_nodes]
        for field in ("extras", "relations", "uncertainties"):
            record.setdefault(field, [])
        records[uid] = record
    return records, symbols
