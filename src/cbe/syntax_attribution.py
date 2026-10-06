"""Program-verified syntax attribution for inert Python declarations.

This is deliberately weaker than a model source review: imports and class
creation can have runtime effects.  The result says only what AST syntax is
present in the frozen exclusive spans.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
from typing import Any

from cbe.static_literals import _frozen_source

CONTRACT = "syntax-attribution/1"


def _structural_container(node: ast.ClassDef, ledger: dict, sid: str,
                          source: str) -> list[str] | None:
    """Prove declaration ownership, never the member bodies' behavior."""
    if node.bases or node.decorator_list or node.keywords or node.type_params:
        return None
    symbols = ledger["inventory"]["symbols"]
    members = []
    for statement in node.body:
        if isinstance(statement, ast.Pass) or (
            isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            continue
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
        args = statement.args
        if (statement.decorator_list or args.defaults or any(x is not None for x in args.kw_defaults)
            or statement.returns or statement.type_params
            or any(a.annotation for a in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                                          *([args.vararg] if args.vararg else []),
                                          *([args.kwarg] if args.kwarg else [])])):
            return None
        start = _offset(source, statement.lineno, statement.col_offset)
        matches = [ident for ident, item in symbols.items()
                   if item.get("parent_id") == sid and item.get("kind") in {"method", "function"}
                   and item.get("path") == symbols[sid]["path"]
                   and item.get("span", {}).get("start") == start]
        if len(matches) != 1:
            return None
        members.append(matches[0])
    return sorted(members) if members else None


def _offset(source: str, line: int, column: int) -> int:
    lines = source.splitlines(keepends=True)
    return sum(len(text) for text in lines[: line - 1]) + len(
        lines[line - 1].encode("utf-8")[:column].decode("utf-8")
    )


def _inside(node: ast.AST, spans: list[dict[str, int]], source: str) -> bool:
    start = _offset(source, node.lineno, node.col_offset)
    end = _offset(source, node.end_lineno, node.end_col_offset)
    return any(span["start"] <= start and end <= span["end"] for span in spans)


def _overlaps(node: ast.AST, spans: list[dict[str, int]], source: str) -> bool:
    start = _offset(source, node.lineno, node.col_offset)
    end = _offset(source, node.end_lineno, node.end_col_offset)
    return any(start < span["end"] and span["start"] < end for span in spans)


def _literal_assignment(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        if not all(isinstance(target, ast.Name) for target in node.targets):
            return False
        value = node.value
    elif isinstance(node, ast.AnnAssign):
        if not isinstance(node.target, ast.Name):
            return False
        value = node.value
    else:
        return False
    if value is None:
        return False
    try:
        ast.literal_eval(value)
        return True
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False


def _plain_class(node: ast.ClassDef, tree: ast.Module) -> bool:
    if node.decorator_list or node.keywords or node.type_params \
            or any(not isinstance(base, ast.Name) for base in node.bases):
        return False
    rebound: set[str] = set()
    for statement in tree.body:
        if statement is node:
            continue
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            rebound.add(statement.name)
        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
            rebound.update(alias.asname or alias.name.split(".")[0]
                           for alias in statement.names)
        elif isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            rebound.update(item.id for target in targets for item in ast.walk(target)
                           if isinstance(item, ast.Name))
    for base in node.bases:
        builtin = getattr(builtins, base.id, None)
        if base.id in rebound or not isinstance(builtin, type) \
                or not issubclass(builtin, BaseException):
            return False
    for child in node.body:
        if isinstance(child, ast.Pass):
            continue
        if isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant) \
                and isinstance(child.value.value, str):
            continue
        if _literal_assignment(child):
            continue
        return False
    return True


def syntax_attribution(ledger: dict[str, Any], sid: str) -> dict[str, Any] | None:
    """Classify only frozen exclusive spans with declaration-only AST nodes."""
    symbol = ledger["inventory"]["symbols"][sid]
    if symbol["kind"] in {"function", "method", "lambda"}:
        return None
    path = symbol["path"]
    if not path.endswith(".py"):
        return None
    source = _frozen_source(ledger, path)
    spans = symbol.get("exclusive_spans") or [symbol["span"]]
    tree = ast.parse(source)
    if symbol["kind"] == "class":
        nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
                 and _offset(source, node.lineno, node.col_offset) == symbol["span"]["start"]]
        if len(nodes) != 1:
            return None
        node = nodes[0]
        members = _structural_container(node, ledger, sid, source)
        if members is not None:
            behavior = (f"Program syntax locator: declares class {node.name}. "
                        "Member behavior is documented separately; canonical_member_ids locates it. "
                        "This proves declaration ownership only; "
                        "it does not summarize member algorithms or assert runtime construction effects.")
        elif _inside(node, spans, source) and _plain_class(node, tree):
            bases = ", ".join(base.id for base in node.bases) or "none"
            behavior = (
            f"Program syntax evidence: declares class {node.name} with bare base "
            f"names ({bases}), no decorators or metaclass; body contains only "
            "docstring/pass or literal assignments. This does not assert base "
            "identity or runtime construction effects."
            )
        else:
            return None
        line = node.lineno
    elif symbol["kind"] == "module_residual":
        nodes = [node for node in tree.body if _overlaps(node, spans, source)]
        if not nodes or any(not _inside(node, spans, source) for node in nodes):
            return None
        kinds: list[str] = []
        for node in nodes:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                kind = "import statements"
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str):
                kind = "docstring literals"
            elif _literal_assignment(node):
                kind = "literal assignments"
            elif isinstance(node, ast.Pass):
                kind = "pass statements"
            else:
                return None
            if kind not in kinds:
                kinds.append(kind)
        behavior = (
            "Program syntax evidence: module residual contains only "
            + ", ".join(kinds)
            + ". This states source syntax only; imports may execute code and "
              "literal bindings are not verified runtime values."
        )
        line = nodes[0].lineno
    else:
        return None
    return {
        "symbol_id": sid, "behavior": behavior,
        **({"canonical_member_ids": members} if symbol["kind"] == "class" and members is not None else {}),
        "inputs_outputs": None, "effects": None, "failures": None,
        "dependencies": None, "unresolved": None,
        "source_spans": [{"path": path, "start": span["start"], "end": span["end"]}
                         for span in spans],
        "provenance": {
            "source_refs": [{"path": path, "line": line}],
            "fact_contract": CONTRACT,
            "source_revision": ledger["source_revision"],
            "frozen_content_sha256": ledger["inventory"]["files"][path]["content_hash"],
            "evidence_kind": "program_syntax",
        },
    }
