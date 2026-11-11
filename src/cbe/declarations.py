"""Extract declarations and searchable signatures from syntax trees."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from cbe.grammars import (
    GrammarSpec,
    OffsetMap,
    _all_specs,
    _make_parser,
    canonical_symbol_id,
)


_IDENTIFIER_TYPES = frozenset(
    {
        "identifier",
        "type_identifier",
        "field_identifier",
        "property_identifier",
        "private_property_identifier",
        "namespace_identifier",
        "package_identifier",
        "constant",
        "operator_name",
        "destructor_name",
        "scoped_identifier",
        "simple_identifier",
    }
)

_SIGNATURE_LIMIT = 400


@dataclass
class _Declaration:
    node: Any
    kind: str
    name: str
    qualified_name: str
    parent_id: str | None
    symbol_id: str
    start_byte: int
    end_byte: int
    children: list["_Declaration"] = field(default_factory=list)
    ancestors: tuple[str, ...] = ()
    signature: str = ""
    exclusive_end_byte: int | None = None


def _text(offsets: OffsetMap, start_byte: int, end_byte: int) -> str:
    return offsets.raw[start_byte:end_byte].decode("utf-8", errors="replace")


def _node_name(offsets: OffsetMap, node: Any) -> str:
    # Field lookup first: most grammars expose the declared name as ``name``.
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(offsets, name_node.start_byte, name_node.end_byte)
    # C/C++ function declarators carry the name, not a ``name`` field.  This
    # must run before scanning children, otherwise the return type is picked.
    declarator = node.child_by_field_name("declarator")
    if declarator is not None:
        found = _first_identifier(offsets, declarator)
        if found:
            return found
    for child in node.named_children:
        if child.type in _IDENTIFIER_TYPES:
            return _text(offsets, child.start_byte, child.end_byte)
    # Go grouped ``type`` declarations nest the name in ``type_spec``.
    for child in node.named_children:
        if child.type in {"type_spec", "function_declarator", "init_declarator"}:
            found = _node_name(offsets, child)
            if found:
                return found
    return ""


def _first_identifier(offsets: OffsetMap, node: Any) -> str:
    for child in node.named_children:
        if child.type in _IDENTIFIER_TYPES or child.type in {"operator_name", "destructor_name"}:
            return _text(offsets, child.start_byte, child.end_byte)
        found = _first_identifier(offsets, child)
        if found:
            return found
    return ""


def _body_start(node: Any) -> int:
    body = node.child_by_field_name("body")
    return body.start_byte if body is not None else -1


def _declarator_name(offsets: OffsetMap, node: Any, *, type_alias: bool = False) -> str:
    if node.type == "identifier" or (type_alias and node.type == "type_identifier"):
        return _text(offsets, node.start_byte, node.end_byte)
    if node.type == "function_declarator":
        child = node.child_by_field_name("declarator")
        if not type_alias:
            # Parentheses alone do not make a function a variable: the
            # innermost name must be reached through a pointer or reference.
            if child is None or child.type != "parenthesized_declarator":
                return ""
            inner = [part for part in child.named_children if part.type != "comment"]
            if len(inner) != 1 or inner[0].type not in {"pointer_declarator", "reference_declarator"}:
                return ""
    elif node.type in {"init_declarator", "array_declarator", "pointer_declarator", "reference_declarator"}:
        child = node.child_by_field_name("declarator")
        if child is None and node.type == "reference_declarator":
            child = next(iter(node.named_children), None)
    elif node.type == "parenthesized_declarator":
        parts = [part for part in node.named_children if part.type != "comment"]
        child = parts[0] if len(parts) == 1 else None
    else:
        return ""
    return _declarator_name(offsets, child, type_alias=type_alias) if child is not None else ""


def _binding_names(offsets: OffsetMap, node: Any) -> list[str]:
    if node.type in {"identifier", "shorthand_property_identifier_pattern"}:
        return [_text(offsets, node.start_byte, node.end_byte)]
    if node.type in {"pair_pattern", "assignment_pattern", "object_assignment_pattern"}:
        field = "value" if node.type == "pair_pattern" else "left"
        binding = node.child_by_field_name(field)
        return _binding_names(offsets, binding) if binding is not None else []
    if node.type in {"object_pattern", "array_pattern", "rest_pattern"}:
        return [name for child in node.named_children for name in _binding_names(offsets, child)]
    return []


def _contains_node(node: Any, kinds: set[str]) -> bool:
    return node.type in kinds or any(_contains_node(child, kinds) for child in node.named_children)


def _c_declaration_scope(node: Any) -> bool:
    child = node
    ancestor = node.parent
    while ancestor is not None:
        if ancestor.type == "declaration_list":
            if ancestor.parent is None or ancestor.parent.type not in {"namespace_definition", "linkage_specification"}:
                return False
        elif ancestor.type == "template_declaration":
            payload = [part for part in ancestor.named_children
                       if part.type not in {"template_parameter_list", "requires_clause", "comment"}]
            if payload != [child]:
                return False
        elif ancestor.type not in {"translation_unit", "preproc_if", "preproc_ifdef", "preproc_else",
                                   "preproc_elif", "namespace_definition", "linkage_specification"}:
            return False
        child, ancestor = ancestor, ancestor.parent
    return True


def _ordinary_name(spec: GrammarSpec, offsets: OffsetMap, node: Any, scope: str | None) -> str:
    if node.type not in spec.ordinary_declaration_kinds:
        return ""
    if spec.c_declaration_rules and node.type in {"preproc_def", "preproc_function_def"}:
        name = node.child_by_field_name("name")
        return _text(offsets, name.start_byte, name.end_byte) if name is not None and not node.has_error else ""
    if scope == "function" or (scope == "class" and not spec.ordinary_in_class_scope):
        return ""
    if spec.c_declaration_rules and not _c_declaration_scope(node):
        return ""
    if spec.c_declaration_rules and node.has_error:
        # Recovery can split a macro-prefixed function into a fake variable
        # followed by its prototype, or even misidentify a macro's own name.
        return ""
    if spec.ordinary_name_style == "fields":
        return ", ".join(_node_name(offsets, child) for child in node.named_children
                         if child.type == "variable_declarator")
    if spec.ordinary_name_style == "constants":
        left = node.child_by_field_name("left")
        if left is not None and left.type in {"constant", "scope_resolution"}:
            return _text(offsets, left.start_byte, left.end_byte)
        return ""
    if spec.ordinary_name_style == "python":
        left = node.child_by_field_name("left")
        statement = node.parent
        container = statement.parent if statement is not None and statement.type == "expression_statement" else None
        if (left is None or left.type != "identifier" or container is None
                or not (container.type == "module"
                        or (container.type == "block" and container.parent is not None
                            and container.parent.type == "class_definition"))):
            return ""
        return _text(offsets, left.start_byte, left.end_byte)
    ancestor = node.parent
    while ancestor is not None:
        if ancestor.type in {"statement_block", "compound_statement", "block", "for_statement", "if_statement"}:
            return ""
        ancestor = ancestor.parent
    if spec.ordinary_name_style == "bindings":
        ancestor = node.parent
        while ancestor is not None:
            if ancestor.type not in {"lexical_declaration", "variable_declaration", "export_statement",
                                     "ambient_declaration", "declare_statement", "program"}:
                return ""
            ancestor = ancestor.parent
        siblings = list(node.parent.named_children)
        index = siblings.index(node)
        if any(child.type in spec.binding_kinds
               and (value := child.child_by_field_name("value")) is not None
               and value.type in spec.value_function_kinds for child in siblings[index + 1:]):
            return ""  # Preserve the prefix owned by the existing first function binding.
        binding = node.child_by_field_name("name")
        return ", ".join(_binding_names(offsets, binding)) if binding is not None else ""
    if spec.ordinary_name_style == "grouped_names":
        def names_in(part: Any) -> list[str]:
            if part.type in {"var_spec", "const_spec"}:
                return [_text(offsets, child.start_byte, child.end_byte)
                        for child in part.children_by_field_name("name")]
            return [name for child in part.named_children for name in names_in(child)]
        return ", ".join(names_in(node))
    if spec.c_declaration_rules and node.type in {"declaration", "type_definition"}:
        declared_type = node.child_by_field_name("type")
        if (declared_type is not None and _text(offsets, declared_type.start_byte, declared_type.end_byte)
                in spec.recovery_type_keywords):
            return ""  # C++ keywords can look like C-style variable types during recovery.
        if node.type == "declaration" and _contains_node(node, {"function_definition", "compound_statement"}):
            return ""
        names = []
        for declarator in node.children_by_field_name("declarator"):
            name = _declarator_name(offsets, declarator, type_alias=node.type == "type_definition")
            if not name:
                return ""  # Do not publish a mixed variable/function declaration either.
            names.append(name)
        return ", ".join(names)
    names = node.children_by_field_name("name")
    return ", ".join(_text(offsets, child.start_byte, child.end_byte) for child in names)


class _DeclarationExtractor:
    def __init__(self, spec: GrammarSpec, offsets: OffsetMap, root: Any, path: str) -> None:
        self.spec = spec
        self.offsets = offsets
        self.root = root
        self.path = path
        self.declarations: list[_Declaration] = []
        # C recovery may flatten C++ locals and fields directly into a header's
        # translation unit. A second tree only vetoes uncertain ordinary regions;
        # existing functions/types continue to use the original tree and identities.
        self.check_header_scope = spec.name == "c" and PurePosixPath(path).suffix.lower() == ".h" and root.has_error
        self.header_root = None
        self.cpp_spec = next((item for item in _all_specs() if item.name == "cpp"), None)
        if self.check_header_scope and self.cpp_spec is not None:
            try:
                self.header_root = _make_parser(self.cpp_spec).parse(offsets.raw).root_node
            except (ImportError, AttributeError):
                pass  # Without scope evidence, leave uncertain declarations residual.

    def header_scope_matches(self, node: Any, name: str) -> bool:
        if not self.check_header_scope or node.type in {"preproc_def", "preproc_function_def"}:
            return True
        if self.header_root is None:
            return False
        # Anchor each declared identifier, rather than the whole declaration:
        # C recovery can give namespace declarations different spans/scopes.
        def identifiers(part: Any) -> list[Any]:
            if part.type in {"identifier", "type_identifier"}:
                return [part]
            return [item for child in part.named_children for item in identifiers(child)]

        anchors = identifiers(node)
        for declared_name in name.split(", "):
            anchor = next((item for item in anchors
                           if _text(self.offsets, item.start_byte, item.end_byte) == declared_name), None)
            if anchor is None:
                return False
            counterpart = self.header_root.descendant_for_byte_range(anchor.start_byte, anchor.end_byte - 1)
            while counterpart is not None and counterpart.type not in {"declaration", "alias_declaration", "type_definition"}:
                if counterpart.type in {"parameter_list", "compound_statement", "field_declaration_list", "ERROR"}:
                    return False
                counterpart = counterpart.parent
            if (counterpart is None
                    or declared_name not in _ordinary_name(
                        self.cpp_spec, self.offsets, counterpart, None).split(", ")):
                return False
        return True

    def extract(self) -> list[_Declaration]:
        self.visit(self.root, None, None, [None])
        declarations = [decl for decl in self.declarations
                        if decl.kind != "module_region" or not any(
                            other is not decl and decl.start_byte <= other.start_byte
                            and other.end_byte <= decl.end_byte for other in self.declarations)]
        return _coalesce_declarations(self.offsets, declarations)

    def visit(
        self,
        node: Any,
        parent: _Declaration | None,
        scope: str | None,
        prefix: list[int | None],
    ) -> None:
        ntype = node.type
        if ntype in self.spec.wrappers:
            # A wrapper prefix (decorators, ``export``, ``template`` ...) belongs
            # to the first declaration the wrapper contains.  Only that first
            # declaration consumes it, so sibling declarators in a multi-binding
            # statement never copy the wrapper start and never overlap.
            start = prefix[0] if prefix[0] is not None else node.start_byte
            holder: list[int | None] = [start]
            for child in node.named_children:
                self.visit(child, parent, scope, holder)
            # Nested wrappers share ownership of the prefix. Once any inner
            # declaration consumes it, later siblings of every outer wrapper
            # must start at their own node, not at that outer wrapper's start.
            if holder[0] is None:
                prefix[0] = None
            return

        if self.spec.grouped_type_declarations and ntype == "type_declaration" and scope != "function":
            self.visit_go_type(node, parent, prefix)
            return

        if ntype in self.spec.class_kinds:
            if not _is_type_definition(self.spec, node):
                # C/C++ type reference or forward declaration: not a chunk
                # boundary, but still descend in case of nested definitions.
                for child in node.named_children:
                    self.visit(child, parent, scope, prefix)
                return
            decl = _make_declaration(
                self.offsets, node, self.path, parent, self.spec.class_kinds[ntype], prefix[0])
            prefix[0] = None
            self.declarations.append(decl)
            if parent is not None:
                parent.children.append(decl)
            child_scope = scope if decl.kind in {"namespace", "module"} or self.spec.preserve_type_scope else "class"
            for child in node.named_children:
                self.visit(child, decl, child_scope, [None])
            return

        if ntype in self.spec.function_kinds:
            declared = self.spec.function_kinds[ntype]
            kind = "method" if declared == "function" and scope == "class" else declared
            decl = _make_declaration(self.offsets, node, self.path, parent, kind, prefix[0])
            prefix[0] = None
            self.declarations.append(decl)
            if parent is not None:
                parent.children.append(decl)
            for child in node.named_children:
                self.visit(child, decl, "function", [None])
            return

        if ntype in self.spec.binding_kinds:
            value = node.child_by_field_name("value")
            if value is not None and value.type in self.spec.value_function_kinds:
                kind = "method" if scope == "class" else "function"
                decl = _make_declaration(self.offsets, node, self.path, parent, kind, prefix[0])
                prefix[0] = None
                self.declarations.append(decl)
                if parent is not None:
                    parent.children.append(decl)
                self.visit(value, decl, "function", [None])
                return
            # Function bindings retain their established extraction path.
        self.visit_ordinary(node, parent, scope, prefix)

    def visit_go_type(self, node: Any, parent: _Declaration | None, prefix: list[int | None]) -> None:
        specs = [child for child in node.named_children if child.type in {"type_spec", "type_alias"}]
        legacy = _make_declaration(self.offsets, node, self.path, parent, "type", prefix[0])
        prefix[0] = None
        for index, child in enumerate(specs):
            if index == 0:
                # Keep the existing group's canonical identity and full span.
                # Old grammars' alias-only groups may have no discovered name.
                owns_first = legacy.name == _node_name(self.offsets, child)
                legacy.exclusive_end_byte = (child.end_byte if owns_first else child.start_byte)
                if len(specs) == 1 and owns_first:
                    legacy.exclusive_end_byte = None
                self.declarations.append(legacy)
                if parent is not None:
                    parent.children.append(legacy)
                if owns_first:
                    continue
            decl = _make_declaration(self.offsets, child, self.path, parent, "module_region", None)
            self.declarations.append(decl)
            if parent is not None:
                parent.children.append(decl)

    def visit_ordinary(
        self, node: Any, parent: _Declaration | None, scope: str | None, prefix: list[int | None]
    ) -> None:
        ntype = node.type
        name = _ordinary_name(self.spec, self.offsets, node, scope)
        if self.check_header_scope and not name and ntype in {"declaration", "type_definition"}:
            ancestor = node.parent
            while ancestor is not None and ancestor.type != "function_definition":
                ancestor = ancestor.parent
            declared_type = ancestor.child_by_field_name("type") if ancestor is not None else None
            if declared_type is not None and _text(
                    self.offsets, declared_type.start_byte, declared_type.end_byte) == "namespace":
                # C calls a namespace a function and can put ERROR in its using
                # aliases. Confirm these candidates in C++, retaining C vetoes elsewhere.
                names = [_declarator_name(self.offsets, child, type_alias=ntype == "type_definition")
                         for child in node.children_by_field_name("declarator")]
                name = ", ".join(names) if names and all(names) else ""
        if name and not self.header_scope_matches(node, name):
            name = ""
        if name and ntype == "type_definition":
            defined_type = node.child_by_field_name("type")
            if (defined_type is not None and defined_type.type in self.spec.class_kinds
                    and _is_type_definition(self.spec, defined_type)):
                # The existing type owns the definition, with its original id
                # and full span. The typedef adds searchable aliases, no unit.
                first = len(self.declarations)
                for child in node.named_children:
                    self.visit(child, parent, scope, [None])
                for declaration in self.declarations[first:]:
                    if declaration.node == defined_type:
                        declaration.signature += "\n" + name
                return
        if name:
            # Discover children before committing the ordinary region. A value
            # must not wrap another unit or consume its wrapper prefix.
            first = len(self.declarations)
            holder = [prefix[0]]
            for child in node.named_children:
                self.visit(child, parent, scope, holder)
            if len(self.declarations) != first:
                prefix[0] = holder[0]
                return
            decl = _make_declaration(self.offsets, node, self.path, parent, "module_region", prefix[0],
                                     name=name.split(", ", 1)[0])
            # Search metadata holds every name, without duplicating the list in
            # inventory names and canonical ids. Do not truncate long runs.
            decl.signature = name
            prefix[0] = None
            if node.type == "variable_declarator" and node == node.parent.named_children[-1]:
                decl.end_byte = node.parent.end_byte
            self.declarations.append(decl)
            if parent is not None:
                parent.children.append(decl)
            return
        for child in node.named_children:
            self.visit(child, parent, scope, prefix)


def _extract_declarations(spec: GrammarSpec, offsets: OffsetMap, root: Any, path: str) -> list[_Declaration]:
    return _DeclarationExtractor(spec, offsets, root, path).extract()


def _coalesce_declarations(offsets: OffsetMap, declarations: list[_Declaration]) -> list[_Declaration]:
    """Combine adjacent value declarations without crossing syntax or scope boundaries."""
    def category(decl: _Declaration) -> str:
        if decl.kind != "module_region":
            return ""
        ntype = decl.node.type
        first = next((child for child in decl.node.children if child.type != "comment"), None)
        if (ntype in {"alias_declaration", "type_definition", "type_spec", "type_alias"}
                or (first is not None and _text(offsets, first.start_byte, first.end_byte) in {"typedef", "using"})):
            return ""
        if ntype in {"preproc_def", "preproc_function_def"}:
            return "macro"
        return ntype if ntype in {"declaration", "var_declaration", "const_declaration", "variable_declarator",
                                 "field_declaration", "constant_declaration", "assignment"} else ""

    def owner(decl: _Declaration) -> Any:
        node = decl.node.parent
        while node is not None and node.type in {
                "lexical_declaration", "variable_declaration", "export_statement", "expression_statement"
        }:
            node = node.parent
        return node

    result: list[_Declaration] = []
    for decl in sorted(declarations, key=lambda item: (item.start_byte, -item.end_byte)):
        previous = result[-1] if result else None
        if previous is not None and category(decl) and category(decl) == category(previous):
            gap = _text(offsets, previous.end_byte, decl.start_byte)
            gap = re.sub(r"/\*.*?\*/|//[^\n]*", "", gap, flags=re.S)
            if decl.node.type == "assignment":
                gap = re.sub(r"#[^\n]*|(?m:^=begin\b).*?^=end\b", "", gap, flags=re.S | re.M)
            if (previous.parent_id == decl.parent_id and owner(previous) == owner(decl)
                    and decl.start_byte >= previous.end_byte and not gap.strip()):
                previous.end_byte = decl.end_byte
                previous.signature += ", " + decl.signature
                continue
        result.append(decl)
    return result


def _is_type_definition(spec: GrammarSpec, node: Any) -> bool:
    """True when a C/C++ type node actually defines a body.

    ``struct Point p = {...}`` and ``class Foo;`` carry a type node without a
    body and must not split the enclosing function or introduce a chunk.
    Other grammars only emit type declaration nodes for real definitions.
    """

    if not spec.c_declaration_rules:
        return True
    return node.child_by_field_name("body") is not None


def _make_declaration(
    offsets: OffsetMap,
    node: Any,
    path: str,
    parent: _Declaration | None,
    kind: str,
    extend_start: int | None,
    *,
    name: str | None = None,
) -> _Declaration:
    start_byte = node.start_byte
    if extend_start is not None:
        start_byte = min(start_byte, extend_start)
    end_byte = node.end_byte
    name = name if name is not None else _node_name(offsets, node)
    scope = parent.qualified_name if parent is not None else ""
    qualified = f"{parent.qualified_name}.{name}" if parent is not None and name else (name or scope)
    symbol_id = canonical_symbol_id(path, kind, qualified or name, start_byte)
    ancestors = (parent.ancestors + (parent.qualified_name,)) if parent is not None else ()
    body_start = _body_start(node)
    if body_start < 0:
        body_start = start_byte
    signature = offsets.raw[start_byte:body_start].decode("utf-8", errors="replace").strip()
    if len(signature) > _SIGNATURE_LIMIT:
        signature = signature[:_SIGNATURE_LIMIT]
    return _Declaration(
        node=node,
        kind=kind,
        name=name or f"<{kind}>",
        qualified_name=qualified or name or f"<{kind}>",
        parent_id=parent.symbol_id if parent is not None else None,
        symbol_id=symbol_id,
        start_byte=start_byte,
        end_byte=end_byte,
        ancestors=ancestors,
        signature=signature,
    )


