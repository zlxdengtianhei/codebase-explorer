"""Published documents and their index: node pages, INDEX, catalog, structural checks, queries.

The program writes every source range and anchor; the model writes only the
explanations. ``verify`` checks identity, coverage, ownership and navigation;
it does not judge whether an explanation is true.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from cbe import concrete_facts, page_budget
from cbe.catalog_query import query_catalog
from cbe.symbols import SemanticError, inventory_ids
from cbe.token_budget import count_text_tokens
from cbe.treename import normalize_title

# One repository file larger than this becomes its own inventory unit region set;
# a chunk never has to fit a model context alone because batches group many.
SCHEMA = "cbe-semantic/1"
DEPENDENCY_STYLES = {"graph_confirmed": ("graph-confirmed", "-->"),
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


def _build_unit_block(uid: str, units: dict, name_of: Callable[[str], str]) -> str:
    """One unit's page block: the name, then prose only (design 2.4)."""
    unit = units[uid]
    from cbe.records import summary_and_remainder

    lines = [f"### `{name_of(uid)}`", ""]
    summary, explain = summary_and_remainder(unit)
    if summary:
        lines += [literal_links(summary), ""]
    if explain:
        lines += [literal_links(explain), ""]
    if unit.get("ungrounded"):
        lines += [f"check: names {', '.join(unit['ungrounded'])}, not found in this unit's source", ""]
    extras = [extra for extra in unit.get("extras") or []
              if isinstance(extra, dict) and isinstance(extra.get("note"), str)
              and extra["note"].strip()]
    if extras:
        lines += ["**Notes.**", ""]
        lines += [f"- {extra.get('topic')}: {literal_links(extra['note'].strip())}" for extra in extras]
        lines.append("")
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
        lines += ["No graph was provided. This run has no call or import edges: DEPENDENCIES.md "
                  "lists nothing and the catalog carries no edge table."]
    else:
        from cbe.graph import read_graph_quality, graph_state
        quality = read_graph_quality(graph)
        state, _ = graph_state(graph, quality=quality)
        if state == "failed":
            lines += ["No graph backend succeeded, so this run has no call or import edges."]
        elif state == "empty":
            lines += ["The graph is empty: it has no call or import edges."]
        elif state == "unsupported":
            lines += ["The graph does not support this analysis, so this run has no call or import edges."]
        else:
            lines += ["Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. "
                            "External targets are outside the repository; ambiguous targets have multiple candidates. "
                            "Unresolved or unsupported relations, and languages or relation kinds without coverage, "
                            "are listed with their status and are not published as edges."]
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


INDEX_BUDGET = 1500      # tokens the entry page may use before it drops to one level
INDEX_SHOWN_LEVELS = 2   # top-level groups, then one line per child
FILES_SHOWN = 5          # kept for callers that want the old abridged line; pages name every file


def member_files(unit_ids: list[str], symbol_records: dict) -> list[tuple[str, int]]:
    """Files a leaf page's members live in, most members first, then by path."""
    counts: dict[str, int] = {}
    for uid in unit_ids:
        file = (symbol_records.get(uid) or {}).get("file") or (uid.split("::", 1)[0] if "::" in uid else "")
        if file:
            counts[file] = counts.get(file, 0) + 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))


def files_line(counts: list[tuple[str, int]], shown: int | None = None) -> str:
    """The line under a page's title: every file its members live in, most members first.

    The names are the reader's only way to reach a file from a page (a 3.0 experiment
    caught a model guessing paths on pages that carried none), and a page now covers
    several groups, so the list is not abridged by default. ``shown`` keeps the older
    five-name cut for callers that ask for it."""
    listed = counts if shown is None else counts[:shown]
    line = "Files: " + ", ".join(f"`{path}`" for path, _ in listed)
    if len(counts) > len(listed):
        line += f" and {len(counts) - len(listed)} more ({len(counts)} files)"
    return line + "."


