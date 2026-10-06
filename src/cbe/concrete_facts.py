"""Deterministic concrete facts frozen from Python syntax.

Parameter defaults, named constants, flattened option tables, format
templates and literal raises are projected with the stdlib ``ast`` alone:
the source is parsed, never executed, and no model is consulted.  Fact text
is source syntax with a line number, not a verified runtime value.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Iterator

PROJECTION_VERSION = "concrete-facts/1"

MAX_TEXT_CHARS = 160
MAX_CONSTANT_ITEMS = 12
MAX_TABLE_DEPTH = 6

KIND_ORDER = ("param_default", "constant", "option", "template", "raise")

# Placeholder grammars: str.format braces, %-named and single-letter %-codes.
# ``{{``/``%%`` escapes are excluded by the lookaround guards.
_BRACE_PLACEHOLDER = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)(?::[^{}]*)?\}(?!\})")
_PERCENT_NAMED = re.compile(r"%\(([A-Za-z_][A-Za-z0-9_]*)\)[#0\- +]*\d*(?:\.\d+)?[A-Za-z%]")
_PERCENT_BARE = re.compile(r"(?<!%)%[A-Za-z]")


def _capped(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_TEXT_CHARS:
        return text, False
    return text[: MAX_TEXT_CHARS - 1] + "…", True


def _fact(kind: str, symbol: str, text: str, line: int,
          placeholders: list[str] | None = None) -> dict[str, Any]:
    capped, truncated = _capped(text)
    row: dict[str, Any] = {"kind": kind, "symbol": symbol, "text": capped, "line": line}
    if placeholders:
        row["placeholders"] = placeholders
    if truncated:
        row["truncated"] = True
    return row


def _placeholders(literal: str) -> list[str]:
    """Unique placeholder tokens in source order, as written."""
    tokens: list[str] = []
    for pattern in (_BRACE_PLACEHOLDER, _PERCENT_NAMED, _PERCENT_BARE):
        for match in pattern.finditer(literal):
            if match.group(0) not in tokens:
                tokens.append(match.group(0))
    return tokens


def _bind_counts(stmts: list[ast.stmt]) -> dict[str, int]:
    """Direct rebinding counts for one scope; nested scopes are not walked."""
    counts: dict[str, int] = {}
    for stmt in stmts:
        targets: list[ast.expr] = []
        if isinstance(stmt, ast.Assign):
            targets = list(stmt.targets)
        elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            targets = [stmt.target]
        for target in targets:
            for node in ast.walk(target):
                if isinstance(node, ast.Name):
                    counts[node.id] = counts.get(node.id, 0) + 1
    return counts


def _assigned_names(stmt: ast.stmt) -> tuple[list[str], ast.expr | None]:
    if isinstance(stmt, ast.Assign) and all(
            isinstance(target, ast.Name) for target in stmt.targets):
        return [target.id for target in stmt.targets], stmt.value
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return [stmt.target.id], stmt.value
    return [], None


def _constant_text(value: ast.expr) -> str | None:
    """Render a small literal assignment; tables and sets stay out."""
    try:
        literal = ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return None
    if isinstance(literal, (tuple, list, dict)) and len(literal) > MAX_CONSTANT_ITEMS:
        return None
    if isinstance(literal, (set, frozenset, bytes, complex)):
        return None
    return ast.unparse(value)


def _table_entries(node: ast.expr) -> list[tuple[str, ast.expr]] | None:
    """Direct (key, value) pairs of a dict literal or a table-shaped call.

    Shape only: ``{...}``, ``dict(...)`` and bare-name all-keyword calls
    such as ``Namespace(...)``.  ``**`` seeds, starred args, non-string
    dict keys and attribute calls are not tables.
    """
    if isinstance(node, ast.Dict):
        pairs: list[tuple[str, ast.expr]] = []
        for key, item in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value):
                return None
            pairs.append((key.value, item))
        return pairs
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if any(keyword.arg is None for keyword in node.keywords):
            return None
        if any(isinstance(arg, ast.Starred) for arg in node.args) or len(node.args) > 1:
            return None
        pairs = []
        if node.args:
            seed = _table_entries(node.args[0])
            if seed is None:
                return None
            pairs.extend(seed)
        if not node.keywords and not pairs:
            return None
        pairs.extend((keyword.arg, keyword.value) for keyword in node.keywords)
        return pairs
    return None


def _flatten_table(node: ast.expr, prefix: str, out: list[tuple[str, ast.expr]],
                   depth: int = 0) -> bool:
    """Flatten nested tables into (dotted path, leaf) pairs.

    Returns False when ``node`` is not a table; the caller keeps such a
    node whole as one leaf instead of losing the enclosing table.
    """
    if depth > MAX_TABLE_DEPTH:
        return False
    pairs = _table_entries(node)
    if pairs is None:
        return False
    for key, item in pairs:
        path = f"{prefix}.{key}" if prefix else key
        if not _flatten_table(item, path, out, depth + 1):
            out.append((path, item))
    return True


def _table_leaves(name: str, value: ast.expr) -> list[tuple[str, ast.expr]]:
    """Table leaves for one assignment, or [] when the value is not a table.

    A flattened shape counts as an option table only when it has at least
    two entries and real structure: a call value (``dict(...)`` itself or
    ``Option(...)`` leaves) or a nested level in some path.  Flat literal
    dicts stay constants.
    """
    out: list[tuple[str, ast.expr]] = []
    if not _flatten_table(value, "", out):
        return []
    if len(out) < 2:
        return []
    structured = (isinstance(value, ast.Call)
                  or any("." in path for path, _ in out)
                  or any(isinstance(leaf, ast.Call) for _, leaf in out))
    return out if structured else []


def _signature_text(name: str, args: ast.arguments) -> str | None:
    """Render ``name(a, b=default, *, c=default)``; None without any default."""
    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    parts: list[str] = []
    for arg, default in zip(positional, defaults):
        parts.append(arg.arg if default is None else f"{arg.arg}={ast.unparse(default)}")
    if args.posonlyargs:
        parts.insert(len(args.posonlyargs), "/")
    if args.vararg or args.kwonlyargs:
        parts.append(f"*{args.vararg.arg}" if args.vararg else "*")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        parts.append(arg.arg if default is None else f"{arg.arg}={ast.unparse(default)}")
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
    if not any(default is not None for default in defaults) and not any(
            default is not None for default in args.kw_defaults):
        return None
    return f"{name}({', '.join(parts)})"


def _raise_text(node: ast.Raise) -> str | None:
    """``raise Error('literal message')`` only; unraised and formatted args stay out."""
    if not isinstance(node.exc, ast.Call) or not node.exc.args:
        return None
    message = node.exc.args[0]
    if not (isinstance(message, ast.Constant) and isinstance(message.value, str)):
        return None
    return f"raise {ast.unparse(node.exc)}"


def _own_statements(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[ast.stmt]:
    """Statements of one function body, excluding nested defs and classes."""
    stack: list[ast.stmt] = list(reversed(node.body))
    while stack:
        current = stack.pop()
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield current
        stack.extend(reversed(list(ast.iter_child_nodes(current))))


class _Collector:
    """Gather facts per kind, tagged with the catalogue symbol they belong to.

    The owner is None for file-level facts or the catalogue signature name
    (``function``, ``Class`` or ``Class.method``) for symbol-level facts.
    """

    def __init__(self) -> None:
        self.buckets: dict[str, list[tuple[str | None, dict[str, Any]]]] = {
            kind: [] for kind in KIND_ORDER
        }

    def add(self, kind: str, owner: str | None, fact: dict[str, Any]) -> None:
        self.buckets[kind].append((owner, fact))

    def result(self) -> dict[str, Any]:
        ordered = [(owner, fact) for kind in KIND_ORDER for owner, fact in self.buckets[kind]]
        symbols: dict[str, list[dict[str, Any]]] = {}
        for owner, fact in ordered:
            if owner is not None:
                symbols.setdefault(owner, []).append(fact)
        return {
            "file": [fact for owner, fact in ordered if owner is None],
            "symbols": symbols,
            "rows": [fact for _, fact in ordered],
        }

    def visit_module(self, tree: ast.Module) -> None:
        binds = _bind_counts(tree.body)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit_function(node, node.name)
            elif isinstance(node, ast.ClassDef):
                self.visit_class(node)
            else:
                self.visit_assignment(node, None, binds)

    def visit_class(self, node: ast.ClassDef) -> None:
        binds = _bind_counts(node.body)
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit_function(child, f"{node.name}.{child.name}")
            else:
                self.visit_assignment(child, node.name, binds, prefix=node.name)

    def visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, owner: str) -> None:
        signature = _signature_text(node.name, node.args)
        if signature is not None:
            self.add("param_default", owner,
                     _fact("param_default", node.name, signature, node.lineno))
        positional = [*node.args.posonlyargs, *node.args.args]
        defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
        for arg, default in [*zip(positional, defaults),
                             *zip(node.args.kwonlyargs, node.args.kw_defaults)]:
            self._visit_default(arg.arg, default, node)
        statements = list(_own_statements(node))
        local_binds = _bind_counts(statements)
        for statement in statements:
            if isinstance(statement, ast.Raise):
                text = _raise_text(statement)
                if text is not None:
                    self.add("raise", owner,
                             _fact("raise", node.name, text, statement.lineno))
                continue
            self.visit_assignment(statement, owner, local_binds)

    def _visit_default(self, name: str, default: ast.expr | None,
                       node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if (isinstance(default, ast.Constant) and isinstance(default.value, str)
                and _placeholders(default.value)):
            self.add("template", node.name, _fact(
                "template", name, ast.unparse(default), node.lineno,
                placeholders=_placeholders(default.value)))

    def visit_assignment(self, stmt: ast.stmt, owner: str | None,
                         binds: dict[str, int], prefix: str | None = None) -> None:
        names, value = _assigned_names(stmt)
        if value is None:
            return
        for name in names:
            if binds.get(name, 0) > 1:
                continue
            symbol = f"{prefix}.{name}" if prefix else name
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                placeholders = _placeholders(value.value)
                if placeholders:
                    self.add("template", owner, _fact(
                        "template", symbol, ast.unparse(value), stmt.lineno,
                        placeholders=placeholders))
                    continue
            leaves = _table_leaves(name, value)
            if leaves:
                for path, leaf in leaves:
                    self.add("option", owner, _fact(
                        "option", f"{symbol}.{path}", ast.unparse(leaf), leaf.lineno))
                continue
            constant = _constant_text(value)
            if constant is not None:
                self.add("constant", owner, _fact(
                    "constant", symbol, constant, stmt.lineno))


def file_facts(path: str, source: str) -> dict[str, Any]:
    """Extract the concrete facts of one Python file.

    Returns ``{"file": [...], "symbols": {...}, "rows": [...]}``.  Symbol
    keys mirror ``generate._signatures`` (top-level ``name`` and
    ``Class.method``); ``rows`` is every fact in kind priority order.
    """
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return {"file": [], "symbols": {}, "rows": []}
    collector = _Collector()
    collector.visit_module(tree)
    return collector.result()
