"""Published documents and their index: node pages, INDEX, catalog, structural checks, queries.

The program writes every source range and anchor; the model writes only the
explanations. ``verify`` checks identity, coverage, ownership and navigation;
it does not judge whether an explanation is true.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from cbe import concrete_facts
from cbe.symbols import SemanticError, inventory_ids, language_of


# One repository file larger than this becomes its own inventory unit region set;
# a chunk never has to fit a model context alone because batches group many.
SCHEMA = "cbe-semantic/1"


def unit_ranges(uid: str, unit: dict, inventory: dict[str, dict]) -> list[dict]:
    """Program-derived ``[{path, lines:[[start,end],...]}]`` from the inventory.

    The model never supplies a range; the ranged ids come from the unit's own
    inventory id and from any declared members."""
    collected: dict[str, list[list[int]]] = {}
    ids: list[str] = []
    path = uid.split("::", 1)[0]
    if "::" in uid and path in inventory:
        ids.append(uid)
    for member in unit.get("members") or []:
        if isinstance(member, str) and "::" in member \
                and member.split("::", 1)[0] in inventory and member not in ids:
            ids.append(member)
    if not ids:
        return []
    for member in ids:
        member_path = member.split("::", 1)[0]
        for row in inventory.get(member_path, {}).get("symbols", []):
            if row["id"] == member:
                for pair in row["lines"]:
                    if pair not in collected.setdefault(member_path, []):
                        collected[member_path].append(pair)
    return [{"path": p, "lines": pairs} for p, pairs in sorted(collected.items())]


def short_name(uid: str) -> str:
    if uid.startswith("grp:"):
        return uid[4:]
    _path, _, symbol = uid.partition("::")
    return symbol or uid


def unique_short(uid: str, taken: set[str]) -> str:
    base = short_name(uid)
    if base in taken and base != uid:
        path = uid.split("::", 1)[0]
        stem = re.sub(r"\.[a-z]+$", "", path.rsplit("/", 1)[-1], flags=re.IGNORECASE)
        base = f"{stem}:{base}"
    return base


def anchor(uid: str) -> str:
    return "u-" + hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12]


def _relation_link(target: str, units: dict, dispositions: dict, owner: dict,
                   nodes: dict, source_root: Path, page_dir: Path,
                   name_of: Callable[[str], str]) -> str:
    resolved = target if target in units else None
    if resolved is None:
        entry = dispositions.get(target) or {}
        if entry.get("how") in {"unit", "grouped"} and entry.get("unit") in units:
            resolved = entry["unit"]
    if resolved is not None and owner.get(resolved) in nodes:
        return f"[{name_of(resolved)}]({owner[resolved]}.md#{anchor(resolved)})"
    path = target.split("::", 1)[0]
    if (source_root / path).exists():
        return f"[{name_of(target)}]({os.path.relpath(source_root / path, page_dir)})"
    return f"`{name_of(target)}`"


def _build_unit_block(uid: str, units: dict, ranges_map: dict, owner: dict,
                      dispositions: dict, nodes: dict, source_root: Path, page_dir: Path,
                      name_of: Callable[[str], str]) -> str:
    unit = units[uid]
    lines = [f"### `{name_of(uid)}`", ""]
    meta = [f"kind: `{unit.get('kind')}`"]
    src_parts = []
    for entry in ranges_map.get(uid) or []:
        rel = os.path.relpath(source_root / entry["path"], page_dir)
        ranges_text = ",".join(f"L{pair[0]}-L{pair[1]}" for pair in entry["lines"])
        first = entry["lines"][0]
        src_parts.append(f"[{entry['path']} {ranges_text}]({rel}#L{first[0]}-L{first[1]})")
    if src_parts:
        meta.append("source: " + " · ".join(src_parts))
    members = [member for member in unit.get("members") or [] if isinstance(member, str)]
    if members:
        shown = ", ".join(f"`{name_of(member)}`" for member in members[:8])
        meta.append("folds: " + shown + (f" +{len(members) - 8} more" if len(members) > 8 else ""))
    lines.append(" — ".join(meta))
    lines.append("")
    explain = (unit.get("explain") or "").strip()
    if explain:
        lines += [explain, ""]
    extras = [extra for extra in unit.get("extras") or []
              if isinstance(extra, dict) and isinstance(extra.get("note"), str)
              and extra["note"].strip()]
    if extras:
        lines += ["**Notes.**", ""]
        lines += [f"- {extra.get('topic')}: {extra['note'].strip()}" for extra in extras]
        lines.append("")
    relations = [rel for rel in unit.get("relations") or []
                 if isinstance(rel, dict) and isinstance(rel.get("target"), str)
                 and rel["target"].strip()]
    if relations:
        lines += ["**Relations.**", ""]
        for rel in relations:
            link = _relation_link(rel["target"], units, dispositions, owner, nodes,
                                  source_root, page_dir, name_of)
            basis = f" — {rel['basis']}" if rel.get("basis") else ""
            lines.append(f"- {link} ({rel.get('kind') or 'use'}){basis}")
        lines.append("")
    uncertainties = [item for item in unit.get("uncertainties") or []
                     if isinstance(item, str) and item.strip()]
    if uncertainties:
        lines += ["**Uncertainties.**", ""]
        lines += [f"- {item}" for item in uncertainties]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render(*, run_dir: Path, source_root: Path, inventory: dict, units: dict,
           dispositions: dict, tree: dict, index_notes: list[str] | None = None) -> dict:
    """Render node pages, INDEX.md and a catalog under ``run_dir/docs``.

    Returns metadata the caller stores in run state for verification."""
    docs_dir = run_dir / "docs"
    nodes_dir = docs_dir / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    for stale in docs_dir.glob("nodes/*.md"):
        stale.unlink()

    nodes = {node["id"]: dict(node) for node in tree.get("nodes") or []}
    children: dict[str, list[str]] = {nid: [] for nid in nodes}
    owner: dict[str, str] = {}
    for nid, node in nodes.items():
        if node.get("parent") in nodes:
            children[node["parent"]].append(nid)
        for uid in node.get("unit_ids") or []:
            owner[uid] = nid

    taken: set[str] = set()
    name_of = lambda uid: unique_short(uid, taken)
    for uid in sorted(units):
        name_of(uid)
    for key in sorted(dispositions):
        name_of(key)

    anchors: dict[str, str] = {}
    for uid in sorted(units):
        short = anchor(uid)
        if short in anchors:
            raise SemanticError(f"anchor collision: {anchors[short]!r} and {uid!r}")
        anchors[short] = uid

    ranges_map = {uid: unit_ranges(uid, unit, inventory) for uid, unit in units.items()}
    edges_by_from: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for edge in tree.get("depends_on") or []:
        if isinstance(edge, dict) and edge.get("from") in edges_by_from \
                and edge.get("to") in nodes:
            edges_by_from[edge["from"]].append(edge)

    for nid, node in nodes.items():
        lines = [f"# {node.get('title') or nid}", "", f"Node id: `{nid}`", ""]
        if (node.get("capability") or "").strip():
            lines += [f"**Capability.** {node['capability'].strip()}", ""]
        if (node.get("summary") or "").strip():
            lines += [f"**Summary.** {node['summary'].strip()}", ""]
        if children.get(nid):
            lines += ["**Children.**", ""]
            for kid in children[nid]:
                kid_node = nodes[kid]
                lines.append(f"- [{kid_node.get('title') or kid}]({kid}.md) `{kid}` · "
                             f"{len(kid_node.get('unit_ids') or [])} unit(s)")
            lines.append("")
        if edges_by_from.get(nid):
            lines += ["**Depends on** (outgoing; reverse edges and full evidence in the "
                      "catalog appendix).", ""]
            for edge in edges_by_from[nid]:
                target = nodes.get(edge["to"]) or {}
                lines.append(f"- [{target.get('title') or edge['to']}]({edge['to']}.md)")
            lines.append("")
        parent = node.get("parent")
        if parent in nodes:
            lines += [f"Parent: [{nodes[parent].get('title') or parent}]({parent}.md)", ""]
        own = node.get("unit_ids") or []
        if own:
            lines += [f"## Units ({len(own)})", ""]
        for uid in own:
            if uid not in units:
                continue
            block = _build_unit_block(uid, units, ranges_map, owner, dispositions,
                                      nodes, source_root, nodes_dir, name_of)
            lines += [f'<a id="{anchor(uid)}"></a>'] + block.splitlines() + [""]
        (nodes_dir / f"{nid}.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def outline(nid: str, level: int) -> list[str]:
        node = nodes[nid]
        pad = "  " * level
        rows = [f"{pad}- [{node.get('title') or nid}](nodes/{nid}.md) "
                f"({len(node.get('unit_ids') or [])} units)"]
        for kid in children.get(nid) or []:
            rows.extend(outline(kid, level + 1))
        return rows

    roots = [nid for nid, node in nodes.items() if not node.get("parent")]
    index_lines = ["# Codebase Explorer", "", "Structured detail units with program-derived source "
                   "ranges and a semantic responsibility tree. Node pages show outgoing "
                   "dependencies; reverse edges, edge evidence and the full symbol index are "
                   "in `catalog.json`.", "", "## Responsibility tree", ""]
    for root in roots:
        index_lines.extend(outline(root, 0))
    index_lines += ["", "## Reading stats", "",
                    f"- units: {len(units)} · semantic nodes: {len(nodes)} · "
                    f"dispositioned inventory ids: {len(dispositions)}",
                    "- source ranges are program-derived from the inventory, never model-written"]
    if index_notes:
        index_lines += ["", "## Generation notes", ""] + [f"- {item}" for item in index_notes]
    (docs_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    # catalog: semantic index plus the compatibility `symbols` / `files` maps
    symbol_index: dict[str, dict] = {}
    for uid in sorted(units):
        node = owner.get(uid)
        symbol_index[uid] = {"how": "unit", "unit": uid, "node": node,
                             "page": f"nodes/{node}.md" if node in nodes else None,
                             "anchor": f"#{anchor(uid)}"}
    for key in sorted(dispositions):
        if key in symbol_index:
            continue
        entry = dispositions[key]
        target = entry.get("unit")
        if entry.get("how") in {"unit", "grouped"} and target in units:
            node = owner.get(target)
            symbol_index[key] = {"how": entry.get("how"), "unit": target, "node": node,
                                 "page": f"nodes/{node}.md" if node in nodes else None,
                                 "anchor": f"#{anchor(target)}"}
        else:
            symbol_index[key] = {"how": entry.get("how", "index_only"), "unit": None,
                                 "node": None, "page": None, "anchor": None,
                                 "reason": entry.get("reason", "")}


    compatibility_symbols: dict[str, dict] = {}
    compatibility_files: dict[str, dict] = {}
    sources = {path: (source_root / path).read_text(encoding="utf-8")
               for path in inventory if (source_root / path).is_file()}
    for path, entry in inventory.items():
        facts = concrete_facts.file_facts(path, sources.get(path, "")) \
            if path.endswith(".py") else None
        compatibility_files[path] = {"tokens": entry.get("tokens", 0),
                                     "language": language_of(path),
                                     "known_empty": bool(entry.get("known_empty"))}
        if facts and facts.get("file"):
            compatibility_files[path]["facts"] = facts["file"]
        for symbol in entry["symbols"]:
            record: dict[str, Any] = {"file": path, "name": symbol["name"],
                                      **symbol_index.get(symbol["id"], {"node": None, "page": None})}
            if facts and facts["symbols"].get(symbol["name"]):
                record["facts"] = facts["symbols"][symbol["name"]]
            compatibility_symbols[symbol["id"]] = record

    catalog = {
        "schema": SCHEMA, "project": "Codebase Explorer", "version": "",
        "units": {uid: {"node": owner.get(uid),
                        "page": f"nodes/{owner[uid]}.md" if owner.get(uid) in nodes else None,
                        "anchor": f"#{anchor(uid)}", "kind": units[uid].get("kind"),
                        "members": units[uid].get("members") or [],
                        "ranges": ranges_map.get(uid) or []}
                  for uid in sorted(units)},
        "nodes": {nid: {"parent": node.get("parent"), "children": children.get(nid) or [],
                        "unit_ids": node.get("unit_ids") or [], "title": node.get("title"),
                        "capability": node.get("capability"), "summary": node.get("summary")}
                  for nid, node in sorted(nodes.items())},
        "depends_on": tree.get("depends_on") or [],
        "dispositions": dispositions,
        "symbol_index": symbol_index,
        "inventory": inventory,
        "short_names": {uid: unique_short(uid, set())
                        for uid in sorted(set(units) | set(dispositions))},
        "merges": [],
        "symbols": compatibility_symbols,
        "files": compatibility_files,
    }
    (run_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    return {"units_rendered": len(units), "nodes": len(nodes), "owner": owner,
            "ranges_map": ranges_map, "symbol_index": symbol_index,
            "index": str(docs_dir / "INDEX.md")}


def catalog_symbols(catalog: dict) -> dict[str, dict]:
    """Resolve the public search view, including catalogs from earlier runs.

    Inventory IDs retain their names/facts. The semantic index supplies their
    disposition and primary page; synthetic units are also first-class query
    targets. Legacy catalogs without a semantic index retain their old view.
    """
    records = {key: dict(row) for key, row in (catalog.get("symbols") or {}).items()}
    for uid, unit in (catalog.get("units") or {}).items():
        record = {**unit, **records.get(uid, {})}
        record.setdefault("name", (catalog.get("short_names") or {}).get(uid, uid))
        paths = sorted({row["path"] for row in unit.get("ranges") or [] if row.get("path")})
        record.setdefault("files", paths)
        if len(paths) == 1:
            record.setdefault("file", paths[0])
        records[uid] = record
    for sid, resolution in (catalog.get("symbol_index") or {}).items():
        records[sid] = {**records.get(sid, {}),
                        **(catalog.get("dispositions") or {}).get(sid, {}),
                        **resolution}
    return records


def verify(run_dir: Path, inventory: dict, units: dict, dispositions: dict,
           tree: dict) -> list[dict]:
    """Deterministic structural/coverage checks for the semantic artifact.

    These check identity, coverage and ownership. They do NOT judge prose
    quality or whether an explanation is true; that stays with an independent
    review of the source, and a run that passes here is not thereby
    semantically verified."""
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "ok": bool(ok),
                       **({"detail": detail} if detail is not None else {})})

    inv_ids = set(inventory_ids(inventory))
    missing = sorted(inv_ids - set(dispositions))
    broken = [key for key, entry in dispositions.items()
              if (entry or {}).get("how") in {"unit", "grouped"}
              and entry.get("unit") not in units]
    check("semantic_dispositions_cover_inventory", not missing and not broken,
          {"inventory_ids": len(inv_ids), "missing": missing[:12], "broken": broken[:12]})

    nodes = {node["id"]: node for node in tree.get("nodes") or []}
    owner: dict[str, str] = {}
    dupes = []
    for nid, node in nodes.items():
        for uid in node.get("unit_ids") or []:
            if uid in owner:
                dupes.append(f"{uid}:{owner[uid]}+{nid}")
            owner[uid] = nid
    check("unique_primary_ownership", not dupes and set(units) <= set(owner),
          {"units": len(units), "assigned": len(owner), "dupes": dupes[:12],
           "unassigned": sorted(set(units) - set(owner))[:12]})

    roots = [nid for nid, node in nodes.items() if not node.get("parent")]
    children: dict[str, list[str]] = {nid: [] for nid in nodes}
    for nid, node in nodes.items():
        if node.get("parent") in nodes:
            children[node["parent"]].append(nid)
    cycle = False
    seen: set[str] = set()
    stack = roots[:1]
    while stack:
        nid = stack.pop()
        if nid in seen:
            cycle = True
            continue
        seen.add(nid)
        stack.extend(children.get(nid, []))
    check("tree_single_root_acyclic_reachable",
          len(roots) == 1 and not cycle and seen == set(nodes),
          {"nodes": len(nodes), "roots": roots, "cycle": cycle,
           "unreachable": sorted(set(nodes) - seen)[:12]})

    bad_ranges = []
    for uid, unit in units.items():
        ranges = unit_ranges(uid, unit, inventory)
        if not ranges and not uid.startswith("grp:"):
            bad_ranges.append(f"{uid}: no program-derived range")
        for entry in ranges:
            nlines = inventory.get(entry["path"], {}).get("nlines", 0)
            for pair in entry["lines"]:
                if not (1 <= pair[0] <= pair[1] <= nlines):
                    bad_ranges.append(f"{uid}:{entry['path']}:{pair}")
    check("unit_ranges_present_and_inbounds", not bad_ranges, bad_ranges[:12])

    docs = run_dir / "docs"
    links = sorted(docs.rglob("*.md"))
    broken_links = []
    page_texts = {}
    for md in links:
        text = md.read_text(encoding="utf-8")
        page_texts[md.relative_to(docs).as_posix()] = text
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, _, fragment = target.partition("#")
            resolved = (md.parent / file_part).resolve() if file_part else md
            if not resolved.exists():
                broken_links.append(f"{md.relative_to(docs)} -> {target}")
            elif fragment and resolved.suffix == ".md" \
                    and f'id="{fragment}"' not in resolved.read_text(encoding="utf-8"):
                broken_links.append(f"{md.relative_to(docs)} -> {target} (anchor missing)")
    check("relative_links_resolve", not broken_links,
          {"checked": len(links), "broken": broken_links[:12]})
    catalog_path = run_dir / "catalog.json"
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        listed = set(catalog.get("files") or {})
        missing = sorted(set(inventory) - listed)
        known_empty_missing = sorted(path for path, entry in inventory.items()
                                     if entry.get("known_empty")
                                     and not (catalog.get("files") or {}).get(path, {}).get("known_empty"))
        check("catalog_lists_every_file", not missing and not known_empty_missing,
              {"inventory_files": len(inventory), "missing": missing[:12],
               "known_empty_not_marked": known_empty_missing[:12]})
        # Compare the actual CLI view with accepted ownership and rendered
        # anchors, not just the number of catalog entries.
        searchable = query_catalog(run_dir)["symbols"]
        navigation_errors = []
        for sid in sorted(inv_ids | set(units)):
            record = searchable.get(sid)
            disposition = dispositions.get(sid) or {}
            target = sid if sid in units else disposition.get("unit")
            if sid not in units and disposition.get("how") == "index_only":
                if (record is None or record.get("how") != "index_only"
                        or record.get("page") is not None or record.get("anchor") is not None
                        or record.get("reason") != disposition.get("reason", "")):
                    navigation_errors.append(f"{sid}: index-only disposition lost")
                continue
            node = owner.get(target)
            page = f"nodes/{node}.md"
            fragment = f"#{anchor(target)}" if target else None
            if (target not in units or node not in nodes
                    or not record or record.get("unit") != target or record.get("node") != node
                    or record.get("page") != page or record.get("anchor") != fragment
                    or record.get("how") != ("unit" if sid in units else disposition.get("how"))
                    or f'id="{fragment[1:]}"' not in page_texts.get(page, "")):
                navigation_errors.append(f"{sid}: primary page or anchor is missing/wrong")
        check("catalog_navigation_resolves", not navigation_errors,
              {"checked": len(inv_ids | set(units)), "broken": navigation_errors[:12]})
    else:
        check("catalog_lists_every_file", False, "catalog.json is missing")
        check("catalog_navigation_resolves", False, "catalog.json is missing")
    check("semantic_rendered", (docs / "INDEX.md").is_file() and catalog_path.is_file())
    return checks


def query_catalog(run_dir: Path) -> dict[str, Any]:
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog["symbols"] = catalog_symbols(catalog)
    return catalog


def find(run_dir: Path, term: str, limit: int = 25) -> list[dict[str, Any]]:
    catalog = query_catalog(run_dir)
    needle = term.casefold()
    results = [{"id": sid, **record} for sid, record in catalog["symbols"].items()
               if needle in sid.casefold() or needle in json.dumps(record, ensure_ascii=False).casefold()]
    # Module-level facts (constants, option tables, templates) live on file
    # entries; their text is searched like symbol notes.
    results += [{"id": path, **record} for path, record in catalog["files"].items()
                if record.get("facts")
                and needle in json.dumps(record["facts"], ensure_ascii=False).casefold()]
    return results[:limit]


def query(run_dir: Path, symbol_id: str) -> dict[str, Any]:
    catalog = query_catalog(run_dir)
    if symbol_id in catalog["symbols"]:
        return {"id": symbol_id, **catalog["symbols"][symbol_id]}
    if symbol_id in catalog["files"]:
        return {"id": symbol_id, **catalog["files"][symbol_id]}
    raise SemanticError(f"unknown symbol or file: {symbol_id}")