def _node_prose(prep: _RenderPrep, nid: str) -> list[str]:
    """A node's own capability and summary lines, as its page prints them."""
    node = prep.nodes[nid]
    lines: list[str] = []
    if (node.get("capability") or "").strip():
        lines += [literal_links(node["capability"].strip()), ""]
    if (node.get("summary") or "").strip():
        lines += [literal_links(node["summary"].strip()), ""]
    return lines


def _unit_lines(prep: _RenderPrep, nid: str) -> list[str]:
    """The unit explanations one node owns, each as its own block."""
    lines: list[str] = []
    for uid in prep.nodes[nid].get("unit_ids") or []:
        if uid in prep.units:
            lines += _build_unit_block(uid, prep.units, prep.name_of).splitlines() + [""]
    return lines


def page_text(prep: _RenderPrep, root: str, members: tuple[str, ...] = ()) -> str:
    """One published page: the root node, then a section per further node it prints.

    ``members`` names the other nodes printed here; their own units come with
    them. A child that is not printed keeps its own page at ``nodes/<child>.md``
    in both page modes, so a link needs no plan state and the page's token count
    can be measured before the plan is final.
    """
    printed = [root, *members]
    unit_ids = [uid for nid in printed for uid in prep.nodes[nid].get("unit_ids") or []
                if uid in prep.units]
    lines = [f"# {prep.nodes[root].get('title') or root}", ""]
    counts = member_files(unit_ids, prep.symbol_records)
    if counts:
        lines += [files_line(counts), ""]
    seen_titles: dict[str, str] = {str(prep.nodes[root].get("title") or root): root}
    for level, nid in enumerate(printed):
        node = prep.nodes[nid]
        title = str(node.get("title") or nid)
        if level:
            heading = title
            if title in seen_titles:
                # Two nodes of one page share a title: the parent tells them apart.
                parent = prep.nodes.get(node.get("parent") or "") or {}
                heading = f"{title} ({parent.get('title') or parent.get('id') or 'same level'})"
            seen_titles[title] = nid
            lines += [f"## {heading}", ""]
        lines += _node_prose(prep, nid)
        left = [kid for kid in prep.children.get(nid) or [] if kid not in printed]
        if left:
            lines += ["**Children.**", ""]
            for kid in left:
                kid_node = prep.nodes[kid]
                capability = literal_links((kid_node.get("capability") or "").strip())
                lines.append(f"- [{link_text(kid_node.get('title') or kid)}]({kid}.md)"
                             + (f" — {capability}" if capability else ""))
            lines.append("")
        lines += _unit_lines(prep, nid)
    return "\n".join(lines).strip() + "\n"


def subtree_text(catalog: dict, nid: str, depth: int | None = None) -> str:
    """The text of the pages for one node and the nodes below it (``depth`` levels, all when
    None), built from ``catalog.json`` alone: what ``cbe query --id NODE --units`` prints."""
    from types import SimpleNamespace

    names = catalog.get("short_names") or {}
    children = {kid: row.get("children") or [] for kid, row in catalog["nodes"].items()}
    inventory_ids = {row["id"] for entry in catalog["inventory"].values() for row in entry["symbols"]}
    prep = SimpleNamespace(nodes=catalog["nodes"], children=children, units=catalog["units"],
                           symbol_records={sid: row for sid, row in catalog["symbols"].items()
                                           if sid in inventory_ids},
                           name_of=lambda uid: names.get(uid, short_name(uid)))
    return page_text(prep, nid, page_budget.descendants(children, nid, depth))


