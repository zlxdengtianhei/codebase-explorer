"""Small numeric values and immutable diagnostic enums used by accepted facts.

These are mechanically verified source values, not model-authored or
individually source-checked claims.  They never execute the frozen source.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROJECTION_VERSION = "static-source-literals/3"
MAX_LITERAL_CHARS = 160
MAX_MAP_ITEMS = 12
MAX_RETURN_KEYS = 16
MAX_ENUM_ITEMS = 16


def _numeric(value: Any) -> bool:
    return type(value) in {int, float}


def _short_numeric(value: Any) -> bool:
    if _numeric(value):
        return len(str(value)) <= MAX_LITERAL_CHARS
    return (
        isinstance(value, dict) and 0 < len(value) <= MAX_MAP_ITEMS
        and all(isinstance(key, str) and _numeric(item)
                for key, item in value.items())
        and len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        <= MAX_LITERAL_CHARS
    )


def _short_source_literal(value: Any) -> bool:
    # Immutable finite string tuples often define exact diagnostic/branch
    # choices. Preserve them mechanically instead of making an author repeat
    # their values. Arbitrary lists, expressions and long catalogues stay out.
    return _short_numeric(value) or (
        isinstance(value, tuple) and 0 < len(value) <= MAX_ENUM_ITEMS
        and all(isinstance(item, str) and item for item in value)
        and len(set(value)) == len(value)
        and len(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) <= MAX_LITERAL_CHARS
    )


def _top_level_literals(source: str) -> dict[str, tuple[Any, int]]:
    """Reject ambiguous rebinding and every expression outside literal_eval."""
    candidates: dict[str, tuple[Any, int]] = {}
    counts: dict[str, int] = {}
    def target_names(target: ast.AST) -> list[str]:
        return [item.id for item in ast.walk(target) if isinstance(item, ast.Name)]

    for node in ast.parse(source).body:
        names: list[str] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            names = [name for target in node.targets for name in target_names(target)]
            # Chain assignments share the entire RHS; destructuring does not.
            # Keep its rebinding count, but never assign that entire value to
            # each unpacked name or to an attribute/subscript target.
            value = node.value if all(isinstance(target, ast.Name) for target in node.targets) else None
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = target_names(node.target)
            value = node.value
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            names = target_names(node.target)
        for name in names:
            counts[name] = counts.get(name, 0) + 1
            if value is None:
                continue
            try:
                literal = ast.literal_eval(value)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                continue
            if _short_source_literal(literal):
                candidates[name] = (literal, node.lineno)
    return {name: data for name, data in candidates.items()
            if counts[name] == 1}


def _referenced_by_accepted_symbols(
    source: str, symbols: list[tuple[str, dict[str, Any]]],
    candidate_names: set[str],
) -> tuple[dict[str, set[str]], set[str]]:
    """Find static Name loads in accepted executable spans, conservatively.

    A local shadow, module rebinding or apparent container mutation is not
    resolved into a runtime value.  Such names are withheld altogether.
    """
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    declaration_nodes = {
        node for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    }
    unsafe: set[str] = set()
    binding_cache: dict[tuple[ast.AST, str], bool] = {}

    def scope_binds(scope: ast.AST, name: str) -> bool:
        key = (scope, name)
        if key not in binding_cache:
            binding_cache[key] = _scope_binds(scope, name)
        return binding_cache[key]

    def scopes(node: ast.AST) -> list[ast.AST]:
        result: list[ast.AST] = []
        while node in parents:
            node = parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                                 ast.ClassDef, ast.ListComp, ast.SetComp,
                                 ast.DictComp, ast.GeneratorExp)):
                result.append(node)
        return result

    def root_name(node: ast.AST) -> str | None:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            unsafe.update(set(node.names) & candidate_names)
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if node.id not in candidate_names:
                continue
            if not scopes(node) and not any(
                declaration in (node, *list(parents_of(node, parents)))
                for declaration in declaration_nodes
            ):
                unsafe.add(node.id)
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
            name = root_name(node)
            if name in candidate_names:
                unsafe.add(name)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            name = root_name(node.func.value)
            if name in candidate_names and node.func.attr not in {"get", "items", "keys", "values", "copy"}:
                unsafe.add(name)

    source_lines = source.splitlines(keepends=True)
    line_starts = [0]
    for line in source_lines:
        line_starts.append(line_starts[-1] + len(line))
    by_symbol: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
            continue
        if node.id not in candidate_names or node.id in unsafe:
            continue
        node_scopes = scopes(node)
        if not node_scopes:
            continue
        if any(scope_binds(scope, node.id) for scope in node_scopes):
            unsafe.add(node.id)
            continue
        try:
            column = len(source_lines[node.lineno - 1]
                         .encode("utf-8")[:node.col_offset].decode("utf-8"))
            offset = line_starts[node.lineno - 1] + column
        except (IndexError, UnicodeDecodeError):
            continue
        for sid, symbol in symbols:
            span = symbol.get("span") or {}
            if span.get("start", -1) <= offset < span.get("end", -1):
                by_symbol.setdefault(sid, set()).add(node.id)
                break
    return {sid: names - unsafe for sid, names in by_symbol.items()}, unsafe


def parents_of(node: ast.AST, parents: dict[ast.AST, ast.AST]):
    while node in parents:
        node = parents[node]
        yield node


def _scope_binds(scope: ast.AST, name: str) -> bool:
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        args = scope.args
        parameters = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        if args.vararg:
            parameters.append(args.vararg)
        if args.kwarg:
            parameters.append(args.kwarg)
        if name in {arg.arg for arg in parameters}:
            return True
    return any(isinstance(node, ast.Name) and node.id == name
               and isinstance(node.ctx, (ast.Store, ast.Del))
               for node in ast.walk(scope))


def _frozen_source(ledger: dict[str, Any], path: str) -> str:
    root = Path(ledger["repo_root"]).resolve()
    file = root / path
    resolved = file.resolve()
    if not resolved.is_relative_to(root) or file.is_symlink() or not file.is_file():
        raise ValueError(f"frozen source file unavailable or outside repo: {path}")
    record = ((ledger.get("inventory") or {}).get("files") or {}).get(path) or {}
    expected = record.get("content_hash")
    if not isinstance(expected, str) or not expected:
        raise ValueError(f"missing frozen content_hash: {path}")
    raw = file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"frozen source hash mismatch: {path}")
    return raw.decode("utf-8")


def _described_elsewhere(value: Any, prose: str) -> bool:
    """Avoid a second printed table when accepted prose already lists it."""
    if isinstance(value, tuple):
        return all(item in prose for item in value)
    if not isinstance(value, dict):
        return False
    return all(re.search(rf"\b{re.escape(key)}\b\W{{0,4}}{re.escape(str(item))}\b", prose)
               for key, item in value.items())


def accepted_numeric_literals(ledger: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Project accepted facts' named, frozen numeric values and string enums.

    The mapping is keyed by the mentioning symbol id.  A named literal is
    emitted once per file even when several accepted facts mention it.
    """
    symbols = ((ledger.get("inventory") or {}).get("symbols") or {})
    reviews = ledger.get("fact_reviews") or {}
    mentions: dict[str, list[tuple[str, str]]] = {}
    prose_by_file: dict[str, list[str]] = {}
    for sid, detail in sorted((ledger.get("details") or {}).items()):
        symbol = symbols.get(sid)
        review = reviews.get(sid) or {}
        if not isinstance(symbol, dict) or not isinstance(detail, dict):
            continue
        if review.get("state") not in {"source_checked", "batch_accepted", "mechanically_validated"}:
            continue
        digest = hashlib.sha256(json.dumps(
            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        if review.get("content_sha256") != digest:
            continue
        path = symbol.get("path")
        if not isinstance(path, str) or not path.endswith(".py"):
            continue
        prose = str(detail.get("behavior") or "")
        mentions.setdefault(path, []).append((sid, prose))
        prose_by_file.setdefault(path, []).append(prose)
    result: dict[str, list[dict[str, Any]]] = {}
    for path, rows in sorted(mentions.items()):
        source = _frozen_source(ledger, path)
        literals = _top_level_literals(source)
        source_symbols = [(sid, symbols[sid]) for sid, _ in rows]
        references, unsafe = _referenced_by_accepted_symbols(
            source, source_symbols, set(literals)
        )
        all_prose = " ".join(prose_by_file[path])
        emitted: set[str] = set()
        for sid, prose in rows:
            for name, (value, line) in sorted(literals.items()):
                if name in emitted or name in unsafe or not name.isupper():
                    continue
                if not (re.search(rf"\b{re.escape(name)}\b", prose)
                        or name in references.get(sid, set())):
                    continue
                if _described_elsewhere(value, all_prose):
                    continue
                result.setdefault(sid, []).append({
                    "name": name, "value": value, "path": path, "line": line,
                    "evidence_kind": "frozen_source_literal",
                })
                emitted.add(name)
    return result


def compact_literal(record: dict[str, Any]) -> str:
    """A single short, source-located reader line."""
    value = record["value"]
    if isinstance(value, dict):
        rendered = ", ".join(f"{key}={item}" for key, item in value.items())
    else:
        rendered = str(value)
    return f"L{record['line']} [literal]: {record['name']} {{{rendered}}}" if isinstance(value, dict) else (
        f"L{record['line']} [literal]: {record['name']}={rendered}"
    )


def _offset(source: str, line: int, column: int) -> int:
    lines = source.splitlines(keepends=True)
    return sum(len(piece) for piece in lines[:line - 1]) + len(
        lines[line - 1].encode("utf-8")[:column].decode("utf-8")
    )


def _own_returns(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Return]:
    result: list[ast.Return] = []

    def visit(current: ast.AST) -> None:
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Return):
                result.append(child)
            else:
                visit(child)

    visit(node)
    return result


def _return_function_index(source: str) -> dict[str, list[tuple[ast.AST, int, int]]]:
    """One parse and linear source-position index per validated file/view."""
    lines = source.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    def position(line, column):
        return starts[line - 1] + len(lines[line - 1].encode("utf-8")[:column].decode("utf-8"))
    result = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.setdefault(node.name, []).append((node, position(node.lineno, node.col_offset),
                position(node.end_lineno, node.end_col_offset)))
    return result


def _literal_return_keys(source: str, symbol: dict[str, Any], *, function_index: dict | None = None) -> dict[str, Any] | None:
    """Project only identical string keys of every direct return-dict statement."""
    span = symbol.get("span") or {}
    start, end = span.get("start"), span.get("end")
    if type(start) is not int or type(end) is not int:
        return None
    index = function_index if function_index is not None else _return_function_index(source)
    candidates = [node for node, node_start, node_end in index.get(symbol.get("name"), [])
                  if start <= node_start and node_end <= end]
    if len(candidates) != 1:
        return None
    returns = _own_returns(candidates[0])
    if not returns:
        return None
    first: list[str] | None = None
    for node in returns:
        value = node.value
        if not isinstance(value, ast.Dict) or not value.keys:
            return None
        keys = [item.value for item in value.keys
                if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        if len(keys) != len(value.keys) or len(keys) != len(set(keys)):
            return None
        if len(keys) > MAX_RETURN_KEYS or sum(len(key) for key in keys) > 240:
            return None
        if first is None:
            first = keys
        elif set(keys) != set(first):
            return None
    return {"keys": first, "line": returns[0].lineno,
            "statement_count": len(returns),
            "evidence_kind": "frozen_return_dict_keys"}


def accepted_return_keys(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Frozen syntax projection for accepted executable facts only."""
    symbols = ((ledger.get("inventory") or {}).get("symbols") or {})
    reviews = ledger.get("fact_reviews") or {}
    result: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    function_indexes: dict[str, dict] = {}
    for sid, detail in sorted((ledger.get("details") or {}).items()):
        symbol = symbols.get(sid) or {}
        review = reviews.get(sid) or {}
        if symbol.get("kind") not in {"function", "method"} or not isinstance(detail, dict):
            continue
        if review.get("state") not in {"source_checked", "batch_accepted", "mechanically_validated"}:
            continue
        digest = hashlib.sha256(json.dumps(
            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        if review.get("content_sha256") != digest:
            continue
        path = symbol.get("path")
        if not isinstance(path, str) or not path.endswith(".py"):
            continue
        if path not in sources:
            sources[path] = _frozen_source(ledger, path)
            function_indexes[path] = _return_function_index(sources[path])
        record = _literal_return_keys(sources[path], symbol, function_index=function_indexes[path])
        if record is None or all(key in str(detail.get("behavior") or "") for key in record["keys"]):
            continue
        result[sid] = {"path": path, **record}
    return result


def compact_return_keys(record: dict[str, Any]) -> str:
    return f"L{record['line']} [return keys]: " + ", ".join(record["keys"])
