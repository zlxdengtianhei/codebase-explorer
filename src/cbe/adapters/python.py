"""Python stdlib ``ast`` adapter.

Migrated knowledge (full functions read before rewrite):
- walk of FunctionDef/AsyncFunctionDef/ClassDef with enclosing kind
  from old ``PythonLanguageAdapter._module_info`` / ``_import_bindings``
- module name and relative import resolution from ``_module_name`` /
  ``_absolute_import_module``
- call/import/inherits relation shape from ``_relations``
Not migrated: cbe-ir/3 identity hashes, CallSiteInventory, capability cells,
repo-wide rglob cache, graph-sitter backends.
"""

from __future__ import annotations

import ast
import io
import platform
import tokenize
from bisect import bisect_left
from pathlib import Path
from cbe.callable_contracts import python_contract

from cbe.ir import (
    CharSpan,
    FailureCode,
    FileIR,
    FileRecord,
    OffsetMap,
    Relation,
    ResolutionMethod,
    ResolutionStatus,
    SourceUnitState,
    Symbol,
    TypedFailure,
    ast_point_to_char,
    canonical_symbol_id,
    exclusive_sha256,
    line_starts,
)

PAYLOAD_KINDS = frozenset({
    "function",
    "method",
    "class",
    "lambda",
    "function_signature",
})

_BUILTINS = frozenset({
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
    "getattr", "globals", "int", "isinstance", "len", "list", "map", "max",
    "min", "next", "object", "open", "print", "range", "repr", "reversed",
    "set", "sorted", "str", "sum", "super", "tuple", "type", "zip",
})