def _entry_page(*, repo: str, nodes: dict, children: dict, roots: list[str],
                overview: str | None, owner: dict, name_of: Callable[[str], str],
                budget: int = INDEX_BUDGET, build: bool = False,
                pages: page_budget.PagePlan | None = None) -> tuple[str, dict]:
    """INDEX.md: the overview, the module tree two levels deep (top-level groups, then one
    capability line per child), and the three commands written once (design 2.4). No file lists,
    unit counts or flows: structure lives in DEPENDENCIES.md and the catalog, not in the reading
    path.

    A page over ``budget`` tokens keeps the top level only and says why; deeper levels stay on the
    node pages."""
    from cbe.token_budget import count_text_tokens

    top = [kid for root in roots for kid in (children.get(root) or [])] or roots

    def depth(nid: str) -> int:
        return 1 + max((depth(kid) for kid in children.get(nid) or []), default=0)

    levels = max((depth(nid) for nid in top), default=1)

    def module_lines(nid: str, level: int, shown: int) -> list[str]:
        node = nodes[nid]
        capability = literal_links((node.get("capability") or "").strip())
        href = f"nodes/{pages.page_of(nid) if pages else nid}.md"
        rows = ["  " * level + f"- [**{link_text(node.get('title') or nid)}**]({href})"
                + (f" — {capability}" if capability else "")]
        if level + 1 < shown:
            for kid in children.get(nid) or []:
                rows += module_lines(kid, level + 1, shown)
        return rows

    def page(shown: int, two_level_tokens: int | None = None) -> str:
        lines = [f"# {repo}: code map", ""]
        if (overview or "").strip():
            lines += [literal_links(overview.strip()), ""]
        lines += ["## Modules", ""]
        if pages and pages.mode == "budget" and len(pages.pages) < len(nodes):
            lines += [f"Pages are cut by a {pages.budget:,}-token budget: one page may carry several "
                      "groups, printed on it as sections.", ""]
        for nid in top:
            lines += module_lines(nid, 0, shown)
        if two_level_tokens is not None:
            lines += ["", f"Two levels would take about {two_level_tokens:,} tokens, over this page's "
                      f"{budget:,}-token budget, so only the top level is listed here. "
                      "Each page lists the children it does not print."]
        lines += ["", "## Read further", "",
                  "`RUN` is this run directory. Signatures, call edges and source are looked up here, "
                  "not printed on the pages:", "",
                  '- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name',
                  '- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit',
                  '- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked',
                  *(["", "How to install, build, package, integrate and migrate, from the README, docs and "
                     "build manifests: [BUILD.md](BUILD.md)"] if build else []),
                  "", "More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)"]
        return "\n".join(lines) + "\n"

    shown = min(INDEX_SHOWN_LEVELS, levels)
    text = page(shown)
    tokens = count_text_tokens(text)
    if tokens > budget and shown > 1:
        shown = 1
        text = page(1, two_level_tokens=tokens)
        tokens = count_text_tokens(text)
    return text, {"budget": budget, "tokens": tokens, "over_budget": tokens > budget, "levels": levels,
                  "levels_shown": shown}


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
    overview: dict | None
    graph: dict | None
    context: dict | None
    basis: dict | None
    source_tokens: int | None
    read_budget: dict | None
    clustering: dict | None
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
    pages: page_budget.PagePlan = None  # type: ignore[assignment]  # set by attach_pages

    def name_of(self, uid: str) -> str:
        return self.names.get(uid, short_name(uid))

    def page_link(self, nid: str, prefix: str = "") -> str:
        """Link to the page that prints this node; a node printed as a section of a bigger
        page is found by its heading there (pages carry no anchors, design 2.4)."""
        return f"{prefix}{self.pages.page_of(nid)}.md"

    def dependency_line(self, edge, target, prefix=""):
        return (f"- [{link_text(self.nodes[target].get('title') or target)}]({self.page_link(target, prefix)}) · "
                + (f"containment · → {edge['count']} / ← {edge['reverse_count']} edge(s) "
                   f"(ancestor direct units and descendant subtree; → follows {code_text(edge['from'])} → {code_text(edge['to'])})"
                   if edge["source"] == "containment" else
                   self.labels[edge["source"]]
                   + (f" · {edge['count']} edge(s)" if edge["count"] else ""))
                + (" · " + literal_links(edge["description"]) if edge["description"] else ""))


