"""What each task's author is told: the rules and task bodies for every task kind."""

from __future__ import annotations

import json
from pathlib import Path

from cbe.batching import Module
from cbe.checks import RELATION_KINDS
from cbe.projection import DEFAULT_GRAPH_MAX_TOKENS, graph_prompt_lines
from cbe.token_budget import count_text_tokens


TOOL_FREE_RULES = """You document source code in one response. Use only supplied source and signatures. Never use tools or ask to read files. Return exactly one JSON object, no Markdown fences. Separate observed syntax from inferred behavior; state uncertainty instead of inventing runtime facts. Be concise. Test functions and trivial accessors need no individual prose. Paths identify files; do not repeat large source passages."""


def names_prompt(modules: list[Module]) -> str:
    rows = [{"module": module.number, "subsystem": module.bucket,
             "kind": "tests" if module.is_test else "source",
             "files": [f.path for f in module.files],
             "signatures": [name for f in module.files for name in f.signatures[:30]]}
            for module in modules]
    return ("TASK: Give each source module a short functional title, not a numbered part or path hash. "
            "Return JSON: {\"names\":[{\"module\":0,\"title\":\"...\"}, ...]}. "
            "Respect each module's subsystem and test/source kind. Name the common role, not a list of unrelated files. "
            "Keep mixed-language scope honest. Modules:\n" + json.dumps(rows, ensure_ascii=False))


FILE_TASK_RULES = (
    "Read every listed source file completely with your file-reading tool; page through long files. "
    "Use only those source files, the supplied signatures, and the provided frozen graph evidence. "
    "Do not open other source files, execute repository code, search the web, or modify the repository. "
    "You may Read a graph evidence file only when this task supplies its path. "
    "Separate observed syntax from inferred behavior; state uncertainty instead "
    "of inventing runtime facts. Be concise. Test functions and trivial accessors need no individual prose. "
    "Paths identify files; do not repeat large source passages.")
NO_FILE_RULES = (
    "Everything you need is in this file. Do not read source files, run code, search the web, or modify "
    "the repository. Do not invent details that the supplied material does not show.")