class PythonAdapter:
    language = "python"
    backend_id = "python_ast"
    backend_version = platform.python_version()

    def parse(
        self,
        path: str,
        offsets: OffsetMap,
        content_hash: str,
    ) -> FileIR | TypedFailure:
        try:
            tree = ast.parse(offsets.text, filename=path)
        except (SyntaxError, ValueError) as exc:
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"Python AST parse failed for {path}: {exc}",
                backend_id=self.backend_id,
                language=self.language,
                details=(type(exc).__name__,),
            )
        if not isinstance(tree, ast.Module):
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"Python adapter requires ast.Module, got {type(tree).__name__}",
                backend_id=self.backend_id,
                language=self.language,
            )
        starts = line_starts(offsets.text)
        text_len = len(offsets.text)
        module_name = _module_name(path)
        tokens = _python_tokens(offsets.raw)
        symbols: list[Symbol] = []
        index: dict[str, Symbol] = {}
        parent_map: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent_map[child] = node

        def node_span(node: ast.AST) -> CharSpan:
            start = ast_point_to_char(
                offsets, starts, getattr(node, "lineno", 1), getattr(node, "col_offset", 0)
            )
            end_line = getattr(node, "end_lineno", None) or getattr(node, "lineno", 1)
            end_col = getattr(node, "end_col_offset", None)
            if end_col is None:
                end_col = getattr(node, "col_offset", 0)
            end = ast_point_to_char(offsets, starts, end_line, end_col)
            for dec in getattr(node, "decorator_list", ()) or ():
                start = min(
                    start,
                    decorator_introducer_char(offsets, starts, tokens, dec),
                )
            return CharSpan(start, max(end, start))

        def signature_of(node: ast.AST) -> str:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                header_start = ast_point_to_char(offsets, starts, node.lineno, node.col_offset)
                if node.body:
                    first = node.body[0]
                    body_start = ast_point_to_char(offsets, starts, first.lineno, first.col_offset)
                    header = offsets.text[header_start:body_start].rstrip()
                    if header:
                        return header
            span = node_span(node)
            source = offsets.text[span.start:span.end]
            if not source:
                return node.__class__.__name__
            return source.splitlines()[0].strip()

        def decorator_names(node: ast.AST) -> tuple[str, ...]:
            names = []
            for dec in getattr(node, "decorator_list", ()):
                names.append(_expr_name(dec))
            return tuple(dict.fromkeys(names))

        def walk(
            node: ast.AST,
            scope: tuple[str, ...],
            parent_id: str | None,
            enclosing_kind: str | None,
        ) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "method" if enclosing_kind == "class" else "function"
                    lexical = ".".join((*scope, child.name))
                    qualified = ".".join(part for part in (module_name, lexical) if part)
                    span = node_span(child)
                    symbol_id = canonical_symbol_id(path, kind, lexical, span.start)
                    symbol = Symbol(
                        id=symbol_id,
                        path=path,
                        language=self.language,
                        kind=kind,
                        name=child.name,
                        qualified_name=qualified,
                        parent_id=parent_id,
                        span=span,
                        exclusive_spans=(span,),
                        signature=signature_of(child),
                        decorators=decorator_names(child),
                        extra={
                            "async": isinstance(child, ast.AsyncFunctionDef),
                            "anchor": span.start,
                            "callable_contract": python_contract(child, offsets, path, content_hash),
                        },
                    )
                    symbols.append(symbol)
                    index[symbol_id] = symbol
                    walk(child, (*scope, child.name), symbol_id, "function")
                elif isinstance(child, ast.Lambda):
                    lexical = ".".join((*scope, "<lambda>"))
                    qualified = ".".join(part for part in (module_name, lexical) if part)
                    span = node_span(child)
                    symbol_id = canonical_symbol_id(path, "lambda", lexical, span.start)
                    symbol = Symbol(
                        id=symbol_id,
                        path=path,
                        language=self.language,
                        kind="lambda",
                        name="<lambda>",
                        qualified_name=qualified,
                        parent_id=parent_id,
                        span=span,
                        exclusive_spans=(span,),
                        signature=python_contract(child, offsets, path, content_hash)["header"],
                        extra={"anchor": span.start,
                               "callable_contract": python_contract(child, offsets, path, content_hash)},
                    )
                    symbols.append(symbol)
                    index[symbol_id] = symbol
                    walk(child, (*scope, "<lambda>"), symbol_id, "function")
                elif isinstance(child, ast.ClassDef):
                    lexical = ".".join((*scope, child.name))
                    qualified = ".".join(part for part in (module_name, lexical) if part)
                    span = node_span(child)
                    symbol_id = canonical_symbol_id(path, "class", lexical, span.start)
                    symbol = Symbol(
                        id=symbol_id,
                        path=path,
                        language=self.language,
                        kind="class",
                        name=child.name,
                        qualified_name=qualified,
                        parent_id=parent_id,
                        span=span,
                        exclusive_spans=(span,),
                        signature=signature_of(child),
                        decorators=decorator_names(child),
                        extra={"anchor": span.start},
                    )
                    symbols.append(symbol)
                    index[symbol_id] = symbol
                    walk(child, (*scope, child.name), symbol_id, "class")
                else:
                    walk(child, scope, parent_id, enclosing_kind)

        walk(tree, (), None, None)

        exclusive = compute_exclusive_spans(symbols)
        for symbol in symbols:
            symbol.exclusive_spans = exclusive.get(symbol.id, (symbol.span,))
            symbol.extra["exclusive_sha256"] = exclusive_sha256(offsets.text, symbol.exclusive_spans)

        residual_spans = leftover_spans(
            text_len,
            [symbol.span for symbol in symbols if symbol.kind in PAYLOAD_KINDS],
        )
        if residual_spans:
            residual_id = canonical_symbol_id(path, "module_residual", module_name or "<module>", 0)
            residual = Symbol(
                id=residual_id,
                path=path,
                language=self.language,
                kind="module_residual",
                name=Path(path).name,
                qualified_name=module_name or path,
                parent_id=None,
                span=CharSpan(0, text_len),
                exclusive_spans=tuple(residual_spans),
                signature=f"module {module_name or path}",
                extra={
                    "anchor": 0,
                    "exclusive_sha256": exclusive_sha256(offsets.text, tuple(residual_spans)),
                },
            )
            symbols.insert(0, residual)
            index[residual_id] = residual

        relations = _relations(
            path=path,
            module_name=module_name,
            tree=tree,
            symbols=symbols,
            parent_map=parent_map,
            node_span=node_span,
        )
        record = FileRecord(
            path=path,
            language=self.language,
            byte_length=len(offsets.raw),
            char_length=text_len,
            content_hash=content_hash,
            decode="utf-8",
            state=SourceUnitState.INDEXED,
            parser_id=self.backend_id,
            parser_version=self.backend_version,
        )
        return FileIR(
            record=record,
            symbols=tuple(symbols),
            relations=tuple(relations),
            offsets=offsets,
        )