def _prepare_render(*, run_dir: Path, source_root: Path, inventory: dict, units: dict,
                    dispositions: dict, tree: dict, languages: dict[str, str],
                    index_notes: list[str] | None = None, overview: dict | None = None,
                    graph: dict | None = None, context: dict | None = None, basis: dict | None = None,
                    source_tokens: int | None = None, read_budget: dict | None = None,
                    clustering: dict | None = None) -> _RenderPrep:
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
    for uid in sorted(units):
        symbol = symbol_records.get(uid, {})
        base = symbol.get("name") or short_name(uid)
        parts = uid.split("::")
        if symbol.get("kind") == "method" and len(parts) > 2 and "." in parts[2]:
            base = parts[2]
        if "::module_residual::" in uid or symbol.get("kind") == "module_residual":
            # A file's leftover regions have no symbol name: the file is the name.
            base = f"{Path(symbol.get('file') or uid.split('::', 1)[0]).name} module code"
        if units[uid].get("pieces"):
            base = units[uid]["title"]  # the whole of a cut unit is named by its title, not its id
        elif units[uid].get("piece"):
            piece = units[uid]["piece"]
            label = piece["first"] if piece["first"] == piece["last"] else f"{piece['first']}-{piece['last']}"
            base = f"{base.split(' (part ')[0]} (part {label} of {piece['count']})"
        if base in taken:
            # Same name twice in the repository: the file tells them apart, then a number.
            file = Path(symbol.get("file") or uid.split("::", 1)[0]).name
            stem = f"{base} ({file})" if file else base
            base, extra = stem, 2
            while base in taken:
                base, extra = f"{stem} {extra}", extra + 1
        name = base
        suffix = 2
        while name in taken:
            name = f"{base} ({suffix})"
            suffix += 1
        taken.add(name)
        names[uid] = name
    from cbe import aggregation
    unit_edges = aggregation.unit_edges(units, edge_table)
    relationships = aggregation.relationship_view(tree, unit_edges, graph)
    labels = {source: style[0] for source, style in DEPENDENCY_STYLES.items()}
    labels["within_containment"] = "within containment"
    edges_by_from: dict[str, list[dict]] = {nid: [] for nid in nodes}
    edges_by_to: dict[str, list[dict]] = {nid: [] for nid in nodes}
    for edge in relationships["dependencies"]:
        edges_by_from[edge["from"]].append(edge)
        edges_by_to[edge["to"]].append(edge)
    return _RenderPrep(run_dir=run_dir, source_root=source_root, inventory=inventory,
                       dispositions=dispositions, tree=tree, languages=languages,
                       index_notes=index_notes, overview=overview, graph=graph, context=context, basis=basis,
                       source_tokens=source_tokens, read_budget=read_budget, clustering=clustering,
                       docs_dir=docs_dir, nodes_dir=nodes_dir,
                       nodes=nodes, children=children, owner=owner, units=units,
                       symbol_records=symbol_records, sources=sources, ranges_map=ranges_map,
                       edge_table=edge_table, names=names, relationships=relationships,
                       labels=labels, edges_by_from=edges_by_from, edges_by_to=edges_by_to)


def attach_pages(prep: _RenderPrep, *, mode: str, budget: int) -> page_budget.PagePlan:
    """Cut the frozen tree into pages and keep the plan on ``prep``.

    ``cost`` measures the page text this renderer would write, so a page's token
    count in the plan is the count of the bytes that land on disk."""
    roots = [nid for nid, node in prep.nodes.items() if not node.get("parent")]
    plan = page_budget.plan_pages(
        nodes=prep.nodes, children=prep.children, roots=roots, budget=budget, mode=mode,
        cost=lambda root, members: count_text_tokens(page_text(prep, root, members)))
    prep.pages = plan
    return plan


def _write_node_pages(prep: _RenderPrep) -> None:
    """One Markdown page per entry in the page plan under ``docs/nodes``.

    A page carries the title, the files all its members live in, the prose of the
    node it is rooted at, and a section per covered subtree (see ``page_text``).
    Signatures, line links and repeated commands stay off the pages (design 2.4);
    the commands are written once in INDEX.md."""
    for page in prep.pages.pages:
        text = page_text(prep, page.root, page.members)
        (prep.nodes_dir / f"{page.root}.md").write_text(text, encoding="utf-8")