def detail_prompt(paths: list[str], inventory: dict[str, dict], *,
                  chunks: list[dict] | None = None,
                  source_root: Path | None = None,
                  graph: dict | None = None,
                  graph_max_tokens: int = DEFAULT_GRAPH_MAX_TOKENS,
                  graph_file: str | None = None,
                  context_diagnostics: list[dict] | None = None,
                  issues: list[str] | None = None,
                  embed: bool = True) -> str:
    """Build one detail task.

    ``embed=True`` is the tool-free script driver: the source chunk text is
    inlined once. ``embed=False`` is the host-agent driver: the prompt lists the
    absolute file paths and chunk line ranges instead, so the text is not sent
    twice. Graph context, when present, is attached once at chunk granularity;
    a run without a graph says so instead of implying relations were analyzed.
    """
    inv_rows = [{"file": path, "tokens": inventory[path].get("tokens", 0),
                 "known_empty": bool(inventory[path].get("known_empty")),
                 "symbols": inventory[path]["symbols"]} for path in paths]
    header = [
        "You build compact structured detail units for a code-documentation pipeline. "
        "Use ONLY the supplied source; never invent runtime behavior; record real "
        "uncertainty in 'uncertainties' instead of guessing.",
        "",
        "OUTPUT: exactly one JSON object, no Markdown fences, no commentary:",
        '{"units":[...],"dispositions":{...},"batch_notes":"..."}',
        "",
        "units: objects with EXACTLY these fields",
        "  id (string; for one symbol use its exact inventory id; for a merged group use "
        "'grp:<kebab-slug-starting-with-the-file-name>'; ids unique here)",
        "  kind: class | function | method | group | module_region",
        "  explain (string): prose that lets a senior engineer understand this unit WITHOUT "
        "reading the code and predict its boundary behavior. Cover responsibility and "
        "boundary, key behavior, entry and input/output semantics, behavior-changing "
        "conditions with their consequences, exception catch/propagate/fallback order, side "
        "effects and state, and collaboration with unproven boundaries. Do not restate the "
        "listing line by line; never paraphrase only the signature.",
        "  Do not emit a separate summary field: avoid repeating the same responsibility. "
        "Start explain with a self-contained responsibility sentence of about 25 words or fewer; "
        "the program reuses that first sentence under the signature and in the tree/INDEX. "
        "Keep the remaining explanation for behavior the reader needs to predict.",
        "  extras (list, optional): {\"topic\": condition|failure|side_effect|field|contract, "
        "\"note\": <one clear statement>} only for a necessity the explain does not cover.",
        "  relations (list, optional): {\"target\": <inventory id or grp: id>, \"kind\": "
        + str(sorted(RELATION_KINDS)) + ", \"basis\": <code evidence>}. kind=call only for an "
        "invocation visible in the code; use 'use' when unsure.",
        "  uncertainties (list of strings): real unproven boundaries of this reading.",
        "  members (optional): inventory ids fully explained inside this unit.",
        "Do NOT emit 'source' or any line-range field: the program derives published ranges "
        "from the inventory.",
        "",
        "dispositions: one entry for EVERY id in the INVENTORY below, no key missing, no "
        "extra keys: \"<inventory id>\": {\"how\": unit|grouped|index_only, "
        "\"unit\": \"<unit id>\", \"reason\": \"short code-evidence statement\"}. "
        "how=unit means the symbol got its own unit (unit id == the inventory id); "
        "how=grouped means it is explained inside another unit; how=index_only means pure "
        "constants/imports/re-exports with no behavior worth prose ('unit' may be null; "
        "'reason' required). Never drop an inventory id. Fold trivial getters and test cases; "
        "give real units to anything with actual logic. A file whose symbol list is empty "
        "(a known-empty file) needs no disposition and no unit; do not invent prose for it.",
    ]
    header.append(
        "LENGTH GUIDANCE: Spend prose on behavior, not a fixed introduction for every unit. "
        "Estimate each unit's source tokens from its own implementation (a class header excludes "
        "separately documented members). For source under 50 tokens, one or two sentences usually "
        "suffice; for 50-150 tokens, aim around 70 prose tokens or fewer. For 150-400 tokens, "
        "around 110 prose tokens often suffice; for 400-1000, around 240; for larger units, "
        "around 330, growing with actual complexity. These are references, not ceilings: exceed "
        "them whenever needed to explain behavior-changing conditions, failure paths, or side "
        "effects. Cover every behavior-changing branch and every failure path; let those branches "
        "and paths determine the length. Information quality takes priority; remove repetition "
        "before removing behavior.")
    header.append(
        "AVOID DUPLICATION: Explain a class's class-level responsibility and collaboration; "
        "do not repeat the behavior of members that have their own units in this batch. "
        "For members folded into the class without their own units, explain their behavior, "
        "conditions, and failure paths inside the class unit, not just class attributes. "
        "Include those folded implementations when estimating the class unit's source size. "
        "Keep the coordination needed to understand the class. Each unit must stand alone: "
        "never replace behavior with 'see the class unit' or 'see above'. "
        "A module region containing only imports or constants "
        "must be index_only, because the inventory already locates that non-behavioral material. "
        "Write uncertainties only for a real boundary supported by specific source evidence; "
        "omit boilerplate such as 'not visible in this file'. An empty uncertainties list is "
        "appropriate when no such boundary affects understanding.")
    header.append(
        "BEHAVIOR AND EVIDENCE: State each if/elif branch or distinct case with its own condition "
        "and outcome; do not compress different conditions into one ambiguous sentence. "
        "Explain how a called function changes this unit's result, not merely that it is called, "
        "when that effect is supported by the supplied source. Do not speculate about callers, "
        "decorators, or safety guarantees absent from the source. If a relevant effect cannot "
        "be established, put the specific boundary and its evidence in uncertainties. "
        "Describe only code within this unit's source scope. When a docstring conflicts with "
        "the implementation, follow the implementation and point out the discrepancy. "
        "Keep generation metadata out of prose: no inventory ids or positions, graph-candidate "
        "labels, or references to the generation process.")
    if issues:
        header.append("Correct these review findings without broadening claims: "
                      + json.dumps(issues, ensure_ascii=False))
    body: list[str] = ["INVENTORY (this batch, authoritative ids):",
                       json.dumps(inv_rows, ensure_ascii=False), ""]
    source_texts: dict[str, str] = {}
    for path in paths:
        text = ""
        if source_root is not None:
            try:
                text = (source_root / path).read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                pass
        if not text:
            rows = sorted((c for c in (chunks or []) if c.get("path") == path),
                          key=lambda c: (c.get("start_byte") or 0, c.get("start_line") or 0))
            text = "".join(c.get("text") or "" for c in rows)
        source_texts[path] = text
    source_tokens = sum(count_text_tokens(text) for text in source_texts.values())
    graph_lines = graph_prompt_lines(graph, paths, embed=embed, inventory=inventory,
                                    chunks=chunks, source_tokens=source_tokens,
                                    max_tokens=graph_max_tokens, graph_file=graph_file)
    body += graph_lines
    if context_diagnostics:
        body += ["SOURCE CONTEXT NOTES (program diagnostics, not model evidence):",
                 json.dumps(context_diagnostics[:10], ensure_ascii=False), ""]
    if embed:
        body.append("SOURCE (verbatim; the program derives all line ranges, so the model "
                    "never needs to emit one):")
        for path in paths:
            text = source_texts[path]
            if text:
                note = text
            elif inventory.get(path, {}).get("known_empty"):
                note = "(this file is empty: it has no source text, no inventory id and needs no unit)"
            else:
                note = "(source text was not available; describe only the inventory ids)"
            body += [f"==== FILE {path} ====", note]
    else:
        body.append("SOURCE FILES (read each listed file completely; read no other file):")
        for path in paths:
            rows = [chunk for chunk in (chunks or []) if chunk.get("path") == path]
            target = str((source_root or Path(".")) / path)
            if rows:
                spans = ", ".join(f"L{chunk['start_line']}-L{chunk['end_line']}" for chunk in rows)
                body.append(f"- {target} ({spans})")
            else:
                body.append(f"- {target}")
    return "\n".join(header + body)