def compute_exclusive_spans(symbols: list[Symbol]) -> dict[str, tuple[CharSpan, ...]]:
    """Class/method structural spans may nest; exclusive text does not repeat."""

    by_parent: dict[str | None, list[Symbol]] = {}
    for symbol in symbols:
        by_parent.setdefault(symbol.parent_id, []).append(symbol)
    result: dict[str, tuple[CharSpan, ...]] = {}
    for symbol in symbols:
        children = [
            child
            for child in by_parent.get(symbol.id, ())
            if child.kind in PAYLOAD_KINDS
        ]
        result[symbol.id] = subtract_spans(symbol.span, [child.span for child in children])
    return result


def subtract_spans(parent: CharSpan, holes: list[CharSpan]) -> tuple[CharSpan, ...]:
    kept = [parent]
    for hole in sorted(holes, key=lambda item: (item.start, item.end)):
        next_kept: list[CharSpan] = []
        for span in kept:
            if hole.end <= span.start or hole.start >= span.end:
                next_kept.append(span)
                continue
            if span.start < hole.start:
                next_kept.append(CharSpan(span.start, hole.start))
            if hole.end < span.end:
                next_kept.append(CharSpan(hole.end, span.end))
        kept = next_kept
    return tuple(span for span in kept if span.length > 0)


def leftover_spans(text_len: int, covered: list[CharSpan]) -> list[CharSpan]:
    if text_len <= 0:
        return []
    return list(subtract_spans(CharSpan(0, text_len), covered))


