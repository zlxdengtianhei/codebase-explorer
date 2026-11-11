"""Read-side queries over a rendered run's ``catalog.json``.

``find``, ``query`` and ``source`` back the CLI lookup commands;
``layer_metrics`` measures the storage layers of a run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cbe.symbols import SemanticError


def catalog_symbols(catalog: dict) -> dict[str, dict]:
    """Resolve the current catalog's public search view.

    Inventory IDs retain their names/facts. The semantic index supplies their
    disposition and primary page; synthetic units are also first-class query
    targets.
    """
    records = {key: dict(row) for key, row in (catalog.get("symbols") or {}).items()}
    for uid, unit in (catalog.get("units") or {}).items():
        record = {**records.get(uid, {}), **unit}
        record.setdefault("name", (catalog.get("short_names") or {}).get(uid, uid))
        paths = sorted({row["path"] for row in unit.get("ranges") or [] if row.get("path")})
        record.setdefault("files", paths)
        if len(paths) == 1:
            record.setdefault("file", paths[0])
        records[uid] = record
    for sid, resolution in catalog["symbol_index"].items():
        records[sid] = {**records.get(sid, {}),
                        **(catalog.get("dispositions") or {}).get(sid, {}),
                        **resolution}
    for sid, record in records.items():
        target = record.get("unit") or (sid if sid in (catalog.get("units") or {}) else None)
        detail = (catalog.get("units") or {}).get(target)
        if detail is not None:
            records[sid] = {**detail, **record, "id": sid,
                            "unit_id": target, "unit_ranges": detail.get("ranges", [])}
        else:
            record.setdefault("explain", record.get("reason", ""))
            for field in ("signatures", "relations", "reverse_relations", "outgoing", "incoming"):
                record.setdefault(field, [])
    edge_table = catalog.get("edges") or {}
    for sid, record in records.items():
        record["display_name"] = (catalog.get("short_names") or {}).get(sid, record.get("name", sid))
        for direction in ("outgoing", "incoming"):
            record[direction] = [edge_table[e] if isinstance(e, str) else e
                                 for e in record.get(direction) or []]
    return records
def query_catalog(run_dir: Path) -> dict[str, Any]:
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog["symbols"] = catalog_symbols(catalog)
    return catalog


def format_ranges(ranges: list[dict]) -> str:
    """Compact, unambiguous source coordinates for agent-facing text."""
    return ", ".join(f"{row['path']}:L{start}-L{end}"
                     for row in ranges for start, end in row.get("lines", []))


def find(run_dir: Path, term: str, limit: int = 25) -> list[dict[str, Any]]:
    """Locate matches; detailed evidence stays behind query."""
    from cbe.records import summary_sentence

    catalog = query_catalog(run_dir)
    inventory = {s["id"]: (path, s) for path, entry in catalog.get("inventory", {}).items()
                 for s in entry.get("symbols", [])}
    needle = term.casefold()
    results = []
    candidates = [(sid, record, False) for sid, record in catalog["symbols"].items()]
    candidates += [(path, record, True) for path, record in catalog["files"].items() if record.get("facts")]
    for sid, record, is_file in candidates:
        searchable = {"facts": record["facts"]} if is_file else {"id": sid, **record}
        matched = [field for field, value in searchable.items()
                   if needle in json.dumps(value, ensure_ascii=False).casefold()]
        if not matched:
            continue
        path, symbol = inventory.get(sid, (record.get("file"), {}))
        ranges = ([{"path": path, "lines": symbol["lines"]}] if symbol.get("lines") else
                  record.get("ranges") or [])
        if is_file and not ranges:
            ranges = [{"path": sid, "lines": [[1, max(1, catalog.get("inventory", {}).get(sid, {}).get("nlines", 1))]]}]
        name = record.get("display_name") or record.get("name") or sid
        if "::" in name:
            name = symbol.get("name") or name
        summary = summary_sentence(record) or summary_sentence({"explain": record.get("reason", "")})
        words = summary.split()
        summary = " ".join(words[:25]) + ("…" if len(words) > 25 else "")
        results.append({"id": sid, "name": name, "kind": symbol.get("kind") or record.get("kind") or
                        ("file" if is_file else "symbol"), "location": format_ranges(ranges),
                        "summary": summary, "matched_fields": matched})
    results.sort(key=lambda row: (0 if needle in {row["id"].casefold(), row["name"].casefold(),
                                                  str(catalog["symbols"].get(row["id"], {}).get("display_name", "")).casefold()}
                                 else 1))
    return results[:limit]


def find_text(results: list[dict]) -> str:
    return "".join(f"{r['name']} | {r['id']} | {r['kind']} | {r['location']} | "
                   f"{r['summary']} | match: {','.join(r['matched_fields'])}\n"
                   for r in results)


def query(run_dir: Path, symbol_id: str, edges: str | None = None) -> dict[str, Any]:
    """Compact object view; frozen graph is read only for explicit expansion."""
    if edges is not None and edges != "all" and (
            not edges or set(edges.split(",")) - {"import", "call", "cfg", "dataflow"}):
        raise SemanticError("--edges must be all or comma-separated import,call,cfg,dataflow")
    catalog = query_catalog(run_dir)
    table = catalog.get("edges") or {}
    if symbol_id in catalog.get("nodes", {}):
        return {"id": symbol_id, "name": catalog["nodes"][symbol_id]["title"],
                **catalog["nodes"][symbol_id],
                "dependencies": [e for e in catalog.get("node_dependencies", []) if e["from"] == symbol_id],
                "depended_on_by": [e for e in catalog.get("node_dependencies", []) if e["to"] == symbol_id]}
    if symbol_id in catalog["symbols"]:
        record = {"id": symbol_id, **catalog["symbols"][symbol_id]}
        for direction in ("outgoing", "incoming"):
            record[direction] = [table[e] if isinstance(e, str) else e
                                 for e in record.get(direction) or []]
    elif symbol_id in catalog["files"]:
        def listing(uid, row):
            return {"id": uid, "name": catalog.get("short_names", {}).get(uid, row.get("name", uid)),
                    "ranges": row.get("ranges", []), "summary": row.get("summary", row.get("reason", ""))}
        record = {"id": symbol_id, "ranges": catalog["files"][symbol_id].get("ranges", []),
                  **{key: catalog["files"][symbol_id][key] for key in ("tokens", "language", "known_empty")
                     if key in catalog["files"][symbol_id]},
                  "units": [listing(uid, u) for uid, u in catalog.get("units", {}).items()
                            if any(r["path"] == symbol_id for r in u.get("ranges") or [])],
                  "symbols": [listing(sid, s) for sid, s in catalog["symbols"].items()
                              if s.get("file") == symbol_id and sid not in catalog.get("units", {})],
                  "facts": catalog["files"][symbol_id].get("facts", {}),
                  "imports": [e for e in table.values() if e.get("kind") == "import"
                              and e.get("path") == symbol_id]}
    else:
        raise SemanticError(f"unknown unit, symbol or file: {symbol_id}; "
                            f"first use cbe find --run-dir {run_dir} --term {symbol_id}")
    record.setdefault("name", symbol_id)
    record["display_name"] = catalog.get("short_names", {}).get(symbol_id, record["name"])
    if edges:
        from cbe.records import SourceOwnership, frozen_sources

        context = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
        graph = context.get("graph") or catalog.get("graph") or {}
        nodes = {n["id"]: n for n in graph.get("nodes") or []}
        ownership = SourceOwnership(frozen_sources(context), context.get("chunks") or [],
                                    catalog["symbols"])
        members = ({symbol_id, *record.get("folded_members", [])}
                   if symbol_id in catalog.get("units", {}) else {symbol_id})
        def matches(edge):
            if symbol_id in catalog["files"]:
                node = nodes.get(edge.get("source"), {})
                owner = nodes.get(node.get("owner"), node)
                return (edge.get("path") or owner.get("path")) == symbol_id
            return ownership.edge_source(edge, nodes) in members
        from cbe.graph import NO_DATAFLOW_MESSAGE, built_without_dataflow

        if built_without_dataflow(graph) and "dataflow" in edges.split(","):
            if edges == "dataflow":
                raise SemanticError(NO_DATAFLOW_MESSAGE)
            record["notice"] = NO_DATAFLOW_MESSAGE
        record["raw_edges"] = [e for e in graph.get("edges") or []
                               if (edges == "all" or e.get("kind") in edges.split(",")) and matches(e)]
    return record


def query_text(record: dict) -> str:
    """Agent view: prose once, one line per relation or graph edge."""
    from cbe.records import summary_and_remainder

    summary, remainder = summary_and_remainder(record)
    lines = [f"{record.get('display_name', record['name'])}  {record['id']}"]
    for field in ("dependencies", "depended_on_by", "signature", "signatures", "ranges", "summary", "explain", "extras",
                  "uncertainties", "relations", "reverse_relations", "folded_members",
                  "internal_edge_counts", "facts", "units", "symbols", "notice"):
        value = record.get(field)
        if not value or (field == "summary" and remainder != (record.get("explain") or "").strip()):
            continue
        if field == "signatures" and len(value) == 1 and value[0]["signature"] == record.get("signature"):
            continue
        if field == "ranges":
            lines.append(f"ranges: {format_ranges(value)}")
        elif field in {"units", "symbols"}:
            lines.extend(f"{field}: {row['name']} | {row['id']} | {format_ranges(row['ranges'])} | {row['summary']}"
                         for row in value)
        elif isinstance(value, list):
            lines.extend(f"{field}: {json.dumps(row, ensure_ascii=False)}" for row in value)
        else:
            lines.append(f"{field}: {value}")
    for direction in ("outgoing", "incoming", "imports", "raw_edges"):
        for edge in record.get(direction) or []:
            endpoint = "source" if direction == "incoming" else "target"
            lines.append(f"{direction}: {edge.get('kind')} {edge.get(endpoint + '_name', edge.get(endpoint))} "
                         f"{edge.get(endpoint + '_symbol') or edge.get(endpoint)} [{edge.get('status', 'structural')}] "
                         f"{edge.get('path', '')}:L{edge.get('line', '')} id={edge['id']}")
    return "\n".join(lines) + "\n"


def source(run_dir: Path, object_id: str, context: int = 0) -> str:
    """Return numbered frozen source, checking all selected files before output."""
    from cbe.records import frozen_sources

    if context < 0:
        raise SemanticError("--context must be nonnegative")
    record = query(run_dir, object_id)
    ranges = record.get("ranges") or []
    if not ranges:
        raise SemanticError(f"no source ranges for: {object_id}")
    frozen = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
    texts = frozen_sources(frozen, [row["path"] for row in ranges])
    selected: dict[str, list[list[int]]] = {}
    for row in ranges:
        nlines = len(texts[row["path"]].splitlines())
        for start, end in row["lines"]:
            if nlines == 0:
                selected.setdefault(row["path"], [])
                continue
            if not 1 <= start <= end <= nlines:
                raise SemanticError(f"source range out of bounds: {row['path']}:{start}-{end}")
            selected.setdefault(row["path"], []).append([max(1, start - context), min(nlines, end + context)])
    output = []
    for path, spans in sorted(selected.items()):
        merged: list[list[int]] = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        lines = texts[path].splitlines()
        if not merged:
            output.append(f"# {path}: empty file")
        for start, end in merged:
            output.append(f"# {path}:L{start}-L{end}")
            output.extend(f"{number}: {lines[number - 1]}" for number in range(start, end + 1))
    return "\n".join(output) + "\n"


def layer_metrics(run_dir: Path) -> dict:
    """One storage-based token measure.

    Markdown includes page metadata, navigation, signatures and usage examples.
    Catalog JSON includes its preserved copies of prose. Frozen graph evidence
    is reported as UTF-8 JSON bytes, excluded from token ratios.
    These are storage layers, not disjoint semantic content classifications.
    The denominator counts each complete frozen source file exactly once.
    """
    from cbe.records import frozen_sources, summary_and_remainder
    from cbe.token_budget import count_text_tokens, count_section_tokens

    context = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
    source_tokens = sum(count_text_tokens(text) for text in frozen_sources(context).values())
    semantic = sum(count_text_tokens(path.read_text(encoding="utf-8"))
                   for path in sorted((run_dir / "docs").rglob("*.md")))
    catalog_text = (run_dir / "catalog.json").read_text(encoding="utf-8")
    catalog = json.loads(catalog_text)
    catalog_tokens = count_text_tokens(catalog_text)
    body_lines = set()
    for unit in catalog.get("units", {}).values():
        for field in ("explain", "summary"):
            body_lines.update(line.strip() for line in (unit.get(field) or "").splitlines() if line.strip())
        _, remainder = summary_and_remainder(unit)
        body_lines.update(line.strip() for line in remainder.splitlines() if line.strip())
        for extra in unit.get("extras") or []:
            if isinstance(extra, dict):
                body_lines.update(line.strip() for line in
                                  f"- {extra.get('topic')}: {str(extra.get('note', '')).strip()}".splitlines()
                                  if line.strip())
        for item in unit.get("uncertainties") or []:
            body_lines.update(line.strip() for line in f"- {item}".splitlines() if line.strip())
    breakdown = dict.fromkeys(("model_body", "signature_location", "heading_anchor", "relations",
                               "footer", "index", "node_text"), 0)
    for path in sorted((run_dir / "docs").rglob("*.md")):
        sections = []
        in_units = False
        in_footer = False
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith("### ") or '<a id="u-' in stripped:
                in_units = True
            if stripped.startswith("## Look up code"):
                in_footer = True
            if path.parent == run_dir / "docs":
                category = "index"
            elif re.match(r"\[f\d+\]: ", stripped):
                category = "signature_location"
            elif in_footer:
                category = "footer"
            elif in_units and stripped in body_lines:
                category = "model_body"
            elif stripped.startswith(("### ", '<a id="u-')):
                category = "heading_anchor"
            elif in_units and re.match(r"`.*` · \[", stripped):
                category = "signature_location"
            elif in_units and re.search(r": \[.*\](?:\(|\[)", stripped):
                category = "relations"
            else:
                category = "node_text"
            sections.append((category, line))
        for category, count in count_section_tokens(sections).items():
            breakdown[category] += count
    graph = context.get("graph") or catalog.get("graph")
    graph_bytes = (len(json.dumps(graph, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                   if graph else 0)
    if catalog.get("graph"):
        catalog_tokens = count_text_tokens(json.dumps({**catalog, "graph": None}, ensure_ascii=False, indent=2) + "\n")
    graph_tokens = 0
    deterministic = catalog_tokens
    return {"tokenizer": "o200k_base", "source_tokens": source_tokens,
            "semantic_tokens": semantic, "semantic_breakdown": breakdown,
            "model_body_tokens": breakdown["model_body"],
            "model_body_source_ratio": breakdown["model_body"] / source_tokens if source_tokens else None,
            "published_markdown_source_ratio": semantic / source_tokens if source_tokens else None,
            "deterministic_tokens": deterministic,
            "catalog_tokens": catalog_tokens, "frozen_graph_tokens": graph_tokens,
            "frozen_graph_bytes": graph_bytes,
            "semantic_source_ratio": semantic / source_tokens if source_tokens else None,
            "deterministic_source_ratio": deterministic / source_tokens if source_tokens else None,
            "scope": "Breakdown partitions full Markdown BPE tokens by the first byte's line: model_body "
                     "is published unit explain, summary, extras and uncertainties; signature_location includes "
                     "shared source-file reference definitions (including ones used by relations); "
                     "heading_anchor, relations, footer, INDEX and node_text (including labels/whitespace) "
                     "partition the rest. model_body/source and published_markdown/source use complete frozen files. "
                     "semantic: all published Markdown (node pages + INDEX, including navigation, "
                     "signatures and commands); deterministic: catalog.json as serialized, including "
                     "preserved prose copies and edge references, excluding the graph field; frozen graph "
                     "is excluded from token ratios (frozen_graph_tokens=0), reported separately as frozen_graph_bytes "
                     "using UTF-8 JSON with ensure_ascii=False and compact separators; complete "
                     "graph evidence is expanded only with query --edges; source: complete frozen files counted once; "
                     "context source chunks, host prompts, raw answers and summary.json excluded; layers are "
                     "storage measures, not disjoint content classes"}
