"""Structured detail units, semantic ownership tree, and source-anchored rendering.

This is the generation-stage port of the semantic-hierarchy prototype. It keeps
the parts that produce the user-visible effect — structured detail units with an
explicit disposition for every inventory id, program-derived source ranges, a
semantic responsibility tree with one primary owner per unit, and a readable
node render — and drops the prototype's runners, caches, GLM callers and
experiment ledgers, which the existing ``generate.py`` / ``host_run.py`` state
machine already provides.

Retained obligations from the prototype: the model never emits line numbers (the program
derives published ranges from the inventory); every inventory id gets exactly
one disposition (unit / grouped / index_only), so nothing is silently dropped;
length and count measures are diagnostics, never model-repair triggers; the
ownership tree must be single-rooted and acyclic for containment while
dependency cycles stay allowed; each unit has exactly one primary owner. New
behaviour the prototype did not have: the inventory can come from a
``cbe.source_context`` snapshot rather than only a fresh AST scan, so the same
inventory and source ranges are shared with the graph and context authors.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from cbe.token_budget import count_text_tokens


UNIT_KINDS = {"class", "function", "method", "group", "module_region"}
DISPOSITION_HOW = {"unit", "grouped", "index_only"}
RELATION_KINDS = {"call", "inherit", "override", "import", "raise", "use",
                  "contract", "group"}
EXTRA_TOPICS = {"condition", "failure", "side_effect", "field", "contract"}

# One repository file larger than this becomes its own inventory unit region set;
# a chunk never has to fit a model context alone because batches group many.
SCHEMA = "cbe-semantic/1"

_LANGUAGE_BY_SUFFIX = {
    ".py": "python", ".pyi": "python", ".ts": "typescript", ".tsx": "typescript",
    ".mts": "typescript", ".cts": "typescript", ".js": "javascript", ".jsx": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".c": "c", ".h": "c", ".cc": "cpp",
    ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".rs": "rust", ".java": "java",
    ".go": "go", ".sql": "sql",
}


class SemanticError(ValueError):
    """The semantic stage cannot continue with the given input."""


def language_of(path: str) -> str:
    return _LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower(), "unknown")


# ------------------------------------------------------------------ inventory


def _node_span(node: ast.AST) -> list[int]:
    """Decorator-aware 1-based inclusive span; a decorated symbol starts at its
    first decorator so a segment boundary never orphans it."""
    start = node.lineno  # type: ignore[attr-defined]
    decorators = getattr(node, "decorator_list", None)
    if decorators:
        start = min(start, min(item.lineno for item in decorators))
    return [start, node.end_lineno]  # type: ignore[attr-defined]


def _python_inventory(path: str, source: str, digest: str, tokens: int) -> dict:
    rows: list[dict[str, Any]] = []
    regions: list[list[int]] = []
    region_start: int | None = None
    seen: dict[str, int] = {}

    def unique_id(name: str, start: int) -> str:
        # Two ``def reserve_run`` overloads are two real symbols; the second
        # carries its start line so no inventory id is ever duplicated.
        count = seen.get(name, 0)
        seen[name] = count + 1
        return f"{path}::{name}" if count == 0 else f"{path}::{name}@{start}"

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        tree = None
    nlines = source.count("\n") + (1 if source and not source.endswith("\n") else 0)
    for node in list(tree.body) if tree is not None else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if region_start is not None:
                regions.append([region_start, (node.lineno - 1) or region_start])
                region_start = None
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            span = _node_span(node)
            rows.append({"id": unique_id(node.name, span[0]), "name": node.name, "kind": kind,
                         "parent": None, "lines": [span]})
            if kind == "class":
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        child_span = _node_span(child)
                        qualified = f"{node.name}.{child.name}"
                        rows.append({"id": unique_id(qualified, child_span[0]),
                                     "name": qualified, "kind": "method",
                                     "parent": f"{path}::{node.name}", "lines": [child_span]})
        elif region_start is None:
            region_start = node.lineno
    if region_start is not None:
        regions.append([region_start, max(nlines, region_start)])
    if regions:
        rows.append({"id": f"{path}::<module top-level>", "name": "<module top-level>",
                     "kind": "module_region", "parent": None, "lines": regions})
    return {"tokens": tokens, "sha256": digest, "nlines": max(nlines, 1), "symbols": rows}


def _file_region_inventory(path: str, source: str, digest: str, tokens: int) -> dict:
    """Languages without an AST inventory still get one whole-file region so the
    disposition coverage check has a real id and no source is silently dropped."""
    nlines = source.count("\n") + (1 if source and not source.endswith("\n") else 0)
    rows = [{"id": f"{path}::<file>", "name": "<file>", "kind": "module_region",
             "parent": None, "lines": [[1, max(nlines, 1)]]}]
    return {"tokens": tokens, "sha256": digest, "nlines": max(nlines, 1), "symbols": rows}


def build_inventory(rows: dict[str, dict]) -> dict[str, dict]:
    """Inventory from scanned rows ``{path: {source, digest, tokens}}``.

    Python uses AST spans; every other language gets one whole-file region.
    A ``source_context`` snapshot can replace this later: see
    :func:`inventory_from_context`."""
    inventory: dict[str, dict] = {}
    for path in sorted(rows):
        row = rows[path]
        source = row.get("source") or ""
        digest = row.get("digest") or hashlib.sha256(source.encode("utf-8")).hexdigest()
        tokens = row.get("tokens") or count_text_tokens(source)
        if path.endswith((".py", ".pyi")):
            inventory[path] = _python_inventory(path, source, digest, tokens)
        else:
            inventory[path] = _file_region_inventory(path, source, digest, tokens)
    return inventory


def inventory_from_context(context: dict, paths: list[str] | None = None) -> dict[str, dict]:
    """Build the same inventory shape from a ``cbe-context/1`` snapshot.

    Chunk ids become unit ids, so the detail stage, the graph and the query
    layer all name the same thing. A chunk without a name (whole-file region)
    still yields one id. Diagnostics never turn a missing chunk into an empty
    success: a listed path with no chunks raises."""
    wanted = set(paths) if paths is not None else None
    by_path: dict[str, dict] = {}
    for chunk in context.get("chunks") or []:
        path = chunk["path"]
        if wanted is not None and path not in wanted:
            continue
        entry = by_path.setdefault(path, {"tokens": 0, "sha256": "", "nlines": 1,
                                          "symbols": []})
        if not (chunk.get("text") or "").strip():
            # A blank chunk (an empty or whitespace-only file) carries no
            # explainable detail; it must not become a unit with prose.
            continue
        name = chunk.get("name") or "<region>"
        kind = chunk.get("kind") or "module_region"
        if kind not in UNIT_KINDS:
            kind = "module_region"
        entry["symbols"].append({
            "id": chunk["id"], "name": name, "kind": kind, "parent": None,
            "lines": [[int(chunk["start_line"]), int(chunk["end_line"])]],
        })
    for row in context.get("files") or []:
        path = row["path"]
        if wanted is not None and path not in wanted:
            continue
        entry = by_path.setdefault(path, {"tokens": 0, "sha256": "", "nlines": 1,
                                          "symbols": []})
        entry["sha256"] = row.get("sha256", "")
        entry["nlines"] = max((pair[1] for sym in entry["symbols"]
                               for pair in sym["lines"]), default=1)
        entry["tokens"] = sum(count_text_tokens(chunk.get("text") or "")
                              for chunk in (context.get("chunks") or [])
                              if chunk.get("path") == path)
        # No symbols after blank chunks means the file is known-empty; the
        # catalogue still lists it, but no unit or disposition is invented.
        entry["known_empty"] = not entry["symbols"]
    if wanted is not None:
        missing = sorted(path for path in wanted if path not in by_path)
        if missing:
            raise SemanticError("source context has no chunks or file entry for: "
                                 + ", ".join(missing[:10]))
    return by_path


def inventory_ids(inventory: dict[str, dict]) -> list[str]:
    return [row["id"] for file in inventory.values() for row in file["symbols"]]


def ensure_chunk_coverage(context: dict, repo: Path, ast_inventory: dict[str, dict],
                          paths: list[str]) -> dict:
    """Guarantee every non-empty requested path has a readable source chunk.

    A genuinely empty file (no bytes, or whitespace only) is known-empty: it
    gets a ``known_empty`` diagnostic and **no** chunk, so the inventory and
    render never invent a missing-grammar region or force prose for it. A
    non-empty path with no chunk is a real grammar/unsupported-language gap, so
    the AST/file-region fallback supplies a chunk and a visible
    ``context_fallback`` diagnostic. Mutates and returns ``context``."""
    chunks = context.setdefault("chunks", [])
    files = context.setdefault("files", [])
    diagnostics = context.setdefault("diagnostics", [])
    present = {chunk["path"] for chunk in chunks}
    listed = {row["path"] for row in files}
    for path in paths:
        if path in present:
            continue
        try:
            text = (repo / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            diagnostics.append({"path": path, "code": "source_unavailable", "message": str(exc)})
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if path not in listed:
            files.append({"path": path, "language": language_of(path), "sha256": digest})
        if text.strip() == "":
            diagnostics.append({"path": path, "code": "known_empty",
                                "message": "file is empty; it has no source chunk, no inventory id "
                                           "and needs no detail unit"})
            continue
        lines = text.splitlines()
        symbols = (ast_inventory.get(path) or {}).get("symbols") or []
        if not symbols:
            nlines = max(len(lines), 1)
            symbols = [{"id": f"{path}::<file>", "name": "<file>",
                        "kind": "module_region", "lines": [[1, nlines]]}]
        for symbol in symbols:
            start, end = symbol["lines"][0]
            body = "\n".join(lines[max(start - 1, 0):end])
            chunks.append({"id": symbol["id"], "path": path, "language": language_of(path),
                           "kind": symbol["kind"], "name": symbol["name"],
                           "start_line": start, "end_line": end,
                           "start_byte": 0, "end_byte": 0, "text": body,
                           "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
        diagnostics.append({"path": path, "code": "context_fallback",
                            "message": "no chunk grammar output for this path; the AST/file-region "
                                       "fallback supplied the reading chunk"})
    return context


def inventory_for_paths(inventory: dict[str, dict], paths: Iterable[str]) -> dict[str, dict]:
    chosen = set(paths)
    return {path: inventory[path] for path in sorted(inventory) if path in chosen}


# ------------------------------------------------------------------ detail schema


def unit_digest(unit: dict) -> dict:
    """Complete semantic view of one unit for tree decisions: full explain,
    every extra note, every uncertainty and every relation with its basis."""
    relations = [{"target": rel.get("target"), "kind": rel.get("kind", "use"),
                  "basis": rel.get("basis") or ""}
                 for rel in unit.get("relations") or [] if isinstance(rel, dict)]
    extras = [{"topic": extra.get("topic"), "note": extra.get("note")}
              for extra in unit.get("extras") or [] if isinstance(extra, dict)]
    uncertainties = [item for item in unit.get("uncertainties") or [] if isinstance(item, str)]
    return {"id": unit.get("id"), "kind": unit.get("kind"),
            "explain": unit.get("explain") or "", "extras": extras,
            "uncertainties": uncertainties, "relations": relations,
            "members": unit.get("members") or []}


def _normalize_choice(value: Any, allowed: "set[str] | frozenset[str]",
                      default: str) -> tuple[str, bool]:
    """Conservative enum repair: keep a valid value, unwrap a one-element list
    the model sometimes emits (``["use"]``), otherwise fall back to a safe
    default. Returns (value, changed)."""
    if isinstance(value, str) and value in allowed:
        return value, False
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str) \
            and value[0] in allowed:
        return value[0], True
    return default, True


def validate_details(payload: Any, paths: list[str], inventory: dict[str, dict],
                     known_unit_ids: set[str]) -> list[str]:
    """Hard problems only (empty list = acceptable).

    Hard means structure, symbol identity, references, coverage, and nonempty
    required content. Length and count are never checked here and never trigger
    a model repair. The function never mutates its input."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["result is not a JSON object"]
    units = payload.get("units")
    if not isinstance(units, list):
        return ["units must be a list"]
    scope_ids = {row["id"] for path in paths for row in inventory[path]["symbols"]}
    if not units and scope_ids:
        # An empty batch (every file known-empty, no inventory id) may validly
        # return no units; a batch with ids must explain them.
        return ["units must be a nonempty list"]
    seen: set[str] = set()
    for unit in units:
        if not isinstance(unit, dict):
            problems.append("unit is not an object")
            continue
        uid = unit.get("id")
        if not isinstance(uid, str) or not uid.strip():
            problems.append("unit without id")
            continue
        if uid in seen or uid in known_unit_ids:
            problems.append(f"duplicate unit id {uid}")
        seen.add(uid)
        if "::" not in uid and not uid.startswith("grp:"):
            problems.append(f"unit id {uid} is neither 'path::name' nor 'grp:...'")
        kind = unit.get("kind")
        if not isinstance(kind, str) or kind not in UNIT_KINDS:
            problems.append(f"{uid}: kind must be one of {sorted(UNIT_KINDS)}; got {kind!r}")
        explain = unit.get("explain")
        if not isinstance(explain, str) or not explain.strip():
            problems.append(f"{uid}: explain must be a nonempty paragraph")
        extras = unit.get("extras", [])
        if not isinstance(extras, list):
            problems.append(f"{uid}: extras must be a list")
        else:
            for extra in extras:
                topic = extra.get("topic") if isinstance(extra, dict) else None
                if not isinstance(topic, str) or topic not in EXTRA_TOPICS:
                    problems.append(f"{uid}: extra topic must be one of {sorted(EXTRA_TOPICS)}; "
                                    f"got {topic!r}")
                    continue
                note = extra.get("note")
                if not isinstance(note, str) or not note.strip():
                    problems.append(f"{uid}: extra note must be a nonempty string")
        relations = unit.get("relations", [])
        if not isinstance(relations, list):
            problems.append(f"{uid}: relations must be a list")
        else:
            for rel in relations:
                if not isinstance(rel, dict) or not isinstance(rel.get("target"), str) \
                        or not rel["target"].strip():
                    problems.append(f"{uid}: relation needs a nonempty target")
                    continue
                rel_kind = rel.get("kind", "use")
                if not isinstance(rel_kind, str) or rel_kind not in RELATION_KINDS:
                    problems.append(f"{uid}: relation kind must be one of {sorted(RELATION_KINDS)}; "
                                    f"got {rel_kind!r}")
        uncertainties = unit.get("uncertainties", [])
        if not isinstance(uncertainties, list) or any(not isinstance(item, str) for item in uncertainties):
            problems.append(f"{uid}: uncertainties must be a list of strings")
        members = unit.get("members", [])
        if members and not isinstance(members, list):
            problems.append(f"{uid}: members must be a list")
    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, dict):
        return problems + ["dispositions must be an object keyed by inventory id"]
    missing = sorted(scope_ids - set(dispositions))
    extra = sorted(set(dispositions) - scope_ids)
    if missing:
        problems.append(f"dispositions missing inventory ids: {missing[:12]}")
    if extra:
        problems.append(f"dispositions has non-scope keys: {extra[:12]}")
    for key, entry in dispositions.items():
        if key not in scope_ids:
            continue
        how = entry.get("how") if isinstance(entry, dict) else None
        if not isinstance(how, str) or how not in DISPOSITION_HOW:
            problems.append(f"disposition {key}: how must be one of {sorted(DISPOSITION_HOW)}; "
                            f"got {how!r}")
            continue
        target = entry.get("unit")
        if how in {"unit", "grouped"}:
            if not isinstance(target, str) or target not in seen:
                problems.append(f"disposition {key}: unit target {target!r} is not a unit "
                                "defined in this result")
        if how == "unit" and target != key:
            problems.append(f"disposition {key}: how=unit requires target == the same id")
        reason = entry.get("reason")
        if how == "index_only" and (not isinstance(reason, str) or not reason.strip()):
            problems.append(f"disposition {key}: index_only requires a reason")
        if reason is not None and not isinstance(reason, str):
            problems.append(f"disposition {key}: reason must be a string")
    notes = payload.get("batch_notes")
    if not isinstance(notes, str) or not notes.strip():
        problems.append("batch_notes must be a nonempty string")
    return problems


