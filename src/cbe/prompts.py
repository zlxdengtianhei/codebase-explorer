"""What each task's author is told: the rules and task bodies for every task kind."""

from __future__ import annotations

import json
from pathlib import Path

from cbe import symbols
from cbe.checks import RELATION_KINDS
from cbe.projection import DEFAULT_GRAPH_MAX_TOKENS, graph_prompt_lines
from cbe.token_budget import count_text_tokens


TOOL_FREE_RULES = """You document source code in one response. Use only supplied source and signatures. Never use tools or ask to read files. Return exactly one JSON object, no Markdown fences. Separate observed syntax from inferred behavior; state uncertainty instead of inventing runtime facts. Be concise. Trivial accessors need no individual prose; tests that pin the same behavior share one explanation. Paths identify files; do not repeat large source passages."""


FILE_TASK_RULES = (
    "Read every listed source file completely with your file-reading tool; page through long files. "
    "Use only those source files, the supplied signatures, and the provided frozen graph evidence. "
    "Do not open other source files, execute repository code, search the web, or modify the repository. "
    "Use your file-reading tool for the listed files and your file-writing tool for the result file. "
    "Do not run shell commands, scripts, or interpreters, not even to assemble or check the JSON: "
    "in the user's harness each one asks for permission, and this task does not need them. "
    "(If your harness has no file-reading or file-writing tool, use the plainest command that reads or writes that one file.) "
    "You may Read a graph evidence file only when this task supplies its path. "
    "Separate observed syntax from inferred behavior; state uncertainty instead "
    "of inventing runtime facts. Be concise. Trivial accessors need no individual prose; tests that pin the same "
    "behavior share one explanation. Paths identify files; do not repeat large source passages.")
NO_FILE_RULES = (
    "Everything you need is in this file. Do not read source files, run code, search the web, or modify "
    "the repository. Do not invent details that the supplied material does not show.")


def symbol_lines(paths: list[str], inventory: dict[str, dict], table: list[dict]) -> list[str]:
    """The numbered symbol list: one line per symbol, grouped by file."""
    rows_by_path: dict[str, list[dict]] = {}
    for row in table:
        rows_by_path.setdefault(row["path"], []).append(row)
    lines = []
    for path in paths:
        entry = inventory[path]
        lines.append(f"== {path} ({entry.get('tokens', 0)} tokens)"
                     + (" [empty file: no symbols]" if entry.get("known_empty") else ""))
        for row in rows_by_path.get(path, []):
            spans = ",".join(f"{a}-{b}" for a, b in row["lines"])
            lines.append(f"{row['n']} {row['kind']} {row['name']} L{spans}")
    return lines


