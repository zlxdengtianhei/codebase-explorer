"""What each task's author is told: the rules and task bodies for every task kind."""

from __future__ import annotations

import json
from pathlib import Path

from cbe import symbols
from cbe.token_budget import count_text_tokens


TOOL_FREE_RULES = """You document source code in one response. Use only supplied source and signatures. Never use tools or ask to read files. Return exactly one JSON object, no Markdown fences. Separate observed syntax from inferred behavior; state uncertainty instead of inventing runtime facts. Be concise. Paths identify files; do not repeat source passages."""

FILE_TASK_RULES = (
    "Read every listed source file completely with your file-reading tool; page through long files. "
    "Use only those source files and the supplied signatures. "
    "Do not open other source files, execute repository code, search the web, or modify the repository. "
    "Use your file-reading tool for the listed files and your file-writing tool for the result file. "
    "Do not run shell commands, scripts, or interpreters, not even to assemble or check the JSON: "
    "in the user's harness each one asks for permission, and this task does not need them. "
    "(If your harness has no file-reading or file-writing tool, use the plainest command that reads or writes that one file.) "
    "Separate observed syntax from inferred behavior; state uncertainty instead "
    "of inventing runtime facts. Be concise.")
NO_FILE_RULES = (
    "Everything you need is in this file. Do not read source files, run code, search the web, or modify "
    "the repository. Do not invent details that the supplied material does not show.")

#: The writing rules of a detail answer (design 2.1): one short piece per function,
#: method and class; what it does, not what its signature already says.
DETAIL_STYLE = """DETAIL STYLE:
- Write one detail for every function, method and class in the list. A tiny one (a getter, a setter, a one-line predicate) gets one short phrase; do not skip it.
- A run of trivial members of one class may share one grouped unit, but the sentence must name every symbol it covers (write the symbol's name).
- Length: 1 to 3 sentences, about 25 to 60 tokens. Hard ceiling: 100 tokens, and never more than half the symbol's own source tokens; a small symbol still gets about 25 tokens of room.
- Start with the subject: "`parse_config` reads the file and ...". Say what it does, what it returns or changes, and what happens on failure. Do not restate the signature, parameter names or types.
- A grouped unit needs a short `title` (2 to 6 words) and one `explain` that covers the group. Every symbol in the group must appear by name in that text.
- Do not write call relations: call edges come from the program's graph, never from you.
- `uncertainties` (optional list of strings): only a real boundary the source does not settle.
- `extras` (optional list): {"topic": condition|failure|side_effect|field|contract, "note": one statement} only when the explain cannot carry it."""


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
    """The text a gap-fill ask carries: only what is still missing."""
    lines = ["", "FOLLOW-UP: the units returned earlier for this batch were accepted and are kept. "
             "Do not repeat them."]
    if problem:
        lines.append(f"The last answer could not be used: {problem}")
    if invalid:
        lines.append("These units were rejected; return each again, corrected:")
        lines += [f"- h={row['h']}: {row['why']}" for row in invalid]
    if gaps:
        lines.append("These functions, methods or classes still have no detail:")
        lines += [f"{row['n']} {row['kind']} {row['name']} ({row['path']})" for row in gaps]
    lines.append("Return the same JSON shape with only these units, using the same symbol numbers.")
    return "\n".join(lines)


def _detail_header() -> list[str]:
    return [
        "You build short structured detail units for a code-documentation pipeline. "
        "Use ONLY the supplied source; never invent runtime behavior.",
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
        "  explain (string): the detail, written as DETAIL STYLE below requires.",
        "Do NOT emit 'source', a kind, an id or any line-range field: the program derives them from "
        "the numbered symbols.",
        "",
        DETAIL_STYLE,
    ]