def normalize_details(payload: Any, paths: list[str], inventory: dict[str, dict],
                      known_unit_ids: set[str]) -> list[str]:
    """Make a usable answer compliant without dropping facts.

    Only shape is repaired: non-dict units are dropped, invalid relation kinds
    become ``use``, an absent uncertainty list becomes ``[]``, and a missing
    disposition becomes ``index_only`` with a reason. Facts are never removed.
    Raises when nothing usable is left."""
    if not isinstance(payload, dict):
        raise ValueError("module result is not a JSON object")
    if not isinstance(payload.get("units"), list):
        raise ValueError("module result has no units list")
    if not payload["units"] and any(inventory.get(path, {}).get("symbols") for path in paths):
        raise ValueError("module result has no units")
    flags: list[str] = []
    units = [unit for unit in payload["units"] if isinstance(unit, dict)
             and isinstance(unit.get("id"), str) and unit["id"].strip()]
    if len(units) != len(payload["units"]):
        flags.append(f"dropped {len(payload['units']) - len(units)} malformed unit(s)")
    for unit in units:
        kind, changed = _normalize_choice(unit.get("kind"), UNIT_KINDS, "module_region")
        if changed:
            flags.append(f"{unit['id']}: kind rewritten to {kind}")
            unit["kind"] = kind
        if not isinstance(unit.get("explain"), str) or not unit["explain"].strip():
            flags.append(f"{unit['id']}: explain was empty; wrote a placeholder")
            unit["explain"] = "No explanation was returned for this unit."
        if not isinstance(unit.get("extras"), list):
            flags.append(f"{unit['id']}: extras was not a list; dropped")
            unit["extras"] = []
        for extra in unit["extras"]:
            if not isinstance(extra, dict):
                continue
            topic, changed = _normalize_choice(extra.get("topic"), EXTRA_TOPICS, "contract")
            if changed:
                extra["topic"] = topic
        relations = unit.get("relations")
        if relations is not None and not isinstance(relations, list):
            flags.append(f"{unit['id']}: relations was not a list; dropped")
            unit["relations"] = []
        for rel in unit.get("relations") or []:
            if not isinstance(rel, dict):
                continue
            rel_kind, changed = _normalize_choice(rel.get("kind", "use"), RELATION_KINDS, "use")
            if changed:
                flags.append(f"{unit['id']}: relation kind rewritten to {rel_kind}")
                rel["kind"] = rel_kind
        if not isinstance(unit.get("uncertainties"), list):
            flags.append(f"{unit['id']}: uncertainties was not a list; dropped")
            unit["uncertainties"] = []
    payload["units"] = units
    scope_ids = {row["id"] for path in paths for row in inventory[path]["symbols"]}
    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, dict):
        dispositions = {}
        flags.append("dispositions was missing; rebuilt as index_only")
    for key in sorted(scope_ids - set(dispositions)):
        dispositions[key] = {"how": "index_only", "unit": None,
                             "reason": "no disposition returned; indexed without prose"}
        flags.append(f"{key}: disposition missing; treated as index_only")
    for key in sorted(set(dispositions) - scope_ids):
        dispositions.pop(key)
        flags.append(f"{key}: disposition key was not in this batch; dropped")
    for key, entry in dispositions.items():
        how = entry.get("how") if isinstance(entry, dict) else None
        if not isinstance(how, str) or how not in DISPOSITION_HOW:
            dispositions[key] = {"how": "index_only", "unit": None,
                                 "reason": "invalid disposition; indexed without prose"}
            flags.append(f"{key}: invalid disposition; treated as index_only")
    payload["dispositions"] = dispositions
    if not isinstance(payload.get("batch_notes"), str) or not payload["batch_notes"].strip():
        payload["batch_notes"] = "No batch notes returned."
        flags.append("batch_notes was empty")
    return flags


