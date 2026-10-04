"""Small frozen Python statement atoms, without executing code or proving paths.

An atom names syntax and lexical enclosing guards. It does not assert path
feasibility, a callee's effects, or runtime binding. IDs bind statement+guard.
"""
from __future__ import annotations
import ast
import hashlib
import json
from functools import lru_cache

from cbe.static_literals import _frozen_source, _offset

BOUNDARY = "Frozen statement syntax and lexical guards only; reachability, runtime binding and dynamic effects unknown."


@lru_cache(maxsize=8)
def _parsed_source(source: str) -> ast.Module:
    # Per-process pure parsing cache. Every caller still rechecks frozen bytes
    # before reaching this cache; no ledger or source evidence is cached.
    return ast.parse(source)


@lru_cache(maxsize=8)
def _line_table(source: str) -> tuple[list[str], list[int]]:
    lines = source.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    return lines, starts


def _position(source: str, line: int, column: int) -> int:
    lines, starts = _line_table(source)
    return starts[line - 1] + len(lines[line - 1].encode("utf-8")[:column].decode("utf-8"))


@lru_cache(maxsize=8)
def _function_index(source: str) -> dict:
    index = {}
    for node in ast.walk(_parsed_source(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            index.setdefault(node.name, []).append((node, _position(source, node.lineno, node.col_offset),
                _position(source, node.end_lineno, node.end_col_offset)))
    return index


def atoms_for(ledger: dict, sid: str, spans: list[dict] | None = None,
              *, max_atoms: int = 8) -> dict:
    if max_atoms < 1:
        raise ValueError("max_atoms must be positive")
    symbol = ledger.get("inventory", {}).get("symbols", {}).get(sid)
    if not symbol or not symbol["path"].endswith(".py") or symbol["kind"] not in {"function", "method"}:
        return {"status": "limited", "boundary": BOUNDARY, "atoms": []}
    source = _frozen_source(ledger, symbol["path"])
    own = symbol["span"]
    candidates = [node for node, start, end in _function_index(source).get(symbol["name"], [])
        if own["start"] <= start and end <= own["end"]]
    if len(candidates) != 1:
        return {"status": "limited", "boundary": BOUNDARY, "atoms": []}
    allowed = spans or [own]
    rows = []
    def visit(node, guards):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        kind = None
        if isinstance(node, ast.Return):
            if node.value is None or isinstance(node.value, ast.Constant) and node.value.value is None:
                kind = "return_none"
            elif guards or any(isinstance(part, ast.BoolOp) for part in ast.walk(node.value)):
                kind = "return_expression"
        elif isinstance(node, ast.Raise):
            kind = "raise_expression" if node.exc is not None else "reraise"
        elif isinstance(node, ast.AugAssign):
            kind = "update"
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "append":
            kind = "append_call"
        start = _position(source, node.lineno, node.col_offset) if kind else -1
        end = _position(source, node.end_lineno, node.end_col_offset) if kind else -1
        if kind and any(span["start"] <= start and end <= span["end"] for span in allowed):
            text = ast.unparse(node)
            # Keep complete atom syntax or explicitly disclose a skipped atom;
            # truncating expressions could change their meaning.
            if len(text) <= 240 and all(len(g) <= 120 for g in guards):
                row = {"kind": kind, "syntax": text, "guards": guards, "line": node.lineno}
                row["id"] = hashlib.sha256(json.dumps([sid, row], sort_keys=True).encode()).hexdigest()[:16]
                rows.append(row)
            else:
                rows.append(None)
        if isinstance(node, ast.If):
            test_start = _position(source, node.test.lineno, node.test.col_offset)
            test_end = _position(source, node.test.end_lineno, node.test.end_col_offset)
            test = ast.unparse(node.test) if any(s["start"] <= test_start and test_end <= s["end"] for s in allowed) else "condition outside owned view: unknown"
            for child in node.body:
                visit(child, [*guards, test])
            for child in node.orelse:
                visit(child, [*guards, f"not ({test})"])
            return
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            expression = node.test if isinstance(node, ast.While) else node.iter
            first = _position(source, expression.lineno, expression.col_offset)
            last = _position(source, expression.end_lineno, expression.end_col_offset)
            visible = any(s["start"] <= first and last <= s["end"] for s in allowed)
            loop = ("while " + ast.unparse(expression) if isinstance(node, ast.While) else
                    "for " + ast.unparse(node.target) + " in " + ast.unparse(expression)) if visible else "loop condition outside owned view: unknown"
            for child in node.body:
                visit(child, [*guards, loop])
            for child in node.orelse:
                visit(child, [*guards, "loop exhausted without break"])
            return
        if isinstance(node, ast.ExceptHandler):
            visible = node.type is None or any(s["start"] <= _position(source, node.type.lineno, node.type.col_offset)
                and _position(source, node.type.end_lineno, node.type.end_col_offset) <= s["end"] for s in allowed)
            guards = [*guards, "except " + ((ast.unparse(node.type) if node.type else "any") if visible else "type outside owned view: unknown")]
        for child in ast.iter_child_nodes(node):
            visit(child, guards)
    for node in candidates[0].body:
        visit(node, [])
    visible = [row for row in rows if row is not None][:max_atoms]
    return {"status": "partial" if len(visible) != len(rows) else "complete_for_supported_statement_kinds",
            "boundary": BOUNDARY, "atoms": visible, "omitted_atom_count": len(rows) - len(visible)}


def check_atom_refs(ledger: dict, sid: str, refs: object, spans: list[dict]) -> None:
    if refs is None:
        return
    if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs) or len(refs) != len(set(refs)):
        raise ValueError("syntax_atom_refs must be unique atom IDs")
    ids = {atom["id"] for atom in atoms_for(ledger, sid, spans)["atoms"]}
    if not set(refs) <= ids:
        raise ValueError("syntax_atom_refs contain an unpresented or foreign frozen statement/guard")


def assignment_facts(ledger: dict, sid: str, spans: list[dict] | None = None) -> dict:
    projection = atoms_for(ledger, sid, spans)
    if not projection["atoms"] and not projection.get("omitted_atom_count"):
        return {}
    return {"syntax_atoms": projection["atoms"], "syntax_atoms_omitted": projection.get("omitted_atom_count", 0)}


def reader_facts(ledger: dict, sid: str) -> dict:
    facts = atoms_for(ledger, sid)
    return facts if facts["atoms"] or facts.get("omitted_atom_count") else {}