def _write_index(prep: _RenderPrep, build: bool = False) -> dict:
    """INDEX.md, the module tree entry page (see ``_entry_page``)."""
    roots = [nid for nid, node in prep.nodes.items() if not node.get("parent")]
    index_text, index_meta = _entry_page(
        repo=prep.source_root.name, nodes=prep.nodes, children=prep.children, roots=roots,
        overview=(prep.overview or {}).get("overview"), owner=prep.owner, name_of=prep.name_of,
        build=build, pages=prep.pages)
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
                 "Graph-only pairs appear only in the graph.",
                 "Graph-confirmed pairs count edges between two subtrees. "
                 "Graph-only pairs count edges between direct node owners. "
                 "Containment rows show resolved edges between ancestor direct units and a descendant subtree in both directions. "
                 "Within containment rows count direct owner pairs separately. Neither kind of containment row appears in Mermaid or the three dependency totals."]
    if relationships["graph_state"] != "provided":
        dep_lines += ["No usable graph evidence, so no dependency pairs are listed: " + relationships["graph_reason"] + "."]
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
                      f"({prep.page_link(edge['from'], 'nodes/')}) → " + dependency_line(edge, edge["to"], "nodes/")[2:]]
    dep_lines += ["", f"Graph-only pairs are ranked by edge count; {relationships['graph_only_omitted']} omitted.",
                  "", "### Within containment", ""]
    for edge in relationships["dependencies"]:
        if edge["source"] == "within_containment":
            dep_lines += [f"- [{link_text(nodes[edge['from']].get('title') or edge['from'])}]"
                          f"({prep.page_link(edge['from'], 'nodes/')}) → " + dependency_line(edge, edge["to"], "nodes/")[2:]]
    dep_lines += ["", f"Within containment: {relationships['within_containment_count']} pairs, ranked by edge count; "
                  f"{relationships['within_containment_omitted']} omitted. Each graph list keeps at most 40 pairs independently."]
    (prep.docs_dir / "DEPENDENCIES.md").write_text("\n".join(dep_lines) + "\n", encoding="utf-8")


def models_line(models: list[str]) -> str:
    """RUN.md's model line; host runs learn their models only from ``cbe host import-usage``."""
    return "- Models: " + (", ".join(f"`{model}`" for model in models)
                           or "not recorded (run `cbe host import-usage`)")


def _basis_lines(basis: dict) -> list[str]:
    lines = [f"- CBE version: `{basis['cbe_version']}`",
             models_line(basis["models"]),
             f"- Source: {basis['source']['files']} files · SHA-256 `{basis['source']['sha256']}`"]
    graph = basis["graph"]
    if graph is None:
        return lines + ["- Graph: none"]
    backend = graph.get("backend") or {}
    edges = ", ".join(f"{kind}={count}" for kind, count in graph["edge_counts"].items()) or "none"
    replaced = f"yes, latest {graph['updated_at']}" if graph["updated"] else "no"
    tools = ", ".join(f"`{part.get('name')}` {part.get('version') or 'version unknown'}"
                      for part in backend.get("components") or [backend]) or "unknown"
    return lines + [f"- Graph: SHA-256 `{graph['digest']}` · built by {tools} · edges {edges} · replaced {replaced}"]


