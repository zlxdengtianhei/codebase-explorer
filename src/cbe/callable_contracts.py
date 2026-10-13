"""Frozen declaration syntax, independent of model-authored behavior acceptance.

Reuse the enrolled AST backends. No imports/evaluation of the target program and
no inference about decorators, bound methods, constructors or runtime values.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import io
import tokenize
from typing import Any

from cbe.ir import OffsetMap, ast_point_to_char, line_starts

SCHEMA = "callable-syntax/1"


def _python_signature_shape(node: ast.AST) -> str:
    fields = {"args": ast.dump(node.args, include_attributes=False),
              "async": isinstance(node, ast.AsyncFunctionDef),
              "name": getattr(node, "name", None),
              "returns": ast.dump(node.returns, include_attributes=False) if getattr(node, "returns", None) else None,
              "type_params": [ast.dump(p, include_attributes=False) for p in getattr(node, "type_params", ())]}
    return repr(fields)


def _compact_python_header(node: ast.AST, raw_header: str) -> dict:
    """Use stdlib AST formatting, then prove signature equivalence; never eval.

    Comments are retained separately, including comments inside multiline heads.
    Unsupported formatting keeps the original bytes rather than inventing success.
    """
    try:
        comments = [t.string for t in tokenize.generate_tokens(io.StringIO(raw_header + "\n    pass\n").readline)
                    if t.type == tokenize.COMMENT]
        if comments:
            # A positional comment may identify a particular parameter. Keep
            # its raw placement rather than moving prose to a different clause.
            return {"compact_header": raw_header, "compact_header_verified": False, "header_comments": []}
        declaration = copy.deepcopy(node)
        if isinstance(node, ast.Lambda):
            declaration.body = ast.Constant(None)
            text = ast.unparse(declaration)
            assert text.endswith("None")
            header = text[:-4].rstrip()
            reparsed = ast.parse(header + " None", mode="eval").body
        else:
            declaration.decorator_list = []
            declaration.body = [ast.Pass()]
            text = ast.unparse(declaration)
            header = text.rpartition("\n")[0]
            reparsed = ast.parse(header + "\n    pass\n").body[0]
        original = _python_signature_shape(node)
        assert original == _python_signature_shape(reparsed)
        return {"compact_header": header, "compact_header_verified": True,
                "signature_ast_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "header_comments": []}
    except (AssertionError, SyntaxError, ValueError, tokenize.TokenError, IndentationError):
        return {"compact_header": raw_header, "compact_header_verified": False,
                "header_comments": []}


def _base(path: str, digest: str, language: str, start: int, end: int, header: str) -> dict:
    return {"schema": SCHEMA, "status": "complete", "evidence_kind": "program_syntax",
            "source_path": path, "content_hash": digest, "language": language,
            "header_span": {"start": start, "end": end}, "header": header,
            "runtime_contract": "unknown", "parameters": [], "return_annotation": None,
            "generics": None, "async": False}


def python_contract(node: ast.AST, offsets: OffsetMap, path: str, digest: str) -> dict | None:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return None
    starts = line_starts(offsets.text)
    start = ast_point_to_char(offsets, starts, node.lineno, node.col_offset)
    first = node.body if isinstance(node, ast.Lambda) else node.body[0]
    end = ast_point_to_char(offsets, starts, first.lineno, first.col_offset)
    contract = _base(path, digest, "python", start, end, offsets.text[start:end].rstrip())
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)

    def expression(value: ast.AST | None) -> str | None:
        return ast.get_source_segment(offsets.text, value) if value is not None else None

    def parameter(arg: ast.arg, kind: str, default: ast.AST | None = None) -> dict:
        return {"name": arg.arg, "kind": kind, "annotation": expression(arg.annotation),
                "has_default": default is not None, "default_expr": expression(default),
                "required_in_declaration": default is None and kind not in {"var_positional", "var_keyword"}}

    contract["parameters"] = [parameter(arg, "positional_only" if i < len(args.posonlyargs)
                                         else "positional_or_keyword", default)
                              for i, (arg, default) in enumerate(zip(positional, defaults))]
    if args.vararg:
        contract["parameters"].append(parameter(args.vararg, "var_positional"))
    contract["parameters"].extend(parameter(arg, "keyword_only", default)
                                   for arg, default in zip(args.kwonlyargs, args.kw_defaults))
    if args.kwarg:
        contract["parameters"].append(parameter(args.kwarg, "var_keyword"))
    contract["return_annotation"] = expression(getattr(node, "returns", None))
    contract["async"] = isinstance(node, ast.AsyncFunctionDef)
    contract["generics"] = [expression(p) for p in getattr(node, "type_params", ())] or None
    contract.update(_compact_python_header(node, contract["header"]))
    return contract


def ecma_contract(node: Any, offsets: OffsetMap, path: str, digest: str, language: str) -> dict | None:
    types = {"function_declaration", "generator_function_declaration", "function_expression", "function",
             "generator_function", "arrow_function", "method_definition", "method_signature",
             "abstract_method_signature", "function_signature"}
    if node.type not in types:
        return None
    body = node.child_by_field_name("body")
    end_byte = body.start_byte if body is not None else node.end_byte
    start, end = offsets.char_of_byte(node.start_byte), offsets.char_of_byte(end_byte)
    contract = _base(path, digest, language, start, end, offsets.text[start:end].rstrip())

    def text(value: Any) -> str | None:
        return offsets.raw[value.start_byte:value.end_byte].decode("utf-8") if value is not None else None

    params = node.child_by_field_name("parameters")
    single = node.child_by_field_name("parameter")
    children = list(params.named_children) if params is not None else [single] if single is not None else []
    if params is None and single is None:
        contract.update(status="limited", limitation="Parser node has no recognized parameter field")
    for p in children:
        if p.type == "comment":
            continue
        if p.type not in {"required_parameter", "optional_parameter", "identifier", "assignment_pattern",
                          "rest_pattern", "object_pattern", "array_pattern", "this"}:
            contract.update(status="limited", limitation=f"Unsupported parameter syntax node: {p.type}")
        pattern = p.child_by_field_name("pattern") or p.child_by_field_name("left") or p
        default = p.child_by_field_name("value") or p.child_by_field_name("right")
        annotation = p.child_by_field_name("type")
        rest = pattern.type == "rest_pattern"
        optional = p.type == "optional_parameter"
        contract["parameters"].append({"name": text(pattern), "kind": "rest" if rest else "positional",
            "annotation": text(annotation), "has_default": default is not None,
            "default_expr": text(default), "optional_in_declaration": optional,
            "required_in_declaration": not (rest or optional or default is not None)})
    contract["return_annotation"] = text(node.child_by_field_name("return_type"))
    contract["generics"] = text(node.child_by_field_name("type_parameters"))
    contract["async"] = any(c.type == "async" for c in node.children)
    return contract