def detail_prompt(paths: list[str], inventory: dict[str, dict], *,
                  chunks: list[dict] | None = None,
                  source_root: Path | None = None,
                  context_diagnostics: list[dict] | None = None,
                  issues: list[str] | None = None,
                  embed: bool = True) -> str:
    """One detail task for a reading batch.

    ``embed=True`` is the tool-free script driver: each file's source is inlined
    once. ``embed=False`` is the host-agent driver: the prompt lists the absolute
    file paths and chunk line ranges instead, so the text is not sent twice."""
    table = symbols.batch_table(paths, inventory)
    header = _detail_header()
    if issues:
        header.append("Correct these review findings without broadening claims: "
                      + json.dumps(issues, ensure_ascii=False))
    body: list[str] = ["SYMBOLS (this batch; number, kind, name, source lines):",
                       *symbol_lines(paths, inventory, table), ""]
    if context_diagnostics:
        body += ["SOURCE CONTEXT NOTES (program diagnostics, not model evidence):",
                 json.dumps(context_diagnostics[:10], ensure_ascii=False), ""]
    body += _source_blocks(paths, inventory, chunks, source_root, embed)
    return "\n".join(header + body)


def gap_detail_prompt(paths: list[str], inventory: dict[str, dict], gaps: list[dict],
                      *, chunks: list[dict] | None = None,
                      source_root: Path | None = None,
                      invalid: list[dict] | None = None,
                      problem: str | None = None,
                      embed: bool = True) -> str:
    """A gap-fill ask: the missing symbols only, with only their own source blocks.

    Design 2.2: a re-ask never resends the whole batch, and a fresh, short
    instruction keeps the fixed overhead small. The numbers stay the batch's
    numbers, so the answer decodes against the same table."""
    by_id = {chunk["id"]: chunk for chunk in chunks or []}
    header = [
        "You write the detail that is still missing for a code-documentation pipeline. "
        "Use ONLY the supplied source; never invent runtime behavior.",
        "",
        'OUTPUT: exactly one JSON object, no Markdown fences: '
        '{"units":[{"h":[12],"explain":"..."},{"h":[20,21],"title":"...","explain":"..."}]}',
        "Name symbols by the numbers below only. One unit per symbol, or one grouped unit whose "
        "sentence names every symbol in it.",
        "Length: 1 to 3 sentences, about 25 to 60 tokens, hard ceiling 100 and at most half the "
        "symbol's source; a tiny symbol gets one short phrase. Start with the subject; do not "
        "restate the signature or parameter types. Do not write call relations.",
        "",
        "SYMBOLS STILL WITHOUT A DETAIL (number, kind, name):",
    ]
    body = list(header)
    for row in gaps:
        body.append(f"{row['n']} {row['kind']} {row['name']}")
    body.append("")
    body += gap_note(gaps, invalid or [], problem).splitlines()[1:]
    body.append("")
    if embed:
        body.append("SOURCE OF THESE SYMBOLS (verbatim):")
        for row in gaps:
            chunk = by_id.get(row["id"])
            text = (chunk or {}).get("text") or ""
            body += [f"==== {row['path']} :: {row['name']} ====",
                     text or "(source text was not available; describe only the listed symbol)"]
    else:
        body.append("SOURCE FILES AND LINES (read only these spans):")
        for row in gaps:
            chunk = by_id.get(row["id"])
            target = str((source_root or Path(".")) / row["path"])
            span = (f"L{chunk['start_line']}-L{chunk['end_line']}" if chunk
                    else ",".join(f"L{a}-L{b}" for a, b in row["lines"]))
            body.append(f"- {target} ({span})")
    return "\n".join(body)


def _source_blocks(paths: list[str], inventory: dict[str, dict], chunks: list[dict] | None,
                   source_root: Path | None, embed: bool,
                   only: set[str] | None = None) -> list[str]:
    """The source part of a detail prompt: whole files, or listed paths and spans."""
    if embed:
        out = ["SOURCE (verbatim; the program derives all line ranges, so the model "
               "never needs to emit one):"]
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
            note = text or ("(this file is empty: it has no source text, no inventory id and needs no unit)"
                            if inventory.get(path, {}).get("known_empty")
                            else "(source text was not available; describe only the listed symbols)")
            out += [f"==== FILE {path} ====", note]
        return out
    out = ["SOURCE FILES (read each listed file completely; read no other file):"]
    for path in paths:
        rows = [chunk for chunk in (chunks or []) if chunk.get("path") == path
                and (only is None or chunk["id"] in only)]
        target = str((source_root or Path(".")) / path)
        if rows:
            spans = ", ".join(f"L{chunk['start_line']}-L{chunk['end_line']}" for chunk in rows)
            out.append(f"- {target} ({spans})")
        else:
            out.append(f"- {target}")
    return out


