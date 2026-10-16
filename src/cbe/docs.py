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
from cbe.symbols import SemanticError, inventory_ids


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


def _file_link(label: str, path: str, source_links: dict[str, str]) -> str:
    reference = source_links.setdefault(path, f"f{len(source_links) + 1}")
    return f"[{label}][{reference}]"


def _relation_link(target: str, units: dict, dispositions: dict, owner: dict,
                   nodes: dict, source_root: Path, page_dir: Path,
                   name_of: Callable[[str], str], source_links: dict[str, str]) -> str:
    resolved = target if target in units else None
    if resolved is None:
        entry = dispositions.get(target) or {}
        if entry.get("how") in {"unit", "grouped"} and entry.get("unit") in units:
            resolved = entry["unit"]
    if resolved is not None and owner.get(resolved) in nodes:
        return f"[{name_of(resolved)}]({owner[resolved]}.md#{anchor(resolved)})"
    path = target.split("::", 1)[0]
    if (source_root / path).exists():
        return _file_link(name_of(target), path, source_links)
    return f"[{name_of(target)}](../../catalog.json)"


def _build_unit_block(uid: str, units: dict, ranges_map: dict, owner: dict,
                      dispositions: dict, nodes: dict, source_root: Path, page_dir: Path,
                      name_of: Callable[[str], str], source_links: dict[str, str]) -> str:
    unit = units[uid]
    lines = [f"### `{name_of(uid)}`", ""]
    raw_signature = unit.get("signature") or unit.get("kind") or "unit"
    declaration = re.search(r"\b(?:async def|def|class)\s+\w", raw_signature)
    if declaration:
        raw_signature = raw_signature[declaration.start():]
    signature = " ".join(raw_signature.split())
    if len(signature) > 88:
        signature = signature[:85] + "…"
    location = ""
    ranges = unit.get("ranges") or []
    if ranges:
        entry = unit.get("primary_range") or ranges[0]
        start, end = entry["lines"][0]
        location = " · " + _file_link(f"{entry['path']}:L{start}-L{end}", entry["path"], source_links)
    lines += [f"`{signature.replace('`', '')}`{location}", ""]
    summary = unit.get("summary") or ""
    explain = (unit.get("explain") or "").strip()
    if summary:
        lines += [summary, ""]
        if explain.startswith(summary):
            explain = explain[len(summary):].lstrip()
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
        labels = {"call": "调用", "inherit": "继承", "override": "覆盖", "import": "导入",
                  "raise": "抛出", "use": "使用", "contract": "契约", "group": "分组"}
        grouped: dict[str, list[str]] = {}
        for rel in relations:
            label = labels.get(rel.get("kind"), rel.get("kind") or "使用")
            link = _relation_link(rel["target"], units, dispositions, owner, nodes,
                                  source_root, page_dir, name_of, source_links)
            if link not in grouped.setdefault(label, []):
                grouped[label].append(link)
        lines += ["；".join(f"{label}：{'、'.join(links)}" for label, links in grouped.items()), ""]
    uncertainties = [item for item in unit.get("uncertainties") or []
                     if isinstance(item, str) and item.strip()]
    if uncertainties:
        lines += ["**Uncertainties.**", ""]
        lines += [f"- {item}" for item in uncertainties]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render(*, run_dir: Path, source_root: Path, inventory: dict, units: dict,
           dispositions: dict, tree: dict, languages: dict[str, str],
           index_notes: list[str] | None = None, system: dict | None = None,
           graph: dict | None = None, context: dict | None = None) -> dict:
    """Render node pages, INDEX.md and a catalog under ``run_dir/docs``.

    ``languages`` maps each path to the language frozen in the source context,
    so the catalog agrees with the plan even when it remapped a suffix.

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

    anchors: dict[str, str] = {}
    for uid in sorted(units):
        key = anchor(uid)
        if key in anchors:
            raise SemanticError(f"anchor collision: {anchors[key]!r} and {uid!r}")
        anchors[key] = uid
    ranges_map = {uid: unit_ranges(uid, unit, inventory) for uid, unit in units.items()}
    from cbe.records import build_records, frozen_sources

    if context is None and (run_dir / "context.json").is_file():
        context = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
    sources = (frozen_sources(context, list(inventory)) if context is not None else
               {path: (source_root / path).read_text(encoding="utf-8")
                for path in inventory if (source_root / path).is_file()})
    edge_table = {}
    units, symbol_records = build_records(units, dispositions, inventory, ranges_map,
                                          sources, languages, context, graph, edge_table)
    ranges_map = {uid: record["ranges"] for uid, record in units.items()}
    names = {}
    taken: set[str] = set()
    for uid in sorted(set(units) | set(dispositions)):
        symbol = symbol_records.get(uid, {})
        base = symbol.get("name") or short_name(uid)
        parts = uid.split("::")
        if symbol.get("kind") == "method" and len(parts) > 2 and "." in parts[2]:
            base = parts[2]
        if "::module_residual::" in uid or symbol.get("kind") == "module_residual":
            spans = symbol["ranges"][0]["lines"]
            base = f"{Path(symbol['file']).name} 模块代码（L{spans[0][0]}—L{spans[-1][1]}）"
        if base in taken:
            base = f"{uid.split('::', 1)[0]}:{base}"
        name = base
        suffix = 2
        while name in taken:
            name = f"{base} ({suffix})"
            suffix += 1
        taken.add(name)
        names[uid] = name
    name_of = lambda uid: names.get(uid, short_name(uid))
    edges_by_from: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for edge in tree.get("depends_on") or []:
        if isinstance(edge, dict) and edge.get("from") in edges_by_from \
                and edge.get("to") in nodes:
            edges_by_from[edge["from"]].append(edge)

    for nid, node in nodes.items():
        source_links: dict[str, str] = {}
        lines = [f"# {node.get('title') or nid}", ""]
        if (node.get("capability") or "").strip():
            lines += [f"**Capability.** {node['capability'].strip()}", ""]
        if (node.get("summary") or "").strip():
            lines += [node['summary'].strip(), ""]
        if children.get(nid):
            lines += ["**Children.**", ""]
            for kid in children[nid]:
                kid_node = nodes[kid]
                lines.append(f"- [{kid_node.get('title') or kid}]({kid}.md) `{kid}` · "
                             f"{len(kid_node.get('unit_ids') or [])} unit(s)")
            lines.append("")
        if edges_by_from.get(nid):
            lines += ["**Depends on.**", ""]
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
                                      nodes, source_root, nodes_dir, name_of, source_links)
            lines += [f'<a id="{anchor(uid)}"></a>'] + block.splitlines() + [""]
        lines += ["## 怎样查", "", '`RUN` 为运行目录。用本页单元标题查 `ID`（精确名称优先）：',
                  '`cbe find --run-dir "$RUN" --term "单元标题"`。再用结果中的 `ID`：',
                  '`cbe query --run-dir "$RUN" --id "$ID"`；'
                  '`cbe source --run-dir "$RUN" --id "$ID" --context 2`。', ""]
        lines += [f"[{ref}]: {os.path.relpath(source_root / path, nodes_dir)}"
                  for path, ref in source_links.items()]
        (nodes_dir / f"{nid}.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def outline(nid: str, level: int) -> list[str]:
        node = nodes[nid]
        pad = "  " * level
        rows = [f"{pad}- [{node.get('title') or nid}](nodes/{nid}.md) "
                f"({len(node.get('unit_ids') or [])} units)"]
        for uid in (node.get("unit_ids") or [])[:1]:
            if uid in units:
                rows.append(f"{pad}  - [{name_of(uid)}](nodes/{nid}.md#{anchor(uid)}) · "
                            + units[uid]["summary"])
        for kid in children.get(nid) or []:
            rows.extend(outline(kid, level + 1))
        return rows

    roots = [nid for nid, node in nodes.items() if not node.get("parent")]
    index_lines = ["# Codebase Explorer", "", "## 给 agent 的读法", "",
                   "先读 INDEX 的责任树。按维护问题打开节点页，再选单元。",
                   "节点页保留语义解释。完整签名、全部范围、折叠成员、关系依据和图边保存在 `catalog.json`。",
                   "将 `RUN` 设为本次运行目录的绝对路径。先找 id，再查解释或冻结源码。", "", "```sh",
                   'cbe find --run-dir "$RUN" --term "SEARCH_TERM"',
                   'cbe query --run-dir "$RUN" --id "$ID"',
                   'cbe source --run-dir "$RUN" --id "$ID" --context 2', "```", "",
                   "`ID` 可为单元 id、符号 id 或文件路径。命令返回正文，不必再追页面位置。",
                   "`source` 从冻结源码取代码，并先核对摘要。",
                   "图的反向边、状态和原始依据也在 catalog 中。", "", "## Responsibility tree", ""]
    for root in roots:
        index_lines.extend(outline(root, 0))
    index_lines += ["", "## Reading stats", "",
                    f"- units: {len(units)} · semantic nodes: {len(nodes)} · "
                    f"dispositioned inventory ids: {len(dispositions)}",
                    "- source ranges are program-derived from the inventory, never model-written"]
    index_lines += ["", "## 图覆盖 / Graph coverage", ""]
    if graph is None:
        index_lines += ["未提供图；关系仅靠模型阅读源码推断，可能不准确。"]
    else:
        from cbe.graph import read_graph_quality, graph_state
        quality = read_graph_quality(graph, repo=source_root)
        state, _ = graph_state(graph, quality=quality)
        if state == "failed":
            index_lines += ["没有后端跑成；图不可作为关系证据，关系仅靠模型阅读源码。"]
        elif state == "empty":
            index_lines += ["图为空，没有图确认的关系；关系仅靠模型阅读源码。"]
        elif state == "unsupported":
            index_lines += ["图不支持本次分析；关系仅靠模型阅读源码，可能不准确。"]
        else:
            index_lines += ["来源：静态分析图；resolved 表示图确认的关系（不保证语义正确）。"
                            "external 表示图确认目标在仓外；ambiguous 表示图给出候选。"
                            "unresolved、unsupported 及未覆盖的语言/关系种类仅靠模型阅读源码，可能不准确。"]
        by_language: dict[str, list[dict]] = {}
        for row in quality["edge_counts"]:
            by_language.setdefault(row["language"], []).append(row)
        index_lines += ["import、call 的状态比例分别按各自边数计算；"
                        "cfg、dataflow 是结构边，不按状态算可信度，仅列边数。"]
        for language, rows in sorted(by_language.items()):
            by_kind = {row["kind"]: row for row in rows}
            relations = []
            for kind in ("import", "call"):
                row = by_kind.get(kind)
                if row is None:
                    continue
                total = row["total"]
                proportions = ", ".join(f"{status} {count}/{total} ({count / total:.0%})"
                                        for status, count in row["statuses"].items() if count) if total else "无边"
                relations.append(f"{language} {kind}: {proportions}")
            structural = ", ".join(f"{kind}={by_kind[kind]['total']}"
                                   for kind in ("cfg", "dataflow") if kind in by_kind)
            if relations:
                index_lines += [" · ".join(relations) + "。"]
            if structural:
                index_lines += [f"{language} 结构边：{structural}。"]
        incomplete = quality["incomplete_capabilities"]
        if incomplete:
            index_lines += ["不完整：" + "; ".join(
                f"{c.get('language')}/{c.get('graph')} {c.get('status')}"
                for c in incomplete) + "。"]
        integrity = [f"悬空边 {quality['dangling_edges']['count']}",
                     f"清单外节点 {quality['nodes_outside_manifest']['count']}",
                     f"文件不存在的节点 {quality['nodes_missing_files']['count']}"
                     if quality["file_existence_checked"] else "文件存在性未检查"]
        if quality["frontend_failures"]:
            integrity.append("前端失败，见图 diagnostics")
        if quality["backend_completed"] is None:
            integrity.append("后端完成状态未知")
        index_lines += ["程序核：" + "；".join(integrity) + "。"]
    if system:
        index_lines += ["", "## Overview", "", system["overview"],
                        "", "## Maintenance navigation", "", system["maintenance_navigation"]]
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
    for path, entry in inventory.items():
        facts = concrete_facts.file_facts(path, sources.get(path, "")) \
            if path.endswith(".py") else None
        compatibility_files[path] = {"tokens": entry.get("tokens", 0),
                                     "language": languages.get(path, "unknown"),
                                     "known_empty": bool(entry.get("known_empty")),
                                     "ranges": [{"path": path, "lines": [[1, max(1, len(sources.get(path, '').splitlines()))]]}],
                                     "signatures": [{"id": sid, "signature": row["signature"]}
                                                    for sid, row in symbol_records.items() if row["file"] == path]}
        if facts and facts.get("file"):
            compatibility_files[path]["facts"] = facts["file"]
        for symbol in entry["symbols"]:
            record: dict[str, Any] = {**symbol_records[symbol["id"]], "file": path, "name": symbol["name"],
                                      **symbol_index.get(symbol["id"], {"node": None, "page": None})}
            if facts and facts["symbols"].get(symbol["name"]):
                record["facts"] = facts["symbols"][symbol["name"]]
            compatibility_symbols[symbol["id"]] = record

    catalog = {
        "schema": SCHEMA, "project": "Codebase Explorer", "version": "",
        "units": {uid: {**units[uid], "node": owner.get(uid),
                        "page": f"nodes/{owner[uid]}.md" if owner.get(uid) in nodes else None,
                        "anchor": f"#{anchor(uid)}"} for uid in sorted(units)},
        "edges": edge_table,
        "graph": None if (context or {}).get("graph") is not None else graph,
        "graph_ref": "context.json" if (context or {}).get("graph") is not None else None,
        "nodes": {nid: {"parent": node.get("parent"), "children": children.get(nid) or [],
                        "unit_ids": node.get("unit_ids") or [], "title": node.get("title"),
                        "capability": node.get("capability"), "summary": node.get("summary")}
                  for nid, node in sorted(nodes.items())},
        "depends_on": tree.get("depends_on") or [],
        "dispositions": dispositions,
        "symbol_index": symbol_index,
        "inventory": inventory,
        "short_names": names,
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
        record = {**records.get(uid, {}), **unit}
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


def prose_for_links(text: str) -> str:
    """Hide code blocks and paired code spans within each prose paragraph.

    Inline spans may cross a soft line break, but never a blank line or a
    fenced/indented code block. An unmatched delimiter remains ordinary prose.
    """
    paragraphs = []
    pending = []
    fence = None

    def flush():
        paragraph = "".join(pending)
        paragraphs.append(re.sub(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", "", paragraph,
                                 flags=re.DOTALL))
        pending.clear()

    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker and (marker[1][0] != "`" or "`" not in marker[2]):
            flush()
            fence = marker[1]
        elif not line.strip() or line.startswith(("    ", "\t")):
            flush()
            paragraphs.append("\n")
        else:
            pending.append(line)
    flush()
    return "".join(paragraphs)


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
        # Undefined CommonMark references are literal text (e.g. Python a[b][c]).
        # Only fN is our generated reference namespace; code examples are opaque.
        link_text = prose_for_links(text)
        references = dict(re.findall(r"^\[([^\]\n]+)\]:\s*(\S+)\s*$", link_text, re.MULTILINE))
        for reference in re.findall(r"\[[^\]\n]+\]\[([^\]\n]+)\]", link_text):
            if re.fullmatch(r"f\d+", reference) and reference not in references:
                broken_links.append(f"{md.relative_to(docs)} -> [{reference}] (definition missing)")
        targets = re.findall(r"\]\(([^)\s]+)\)", link_text) + list(references.values())
        for target in targets:
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


def format_ranges(ranges: list[dict]) -> str:
    """Compact, unambiguous source coordinates for agent-facing text."""
    return ", ".join(f"{row['path']}:L{start}-L{end}"
                     for row in ranges for start, end in row.get("lines", []))


def find(run_dir: Path, term: str, limit: int = 25) -> list[dict[str, Any]]:
    """Locate matches; detailed evidence stays behind query, including for old catalogs."""
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
                   f"{r['summary']} | match: {','.join(r['matched_fields'])}\n" for r in results)


def query(run_dir: Path, symbol_id: str, edges: str | None = None) -> dict[str, Any]:
    """Compact object view; frozen graph is read only for explicit expansion."""
    if edges is not None and edges != "all" and (
            not edges or set(edges.split(",")) - {"import", "call", "cfg", "dataflow"}):
        raise SemanticError("--edges must be all or comma-separated import,call,cfg,dataflow")
    catalog = query_catalog(run_dir)
    table = catalog.get("edges") or {}
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
        raise SemanticError(f"unknown unit, symbol or file: {symbol_id}")
    record.setdefault("name", symbol_id)
    record["display_name"] = catalog.get("short_names", {}).get(symbol_id, record["name"])
    if edges:
        from cbe.records import SourceOwnership, frozen_sources

        context = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
        graph = context.get("graph") or catalog.get("graph") or {}
        nodes = {n["id"]: n for n in graph.get("nodes") or []}
        ownership = SourceOwnership(frozen_sources(context), context.get("chunks") or [],
                                    catalog["symbols"])
        members = {symbol_id, *record.get("folded_members", [])}
        def matches(edge):
            if symbol_id in catalog["files"]:
                node = nodes.get(edge.get("source"), {})
                owner = nodes.get(node.get("owner"), node)
                return (edge.get("path") or owner.get("path")) == symbol_id
            return ownership.edge_source(edge, nodes) in members
        record["raw_edges"] = [e for e in graph.get("edges") or []
                               if (edges == "all" or e.get("kind") in edges.split(",")) and matches(e)]
    return record


def query_text(record: dict) -> str:
    """Agent view: prose once, one line per relation or graph edge."""
    lines = [f"{record.get('display_name', record['name'])}  {record['id']}"]
    for field in ("signature", "signatures", "ranges", "summary", "explain", "extras",
                  "uncertainties", "relations", "reverse_relations", "folded_members",
                  "internal_edge_counts", "facts", "units", "symbols"):
        value = record.get(field)
        if not value or (field == "summary" and record.get("explain", "").startswith(value)):
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
    """One storage-based token measure, usable on old and new render outputs.

    Markdown includes page metadata, navigation, signatures and usage examples.
    Catalog JSON includes its preserved copies of prose. Frozen graph evidence
    is reported as UTF-8 JSON bytes, excluded from token ratios.
    These are storage layers, not disjoint semantic content classifications.
    The denominator counts each complete frozen source file exactly once.
    """
    from cbe.records import frozen_sources
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
        explain, summary = unit.get("explain") or "", unit.get("summary") or ""
        if summary and explain.startswith(summary):
            body_lines.update(line.strip() for line in explain[len(summary):].lstrip().splitlines() if line.strip())
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
            if stripped.startswith("## 怎样查"):
                in_footer = True
            if path.name == "INDEX.md":
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
            elif in_units and re.search(r"：\[.*\](?:\(|\[)", stripped):
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