# ------------------------------------------------------------------ ranges and names


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


# ------------------------------------------------------------------ tree


_NODE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def validate_tree(payload: Any, unit_universe: set[str]) -> list[str]:
    """Hard problems only: one root, an acyclic contains graph, every node
    reachable, every unit assigned to exactly one primary owner, and a real
    capability text on any node with children. Dependency cycles stay allowed."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["tree result is not a JSON object"]
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["nodes must be a nonempty list"]
    by_id: dict[str, dict] = {}
    roots: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            problems.append("node is not an object")
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or not _NODE_ID.match(nid):
            problems.append(f"bad node id {nid!r}")
            continue
        if nid in by_id:
            problems.append(f"duplicate node id {nid}")
        by_id[nid] = node
        if node.get("parent") is None:
            roots.append(nid)
    if len(roots) != 1:
        problems.append(f"exactly one root required, found {roots}")
    for nid, node in by_id.items():
        parent = node.get("parent")
        if parent is not None and (not isinstance(parent, str) or parent not in by_id):
            problems.append(f"node {nid}: parent {parent!r} does not exist")
        for field in ("title", "capability", "summary"):
            if not isinstance(node.get(field), str) or not node[field].strip():
                problems.append(f"node {nid}: {field} must be a nonempty string")
        unit_ids = node.get("unit_ids")
        if not isinstance(unit_ids, list) or any(not isinstance(item, str) for item in unit_ids):
            problems.append(f"node {nid}: unit_ids must be a list of strings")
    children: dict[str, list[str]] = {nid: [] for nid in by_id}
    for nid, node in by_id.items():
        parent = node.get("parent")
        if isinstance(parent, str) and parent in by_id:
            children[parent].append(nid)
    root = roots[0] if len(roots) == 1 else None
    if root is not None:
        seen: set[str] = set()
        stack = [root]
        while stack:
            nid = stack.pop()
            if nid in seen:
                problems.append(f"node {nid} reachable twice: contains graph has a cycle")
                continue
            seen.add(nid)
            stack.extend(children.get(nid, []))
        unreachable = sorted(set(by_id) - seen)
        if unreachable:
            problems.append(f"nodes unreachable from root: {unreachable[:12]}")
    owner: dict[str, str] = {}
    for nid, node in by_id.items():
        for uid in node.get("unit_ids") or []:
            if not isinstance(uid, str):
                continue  # already reported as a bad unit_ids list above
            if uid not in unit_universe:
                problems.append(f"node {nid}: unknown unit id {uid}")
            elif uid in owner:
                problems.append(f"unit {uid} assigned to both {owner[uid]} and {nid}")
            else:
                owner[uid] = nid
    unassigned = sorted(unit_universe - set(owner))
    if unassigned:
        problems.append(f"units with no primary owner: {unassigned[:12]}")
    for nid, node in by_id.items():
        capability = node.get("capability")
        if children.get(nid) and isinstance(capability, str) and len(capability) < 40:
            problems.append(f"node {nid} has children but capability text is not a real "
                            "explanation (<40 chars)")
    edges = payload.get("depends_on")
    if not isinstance(edges, list):
        problems.append("depends_on must be a list")
    else:
        for edge in edges:
            if not isinstance(edge, dict) or edge.get("from") not in by_id \
                    or edge.get("to") not in by_id:
                problems.append(f"depends_on edge with unknown endpoint: {edge!r}"[:200])
                continue
            if not isinstance(edge.get("basis"), str) or not edge["basis"].strip():
                problems.append(f"depends_on {edge.get('from')}->{edge.get('to')}: "
                                "basis (evidence) is required")
    return problems


def normalize_tree(payload: Any, unit_universe: set[str]) -> list[str]:
    """Repair shape only: drop bad nodes, reattach orphans under the first root,
    and assign unowned units to a fallback node. Never drops a unit."""
    if not isinstance(payload, dict):
        raise ValueError("tree result is not a JSON object")
    nodes = [node for node in payload.get("nodes") or []
             if isinstance(node, dict) and isinstance(node.get("id"), str)
             and _NODE_ID.match(node["id"])]
    if not nodes:
        raise ValueError("tree result has no usable nodes")
    flags: list[str] = []
    seen: set[str] = set()
    unique: list[dict] = []
    for node in nodes:
        if node["id"] in seen:
            flags.append(f"dropped duplicate node {node['id']}")
            continue
        seen.add(node["id"])
        unique.append(node)
    nodes = unique
    by_id = {node["id"]: node for node in nodes}
    roots = [node for node in nodes if node.get("parent") is None]
    if not roots:
        nodes[0]["parent"] = None
        roots = [nodes[0]]
        flags.append("no root; promoted the first node")
    root = roots[0]["id"]
    for node in nodes:
        parent = node.get("parent")
        if node["id"] != root and (not isinstance(parent, str) or parent not in by_id):
            node["parent"] = root
            flags.append(f"{node['id']}: parent missing; attached to root")
    for field in ("title", "capability", "summary"):
        for node in nodes:
            if not isinstance(node.get(field), str) or not node[field].strip():
                node[field] = node.get("title") or node["id"]
                flags.append(f"{node['id']}: {field} was empty")
    for node in nodes:
        if not isinstance(node.get("unit_ids"), list):
            node["unit_ids"] = []
    owner: set[str] = set()
    for node in nodes:
        kept = [uid for uid in node["unit_ids"] if isinstance(uid, str) and uid in unit_universe
                and uid not in owner]
        if len(kept) != len(node["unit_ids"]):
            flags.append(f"{node['id']}: dropped unknown or duplicate unit ids")
        node["unit_ids"] = kept
        owner.update(kept)
    missing = sorted(unit_universe - owner)
    if missing:
        fallback = by_id.get(root)
        assert fallback is not None
        fallback.setdefault("unit_ids", []).extend(missing)
        flags.append(f"{len(missing)} unit(s) had no owner; assigned to the root")
    if not isinstance(payload.get("depends_on"), list):
        payload["depends_on"] = []
        flags.append("depends_on was not a list; dropped")
    payload["nodes"] = nodes
    return flags


def mechanical_tree(modules: list[dict], units: dict[str, dict]) -> dict:
    """A real structural fallback when the tree task cannot run: one node per
    module/batch under a single root. It is honestly coarse, not a semantic
    grouping, and the renderer says so."""
    nodes = [{"id": "root", "parent": None, "title": "Codebase",
              "capability": "Every source area of the repository. The semantic tree task "
                            "did not produce accepted output, so the program grouped units "
                            "by their reading batch; this is a structural fallback.",
              "summary": "Open the area page for one batch of source files.",
              "unit_ids": []}]
    module_of: dict[str, str] = {}
    for module in modules:
        nid = f"area-{module['number'] + 1}"
        nodes.append({"id": nid, "parent": "root", "title": module.get("title") or nid,
                      "capability": "The source files in this reading batch.",
                      "summary": "Units read from this batch of files.",
                      "unit_ids": []})
        for path in module["files"]:
            module_of[path] = nid
    by_id = {node["id"]: node for node in nodes}
    for uid in units:
        path = uid.split("::", 1)[0]
        nid = module_of.get(path, "root")
        by_id[nid]["unit_ids"].append(uid)
    return {"nodes": nodes, "depends_on": [],
            "fallback": "mechanical batch grouping; the tree task did not complete"}


# ------------------------------------------------------------------ prompts


# ------------------------------------------------------------------ graph projection

#: The prompt-facing schema. It is a bounded projection of ``cbe-graph/1``, not a new graph.
GRAPH_PROJECTION_SCHEMA = "cbe-graph-projection/1"

#: Default prompt budget. The complete graph stays in the frozen ``context.json``;
#: these caps only bound what one completion sees, with explicit omission counts.
DEFAULT_GRAPH_MAX_NODES = 200
DEFAULT_GRAPH_MAX_EDGES = 320

#: Semantic relations are included before structural ones, and resolved before
#: unresolved, so a budget cut never silently drops the import/call evidence.
_GRAPH_KIND_PRIORITY = {"import": 0, "call": 1, "cfg": 2, "dataflow": 3}
_GRAPH_STATUS_PRIORITY = {"resolved": 0, "ambiguous": 1, "unresolved": 2, "external": 3,
                          "unsupported": 4}
_SEMANTIC_GRAPH_KINDS = ("import", "call")
_STRUCTURAL_GRAPH_KINDS = ("cfg", "dataflow")


def graph_state(graph: Any) -> tuple[str, str]:
    """Classify a graph as one of ``absent|unsupported|failed|empty|provided``.

    An empty graph is a verified result, not a missing graph, and is never
    reported as "not provided". """
    if graph is None:
        return "absent", "no graph was provided for this run"
    if not isinstance(graph, dict) or graph.get("schema") != "cbe-graph/1":
        found = graph.get("schema") if isinstance(graph, dict) else type(graph).__name__
        return "unsupported", f"graph schema is {found!r}, expected 'cbe-graph/1'"
    nodes = [node for node in graph.get("nodes") or [] if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges") or [] if isinstance(edge, dict)]
    if nodes or edges:
        return "provided", f"{len(nodes)} nodes, {len(edges)} edges"
    statuses = {str(cap.get("status")) for cap in graph.get("capabilities") or []
                if isinstance(cap, dict) and cap.get("status")}
    if statuses & {"failed", "unavailable"}:
        return "failed", "backend failed or was unavailable"
    if "unsupported" in statuses and not (statuses & {"resolved", "partial", "empty"}):
        return "unsupported", "no requested language/graph type is supported"
    diagnostics = {row.get("code") for row in graph.get("diagnostics") or []
                   if isinstance(row, dict)}
    if "no_language_requested" in diagnostics or (
            "analyzed_languages" in graph and not graph["analyzed_languages"]):
        return "unsupported", "no language was selected for analysis"
    if "no_backend_completed" in diagnostics:
        return "failed", "no backend completed; the empty graph is not authoritative"
    return "empty", "the analyzer ran and found no relation"


def _compact_graph_node(node: dict) -> dict:
    out: dict[str, Any] = {"id": node.get("id"), "kind": node.get("kind"),
                           "name": node.get("name")}
    if node.get("path"):
        out["path"] = node["path"]
        out["lines"] = [node.get("start_line"), node.get("end_line")]
    else:
        out["boundary"] = True
    for key in ("owner", "label"):
        if node.get(key) and node.get(key) != node.get("name"):
            out[key] = node[key]
    return out


def _compact_graph_edge(edge: dict) -> dict:
    out: dict[str, Any] = {"id": edge.get("id"), "source": edge.get("source"),
                           "target": edge.get("target"), "kind": edge.get("kind"),
                           "status": edge.get("status")}
    for key in ("path", "line", "expression", "target_expression", "method_full_name", "owner"):
        if edge.get(key) is not None:
            out[key] = edge[key]
    candidates = edge.get("candidates")
    if isinstance(candidates, list) and candidates:
        out["candidates"] = candidates[:8]
        out["candidate_count"] = len(candidates)
    return out


def project_graph(graph: Any, paths: list[str], *, max_nodes: int = DEFAULT_GRAPH_MAX_NODES,
                  max_edges: int = DEFAULT_GRAPH_MAX_EDGES) -> dict[str, Any]:
    """Bounded, deterministic, referentially closed projection for one prompt.

    Every included relation keeps both endpoints, even a boundary node outside
    the requested paths, so no selected edge dangles. Import/call edges are
    taken first; cfg/dataflow edges are sampled deterministically by edge id and
    labeled as such. Counts of total/selected/omitted are always reported. This
    is a projection, never a second graph or scheduler."""
    state, detail = graph_state(graph)
    result: dict[str, Any] = {
        "schema": GRAPH_PROJECTION_SCHEMA, "state": state, "state_detail": detail,
        "scope": {"paths": sorted(set(paths)), "direction": "both",
                  "relation_scope": "incident_to_paths",
                  "boundary_endpoints_retained": True},
    }
    if state in {"absent", "unsupported", "failed"}:
        return result
    nodes = [node for node in graph.get("nodes") or [] if isinstance(node, dict) and node.get("id")]
    edges = [edge for edge in graph.get("edges") or [] if isinstance(edge, dict)]
    by_id = {node["id"]: node for node in nodes}
    result["backend"] = graph.get("backend")
    result["capabilities"] = list(graph.get("capabilities") or [])
    result["diagnostics"] = list(graph.get("diagnostics") or [])[:20]
    provenance = graph.get("provenance")
    if isinstance(provenance, dict):
        result["provenance"] = {key: provenance[key] for key in
                                ("source_stable", "config_stable", "analyzed_languages", "fingerprint")
                                if key in provenance}
    selected_paths = set(paths)
    path_node_ids = {node["id"] for node in nodes if node.get("path") in selected_paths}
    if not path_node_ids:
        result["state"] = "no_local_nodes"
        result["counts"] = {"nodes_total": len(nodes), "edges_total": len(edges),
                            "nodes_selected": 0, "edges_selected": 0,
                            "edges_in_scope": 0}
        return result

    incident = [edge for edge in edges
                if edge.get("source") in path_node_ids or edge.get("target") in path_node_ids]

    def edge_rank(edge: dict) -> tuple:
        return (_GRAPH_KIND_PRIORITY.get(edge.get("kind"), 9),
                _GRAPH_STATUS_PRIORITY.get(edge.get("status"), 9), str(edge.get("id")))

    ranked = sorted(incident, key=edge_rank)
    selected_nodes: dict[str, dict] = {}
    selected_edges: list[dict] = []
    omitted_by_kind: dict[str, int] = {}
    omitted_missing_endpoint = 0
    # Relations first, in priority order: a semantic edge and both its endpoints
    # are taken before any structural node, so a budget cut can never drop
    # import/call evidence in favour of CFG blocks.
    for edge in ranked:
        if len(selected_edges) >= max_edges:
            omitted_by_kind[edge.get("kind")] = omitted_by_kind.get(edge.get("kind"), 0) + 1
            continue
        endpoints = [edge.get("source"), edge.get("target")]
        if any(endpoint and endpoint not in by_id for endpoint in endpoints):
            omitted_missing_endpoint += 1  # never emit a dangling edge
            continue
        missing = [endpoint for endpoint in endpoints if endpoint and endpoint not in selected_nodes]
        if len(selected_nodes) + len(set(missing)) > max_nodes:
            omitted_by_kind[edge.get("kind")] = omitted_by_kind.get(edge.get("kind"), 0) + 1
            continue
        for endpoint in missing:
            selected_nodes[endpoint] = _compact_graph_node(by_id[endpoint])
        selected_edges.append(_compact_graph_edge(edge))
    # Then any remaining reading-scope node, so a file/function with no edge is
    # still visible, without ever displacing a relation.
    for node_id in sorted(path_node_ids, key=lambda item: (by_id[item].get("path") or "",
                                                           by_id[item].get("start_line") or 0, item)):
        if len(selected_nodes) >= max_nodes:
            break
        selected_nodes.setdefault(node_id, _compact_graph_node(by_id[node_id]))

    by_kind: dict[str, dict[str, int]] = {}
    for kind in ("import", "call", "cfg", "dataflow"):
        scope = [edge for edge in incident if edge.get("kind") == kind]
        chosen = sum(1 for edge in selected_edges if edge.get("kind") == kind)
        if scope or chosen:
            by_kind[kind] = {"in_scope": len(scope), "selected": chosen,
                             "omitted": len(scope) - chosen}
    semantic_omitted = sum(omitted_by_kind.get(kind, 0) for kind in _SEMANTIC_GRAPH_KINDS)
    aggregation: dict[str, dict[str, dict[str, int]]] = {}
    for kind in _STRUCTURAL_GRAPH_KINDS:
        scope = [edge for edge in incident if edge.get("kind") == kind]
        if not scope:
            continue
        owners: dict[str, dict[str, int]] = {}
        chosen_ids = {edge.get("id") for edge in selected_edges}
        for edge in scope:
            owner = edge.get("owner")
            if not owner:
                source_node = by_id.get(edge.get("source")) or {}
                owner = source_node.get("owner") or edge.get("path") or source_node.get("path") or "<unknown>"
            row = owners.setdefault(owner, {"in_scope": 0, "selected": 0})
            row["in_scope"] += 1
            if edge.get("id") in chosen_ids:
                row["selected"] += 1
        aggregation[kind] = dict(sorted(owners.items())[:50])

    result["nodes"] = sorted(selected_nodes.values(),
                             key=lambda node: (node.get("path") or "", node.get("kind") or "",
                                               node.get("lines") or [0, 0], node.get("id") or ""))
    result["edges"] = selected_edges
    result["counts"] = {
        "nodes_total": len(nodes), "nodes_selected": len(selected_nodes),
        "nodes_omitted": len(nodes) - len(selected_nodes),
        "edges_total": len(edges), "edges_in_scope": len(incident),
        "edges_selected": len(selected_edges),
        "edges_omitted": len(incident) - len(selected_edges),
        "edges_omitted_by_kind": {kind: count for kind, count in omitted_by_kind.items() if count},
        "edges_omitted_missing_endpoint": omitted_missing_endpoint,
        "by_kind": by_kind,
    }
    result["sampling"] = {
        "priority": "import/call before cfg/dataflow; resolved before unresolved; then edge id",
        "import_call": ("all included" if semantic_omitted == 0 else
                        f"{semantic_omitted} import/call edge(s) omitted after the budget"),
        "cfg_dataflow": "deterministically sampled by edge id; not a representative subset",
        "aggregation": "cfg/dataflow in_scope/selected counts per owner" if aggregation else None,
    }
    if aggregation:
        result["cfg_dataflow_by_owner"] = aggregation
    return result


def graph_prompt_lines(graph: Any, paths: list[str], *, embed: bool,
                       expand_context_path: str | None = None,
                       max_nodes: int = DEFAULT_GRAPH_MAX_NODES,
                       max_edges: int = DEFAULT_GRAPH_MAX_EDGES) -> list[str]:
    """Prompt body lines that state the graph state and, when present, a bounded
    deterministic projection with explicit omissions and a host expansion path."""
    state, detail = graph_state(graph)
    if state == "absent":
        return ["GRAPH: not provided for this run. Do not infer imports, calls or data flow; state the "
                "boundary in 'uncertainties' when a relation would matter.", ""]
    if state == "unsupported":
        return [f"GRAPH: unsupported for this run ({detail}). Do not infer relations from the graph; "
                "state unproven boundaries in 'uncertainties'.", ""]
    if state == "failed":
        return [f"GRAPH: analysis failed or was unavailable ({detail}). Treat relations as unknown, not "
                "absent, and do not invent them.", ""]
    if state == "empty":
        return ["GRAPH: provided and successfully empty (the analyzer ran and found no node or relation). "
                "An empty graph is a verified result, not a missing graph; still state any unproven boundary.", ""]
    projection = project_graph(graph, paths, max_nodes=max_nodes, max_edges=max_edges)
    if projection.get("state") == "no_local_nodes":
        return [f"GRAPH: provided for this run ({detail}) but no graph node anchors the listed file(s). This is "
                "not an empty graph and not a missing graph: the analyzer produced no symbol node for these "
                "paths. Do not infer either the presence or the absence of relations from it; keep unproven "
                "boundaries in 'uncertainties'.", ""]
    counts = projection["counts"]
    omitted = counts["edges_omitted_by_kind"] or "none"
    lines = [
        "LOCAL GRAPH EVIDENCE (a deterministic projection of the frozen full graph; an edge is evidence, "
        "not proof of behavior). Boundary nodes outside the listed files are kept so every included relation "
        "stays resolvable.",
        f"Scope: relations incident to {sorted(set(paths))}. Totals {counts['nodes_total']} nodes / "
        f"{counts['edges_total']} edges; included {counts['nodes_selected']} nodes / {counts['edges_selected']} "
        f"edges; omitted {counts['edges_omitted']} incident edge(s) by kind: {omitted}. "
        "Import/call relations are prioritized; CFG/dataflow edges are deterministically sampled by edge id and "
        "are not a representative subset; the omitted edges are not shown and their absence is not evidence.",
    ]
    if embed:
        lines.append("This completion is tool-free: you cannot query the frozen graph, so the projection "
                     "below is the only relation evidence available. Do not claim to have inspected an "
                     "omitted edge.")
    elif expand_context_path:
        command = shlex.join([
            sys.executable, "-m", "cbe", "graph", "query", "--graph", expand_context_path,
            "--path", sorted(set(paths))[0], "--kind", "call", "--direction", "both",
        ])
        lines.append("To expand an omitted relation, run: " + command)
        lines.append("You may replace --path with another listed path and --kind with import, cfg, or "
                     "dataflow. Read only the returned slice; the query does not execute repository code.")
    lines += [json.dumps(projection, ensure_ascii=False), ""]
    return lines


def detail_prompt(paths: list[str], inventory: dict[str, dict], *,
                  chunks: list[dict] | None = None,
                  source_root: Path | None = None,
                  graph: dict | None = None,
                  graph_max_nodes: int = DEFAULT_GRAPH_MAX_NODES,
                  graph_max_edges: int = DEFAULT_GRAPH_MAX_EDGES,
                  expand_context_path: str | None = None,
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
    if issues:
        header.append("Correct these review findings without broadening claims: "
                      + json.dumps(issues, ensure_ascii=False))
    body: list[str] = ["INVENTORY (this batch, authoritative ids):",
                       json.dumps(inv_rows, ensure_ascii=False), ""]
    body += graph_prompt_lines(graph, paths, embed=embed,
                               expand_context_path=expand_context_path,
                               max_nodes=graph_max_nodes, max_edges=graph_max_edges)
    if context_diagnostics:
        body += ["SOURCE CONTEXT NOTES (program diagnostics, not model evidence):",
                 json.dumps(context_diagnostics[:10], ensure_ascii=False), ""]
    if embed:
        body.append("SOURCE (verbatim; the program derives all line ranges, so the model "
                    "never needs to emit one):")
        for path in paths:
            text = ""
            if source_root is not None:
                try:
                    text = (source_root / path).read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    text = ""
            if not text:
                rows = sorted((chunk for chunk in (chunks or []) if chunk.get("path") == path),
                              key=lambda chunk: (chunk.get("start_byte") or chunk.get("start_line") or 0,
                                                 chunk.get("start_line") or 0))
                text = "".join(chunk.get("text") or "" for chunk in rows)
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


def tree_prompt(units: dict[str, dict], files: list[str]) -> str:
    digests = [unit_digest(units[uid]) for uid in sorted(units)]
    return (
        "You design a recursive semantic responsibility tree for a codebase, from the "
        "structured detail units below. You see no raw source: reason only from these "
        "units. Each unit carries its COMPLETE explain, extras, uncertainties and "
        "relations; all of them are authoritative for grouping decisions.\n\n"
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
        "UNITS:\n" + json.dumps(digests, ensure_ascii=False)
    )


# ------------------------------------------------------------------ render


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

    from cbe import concrete_facts

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
        from cbe import generate
        searchable = generate._query_catalog(run_dir)["symbols"]
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
