"""Tree-sitter TypeScript/TSX adapter.

The old Mac adapter validated a tree-sitter program root then extracted
declarations with regular expressions. This product walks the real syntax
tree. Regex is not used to invent symbols.
"""

from __future__ import annotations

from typing import Any, Callable
from cbe.callable_contracts import ecma_contract

from cbe.adapters.python import PAYLOAD_KINDS, compute_exclusive_spans, leftover_spans
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
    canonical_symbol_id,
    exclusive_sha256,
)


def _load_language(kind: str):
    try:
        import tree_sitter_typescript as tstypescript
        from tree_sitter import Language
    except ImportError as exc:  # pragma: no cover - environment probe
        raise RuntimeError(f"tree-sitter typescript is not importable: {exc}") from exc
    if kind == "tsx":
        return Language(tstypescript.language_tsx())
    return Language(tstypescript.language_typescript())


def make_parser(kind: str):
    from tree_sitter import Parser

    language = _load_language(kind)
    try:
        return Parser(language)
    except TypeError:
        parser = Parser()
        setter = getattr(parser, "set_language", None)
        if setter is None:
            raise
        setter(language)
        return parser


class TypeScriptAdapter:
    language = "typescript"
    backend_id = "tree_sitter_typescript"
    extension_language = {
        ".ts": "typescript",
        ".tsx": "tsx",
        ".mts": "typescript",
        ".cts": "typescript",
    }

    def __init__(self) -> None:
        self._parsers: dict[str, Any] = {}

    def _parser(self, kind: str):
        cached = self._parsers.get(kind)
        if cached is None:
            cached = make_parser(kind)
            self._parsers[kind] = cached
        return cached

    def parser_version(self) -> str:
        try:
            import tree_sitter_typescript as tstypescript

            return str(getattr(tstypescript, "__version__", "unknown"))
        except Exception:
            return "unknown"

    def parse(
        self,
        path: str,
        offsets: OffsetMap,
        content_hash: str,
        *,
        language: str | None = None,
    ) -> FileIR | TypedFailure:
        suffix = ""
        if "." in path.rsplit("/", 1)[-1]:
            suffix = "." + path.rsplit(".", 1)[-1]
        kind = "tsx" if suffix in {".tsx", ".jsx"} else "typescript"
        declared = language or self.language
        try:
            parser = self._parser(kind)
            tree = parser.parse(offsets.raw)
        except Exception as exc:
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"tree-sitter failed to parse {path}: {exc}",
                backend_id=self.backend_id,
                language=declared,
            )
        root = tree.root_node
        if getattr(root, "has_error", False):
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"syntax tree contains an error node: {path}",
                backend_id=self.backend_id,
                language=declared,
                details=("normalization stopped before emitting partial success",),
            )
        return normalize_ecma(
            path=path,
            offsets=offsets,
            content_hash=content_hash,
            root=root,
            language=declared,
            backend_id=self.backend_id,
            backend_version=self.parser_version(),
        )


def _node_text(offsets: OffsetMap, node: Any) -> str:
    return offsets.raw[node.start_byte:node.end_byte].decode("utf-8")


def _span(offsets: OffsetMap, node: Any) -> CharSpan:
    return offsets.span_from_bytes(node.start_byte, node.end_byte)


def _child_named(node: Any, field: str) -> Any | None:
    getter = getattr(node, "child_by_field_name", None)
    if getter is None:
        return None
    return getter(field)


def _identifier(offsets: OffsetMap, node: Any) -> str:
    name_node = _child_named(node, "name")
    if name_node is not None:
        return _node_text(offsets, name_node)
    for child in getattr(node, "named_children", ()):
        if child.type in {"identifier", "type_identifier", "property_identifier", "private_property_identifier"}:
            return _node_text(offsets, child)
    return ""


def _walk_named(node: Any):
    yield node
    for child in getattr(node, "named_children", ()):
        yield from _walk_named(child)


