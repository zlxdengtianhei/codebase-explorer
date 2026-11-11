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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from cbe import concrete_facts
from cbe.catalog_query import query_catalog
from cbe.symbols import SemanticError, inventory_ids
from cbe.treename import normalize_title

# One repository file larger than this becomes its own inventory unit region set;
# a chunk never has to fit a model context alone because batches group many.
SCHEMA = "cbe-semantic/1"
DEPENDENCY_STYLES = {"graph_confirmed": ("graph-confirmed", "-->"),
                     "model_inferred": ("model-inferred", "-.->"),
                     "graph_only": ("graph-only", "==>")}


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


def anchor(uid: str) -> str:
    return "u-" + hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12]


def link_text(text: str) -> str:
    """Escape generated Markdown link labels, including literal backslashes."""
    return re.sub(r"([\\\[\]()`*_<>])", r"\\\1", text)


def code_text(text: str) -> str:
    """Keep original IDs verbatim, even when they contain Markdown characters."""
    width = max((len(run) for run in re.findall(r"`+", text)), default=0) + 1
    fence = "`" * width
    return f"{fence} {text} {fence}"


def inline_code(text: str) -> str:
    """Compact code span: padded only where the text itself touches a backtick."""
    fence = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _file_link(label: str, path: str, source_links: dict[str, str]) -> str:
    reference = source_links.setdefault(path, f"f{len(source_links) + 1}")
    return f"[{label}][{reference}]"