def _python_tokens(raw: bytes) -> tuple[tokenize.TokenInfo, ...]:
    """Stdlib tokens for locating decorator ``@``. Does not rewrite source."""

    blob = raw if raw.endswith(b"\n") else raw + b"\n"
    try:
        return tuple(tokenize.tokenize(io.BytesIO(blob).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return ()


_DECORATOR_AT_SKIP = frozenset({
    tokenize.ENCODING,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.COMMENT,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
})


def decorator_introducer_char(
    offsets: OffsetMap,
    starts: tuple[int, ...],
    tokens: tuple[tokenize.TokenInfo, ...],
    dec: ast.AST,
) -> int:
    """Character offset of the ``@`` introducing ``dec``, else the AST expr start.

    CPython decorator nodes begin after ``@``. Parenthesized multi-line
    decorators put the expression on a later line, so subtracting 1 from
    every AST column misses ``@`` and would also shift undecorated heads.
    """

    expr_line = getattr(dec, "lineno", 1)
    expr_col = getattr(dec, "col_offset", 0)
    expr_start = ast_point_to_char(offsets, starts, expr_line, expr_col)
    expr_point = (expr_line, expr_col)
    first_at_or_after = bisect_left(tokens, expr_point, key=lambda tok: tok.start)
    for index in range(first_at_or_after - 1, -1, -1):
        tok = tokens[index]
        if tok.type in _DECORATOR_AT_SKIP:
            continue
        if tok.string == "(":
            continue
        if tok.string == "@":
            return ast_point_to_char(offsets, starts, tok.start[0], tok.start[1])
        break
    if expr_start > 0 and offsets.text[expr_start - 1] == "@":
        return expr_start - 1
    return expr_start


def _module_name(path: str) -> str:
    parts = Path(path).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _absolute_import_module(path: str, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    package = _module_name(path).split(".")[:-1]
    up = node.level - 1
    if up:
        package = package[:-up] if up <= len(package) else []
    return ".".join((*package, *((node.module or "").split(".")))).strip(".")


def _expr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _expr_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    return node.__class__.__name__


def _owner_symbol(
    node: ast.AST,
    parent_map: dict[ast.AST, ast.AST],
    def_to_symbol: dict[ast.AST, Symbol],
) -> Symbol | None:
    current: ast.AST | None = node
    while current is not None:
        if current in def_to_symbol:
            return def_to_symbol[current]
        current = parent_map.get(current)
    return None


def _relations(
    *,
    path: str,
    module_name: str,
    tree: ast.Module,
    symbols: list[Symbol],
    parent_map: dict[ast.AST, ast.AST],
    node_span,
) -> list[Relation]:
    def_to_symbol: dict[ast.AST, Symbol] = {}
    by_qualified: dict[str, Symbol] = {}
    by_name: dict[str, list[Symbol]] = {}
    for symbol in symbols:
        by_qualified[symbol.qualified_name] = symbol
        by_name.setdefault(symbol.name, []).append(symbol)

    # Reconstruct AST node → symbol by matching kind/name/span start.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            kind = (
                "class" if isinstance(node, ast.ClassDef)
                else "lambda" if isinstance(node, ast.Lambda)
                else "method" if _enclosing_class(node, parent_map) else "function"
            )
            name = getattr(node, "name", "<lambda>")
            span = node_span(node)
            for symbol in symbols:
                if symbol.kind == kind and symbol.name == name and symbol.span.start == span.start:
                    def_to_symbol[node] = symbol
                    break

    imports: dict[str, str] = {}
    relations: list[Relation] = []
    seq = 0

    def add_rel(**kwargs: object) -> None:
        nonlocal seq
        seq += 1
        kwargs.setdefault("id", f"{path}::rel::{seq}")
        relations.append(Relation(**kwargs))  # type: ignore[arg-type]

    residual = next((item for item in symbols if item.kind == "module_residual"), None)
    module_subject = residual.id if residual else path

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                imports[local] = alias.name
                add_rel(
                    kind="import",
                    subject_id=module_subject,
                    target_id=None,
                    path=path,
                    span=node_span(node),
                    status=ResolutionStatus.EXTERNAL,
                    method=ResolutionMethod.EXACT,
                    confidence=1.0,
                    reason=f"import {alias.name}",
                    extra={"module": alias.name, "local": local},
                )
        elif isinstance(node, ast.ImportFrom):
            module = _absolute_import_module(path, node)
            for alias in node.names:
                if alias.name == "*":
                    add_rel(
                        kind="import",
                        subject_id=module_subject,
                        target_id=None,
                        path=path,
                        span=node_span(node),
                        status=ResolutionStatus.AMBIGUOUS,
                        method=ResolutionMethod.HEURISTIC,
                        confidence=0.4,
                        reason="wildcard import",
                        extra={"module": module},
                    )
                    continue
                local = alias.asname or alias.name
                target = f"{module}.{alias.name}" if module else alias.name
                imports[local] = target
                add_rel(
                    kind="import",
                    subject_id=module_subject,
                    target_id=None,
                    path=path,
                    span=node_span(node),
                    status=ResolutionStatus.EXTERNAL,
                    method=ResolutionMethod.EXACT,
                    confidence=1.0,
                    reason="from-import",
                    extra={"module": module, "name": alias.name, "local": local},
                )
        elif isinstance(node, ast.ClassDef):
            subject = def_to_symbol.get(node)
            if subject is None:
                continue
            for base in node.bases:
                name = _expr_name(base)
                target_q = imports.get(name, f"{module_name}.{name}" if module_name else name)
                target = by_qualified.get(target_q)
                add_rel(
                    kind="inherits",
                    subject_id=subject.id,
                    target_id=target.id if target else None,
                    path=path,
                    span=node_span(node),
                    status=ResolutionStatus.RESOLVED if target else ResolutionStatus.EXTERNAL,
                    method=ResolutionMethod.EXACT,
                    confidence=1.0 if target else 0.6,
                    reason=f"class {node.name} extends {name}",
                    extra={"base": name},
                )

    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        owner = _owner_symbol(call, parent_map, def_to_symbol)
        subject_id = owner.id if owner else module_subject
        func_name = _expr_name(call.func)
        simple = func_name.split(".")[-1]
        status = ResolutionStatus.UNRESOLVED
        method = ResolutionMethod.HEURISTIC
        confidence = 0.3
        target_id = None
        if simple in _BUILTINS and "." not in func_name:
            status = ResolutionStatus.EXTERNAL
            method = ResolutionMethod.EXACT
            confidence = 1.0
        else:
            local = [item for item in by_name.get(simple, ()) if item.kind in {"function", "method"}]
            if len(local) == 1:
                target_id = local[0].id
                status = ResolutionStatus.RESOLVED
                method = ResolutionMethod.HEURISTIC
                confidence = 0.7
            elif len(local) > 1:
                status = ResolutionStatus.AMBIGUOUS
                confidence = 0.4
            elif simple in imports:
                status = ResolutionStatus.EXTERNAL
                method = ResolutionMethod.EXACT
                confidence = 0.8
        add_rel(
            kind="call",
            subject_id=subject_id,
            target_id=target_id,
            path=path,
            span=node_span(call),
            status=status,
            method=method,
            confidence=confidence,
            reason=f"call {func_name}",
            extra={"callee": func_name},
        )
    return relations


def _enclosing_class(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> bool:
    current = parent_map.get(node)
    while current is not None:
        if isinstance(current, ast.ClassDef):
            return True
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        current = parent_map.get(current)
    return False