def tree_prompt(units: dict[str, dict], files: list[str], edges: list[dict] | None = None, *, merge: bool = False) -> str:
    from cbe.aggregation import digest
    from cbe.principles import PRINCIPLES, grain_bounds

    grain_min, grain_max = grain_bounds()
    digests = [units[uid] if merge else digest(units[uid]) for uid in sorted(units)]
    return (
        "You design a recursive semantic responsibility tree for a codebase, from the "
        "structured detail units below. You see no raw source: reason only from these "
        "units. Each unit carries only its responsibility summary and source location. "
        "The graph below rolls source edges up to units with kind and count. "
        "kind=relation is model-inferred evidence, counted separately from resolved static edges; "
        "missing edges do not prove independence. No full explanations are provided.\n\n"
        + ("MERGE: UNITS are accepted candidate regions. Assign each region id exactly once; "
           "do not repeat their detail units or rewrite their subtrees. The program grafts each "
           "intact subtree at its selected home. Use their top nodes and cross-region edges.\n\n" if merge else "") +
        "OUTPUT: exactly one JSON object, no Markdown fences, no commentary: "
        '{"nodes":[...],"depends_on":[...]}\n\n'
        "nodes: objects with fields\n"
        "  id (short kebab slug, unique), parent (id of the parent; exactly ONE node - the "
        "root - has parent null), title (short name), capability (what responsibility this "
        "node owns and why its children and units belong together; for any node with "
        "children this must be a real explanation of the shared capability), summary (how a "
        "reader should use this subtree; 2-4 sentences), unit_ids (list of unit ids whose "
        "PRIMARY home is this node; every unit id below must appear in exactly one node).\n"
        "A node may have children AND its own unit_ids. The tree may be uneven. Create "
        "genuine intermediate capability nodes; do NOT invent filler nodes and do NOT "
        "flatten everything under the root. Do not mirror the directory layout unless the "
        "responsibilities really coincide.\n"
        "depends_on: list of {from, to, basis} between node ids: 'from' needs 'to'. basis "
        "cites unit-level evidence (unit ids / call / import). Real cycles are allowed.\n\n"
        "Every unit id in UNITS must be assigned exactly once.\n\n"
        "FILES: " + json.dumps(sorted(files), ensure_ascii=False) + "\n\n"
        "UNIT GRAPH (resolved static edges and model-inferred relations; from, to, kind, count):\n" + json.dumps(edges or [], ensure_ascii=False)
        + "\n\nAGGREGATION PRINCIPLES:\n" + "\n".join(
            f"{p.id}: " + p.prompt.format(grain_min=grain_min, grain_max=grain_max) for p in PRINCIPLES)
        + "\n\nUNITS:\n" + json.dumps(digests, ensure_ascii=False)
    )