def gap_note(gaps: list[dict], invalid: list[dict], problem: str | None = None) -> str:
    """The text a detail re-ask appends to the unchanged first ask: only what is still missing."""
    lines = ["", "", "FOLLOW-UP: the units you returned earlier for this batch were accepted and are kept. "
             "Do not repeat them."]
    if problem:
        lines.append(f"Your last answer could not be used: {problem}")
    if invalid:
        lines.append("These units were rejected; return each again, corrected:")
        lines += [f"- h={row['h']}: {row['why']}" for row in invalid]
    if gaps:
        lines.append("These functions, methods or classes with real logic still have no unit. Give each a "
                     "unit, alone or grouped with related symbols (tests that pin the same behavior go in one group):")
        lines += [f"{row['n']} {row['kind']} {row['name']} ({row['path']})" for row in gaps]
    lines.append("Return the same JSON shape with only the additional units, using the same symbol numbers.")
    return "\n".join(lines)


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
    table = symbols.batch_table(paths, inventory)
    header = [
        "You build compact structured detail units for a code-documentation pipeline. "
        "Use ONLY the supplied source; never invent runtime behavior; record real "
        "uncertainty in 'uncertainties' instead of guessing.",
        "",
        "OUTPUT: exactly one JSON object, no Markdown fences, no commentary:",
        '{"units":[{"h":[12],"explain":"..."},{"h":[20,21,22],"title":"parse entrypoints","explain":"..."}],'
        '"notes":"optional"}',
        "",
        "SYMBOLS below are numbered. Refer to a symbol only by its number; never write a name or "
        "path where a number is asked for.",
        "",
        "units: objects with these fields",
        "  h (list of symbol numbers): the symbols this unit explains. One number: the unit is that "
        "symbol. Several numbers: one grouped unit that explains them together; give it a short "
        "'title'. A number may appear in one unit only.",
        "  title (string, grouped units only): a short name for the group.",
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
        "  relations (list, optional): {\"to\": <symbol number in this batch, or a name string "
        "for a target outside it>, \"kind\": "
        + str(sorted(RELATION_KINDS)) + ", \"basis\": <code evidence>}. kind=call only for an "
        "invocation visible in the code; use 'use' when unsure.",
        "  uncertainties (list of strings, optional): real unproven boundaries of this reading.",
        "Do NOT emit 'source', a kind, an id or any line-range field: the program derives them from "
        "the numbered symbols.",
        "",
        "Symbols that no unit lists are indexed by position without prose. Leave out pure "
        "constants, imports, re-exports and trivial accessors; give a unit to every other "
        "function, method or class. Tests are no exception: group the tests that pin the same "
        "behavior into one unit (h lists their numbers) and say in a sentence or two which "
        "behavior they pin and any edge case worth knowing; do not write each test separately. "
        "A file marked empty has no symbols and needs no unit; do not invent prose for it.",
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
        "every class needs its own explanation, either as its own unit or, when it is grouped, "
        "as a sentence in the group's explain that says what the class itself is; "
        "do not repeat the behavior of members that have their own units in this batch. "
        "For members folded into the class without their own units, explain their behavior, "
        "conditions, and failure paths inside the class unit, not just class attributes. "
        "Include those folded implementations when estimating the class unit's source size. "
        "Keep the coordination needed to understand the class. Each unit must stand alone: "
        "never replace behavior with 'see the class unit' or 'see above'. "
        "A module region containing only imports or constants "
        "gets no unit, because the symbol list already locates that non-behavioral material. "
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
        "Keep generation metadata out of prose: no symbol numbers or positions, graph-candidate "
        "labels, or references to the generation process.")
    if issues:
        header.append("Correct these review findings without broadening claims: "
                      + json.dumps(issues, ensure_ascii=False))
    body: list[str] = ["SYMBOLS (this batch; number, kind, name, source lines):", *symbol_lines(paths, inventory, table), ""]
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
                note = "(source text was not available; describe only the listed symbols)"
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


TREE_NAME_INSTRUCTIONS = """You name the modules of a codebase. A program already grouped code units into modules, using call and import edges, shared files and similar wording. You do not regroup. You see no source code: each unit is one line of what it does. Units are numbered u1, u2, ...

For EVERY module below return:
- title: 2 to 6 words naming the module's responsibility. If the members come from one directory, still say what the module does. Titles must differ from each other.
- capability: ONE sentence of about 25 words or fewer: what the module is responsible for and why its members belong together.
- summary: 2 or 3 sentences: when a reader should come to this module and what they find there.
- evidence_units: 2 to 4 unit numbers of that module that show the capability best.

Answer with one JSON object and nothing else:
{"modules": [{"id": "M1", "title": "...", "capability": "...", "summary": "...", "evidence_units": ["u1", "u2"]}]}
"""

TREE_TOP_INSTRUCTIONS = """You name the upper levels of a module tree of a codebase. The program fixed the structure: each GROUP below lists its children. A child is either a module that already has a title, or another group (named in this same answer: name the deepest groups first). You do not regroup or rename the children. You see no source code.

For EVERY group return:
- title: 2 to 6 words naming the shared responsibility of the group as a whole. Not a child's title repeated, not a directory name. Titles must differ from each other.
- capability: ONE sentence of about 25 words or fewer: what the group is responsible for and why these children belong together.
- summary: 2 or 3 sentences: when a reader should come here and how the children divide the work.
{root_note}
Answer with one JSON object and nothing else:
{"groups": [{"id": "G1", "title": "...", "capability": "...", "summary": "..."}]}
"""