def embedded_source_tokens(paths: list[str], chunks: list[dict] | None,
                           source_root: Path | None, only: set[str] | None = None) -> int:
    """Program count of the source text a prompt puts in front of the model."""
    total = 0
    for path in paths:
        text = ""
        if source_root is not None:
            try:
                text = (source_root / path).read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                pass
        if not text:
            text = "".join(c.get("text") or "" for c in (chunks or [])
                           if c.get("path") == path
                           and (only is None or c.get("id") in only))
        elif only is not None:
            text = "".join(c.get("text") or "" for c in (chunks or [])
                           if c.get("path") == path and c.get("id") in only)
        total += count_text_tokens(text)
    return total


LAYER_INSTRUCTIONS = """You group code units into a module tree of a codebase. You see no source code: you see one line per code unit (what it does) or the summary of a group from the layer below, plus a program's candidate grouping and call counts.

A layer answers one question:
- units -> modules: what do these functions, methods and classes do together; why do they belong to one module?
- modules -> systems: what do these modules provide to the outside; why do they belong together?
- systems -> the whole: what does the system offer, and what does it depend on?

Return groups. Each group has:
- title: 2 to 6 words naming what the group is responsible for. Titles must differ from each other.
- capability: ONE sentence (about 25 words or fewer) saying what the group is responsible for and why its members belong together.
- summary: 2 or 3 sentences: when a reader should come here and what they find.
- members: the list of member labels shown below. Every member must appear in exactly one group of your answer.
- why (optional, one sentence): use it when you split, merge or move a candidate group.

Rules:
- Group size: 2 to 12 members. Do not return a group of one; merge it with its closest neighbour.
- Follow the work, not the directory names. A candidate group is only a hint: you may split it, merge it or move a member.
- A function called from 20 or more places may go into a shared-utilities group.
- Write prose, not a listing: no call counts, symbols, file paths or generated labels in the sentences.

Answer with one JSON object and nothing else:
{"groups": [{"title": "...", "capability": "...", "summary": "...", "members": ["u1", "u2"], "why": "..."}]}
"""


def layer_prompt(level: int, blocks: list[str], member_noun: str) -> str:
    """One layer task: the instruction plus this chunk's member blocks."""
    return (LAYER_INSTRUCTIONS + f"\nThis is layer {level}; its members are {member_noun}.\n\nMEMBERS:\n\n"
            + "\n\n".join(blocks))


OVERVIEW_INSTRUCTIONS = """You write the whole-repository page of a code map. You see no source code: you see the top-level groups of the map, each with one sentence and a short summary.

Write 3 to 6 sentences, about 300 to 500 tokens, that answer:
- who uses this code and what problem it solves;
- what the top-level groups offer together;
- where a reader should start reading this map, and in what order to go deeper.

Do not list the groups one by one; say how they make up the whole. Do not invent behavior that the supplied summaries do not show.

Answer with one JSON object and nothing else:
{"overview": "..."}
"""


def overview_prompt(repo: str, blocks: list[str]) -> str:
    return (OVERVIEW_INSTRUCTIONS + f'\nThe repository is "{repo}".\n\nTOP-LEVEL GROUPS:\n\n'
            + "\n\n".join(blocks))


def review_prompt(units: dict | None, detail_task: str) -> str:
    """An independent reader checks one batch's accepted units against the same source."""
    return ("TASK: Check these structured detail units against the source. Return JSON "
            "{\"decision\":\"accepted\" or \"needs_repair\",\"issues\":[...]} . issues is a list of "
            "strings, not objects: one sentence per issue that names the unit id and the problem, for "
            "example \"flask/app.py::method::Flask.run::123: says X but the code does Y\". Only report "
            "material unsupported or missing behavior, a wrong condition or failure surface, or a "
            "unit attributed to the wrong symbol. Do not judge writing style. For example: "
            '\"issues\": [\"pkg/jobs.py::method::Pool.submit::12: says X but the code does Y\"].\n'
            "DOCUMENTATION (structured units): " + json.dumps(units, ensure_ascii=False) + "\n\n" + detail_task)