def _write_run(prep: _RenderPrep) -> None:
    """RUN.md: where this run's facts come from and what was and was not checked."""
    run_lines = ["# Run notes", "", "Where this run's facts come from and what was and was not checked.", ""]
    if prep.basis is not None:
        run_lines += ["## Generation basis", "", *_basis_lines(prep.basis), ""]
    run_lines += ["## Reading stats", "",
                  f"- units: {len(prep.units)} · semantic nodes: {len(prep.nodes)} · "
                  f"dispositioned inventory ids: {len(prep.dispositions)}",
                  "- source ranges are program-derived from the inventory, never model-written",
                  "", "## Graph coverage", ""] + _graph_coverage(prep.graph, prep.source_root)
    if prep.read_budget:
        budget = prep.read_budget
        run_lines += ["", "## Read budget", "",
                      f"- Prompts built for a model: {budget['read_tokens']} tokens "
                      f"(ratio to source {budget['read_ratio']}; target 2.0)",
                      f"- Of which embedded source: {budget['source_read_tokens']} tokens "
                      f"(ratio {budget['source_read_ratio']}; target 1.2)",
                      "- By task: " + ", ".join(f"{kind} {count}" for kind, count in
                                                budget["read_by_kind"].items()),
                      *([f"- Provider receipts: {budget['provider_read_tokens']} tokens "
                         f"(input + cache, ratio to source {budget['provider_read_ratio']})"]
                        if budget.get("provider_read_tokens") else []),
                      *(["- Output tokens by task: "
                         + ", ".join(f"{kind} {count}" for kind, count in
                                     (budget.get("output_by_kind") or {}).items())]
                        if budget.get("output_by_kind") else []),
                      f"- Basis: {budget['basis']}"]
        length = budget.get("explain_length") or {}
        if length:
            run_lines += [f"- Detail length: {length.get('units_asked_again', 0)} explanation(s) over their cap "
                          f"were sent back once for a shorter one that keeps the conditions "
                          f"({length.get('asked_again', 0)} ask(s)); the program cut "
                          f"{length.get('truncated', 0)} at a sentence end"]
        if budget.get("gate_hit"):
            run_lines += ["- The 1.5x source hard gate was reached; the unexplained list below is the rest."]
    docs_tokens = sum(count_text_tokens(path.read_text(encoding="utf-8"))
                      for path in sorted(prep.docs_dir.rglob("*.md")))
    ratio = docs_tokens / prep.source_tokens if prep.source_tokens else None
    run_lines += ["", "## Pages", "",
                  f"- Published Markdown: {docs_tokens} tokens"
                  + (f" (ratio to source {ratio:.2f}; target 0.6, hard 0.7)" if ratio is not None else "")]
    plan = prep.pages
    run_lines += [f"- Page boundary: " + (
        f"cut at render time by a {plan.budget:,}-token budget, not written by the model: "
        f"{len(plan.pages)} page(s) for {len(prep.nodes)} tree node(s)" if plan.mode == "budget"
        else f"one page per tree node ({len(plan.pages)} page(s))")]
    if plan.mode == "budget":
        over = plan.over_budget
        run_lines += [f"- Pages over the budget: {len(over)}" + "".join(
            f"; `{page.root}` {page.tokens:,} tokens ({page.over_budget})" for page in over[:8])]
    if prep.clustering:
        run_lines += ["", "## Clustering", ""] + _clustering_lines(prep.clustering)
    if prep.index_notes:
        run_lines += ["", "## Generation notes", ""] + [f"- {item}" for item in prep.index_notes]
    (prep.docs_dir / "RUN.md").write_text("\n".join(run_lines) + "\n", encoding="utf-8")


def _clustering_lines(clustering: dict) -> list[str]:
    """RUN.md's clustering lines: the layers, what the program cut or merged, and the graph.

    Design 2.3: the reader must see where the structure is the model's and where the
    program had to step in, and whether call counts were available at all."""
    lines: list[str] = []
    for row in clustering.get("layers") or []:
        line = (f"- Layer {row['level']}: {row['groups']} group(s) from {row['tasks']} task(s)"
                + (f"; {row['program_made']} program-made" if row.get("program_made") else "")
                + (f"; {row['parts']} part(s) cut by the program" if row.get("parts") else ""))
        if row.get("retried"):
            line += (f"; {row['retried']} oversized answer(s) were sent back once for division by function")
        if row.get("merged"):
            line += f"; {len(row['merged'])} group(s) merged by the program"
        lines.append(line)
        for item in row.get("split") or []:
            lines.append(f"  - program cut: {item}")
        for item in row.get("merged") or []:
            lines.append(f"  - program merge: {item}")
        for item in row.get("fallback") or []:
            lines.append(f"  - program-made grouping: {item}")
    if not lines:
        lines.append("- No grouping layer ran.")
    if clustering.get("graph"):
        lines.append("- Call counts came from the analysis graph; group blocks showed the call "
                     "counts in and out, and a group with no calls inside is noted.")
    else:
        lines.append("- No graph was provided to this run, so the grouping blocks carried no call "
                     "counts: the group-internal call note and the shared-utility hint did not apply.")
    return lines


