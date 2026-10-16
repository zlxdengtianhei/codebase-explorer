"""Published records: one authority for prose, source identity and graph evidence."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from cbe.symbols import SemanticError


def correction_notice(row: dict) -> str:
    """One explanation of a corrected definition for pages and agent queries."""
    def code_span(text):
        width = max((len(run) for run in re.findall(r"`+", text)), default=0) + 1
        fence = "`" * width
        return f"{fence} {text} {fence}"

    return (f"CBE changed the unit ID from {code_span(row['original'])} "
            f"to the inventory ID {code_span(row['corrected'])}. "
            "The model wrote this body under the wrong ID; it may be inaccurate.")


def summary_sentence(unit: dict) -> str:
    """Use the author's optional sentence, or the first explanation sentence."""
    summary = unit.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    text = (unit.get("explain") or "").strip()
    for match in re.finditer(r"[.!?](?=\s|$)|[。！？]", text):
        if re.search(r"\b(?:i\.e|e\.g)\.$", text[:match.end()], re.IGNORECASE):
            continue
        return text[:match.end()]
    return text.split("\n", 1)[0]


def summary_and_remainder(unit: dict) -> tuple[str, str]:
    """Keep the explanation once when its prefix already serves as summary."""
    summary = unit.get("summary") or ""
    explain = (unit.get("explain") or "").strip()
    if summary and explain.startswith(summary):
        explain = explain[len(summary):].lstrip()
    return summary, explain


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
        raw = (files[path]["source"].encode("utf-8") if "source" in files[path] else
               b"".join(c.get("text", "").encode("utf-8") for c in parts))
        if hashlib.sha256(raw).hexdigest() != files[path].get("sha256"):
            raise SemanticError(f"frozen source digest mismatch: {path}; no code printed")
        sources[path] = raw.decode("utf-8")
    return sources


class SourceOwnership:
    """Resolve coordinates to exclusive frozen chunks, including graph callers."""

    def __init__(self, sources: dict[str, str], chunks: list[dict], symbol_ids):
        self.starts = {}
        self.blocks = defaultdict(list)
        for path, text in sources.items():
            raw = text.encode("utf-8")
            self.starts[path] = (raw, [0] + [i + 1 for i, b in enumerate(raw) if b == 10])
        for chunk in chunks:
            if chunk["id"] in symbol_ids:
                self.blocks[chunk["path"]].append(chunk)

    def at(self, path, line, column=None):
        """Return the symbol owning a one-based source coordinate, or None."""
        if path not in self.starts or not isinstance(line, int) or line < 1:
            return None
        raw, offsets = self.starts[path]
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
        for chunk in self.blocks[path]:
            if chunk.get("start_byte", -1) <= point < chunk.get("end_byte", -1):
                return chunk["id"]
        return None

    def edge_source(self, edge: dict, nodes: dict):
        source = nodes.get(edge.get("source"), {})
        if edge.get("kind") == "call":
            return self.at(edge.get("path") or source.get("path"), edge.get("line"), edge.get("column"))
        owner = nodes.get(source.get("owner"), source)
        return self.at(owner.get("path"), owner.get("start_line"))


def build_records(units: dict, dispositions: dict, inventory: dict, ranges: dict,
                  sources: dict[str, str], languages: dict[str, str],
                  context: dict | None, graph: dict | None,
                  edge_table: dict | None = None) -> tuple[dict, dict]:
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
            declaration = chunk.get("symbol_id") or re.sub(r"::s\d+$", "", sid)
            by_id, by_location = signatures.get(path, ({}, {}))
            location = (symbol["name"], symbol["lines"][0][0])
            signature = by_id.get(declaration, by_location.get(location,
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

    ownership = SourceOwnership(sources, list(chunks.values()), symbols)

    graph_nodes = {n["id"]: n for n in (graph or {}).get("nodes") or []}
    node_symbols = {}
    for nid, node in graph_nodes.items():
        owner = graph_nodes.get(node.get("owner"), node)
        node_symbols[nid] = ownership.at(owner.get("path"), owner.get("start_line"))
    outgoing, incoming = defaultdict(list), defaultdict(list)
    internal = defaultdict(lambda: defaultdict(int))
    edge_table = {} if edge_table is None else edge_table
    for edge in (graph or {}).get("edges") or []:
        source = graph_nodes.get(edge.get("source"), {})
        caller = ownership.edge_source(edge, graph_nodes)
        callee = node_symbols.get(edge.get("target"))
        if edge.get("kind") in {"cfg", "dataflow"}:
            if caller:
                internal[caller][edge["kind"]] += 1
            continue
        evidence = {key: edge[key] for key in ("id", "kind", "status", "source", "target", "path", "line", "column")
                    if key in edge}
        evidence.update(source_symbol=caller, target_symbol=callee,
                        source_name=symbols.get(caller, {}).get("name") or source.get("name") or edge.get("source"),
                        target_name=symbols.get(callee, {}).get("name") or graph_nodes.get(edge.get("target"), {}).get("name") or edge.get("expression") or edge.get("method_full_name") or edge.get("target") or "unknown target")
        edge_table[edge["id"]] = evidence
        if caller:
            outgoing[caller].append(edge["id"])
        if callee:
            incoming[callee].append(edge["id"])
    availability = graph_state(graph)[0]
    for sid, symbol in symbols.items():
        symbol.update(graph_state=availability, outgoing=outgoing[sid], incoming=incoming[sid],
                      internal_edge_counts=dict(internal[sid]))

    records = {}
    for uid, unit in units.items():
        declared_members = [member for member in unit.get("members") or [] if isinstance(member, str)]
        members = list(dict.fromkeys(([uid] if uid in symbols else []) + declared_members +
                                     [sid for sid, d in dispositions.items() if d.get("unit") == uid]))
        signature_rows = [{"id": sid, "signature": symbols[sid]["signature"]}
                          for sid in members if sid in symbols]
        primary_id = next((row["id"] for row in signature_rows if row["signature"]),
                          next((sid for sid in members if sid in symbols), None))
        complete_ranges = {row["path"]: [pair[:] for pair in row["lines"]] for row in ranges[uid]}
        for sid in members:
            for row in symbols.get(sid, {}).get("ranges", []):
                pairs = complete_ranges.setdefault(row["path"], [])
                pairs.extend(pair[:] for pair in row["lines"] if pair not in pairs)
        effective_ranges = [{"path": path, "lines": pairs} for path, pairs in sorted(complete_ranges.items())]
        primary_range = (symbols[primary_id]["ranges"][0] if primary_id else
                         next(iter(effective_ranges), None))
        record = {**unit, "id": uid, "summary": summary_sentence(unit),
                  "ranges": effective_ranges, "primary_range": primary_range, "signatures": signature_rows,
                  "signature": next((r["signature"] for r in signature_rows if r["signature"]), ""),
                  "members": unit.get("members") or [], "folded_members": [m for m in members if m != uid],
                  "reverse_relations": reverse[uid], "graph_state": availability}
        # Correction metadata is derived exclusively from active task flags.
        record.pop("id_corrections", None)
        for direction, edges in (("outgoing", outgoing), ("incoming", incoming)):
            record[direction] = list(dict.fromkeys(eid for sid in members for eid in edges[sid]))
        record["internal_edge_counts"] = {
            kind: sum(internal[sid].get(kind, 0) for sid in members)
            for kind in ("cfg", "dataflow")}
        for field in ("extras", "relations", "uncertainties"):
            record.setdefault(field, [])
        records[uid] = record
    return records, symbols
