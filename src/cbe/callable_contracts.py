"""Frozen declaration syntax, independent of model-authored behavior acceptance.

Reuse the enrolled AST backends. No imports/evaluation of the target program and
no inference about decorators, bound methods, constructors or runtime values.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import io
import re
import tokenize
from pathlib import Path
from typing import Any

from cbe.ir import OffsetMap, ast_point_to_char, line_starts

SCHEMA = "callable-syntax/1"
KINDS = frozenset({"function", "method", "lambda", "function_signature"})
BOUNDARY = "Declaration syntax only; decorators, binding, class construction, inheritance and dynamic runtime signatures are not inferred."


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


def contracts_for(ledger: dict, ids: list[str] | None = None, *, frozen_files: dict | None = None) -> dict[str, dict]:
    """Read-only projection for new or historical inventories; never rebind calls.

    Missing old metadata is recomputed through ParserSet after frozen-hash
    validation. Hash/decode failures propagate; unsupported nodes stay limited.
    """
    from cbe.inventory import Inventory
    from cbe.packets import load_frozen_offsets
    from cbe.parser import ParserSet
    from cbe.ir import FileIR

    symbols = ledger["inventory"]["symbols"]
    wanted = [sid for sid in (ids if ids is not None else list(symbols))
              if sid in symbols and symbols[sid]["kind"] in KINDS]
    result = {}
    if not wanted:
        return result
    files = frozen_files if frozen_files is not None else Inventory.from_dict(ledger["inventory"]).files
    parser = ParserSet()
    for path in sorted({symbols[sid]["path"] for sid in wanted}):
        offsets = load_frozen_offsets(Path(ledger["repo_root"]), path, files[path])
        parsed = parser.parse_file(Path(ledger["repo_root"]), path, offsets.raw)
        by_id = {s.id: s for s in parsed.symbols} if isinstance(parsed, FileIR) else {}
        for sid in wanted:
            if symbols[sid]["path"] != path:
                continue
            value = (by_id[sid].extra.get("callable_contract") if sid in by_id else None)
            if value is None:
                node_type = by_id[sid].extra.get("node_type") if sid in by_id else None
                value = {"schema": SCHEMA, "status": "limited", "evidence_kind": "program_syntax",
                         "source_path": path, "content_hash": files[path].content_hash,
                         "runtime_contract": "unknown", "limitation":
                         (f"No supported callable declaration node at frozen identity (node={node_type or 'unknown'})"
                          if isinstance(parsed, FileIR) else f"Frozen parser failure: {parsed.message}")}
            result[sid] = {**value, "source_revision": ledger["source_revision"]}
    return result


def prompt_contract(contract: dict) -> dict:
    """No duplicated raw header; parameters are compact program attribution."""
    if contract["status"] != "complete":
        return {"status": "limited", "limitation": contract["limitation"]}
    return {"parameter_columns": ["name", "kind", "annotation", "default_expr", "required_in_declaration"],
            "parameters": [[p.get(k) for k in ("name", "kind", "annotation", "default_expr", "required_in_declaration")]
                           for p in contract["parameters"]],
            "return_annotation": contract["return_annotation"], "generics": contract["generics"],
            "async": contract["async"], "runtime_contract": "unknown"}


def publication_projection(contract: dict, declaration_name: str | None = None) -> dict:
    """A Python heading may supply the name once, with a token-verified tail.

    Reassembly must equal the already AST-verified complete header byte for
    byte. Comments, lambda/ECMA and nonmatching local IDs retain the full head.
    """
    header = contract.get("compact_header", contract.get("header", ""))
    if (declaration_name and contract.get("language") == "python"
            and contract.get("compact_header_verified") and not contract.get("header_comments")):
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(header + " pass\n").readline))
            definition = next(index for index, token in enumerate(tokens) if token.string == "def")
            name = tokens[definition + 1]
            if name.type == tokenize.NAME and name.string == declaration_name:
                starts = line_starts(header)
                end = starts[name.end[0] - 1] + name.end[1]
                tail = header[end:]
                prefix = ("async def " if contract.get("async") else "def ") + declaration_name
                if prefix + tail == header:
                    return {"header": header, "text": ("async " if contract.get("async") else "") + tail,
                            "representation": "python_heading_and_parameter_tail", "verified": True}
        except (StopIteration, IndexError, tokenize.TokenError):
            pass
    return {"header": header, "text": header, "representation": "full_head", "verified": False}


def render_contract(contract: dict, declaration_name: str | None = None) -> str:
    if contract["status"] != "complete":
        return "[syntax limited] " + contract["limitation"]
    # Keep whitespace inside string/default expressions exactly; Markdown may
    # contain backticks. Fences preserve multiline and arbitrary literal syntax.
    header = publication_projection(contract, declaration_name)["text"]
    if contract.get("compact_header_verified") and contract.get("header_comments"):
        header += "\n" + "\n".join(contract["header_comments"])
    if (contract.get("compact_header_verified") and "\n" not in header
            and "`" not in header and not header.startswith(" ") and not header.endswith(" ")):
        return f"`{header}`"
    fence = "`" * max(3, max((len(run) for run in re.findall(r"`+", header)), default=0) + 1)
    return f"{fence}\n{header}\n{fence}"


def behavior_token_recommendation(policy: dict, contract: dict | None) -> int | None:
    """Recommend prose after reserving syntax; never a semantic admission gate."""
    quota = policy.get("suggested_output_tokens")
    if policy.get("allocation_basis") == "behavior_display":
        # Normal final-layout preflight already includes the program syntax.
        # Deducting it again would silently shrink the author's behavior pool.
        return quota
    if quota is None or contract is None:
        return quota
    from cbe.token_budget import count_text_tokens
    floor = {"brief": 6, "standard": 15, "deep": 30}.get(policy.get("tier"), 15)
    return max(floor, int(quota) - count_text_tokens(render_contract(contract)))


def reader_references(ledger: dict, ids: list[str] | None = None) -> dict[str, dict]:
    """Expose existing graph candidates and frozen named-literal use locators.

    A syntactic reference is not proof of a runtime binding, shared mutable
    identity, execution, or successful behavioral review.
    """
    from cbe.static_literals import _frozen_source, _top_level_literals, _referenced_by_accepted_symbols
    symbols = ledger["inventory"]["symbols"]
    wanted = set(ids if ids is not None else symbols) & set(symbols)
    result: dict[str, dict] = {}
    for edge in (ledger.get("graph") or {}).get("edges") or []:
        sid, target = edge.get("subject_id"), edge.get("target_id")
        if sid not in wanted or target not in symbols:
            continue
        row = {k: edge.get(k) for k in ("kind", "target_id", "status", "method", "confidence", "reason")}
        row.update(source_path=edge.get("path"), source_span=edge.get("span"),
                   source_revision=ledger["source_revision"])
        row["evidence_kind"] = "static_graph_candidate"
        row["runtime_relation"] = "unknown"
        result.setdefault(sid, {"callees": [], "declarations": []})["callees"].append(row)
    for path in sorted({symbols[sid]["path"] for sid in wanted if symbols[sid]["path"].endswith(".py")}):
        source = _frozen_source(ledger, path)
        literals = _top_level_literals(source)
        if not literals:
            continue
        source_symbols = [(sid, symbols[sid]) for sid in wanted
                          if symbols[sid]["path"] == path and symbols[sid]["kind"] in KINDS]
        source_symbols.sort(key=lambda row: (row[1]["span"]["end"] - row[1]["span"]["start"], row[0]))
        uses, _ = _referenced_by_accepted_symbols(source, source_symbols, set(literals))
        for sid, names in uses.items():
            rows = [{"name": name, "source_path": path, "line": literals[name][1],
                     "evidence_kind": "frozen_name_reference", "runtime_binding": "unknown",
                     "source_revision": ledger["source_revision"],
                     "content_hash": ledger["inventory"]["files"][path]["content_hash"]}
                    for name in sorted(names)]
            if rows:
                result.setdefault(sid, {"callees": [], "declarations": []})["declarations"] = rows
    return result


def query_only_syntax(contract: dict, *, published: bool) -> dict:
    """Semantic delta, not the transport JSON size or model input cost.

    Complete parameters/kinds/defaults/annotations come from the very same AST
    declaration whose full header is published. Provenance is operational. A
    limited projection cannot claim this equivalence and is counted conservatively.
    """
    if published and contract["status"] == "complete":
        return {}
    fields = ("status", "header", "parameters", "return_annotation", "generics", "async",
              "limitation", "runtime_contract")
    return {k: contract[k] for k in fields if contract.get(k) not in (None, "", [])}