def _write_catalog(prep: _RenderPrep) -> dict:
    """``catalog.json``: semantic index plus the per-id ``symbols`` and per-file ``files`` maps."""
    units, owner, nodes = prep.units, prep.owner, prep.nodes
    plan = prep.pages

    def page_of(node: str | None) -> str | None:
        return f"nodes/{plan.page_of(node)}.md" if node in nodes else None

    symbol_index: dict[str, dict] = {}
    for uid in sorted(units):
        node = owner.get(uid)
        symbol_index[uid] = {"how": "unit", "unit": uid, "node": node,
                             "page": page_of(node),
                             "anchor": f"#{anchor(uid)}"}
    for key in sorted(prep.dispositions):
        if key in symbol_index:
            continue
        entry = prep.dispositions[key]
        target = entry.get("unit")
        if entry.get("how") in {"unit", "grouped"} and target in units:
            node = owner.get(target)
            symbol_index[key] = {"how": entry.get("how"), "unit": target, "node": node,
                                 "page": page_of(node),
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
                        "page": page_of(owner.get(uid)),
                        "anchor": f"#{anchor(uid)}"} for uid in sorted(units)},
        "pages": plan.report(),
        "edges": prep.edge_table,
        "graph": None if (prep.context or {}).get("graph") is not None else prep.graph,
        "graph_ref": "context.json" if (prep.context or {}).get("graph") is not None else None,
        "nodes": {nid: {"parent": node.get("parent"), "children": prep.children.get(nid) or [],
                        "unit_ids": node.get("unit_ids") or [], "title": node.get("title"),
                        "capability": node.get("capability"), "summary": node.get("summary")}
                  for nid, node in sorted(nodes.items())},
        "depends_on": prep.tree.get("depends_on") or [],
        "node_dependencies": relationships["dependencies"],
        "relationships": {k: v for k, v in relationships.items() if k not in {"dependencies"}},
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
           index_notes: list[str] | None = None, overview: dict | None = None,
           graph: dict | None = None, context: dict | None = None, basis: dict | None = None,
           source_tokens: int | None = None, read_budget: dict | None = None,
           clustering: dict | None = None, build_page: str | None = None,
           pages: str = page_budget.DEFAULT_PAGE_MODE,
           page_budget_tokens: int = page_budget.DEFAULT_PAGE_BUDGET) -> dict:
    """Render node pages, INDEX.md, DEPENDENCIES.md, RUN.md and a catalog under ``run_dir/docs``,
    and BUILD.md when ``build_page`` holds its text (``--build-page``).

    ``languages`` maps each path to the language frozen in the source context,
    so the catalog agrees with the plan even when it remapped a suffix.

    ``pages`` chooses the page boundary: ``budget`` (default) cuts pages by
    ``page_budget_tokens`` from the frozen unit explanations, ``group`` keeps one
    page per tree node. Neither mode calls a model.

    Returns metadata the caller stores in run state for verification."""
    prep = _prepare_render(run_dir=run_dir, source_root=source_root, inventory=inventory,
                           units=units, dispositions=dispositions, tree=tree, languages=languages,
                           index_notes=index_notes, overview=overview, graph=graph, context=context,
                           basis=basis, source_tokens=source_tokens, read_budget=read_budget,
                           clustering=clustering)
    plan = attach_pages(prep, mode=pages, budget=page_budget_tokens)
    if build_page is not None:
        (prep.docs_dir / "BUILD.md").write_text(build_page, encoding="utf-8")
    _write_node_pages(prep)
    index_meta = _write_index(prep, build=build_page is not None)
    _write_dependencies(prep)
    _write_run(prep)
    symbol_index = _write_catalog(prep)
    page_tokens = sum(count_text_tokens(path.read_text(encoding="utf-8"))
                      for path in sorted(prep.docs_dir.rglob("*.md")))
    return {"units_rendered": len(prep.units), "nodes": len(prep.nodes), "owner": prep.owner,
            "pages": plan.report(), "page_count": len(plan.pages),
            "relationship_counts": prep.relationships["counts"],
            "within_containment_count": prep.relationships["within_containment_count"],
            "page_tokens": page_tokens,
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
        # The page a node lands on is the plan's decision, recorded in the catalog;
        # a catalog without a plan is the older one-page-per-node shape.
        root_of = {nid: str(catalog.get("pages", {}).get("root_of", {}).get(nid, nid))
                   for nid in nodes}
        page_files = {f"nodes/{root}.md" for root in set(root_of.values())}
        rendered_pages = {name for name in page_texts if name.startswith("nodes/")}
        _add_check(checks, "catalog_pages_match_plan",
                   page_files == rendered_pages,
                   {"pages": len(page_files), "missing": sorted(page_files - rendered_pages)[:12],
                    "unplanned": sorted(rendered_pages - page_files)[:12]})
        plan_pages = (catalog.get("pages") or {}).get("pages") or []
        budget = (catalog.get("pages") or {}).get("budget") or 0
        over = [f"{row['root']}: {row['tokens']} tokens" for row in plan_pages
                if budget and row.get("tokens", 0) > budget and not row.get("over_budget")]
        _add_check(checks, "pages_respect_budget", not over,
                   {"budget": budget, "pages": len(plan_pages), "over_budget_without_reason": over[:12],
                    "pages_over_budget_with_reason": [row["root"] for row in plan_pages
                                                      if row.get("over_budget")][:12]})
        # A page's Files line is a reader's only path to a file, so a source file that has
        # a unit printed on a page must be named on at least one page. Files whose symbols
        # only sit inside a group unit have no unit of their own and are not asked for.
        named = {path for name, text in page_texts.items() if name.startswith("nodes/")
                 for line in text.splitlines() if line.startswith("Files: ")
                 for path in re.findall(r"`([^`]+)`", line)}
        placed = {row["file"] for row in (catalog.get("symbols") or {}).values() if row.get("how") == "unit" and row.get("page")}
        _add_check(checks, "source_files_named_on_a_page", placed <= named,
                   {"files": len(placed), "unnamed": sorted(placed - named)[:12]})
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
            page = f"nodes/{root_of.get(node, node)}.md"
            if (target not in units or node not in nodes
                    or not record or record.get("unit") != target or record.get("node") != node
                    or record.get("page") != page
                    or record.get("how") != ("unit" if sid in units else disposition.get("how"))
                    or page not in page_texts):
                navigation_errors.append(f"{sid}: primary page is missing/wrong")
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
    shape_problems = []
    for nid, node in nodes.items():
        kids = children[nid]
        if kids and not 2 <= len(kids) <= 12:
            shape_problems.append(f"{nid}: {len(kids)} children")
        if not kids and not node.get("unit_ids"):
            shape_problems.append(f"{nid}: empty leaf")
        # Design 2.3: a group holds 2 to 12 members, the leaf layer's units included.
        if not kids and len(node.get("unit_ids") or []) > 12:
            shape_problems.append(f"{nid}: {len(node['unit_ids'])} units")
    _add_check(checks, "group_sizes_within_bounds", not shape_problems or not units,
               {"problem_nodes": shape_problems[:12]})
    source_tokens = sum(entry.get("tokens", 0) for entry in inventory.values())
    pages_tokens = sum(count_text_tokens(text) for text in page_texts.values())
    page_ratio = pages_tokens / source_tokens if source_tokens else None
    _add_check(checks, "pages_within_budget",
               not source_tokens or source_tokens < 20_000 or page_ratio <= 0.7,
               {"source_tokens": source_tokens, "page_tokens": pages_tokens,
                "ratio": round(page_ratio, 3) if page_ratio is not None else None,
                "target": 0.6, "hard_max": 0.7})
    _add_check(checks, "semantic_rendered", (docs / "INDEX.md").is_file() and (run_dir / "catalog.json").is_file())
    return checks