def _relation_link(target: str, units: dict, dispositions: dict, owner: dict,
                   nodes: dict, source_root: Path,
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


def _build_unit_block(uid: str, units: dict, owner: dict,
                      dispositions: dict, nodes: dict, source_root: Path,
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
    from cbe.records import summary_and_remainder

    summary, explain = summary_and_remainder(unit)
    if summary:
        lines += [literal_links(summary), ""]
    if explain:
        lines += [literal_links(explain), ""]
    extras = [extra for extra in unit.get("extras") or []
              if isinstance(extra, dict) and isinstance(extra.get("note"), str)
              and extra["note"].strip()]
    if extras:
        lines += ["**Notes.**", ""]
        lines += [f"- {extra.get('topic')}: {literal_links(extra['note'].strip())}" for extra in extras]
        lines.append("")
    relations = [rel for rel in unit.get("relations") or []
                 if isinstance(rel, dict) and isinstance(rel.get("target"), str)
                 and rel["target"].strip()]
    if relations:
        labels = {"call": "calls", "inherit": "inherits", "override": "overrides", "import": "imports",
                  "raise": "raises", "use": "uses", "contract": "contract", "group": "group"}
        grouped: dict[str, list[str]] = {}
        for rel in relations:
            label = labels.get(rel.get("kind"), rel.get("kind") or "uses")
            link = _relation_link(rel["target"], units, dispositions, owner, nodes,
                                  source_root, name_of, source_links)
            if link not in grouped.setdefault(label, []):
                grouped[label].append(link)
        lines += ["; ".join(f"{label}: {', '.join(links)}" for label, links in grouped.items()), ""]
    uncertainties = [item for item in unit.get("uncertainties") or []
                     if isinstance(item, str) and item.strip()]
    if uncertainties:
        lines += ["**Uncertainties.**", ""]
        lines += [f"- {literal_links(item)}" for item in uncertainties]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _graph_coverage(graph: dict | None, source_root: Path) -> list[str]:
    """What the graph covers, in plain lines (RUN.md)."""
    lines: list[str] = []
    if graph is None:
        lines += ["No graph was provided. Relations are inferred by the model from source and may be inaccurate."]
    else:
        from cbe.graph import read_graph_quality, graph_state
        quality = read_graph_quality(graph)
        state, _ = graph_state(graph, quality=quality)
        if state == "failed":
            lines += ["No graph backend succeeded. Relations are inferred by the model from source."]
        elif state == "empty":
            lines += ["The graph is empty. No relations are graph-confirmed; relations are inferred by the model from source."]
        elif state == "unsupported":
            lines += ["The graph does not support this analysis. Relations are inferred by the model from source and may be inaccurate."]
        else:
            lines += ["Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. "
                            "External targets are outside the repository; ambiguous targets have multiple candidates. "
                            "Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate."]
        by_language: dict[str, list[dict]] = {}
        for row in quality["edge_counts"]:
            by_language.setdefault(row["language"], []).append(row)
        lines += ["Import and call status ratios use the edge count of each kind. "
                        "CFG and dataflow are structural edges; only their counts are shown, without status ratios."]
        for language, rows in sorted(by_language.items()):
            by_kind = {row["kind"]: row for row in rows}
            relations = []
            for kind in ("import", "call"):
                row = by_kind.get(kind)
                if row is None:
                    continue
                total = row["total"]
                proportions = ", ".join(f"{status} {count}/{total} ({count / total:.0%})"
                                        for status, count in row["statuses"].items() if count) if total else "no edges"
                relations.append(f"{language} {kind}: {proportions}")
            structural = ", ".join(f"{kind}={by_kind[kind]['total']}"
                                   for kind in ("cfg", "dataflow") if kind in by_kind)
            if relations:
                lines += [" · ".join(relations) + "."]
            if structural:
                lines += [f"{language} structural edges: {structural}."]
        incomplete = quality["incomplete_capabilities"]
        if incomplete:
            lines += ["Incomplete capabilities: " + "; ".join(
                f"{c.get('language')}/{c.get('graph')} {c.get('status')}"
                for c in incomplete) + "."]
        integrity = [f"dangling edges {quality['dangling_edges']['count']}",
                     f"nodes outside manifest {quality['nodes_outside_manifest']['count']}",
                     f"nodes with missing files {quality['nodes_missing_files']['count']}"
                     if quality["file_existence_checked"] else "file existence not checked"]
        if quality["frontend_failures"]:
            integrity.append("frontend failed; see graph diagnostics")
        if quality["backend_completed"] is None:
            integrity.append("backend completion unknown")
        lines += ["Program checks: " + "; ".join(integrity) + "."]
    return lines


INDEX_MIN_TOKENS = 2000   # the entry page may use at least this many tokens ...
INDEX_SHARE = 0.03        # ... or this share of the source's tokens
FILES_SHOWN = 3


def _rank_files(units: dict, ranges_map: dict, members: list[str]) -> list[str]:
    """File names of a node's subtree, the ones with most unit lines first."""
    lines: dict[str, int] = {}
    for uid in members:
        for rng in ranges_map.get(uid) or units.get(uid, {}).get("ranges") or []:
            lines[rng["path"]] = lines.get(rng["path"], 0) + sum(b - a + 1 for a, b in rng["lines"])
    return [path for path, _ in sorted(lines.items(), key=lambda item: (-item[1], item[0]))]


def _short_names(paths) -> dict[str, str]:
    """The shortest trailing part of each path that no other path shares (``a/b.py``, ``b.py`` ...)."""
    split = {path: path.split("/") for path in set(paths)}
    depth = max((len(parts) for parts in split.values()), default=1)
    names: dict[str, str] = {}
    for width in range(1, depth + 1):
        count: dict[str, int] = {}
        for parts in split.values():
            key = "/".join(parts[-width:])
            count[key] = count.get(key, 0) + 1
        for path, parts in split.items():
            key = "/".join(parts[-width:])
            if path not in names and (count[key] == 1 or width >= len(parts)):
                names[path] = key
    return names


def _entry_page(*, repo: str, nodes: dict, children: dict, roots: list[str], units: dict, ranges_map: dict,
                overview: str | None, flows: list[dict], candidates: list[list[str]], graph_state: str,
                graph_reason: str, owner: dict, name_of: Callable[[str], str], budget: int) -> tuple[str, dict]:
    """INDEX.md: the module tree with one capability line per node, key flows, the three commands.

    The tree is drawn to its full depth. Over the token budget, every node first shows one file instead of
    three, then no file, and only then does the deepest level fold away (it stays on the node pages): the
    leaf modules are what a reader looks for, a representative file is only a hint."""
    from cbe.token_budget import count_text_tokens

    members: dict[str, list[str]] = {}

    def subtree(nid: str) -> list[str]:
        if nid not in members:
            members[nid] = list(nodes[nid].get("unit_ids") or [])
            for kid in children.get(nid) or []:
                members[nid] += subtree(kid)
        return members[nid]

    top = [kid for root in roots for kid in (children.get(root) or [])] or roots

    def depth(nid: str) -> int:
        return 1 + max((depth(kid) for kid in children.get(nid) or []), default=0)

    levels = max((depth(nid) for nid in top), default=1)
    ranked = {nid: _rank_files(units, ranges_map, subtree(nid)) for nid in nodes}
    short = _short_names(path for row in ranked.values() for path in row)

    def module_lines(nid: str, level: int, shown: int, files: int) -> list[str]:
        node = nodes[nid]
        names = [short[path] for path in ranked[nid][:files]]
        capability = literal_links((node.get("capability") or "").strip())
        rows = ["  " * level + f"- [**{link_text(node.get('title') or nid)}**](nodes/{nid}.md)"
                f"{' — ' + capability if capability else ''} "
                f"({len(subtree(nid))} units{'; ' if names else ''}{', '.join(inline_code(n) for n in names)})"]
        if level + 1 < shown:
            for kid in children.get(nid) or []:
                rows += module_lines(kid, level + 1, shown, files)
        return rows

    def flow_lines() -> list[str]:
        shown, rows = flows, []
        if not flows and candidates:
            rows += ["Program candidates, not selected by the model (first 5):"]
            shown = [dict(name=f"Candidate {i}", description="Extracted by the program from resolved calls.",
                          steps=path, inferred_steps=[]) for i, path in enumerate(candidates[:5], 1)]
        elif not flows:
            rows += ["No flows: " + (graph_reason if graph_state != "provided" else
                                     "no resolved calls or no entry units with zero incoming calls") + "."]
        for flow in shown:
            steps = []
            for i, uid in enumerate(flow["steps"]):
                if i:
                    steps.append(" → (model-inferred) → " if i in flow["inferred_steps"] else " → ")
                steps.append(inline_code(name_of(uid)) + ("" if owner.get(uid) in nodes else " (not assigned to a node)"))
            rows.append(f"- **{link_text(flow['name'])}**: {literal_links(flow['description'])} — " + "".join(steps))
        return rows

    def page(shown: int, files: int) -> str:
        lines = [f"# {repo}: code map", ""]
        if (overview or "").strip():
            lines += [literal_links(overview.strip()), ""]
        lines += ["## Modules", ""]
        for nid in top:
            lines += module_lines(nid, 0, shown, files)
        lines += ["", "## Key flows", ""] + flow_lines()
        lines += ["", "## Read further", "",
                  '`RUN` is this run directory. Find an `ID` by name, then read it:', "",
                  '- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name',
                  '- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit',
                  '- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked',
                  "", "More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)"]
        return "\n".join(lines) + "\n"

    ladder = [(levels, FILES_SHOWN), (levels, 1), (levels, 0)] + [(n, 0) for n in range(levels - 1, 0, -1)]
    for shown, files in ladder:
        text = page(shown, files)
        tokens = count_text_tokens(text)
        if tokens <= budget:
            break
    return text, {"budget": budget, "tokens": tokens, "over_budget": tokens > budget, "levels": levels,
                  "levels_shown": shown, "files_per_node": files}


@dataclass
class _RenderPrep:
    """Common preparation for the document writers ``render`` calls.

    Holds the node tree views, the rebuilt unit records, display names and the
    annotated relationship view, so each writer takes one object instead of
    sharing state through module globals."""
    run_dir: Path
    source_root: Path
    inventory: dict
    dispositions: dict
    tree: dict
    languages: dict[str, str]
    index_notes: list[str] | None
    system: dict | None
    graph: dict | None
    context: dict | None
    source_tokens: int | None
    docs_dir: Path
    nodes_dir: Path
    nodes: dict
    children: dict[str, list[str]]
    owner: dict[str, str]
    units: dict
    symbol_records: dict
    sources: dict[str, str]
    ranges_map: dict
    edge_table: dict
    names: dict
    relationships: dict
    labels: dict[str, str]
    edges_by_from: dict[str, list[dict]]
    edges_by_to: dict[str, list[dict]]
    _subtree_sizes: dict[str, int] = field(default_factory=dict)

    def subtree_units(self, nid: str) -> int:
        if nid not in self._subtree_sizes:
            self._subtree_sizes[nid] = len(self.nodes[nid].get("unit_ids") or []) \
                + sum(self.subtree_units(k) for k in self.children[nid])
        return self._subtree_sizes[nid]

    def name_of(self, uid: str) -> str:
        return self.names.get(uid, short_name(uid))

    def dependency_line(self, edge, target, prefix=""):
        return (f"- [{link_text(self.nodes[target].get('title') or target)}]({prefix}{target}.md) · "
                + (f"containment · → {edge['count']} / ← {edge['reverse_count']} edge(s) "
                   f"(ancestor direct units and descendant subtree; → follows {code_text(edge['from'])} → {code_text(edge['to'])})"
                   if edge["source"] == "containment" else
                   self.labels[edge["source"]]
                   + "".join(f" · {text}" for text in (
                       f"{edge['count']} edge(s)" if edge["count"] else "",
                       f"{edge.get('inferred_count', 0)} inferred relation(s)" if edge.get("inferred_count") else "") if text))
                + (" · " + literal_links(edge["description"]) if edge["description"] else ""))


def _prepare_render(*, run_dir: Path, source_root: Path, inventory: dict, units: dict,
                    dispositions: dict, tree: dict, languages: dict[str, str],
                    index_notes: list[str] | None = None, system: dict | None = None,
                    graph: dict | None = None, context: dict | None = None,
                    source_tokens: int | None = None) -> _RenderPrep:
    """Build the tree views, records, display names and relations every writer needs."""
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
            base = f"{Path(symbol['file']).name} module code (L{spans[0][0]}–L{spans[-1][1]})"
        if base in taken:
            base = f"{uid.split('::', 1)[0]}:{base}"
        name = base
        suffix = 2
        while name in taken:
            name = f"{base} ({suffix})"
            suffix += 1
        taken.add(name)
        names[uid] = name
    from cbe import aggregation
    unit_edges = aggregation.unit_edges(units, edge_table)
    relationships = aggregation.annotate_relationships(
        aggregation.relationship_view(tree, unit_edges, graph), system or {}, unit_edges)
    labels = {source: style[0] for source, style in DEPENDENCY_STYLES.items()}
    labels["within_containment"] = "within containment"
    edges_by_from: dict[str, list[dict]] = {nid: [] for nid in nodes}
    edges_by_to: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for edge in relationships["dependencies"]:
        edges_by_from[edge["from"]].append(edge)
        edges_by_to[edge["to"]].append(edge)
    return _RenderPrep(run_dir=run_dir, source_root=source_root, inventory=inventory,
                       dispositions=dispositions, tree=tree, languages=languages,
                       index_notes=index_notes, system=system, graph=graph, context=context,
                       source_tokens=source_tokens, docs_dir=docs_dir, nodes_dir=nodes_dir,
                       nodes=nodes, children=children, owner=owner, units=units,
                       symbol_records=symbol_records, sources=sources, ranges_map=ranges_map,
                       edge_table=edge_table, names=names, relationships=relationships,
                       labels=labels, edges_by_from=edges_by_from, edges_by_to=edges_by_to)


def _write_node_pages(prep: _RenderPrep) -> None:
    """One Markdown page per semantic node under ``docs/nodes``."""
    for nid, node in prep.nodes.items():
        source_links: dict[str, str] = {}
        lines = [f"# {node.get('title') or nid}", ""]
        if (node.get("capability") or "").strip():
            lines += [f"**Capability.** {literal_links(node['capability'].strip())}", ""]
        if (node.get("summary") or "").strip():
            lines += [literal_links(node['summary'].strip()), ""]
        if prep.children.get(nid):
            lines += ["**Children.**", ""]
            for kid in prep.children[nid]:
                kid_node = prep.nodes[kid]
                lines.append(f"- [{link_text(kid_node.get('title') or kid)}]({kid}.md) `{kid}` · "
                             f"{prep.subtree_units(kid)} unit(s)")
            lines.append("")
        if prep.edges_by_from.get(nid):
            lines += ["**Depends on.**", ""]
            for edge in prep.edges_by_from[nid]:
                lines.append(prep.dependency_line(edge, edge["to"]))
            lines.append("")
        if prep.edges_by_to.get(nid):
            lines += ["**Depended on by.**", ""]
            lines += [prep.dependency_line(edge, edge["from"]) for edge in prep.edges_by_to[nid]]
            lines.append("")
        parent = node.get("parent")
        if parent in prep.nodes:
            lines += [f"Parent: [{link_text(prep.nodes[parent].get('title') or parent)}]({parent}.md)", ""]
        own = node.get("unit_ids") or []
        if own:
            lines += [f"## Units ({len(own)})", ""]
        for uid in own:
            if uid not in prep.units:
                continue
            block = _build_unit_block(uid, prep.units, prep.owner, prep.dispositions,
                                     prep.nodes, prep.source_root, prep.name_of, source_links)
            lines += [f'<a id="{anchor(uid)}"></a>'] + block.splitlines() + [""]
        lines += ["## Look up code", "", '`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):',
                  '`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:',
                  '`cbe query --run-dir "$RUN" --id "$ID"`; '
                  '`cbe source --run-dir "$RUN" --id "$ID" --context 2`.', ""]
        lines += [f"[{ref}]: {os.path.relpath(prep.source_root / path, prep.nodes_dir)}"
                  for path, ref in source_links.items()]
        (prep.nodes_dir / f"{nid}.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _write_index(prep: _RenderPrep) -> dict:
    """INDEX.md, the module tree entry page (see ``_entry_page``)."""
    roots = [nid for nid, node in prep.nodes.items() if not node.get("parent")]
    index_text, index_meta = _entry_page(
        repo=prep.source_root.name, nodes=prep.nodes, children=prep.children, roots=roots,
        units=prep.units, ranges_map=prep.ranges_map,
        overview=(prep.system or {}).get("overview"), flows=prep.relationships["key_flows"],
        candidates=prep.relationships["candidate_flows"], graph_state=prep.relationships["graph_state"],
        graph_reason=prep.relationships["graph_reason"], owner=prep.owner, name_of=prep.name_of,
        budget=max(INDEX_MIN_TOKENS, int(INDEX_SHARE * (prep.source_tokens or 0))))
    (prep.docs_dir / "INDEX.md").write_text(index_text, encoding="utf-8")
    return index_meta


def _write_dependencies(prep: _RenderPrep) -> None:
    """DEPENDENCIES.md: the cross-node dependency list with a Mermaid diagram."""
    relationships = prep.relationships
    nodes = prep.nodes
    dependency_line = prep.dependency_line
    dep_lines = ["# Dependencies", "",
                 "Arrows point from a user to its dependency. Containment is structural, not a dependency. "
                 "Graph-confirmed pairs appear in both the tree and resolved call/import edges. "
                 "Model-inferred pairs appear only in the tree. Graph-only pairs appear only in the graph.",
                 "Graph-confirmed and model-inferred pairs count edges between two subtrees. "
                 "Graph-only pairs count edges between direct node owners. "
                 "Containment rows show resolved edges between ancestor direct units and a descendant subtree in both directions. "
                 "Within containment rows count direct owner pairs separately. Neither kind of containment row appears in Mermaid or the three dependency totals."]
    if relationships["graph_state"] != "provided":
        dep_lines += ["No usable graph evidence; only model-inferred dependencies are listed: " + relationships["graph_reason"] + "."]
    degree = {}
    for edge in relationships["dependencies"]:
        if edge.get("containment"):
            continue
        for endpoint in (edge["from"], edge["to"]):
            degree[endpoint] = degree.get(endpoint, 0) + 1
    selected = sorted(degree, key=lambda nid: (-degree[nid], nid))[:15]
    aliases = {nid: f"n{i}" for i, nid in enumerate(selected)}
    if selected:
        # Numeric Mermaid entity escapes protect quotes, brackets, markup and
        # fences; only safe program-generated aliases become Mermaid ids.
        def mermaid_label(text):
            return "".join(c if c.isalnum() or c in " _-" else f"#{ord(c)};" for c in text[:100])
        dep_lines += ["", "```mermaid", "flowchart LR"]
        dep_lines += [f'  {aliases[nid]}["{mermaid_label(nodes[nid].get("title") or nid)}"]'
                      for nid in selected]
        for edge in relationships["dependencies"]:
            if not edge.get("containment") and edge["from"] in aliases and edge["to"] in aliases:
                arrow = DEPENDENCY_STYLES[edge["source"]][1]
                dep_lines.append(f"  {aliases[edge['from']]} {arrow} {aliases[edge['to']]}")
        dep_lines += ["```", "", f"Selected {len(selected)} nodes by connection count. Legend: "
                      + "; ".join(f"`{arrow}` {label}" for label, arrow in DEPENDENCY_STYLES.values()) + "."]
    else:
        dep_lines += ["No node dependencies."]
    dep_lines += ["", "## Dependency list", ""]
    for edge in relationships["dependencies"]:
        if edge["source"] == "within_containment":
            continue
        dep_lines += [f"- [{link_text(nodes[edge['from']].get('title') or edge['from'])}]"
                      f"(nodes/{edge['from']}.md) → " + dependency_line(edge, edge["to"], "nodes/")[2:]]
    dep_lines += ["", f"Graph-only pairs are ranked by edge count; {relationships['graph_only_omitted']} omitted.",
                  "", "### Within containment", ""]
    for edge in relationships["dependencies"]:
        if edge["source"] == "within_containment":
            dep_lines += [f"- [{link_text(nodes[edge['from']].get('title') or edge['from'])}]"
                          f"(nodes/{edge['from']}.md) → " + dependency_line(edge, edge["to"], "nodes/")[2:]]
    dep_lines += ["", f"Within containment: {relationships['within_containment_count']} pairs, ranked by edge count; "
                  f"{relationships['within_containment_omitted']} omitted. Each graph list keeps at most 40 pairs independently."]
    if not (prep.system or {}).get("dependency_descriptions"):
        dep_lines += ["", "The system response provided no key dependency descriptions."]
    (prep.docs_dir / "DEPENDENCIES.md").write_text("\n".join(dep_lines) + "\n", encoding="utf-8")


def _write_run(prep: _RenderPrep) -> None:
    """RUN.md: where this run's facts come from and what was and was not checked."""
    run_lines = ["# Run notes", "", "Where this run's facts come from and what was and was not checked.", "",
                 "## Reading stats", "",
                 f"- units: {len(prep.units)} · semantic nodes: {len(prep.nodes)} · "
                 f"dispositioned inventory ids: {len(prep.dispositions)}",
                 "- source ranges are program-derived from the inventory, never model-written",
                 "", "## Graph coverage", ""] + _graph_coverage(prep.graph, prep.source_root)
    if prep.index_notes:
        run_lines += ["", "## Generation notes", ""] + [f"- {item}" for item in prep.index_notes]
    (prep.docs_dir / "RUN.md").write_text("\n".join(run_lines) + "\n", encoding="utf-8")


def _write_catalog(prep: _RenderPrep) -> dict:
    """``catalog.json``: semantic index plus the per-id ``symbols`` and per-file ``files`` maps."""
    units, owner, nodes = prep.units, prep.owner, prep.nodes
    symbol_index: dict[str, dict] = {}
    for uid in sorted(units):
        node = owner.get(uid)
        symbol_index[uid] = {"how": "unit", "unit": uid, "node": node,
                             "page": f"nodes/{node}.md" if node in nodes else None,
                             "anchor": f"#{anchor(uid)}"}
    for key in sorted(prep.dispositions):
        if key in symbol_index:
            continue
        entry = prep.dispositions[key]
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

    catalog_symbol_rows: dict[str, dict] = {}
    catalog_file_rows: dict[str, dict] = {}
    for path, entry in prep.inventory.items():
        facts = concrete_facts.file_facts(path, prep.sources.get(path, "")) \
            if path.endswith(".py") else None
        catalog_file_rows[path] = {"tokens": entry.get("tokens", 0),
                                   "language": prep.languages.get(path, "unknown"),
                                   "known_empty": bool(entry.get("known_empty")),
                                   "ranges": [{"path": path, "lines": [[1, max(1, len(prep.sources.get(path, '').splitlines()))]]}],
                                   "signatures": [{"id": sid, "signature": row["signature"]}
                                                  for sid, row in prep.symbol_records.items() if row["file"] == path]}
        if facts and facts.get("file"):
            catalog_file_rows[path]["facts"] = facts["file"]
        for symbol in entry["symbols"]:
            record: dict[str, Any] = {**prep.symbol_records[symbol["id"]], "file": path, "name": symbol["name"],
                                      **symbol_index.get(symbol["id"], {"node": None, "page": None})}
            parts = symbol["id"].split("::")
            fact_name = parts[2] if symbol.get("kind") == "method" and len(parts) > 2 else symbol["name"]
            if facts and facts["symbols"].get(fact_name):
                record["facts"] = facts["symbols"][fact_name]
            catalog_symbol_rows[symbol["id"]] = record

    relationships = prep.relationships
    catalog = {
        "schema": SCHEMA, "project": "Codebase Explorer", "version": "",
        "units": {uid: {**units[uid], "node": owner.get(uid),
                        "page": f"nodes/{owner[uid]}.md" if owner.get(uid) in nodes else None,
                        "anchor": f"#{anchor(uid)}"} for uid in sorted(units)},
        "edges": prep.edge_table,
        "graph": None if (prep.context or {}).get("graph") is not None else prep.graph,
        "graph_ref": "context.json" if (prep.context or {}).get("graph") is not None else None,
        "nodes": {nid: {"parent": node.get("parent"), "children": prep.children.get(nid) or [],
                        "unit_ids": node.get("unit_ids") or [], "title": node.get("title"),
                        "capability": node.get("capability"), "summary": node.get("summary")}
                  for nid, node in sorted(nodes.items())},
        "depends_on": prep.tree.get("depends_on") or [],
        "node_dependencies": relationships["dependencies"],
        "relationships": {k: v for k, v in relationships.items() if k not in {"dependencies", "key_flows"}},
        "key_flows": relationships["key_flows"],
        "dispositions": prep.dispositions,
        "symbol_index": symbol_index,
        "inventory": prep.inventory,
        "short_names": prep.names,
        "symbols": catalog_symbol_rows,
        "files": catalog_file_rows,
    }
    (prep.run_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    return symbol_index


def render(*, run_dir: Path, source_root: Path, inventory: dict, units: dict,
           dispositions: dict, tree: dict, languages: dict[str, str],
           index_notes: list[str] | None = None, system: dict | None = None,
           graph: dict | None = None, context: dict | None = None, source_tokens: int | None = None) -> dict:
    """Render node pages, INDEX.md, DEPENDENCIES.md, RUN.md and a catalog under ``run_dir/docs``.

    ``languages`` maps each path to the language frozen in the source context,
    so the catalog agrees with the plan even when it remapped a suffix.

    Returns metadata the caller stores in run state for verification."""
    prep = _prepare_render(run_dir=run_dir, source_root=source_root, inventory=inventory,
                           units=units, dispositions=dispositions, tree=tree, languages=languages,
                           index_notes=index_notes, system=system, graph=graph, context=context,
                           source_tokens=source_tokens)
    _write_node_pages(prep)
    index_meta = _write_index(prep)
    _write_dependencies(prep)
    _write_run(prep)
    symbol_index = _write_catalog(prep)
    return {"units_rendered": len(prep.units), "nodes": len(prep.nodes), "owner": prep.owner,
            "relationship_counts": prep.relationships["counts"],
            "within_containment_count": prep.relationships["within_containment_count"],
            "key_flows": len(prep.relationships["key_flows"]),
            "candidate_flows": len(prep.relationships["candidate_flows"]),
            "ranges_map": prep.ranges_map, "symbol_index": symbol_index,
            "index": {**index_meta, "path": str(prep.docs_dir / "INDEX.md")}}


def _map_prose(text: str, prose: Callable[[str], str], code: Callable[[str], str]) -> str:
    """Map prose and code separately, respecting fences and paired code spans."""
    paragraphs = []
    pending = []
    fence = None

    def flush():
        paragraph = "".join(pending)
        parts, start = [], 0
        for match in re.finditer(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", paragraph, re.DOTALL):
            parts.extend((prose(paragraph[start:match.start()]), code(match[0])))
            start = match.end()
        parts.append(prose(paragraph[start:]))
        paragraphs.append("".join(parts))
        pending.clear()

    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            paragraphs.append(code(line))
            continue
        if marker and (marker[1][0] != "`" or "`" not in marker[2]):
            flush()
            fence = marker[1]
            paragraphs.append(code(line))
        elif not line.strip():
            flush()
            paragraphs.append(line)
        elif line.startswith(("    ", "\t")) and not pending:
            paragraphs.append(code(line))
        else:
            pending.append(line)
    flush()
    return "".join(paragraphs)


def literal_links(text: str) -> str:
    """Keep model-written inline links as visible text; code stays verbatim.

    Source and navigation links are generated separately by the renderer.
    Escaping the opening parenthesis prevents accidental Markdown links such
    as ``environ['werkzeug.debug.preserve_context'](ctx)``.
    """
    return _map_prose(text, lambda part: part.replace("](", r"]\("), lambda part: part)


def prose_for_links(text: str) -> str:
    """Hide code blocks and paired code spans within each prose paragraph."""
    return _map_prose(text, lambda part: part, lambda part: "")


def _add_check(checks: list[dict], name: str, ok: bool, detail: Any = None) -> None:
    checks.append({"check": name, "ok": bool(ok),
                   **({"detail": detail} if detail is not None else {})})


def _verify_catalog(checks: list[dict], run_dir: Path, inventory: dict, units: dict,
                    dispositions: dict, owner: dict, nodes: dict, inv_ids: set,
                    page_texts: dict) -> None:
    """The catalog-related checks: every file listed, every navigation target reachable."""
    catalog_path = run_dir / "catalog.json"
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        listed = set(catalog.get("files") or {})
        missing = sorted(set(inventory) - listed)
        known_empty_missing = sorted(path for path, entry in inventory.items()
                                     if entry.get("known_empty")
                                     and not (catalog.get("files") or {}).get(path, {}).get("known_empty"))
        _add_check(checks, "catalog_lists_every_file", not missing and not known_empty_missing,
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
        _add_check(checks, "catalog_navigation_resolves", not navigation_errors,
                   {"checked": len(inv_ids | set(units)), "broken": navigation_errors[:12]})
    else:
        _add_check(checks, "catalog_lists_every_file", False, "catalog.json is missing")
        _add_check(checks, "catalog_navigation_resolves", False, "catalog.json is missing")


def verify(run_dir: Path, inventory: dict, units: dict, dispositions: dict,
           tree: dict) -> list[dict]:
    """Deterministic structural/coverage checks for the semantic artifact.

    These check identity, coverage and ownership. They do NOT judge prose
    quality or whether an explanation is true; that stays with an independent
    review of the source, and a run that passes here is not thereby
    semantically verified."""
    checks: list[dict] = []

    inv_ids = set(inventory_ids(inventory))
    missing = sorted(inv_ids - set(dispositions))
    broken = [key for key, entry in dispositions.items()
              if (entry or {}).get("how") in {"unit", "grouped"}
              and entry.get("unit") not in units]
    _add_check(checks, "semantic_dispositions_cover_inventory", not missing and not broken,
               {"inventory_ids": len(inv_ids), "missing": missing[:12], "broken": broken[:12]})

    nodes = {node["id"]: node for node in tree.get("nodes") or []}
    owner: dict[str, str] = {}
    dupes = []
    for nid, node in nodes.items():
        for uid in node.get("unit_ids") or []:
            if uid in owner:
                dupes.append(f"{uid}:{owner[uid]}+{nid}")
            owner[uid] = nid
    _add_check(checks, "unique_primary_ownership", not dupes and set(units) <= set(owner),
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
    _add_check(checks, "tree_single_root_acyclic_reachable",
               len(roots) == 1 and not cycle and seen == set(nodes),
               {"nodes": len(nodes), "roots": roots, "cycle": cycle,
                "unreachable": sorted(set(nodes) - seen)[:12]})
    hollow = sorted(nid for nid, node in nodes.items() if not node.get("unit_ids") and not children[nid])
    _add_check(checks, "no_empty_nodes", not hollow or not units, hollow[:12])
    clashes = [f"{kid}: {nodes[kid].get('title')!r}" for kids in children.values()
               for i, kid in enumerate(kids)
               if normalize_title(str(nodes[kid].get("title"))) in
               {normalize_title(str(nodes[other].get("title"))) for other in kids[:i]}]
    _add_check(checks, "sibling_titles_distinct", not clashes, clashes[:12])

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
    _add_check(checks, "unit_ranges_present_and_inbounds", not bad_ranges, bad_ranges[:12])

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
    _add_check(checks, "relative_links_resolve", not broken_links,
               {"checked": len(links), "broken": broken_links[:12]})
    _verify_catalog(checks, run_dir, inventory, units, dispositions, owner, nodes,
                    inv_ids, page_texts)
    _add_check(checks, "semantic_rendered", (docs / "INDEX.md").is_file() and (run_dir / "catalog.json").is_file())
    return checks