def review_prompt(units: dict | None, detail_task: str) -> str:
    """An independent reader checks one batch's accepted units against the same source."""
    return ("TASK: Check these structured detail units against the source. Return JSON "
            "{\"decision\":\"accepted\" or \"needs_repair\",\"issues\":[...]} . Only report "
            "material unsupported or missing behavior, a wrong condition or failure surface, or a "
            "unit attributed to the wrong symbol. Do not judge writing style.\n"
            "DOCUMENTATION (structured units): " + json.dumps(units, ensure_ascii=False) + "\n\n" + detail_task)


def system_prompt(nodes: list[dict], limit: int, relationships: dict | None = None) -> str:
    """Bound graph context to 12k tokens: remove last candidates, then dependencies.

    Candidate order is the program's stable traversal; dependency order keeps
    tree pairs first, then graph-only pairs by descending count. Node summaries
    retain the existing tree budget and are not truncated here.
    """
    from cbe.token_budget import count_text_tokens

    relationships = relationships or {"dependencies": [], "candidate_flows": []}
    context = {key: relationships.get(key) for key in
               ("graph_state", "graph_reason", "graph_only_omitted")}
    context.update(dependencies=list(relationships["dependencies"][:80]),
                   candidate_flows=list(relationships["candidate_flows"][:24]))
    context["prompt_omitted"] = {key: len(relationships[key]) - len(context[key])
                                 for key in ("dependencies", "candidate_flows")}
    while count_text_tokens(json.dumps(context, ensure_ascii=False)) > 12000:
        key = "candidate_flows" if context["candidate_flows"] else "dependencies"
        if not context[key]:
            break
        context[key].pop()
        context["prompt_omitted"][key] += 1
    summaries = [{"id": node.get("id"), "title": node.get("title"),
                  "capability": node.get("capability"), "summary": node.get("summary"),
                  "parent": node.get("parent"), "units": len(node.get("unit_ids") or [])}
                 for node in nodes]
    return ("TASK: Synthesize these semantic node summaries and program-derived relationships into an overview and maintenance "
            f"navigation for the repository. Return JSON with nonempty strings overview and "
            f"maintenance_navigation, each at most {limit} characters. Explain which node to open for "
            "a maintenance question; do not invent unseen details. Also return dependency_descriptions: "
            "[{\"from\":\"node id\",\"to\":\"node id\",\"description\":\"one sentence\"}], describing "
            "at least one key dependency when the table is nonempty (otherwise []). Use existing pairs only; "
            "the program owns evidence labels. Return key_flows: [{\"name\":\"short name\","
            "\"description\":\"one sentence\",\"steps\":[\"unit id\",\"unit id\"]}]. Select 3-7 key flows "
            "from candidates and keep their unit ids. If fewer than three candidates exist, you may describe "
            "distinct useful subpaths using those same ids. When there are no candidates, return []. "
            "Use 2-8 steps per flow, at most 300 characters per name or description. Describe how the parts "
            "cooperate; link to details rather than repeating unit explanations. Unsupported transitions "
            "will be labeled model inferred by the program.\nRELATIONSHIPS: "
            + json.dumps(context, ensure_ascii=False) + "\nNODE SUMMARIES: " + json.dumps(summaries, ensure_ascii=False))