def normalize_ecma(
    *,
    path: str,
    offsets: OffsetMap,
    content_hash: str,
    root: Any,
    language: str,
    backend_id: str,
    backend_version: str,
) -> FileIR:
    module_name = path.rsplit(".", 1)[0].replace("/", ".")
    symbols: list[Symbol] = []
    relations: list[Relation] = []
    seq = 0
    text_len = len(offsets.text)

    def add_rel(**kwargs: object) -> None:
        nonlocal seq
        seq += 1
        kwargs.setdefault("id", f"{path}::rel::{seq}")
        relations.append(Relation(**kwargs))  # type: ignore[arg-type]

    def add_symbol(
        *,
        kind: str,
        name: str,
        node: Any,
        parent_id: str | None,
        scope: tuple[str, ...],
        extra: dict[str, Any] | None = None,
    ) -> Symbol:
        span = _span(offsets, node)
        lexical = ".".join((*scope, name)) if name else ".".join(scope) or "<anon>"
        symbol_id = canonical_symbol_id(path, kind, lexical, span.start)
        contract = ecma_contract(node, offsets, path, content_hash, language)
        signature = contract["header"] if contract else _node_text(offsets, node)
        newline = signature.find("\n")
        if contract is None and newline != -1:
            signature = signature[:newline].strip()
        elif contract is None:
            signature = signature.strip()
            if len(signature) > 240:
                signature = signature[:240]
        symbol = Symbol(
            id=symbol_id,
            path=path,
            language=language,
            kind=kind,
            name=name or "<anon>",
            qualified_name=".".join(part for part in (module_name, lexical) if part),
            parent_id=parent_id,
            span=span,
            exclusive_spans=(span,),
            signature=signature,
            extra={"anchor": span.start, "node_type": node.type, **(extra or {}),
                   **({"callable_contract": contract} if contract else {})},
        )
        symbols.append(symbol)
        return symbol

    CLASS_TYPES = {
        "class_declaration",
        "abstract_class_declaration",
        "class",
    }
    FUNC_TYPES = {
        "function_declaration",
        "generator_function_declaration",
        "function",
        "generator_function",
    }
    METHOD_TYPES = {
        "method_definition",
        "method_signature",
        "public_field_definition",
        "field_definition",
    }
    FIELD_METHOD_TYPES = {
        "public_field_definition",
        "field_definition",
    }
    FUNCTION_VALUE_TYPES = {
        "arrow_function",
        "function_expression",
        "generator_function",
    }
    TYPE_TYPES = {
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
    }

    def visit(
        node: Any,
        scope: tuple[str, ...],
        parent_id: str | None,
        in_class: bool,
        in_ambient: bool = False,
    ) -> None:
        ntype = node.type
        if ntype == "ambient_declaration":
            for child in node.named_children:
                visit(child, scope, parent_id, in_class, True)
            return
        if ntype in CLASS_TYPES:
            name = _identifier(offsets, node) or "<class>"
            symbol = add_symbol(kind="class", name=name, node=node, parent_id=parent_id, scope=scope)
            heritage = None
            for child in node.named_children:
                if child.type in {"class_heritage", "extends_clause", "implements_clause"}:
                    heritage = child
                    break
            if heritage is not None:
                add_rel(
                    kind="inherits",
                    subject_id=symbol.id,
                    target_id=None,
                    path=path,
                    span=_span(offsets, heritage),
                    status=ResolutionStatus.EXTERNAL,
                    method=ResolutionMethod.HEURISTIC,
                    confidence=0.5,
                    reason=_node_text(offsets, heritage).strip(),
                )
            # Named children once: heritage/decorators/params stay out of method membership.
            for child in node.named_children:
                visit(child, (*scope, name), symbol.id, child.type == "class_body")
            return
        if ntype in FUNC_TYPES:
            name = _identifier(offsets, node) or "<function>"
            kind = "method" if in_class else "function"
            extra = {}
            type_params = _child_named(node, "type_parameters")
            if type_params is not None:
                extra["generics"] = _node_text(offsets, type_params)
            if in_ambient:
                extra["ambient"] = True
            symbol = add_symbol(
                kind=kind,
                name=name,
                node=node,
                parent_id=parent_id,
                scope=scope,
                extra=extra,
            )
            for child in node.named_children:
                visit(child, (*scope, name), symbol.id, False)
            return
        if ntype == "function_signature":
            name = _identifier(offsets, node) or "<function>"
            extra: dict[str, Any] = {"declaration": True}
            type_params = _child_named(node, "type_parameters")
            if type_params is not None:
                extra["generics"] = _node_text(offsets, type_params)
            if in_ambient:
                extra["ambient"] = True
            add_symbol(
                kind="function_signature",
                name=name,
                node=node,
                parent_id=parent_id,
                scope=scope,
                extra=extra,
            )
            return
        if ntype in {"arrow_function", "function_expression", "generator_function"}:
            name_node = _child_named(node, "name")
            name = _node_text(offsets, name_node) if name_node is not None else "<arrow>"
            kind = "function" if name_node is not None else "lambda"
            # Prefer enclosing variable name when this is `const f = () =>`
            parent_var = None
            symbol = add_symbol(
                kind=kind,
                name=name,
                node=node,
                parent_id=parent_id,
                scope=scope,
                extra={"async": "async" in _node_text(offsets, node)[:20]},
            )
            for child in node.named_children:
                visit(child, (*scope, name), symbol.id, False)
            _ = parent_var
            return
        if ntype in METHOD_TYPES:
            name = _identifier(offsets, node) or "<method>"
            if ntype in FIELD_METHOD_TYPES and not any(
                child.type in FUNCTION_VALUE_TYPES for child in node.named_children
            ):
                for child in node.named_children:
                    visit(child, scope, parent_id, in_class)
                return
            extra = {}
            type_params = _child_named(node, "type_parameters")
            if type_params is not None:
                extra["generics"] = _node_text(offsets, type_params)
            symbol = add_symbol(
                kind="method",
                name=name,
                node=node,
                parent_id=parent_id,
                scope=scope,
                extra=extra,
            )
            for child in node.named_children:
                visit(child, (*scope, name), symbol.id, False)
            return
        if ntype in TYPE_TYPES:
            name = _identifier(offsets, node) or ntype
            extra = {}
            type_params = _child_named(node, "type_parameters")
            if type_params is not None:
                extra["generics"] = _node_text(offsets, type_params)
            add_symbol(
                kind="interface" if "interface" in ntype else "type_alias" if "type_alias" in ntype else "enum",
                name=name,
                node=node,
                parent_id=parent_id,
                scope=scope,
                extra=extra,
            )
            return
        if ntype in {"function_type", "constructor_type"}:
            return
        if ntype in {"import_statement", "import"}:
            add_rel(
                kind="import",
                subject_id=path,
                target_id=None,
                path=path,
                span=_span(offsets, node),
                status=ResolutionStatus.EXTERNAL,
                method=ResolutionMethod.EXACT,
                confidence=1.0,
                reason=_node_text(offsets, node).splitlines()[0].strip(),
            )
            return
        if ntype in {"export_statement", "export"}:
            add_rel(
                kind="export",
                subject_id=path,
                target_id=None,
                path=path,
                span=_span(offsets, node),
                status=ResolutionStatus.RESOLVED,
                method=ResolutionMethod.EXACT,
                confidence=1.0,
                reason=_node_text(offsets, node).splitlines()[0].strip(),
            )
            # Continue into exported declaration.
        if ntype == "call_expression":
            function = _child_named(node, "function")
            callee = _node_text(offsets, function) if function is not None else ""
            add_rel(
                kind="call",
                subject_id=parent_id or path,
                target_id=None,
                path=path,
                span=_span(offsets, node),
                status=ResolutionStatus.UNRESOLVED,
                method=ResolutionMethod.HEURISTIC,
                confidence=0.3,
                reason=f"call {callee}",
                extra={"callee": callee},
            )
        for child in node.named_children:
            visit(child, scope, parent_id, in_class, in_ambient)

    visit(root, (), None, False)

    # Bind lexical const/let functions: `export const foo = async () =>`
    _bind_variable_functions(offsets, root, path, language, module_name, symbols)

    exclusive = compute_exclusive_spans(symbols)
    for symbol in symbols:
        symbol.exclusive_spans = exclusive.get(symbol.id, (symbol.span,))
        symbol.extra["exclusive_sha256"] = exclusive_sha256(offsets.text, symbol.exclusive_spans)

    covering_kinds = PAYLOAD_KINDS | {"interface", "type_alias", "enum"}
    named_spans = [item.span for item in symbols if item.kind in covering_kinds]
    residual_spans = leftover_spans(text_len, named_spans)
    if residual_spans:
        residual_id = canonical_symbol_id(path, "module_residual", module_name, 0)
        symbols.insert(
            0,
            Symbol(
                id=residual_id,
                path=path,
                language=language,
                kind="module_residual",
                name=path.rsplit("/", 1)[-1],
                qualified_name=module_name,
                parent_id=None,
                span=CharSpan(0, text_len),
                exclusive_spans=tuple(residual_spans),
                signature=f"module {module_name}",
                extra={
                    "anchor": 0,
                    "exclusive_sha256": exclusive_sha256(offsets.text, tuple(residual_spans)),
                },
            ),
        )
        residual = symbols[0]
        for relation in relations:
            if relation.subject_id == path:
                relation.subject_id = residual.id

    record = FileRecord(
        path=path,
        language=language,
        byte_length=len(offsets.raw),
        char_length=text_len,
        content_hash=content_hash,
        decode="utf-8",
        state=SourceUnitState.INDEXED,
        parser_id=backend_id,
        parser_version=backend_version,
    )
    return FileIR(record=record, symbols=tuple(symbols), relations=tuple(relations), offsets=offsets)


def _bind_variable_functions(
    offsets: OffsetMap,
    root: Any,
    path: str,
    language: str,
    module_name: str,
    symbols: list[Symbol],
) -> None:
    """Name anonymous arrows assigned to const/let/var."""

    existing_starts = {item.span.start for item in symbols}
    for node in _walk_named(root):
        if node.type not in {"lexical_declaration", "variable_declaration"}:
            continue
        for declarator in node.named_children:
            if declarator.type != "variable_declarator":
                continue
            name_node = _child_named(declarator, "name")
            value = _child_named(declarator, "value")
            if name_node is None or value is None:
                continue
            if value.type not in {"arrow_function", "function_expression", "generator_function"}:
                continue
            name = _node_text(offsets, name_node)
            span = _span(offsets, value)
            if span.start in existing_starts:
                for symbol in symbols:
                    if symbol.span.start == span.start and symbol.kind in {"lambda", "function"}:
                        symbol.name = name
                        lexical = name
                        symbol.qualified_name = ".".join(part for part in (module_name, lexical) if part)
                        symbol.kind = "function"
                        extra = dict(symbol.extra)
                        extra["async"] = extra.get("async") or "async" in _node_text(offsets, value)[:24]
                        symbol.extra = extra
                        break