def tree_name_prompt(blocks: list[str]) -> str:
    return TREE_NAME_INSTRUCTIONS + "\nMODULES:\n\n" + "\n\n".join(blocks)


def tree_top_prompt(repo: str, blocks: list[str]) -> str:
    note = (f'G1 is the whole repository "{repo}": its title is the system\'s name or says what it is.\n')
    return TREE_TOP_INSTRUCTIONS.replace("{root_note}", note) + "\nGROUPS:\n\n" + "\n\n".join(blocks)


def tree_retry_note(pending: list[str], problems: list[str], taken: list[str]) -> str:
    """Appended to the first prompt when some nodes of a naming answer were rejected."""
    return ("\n\nSome entries of your previous answer were accepted. Answer again ONLY for: "
            + ", ".join(pending) + " (the same JSON shape, with only these entries). Problems: "
            + "; ".join(problems[:20]) + ("\nTitles already taken, do not reuse: " + "; ".join(taken[:60]) if taken else "")
            + "\n")


def review_prompt(units: dict | None, detail_task: str) -> str:
    """An independent reader checks one batch's accepted units against the same source."""
    return ("TASK: Check these structured detail units against the source. Return JSON "
            "{\"decision\":\"accepted\" or \"needs_repair\",\"issues\":[...]} . issues is a list of "
            "strings, not objects: one sentence per issue that names the unit id and the problem, for "
            "example \"issues\": [\"flask/app.py::method::Flask.run::123: says X but the code does Y\"]. Only report "
            "material unsupported or missing behavior, a wrong condition or failure surface, or a "
            "unit attributed to the wrong symbol. Do not judge writing style.\n"
            "DOCUMENTATION (structured units): " + json.dumps(units, ensure_ascii=False) + "\n\n" + detail_task)


def system_relationship_context(relationships: dict | None = None) -> dict:
    """The exact bounded relationship table shown to the system model."""
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
    return context


def system_prompt(nodes: list[dict], limit: int, relationships: dict | None = None) -> str:
    """Bound graph context to 12k tokens: remove last candidates, then dependencies."""
    context = system_relationship_context(relationships)
    summaries = [{"id": node.get("id"), "title": node.get("title"),
                  "capability": node.get("capability"), "summary": node.get("summary"),
                  "parent": node.get("parent"), "units": len(node.get("unit_ids") or [])}
                 for node in nodes]
    return ("TASK: Synthesize these semantic node summaries and program-derived relationships into an overview "
            f"of the repository. Return JSON with a nonempty string overview of 2 to 4 sentences, at most {limit} "
            "characters: what the system is and how its top-level modules divide the work. Do not invent unseen "
            "details. Also return dependency_descriptions: "
            "[{\"from\":\"node id\",\"to\":\"node id\",\"description\":\"one sentence\"}], describing "
            "at least one key dependency when the table is nonempty (otherwise []). Use existing pairs only; "
            "describe only who uses whom for what. Do not write evidence/source words "
            "(graph-confirmed, model-inferred, graph-only, resolved calls/edges/imports) or call/edge counts; "
            "the program supplies those labels and counts. Return key_flows: [{\"name\":\"short name\","
            "\"description\":\"one sentence\",\"steps\":[\"unit id\",\"unit id\"]}]. Select 3-7 key flows "
            "from candidates and keep their unit ids. If fewer than three candidates exist, you may describe "
            "distinct useful subpaths using those same ids. When there are no candidates, return []. "
            "Use 2-8 steps per flow, at most 300 characters per name or description. Describe how the parts "
            "cooperate; link to details rather than repeating unit explanations. Unsupported transitions "
            "will be labeled model inferred by the program.\nRELATIONSHIPS: "
            + json.dumps(context, ensure_ascii=False) + "\nNODE SUMMARIES: " + json.dumps(summaries, ensure_ascii=False))
