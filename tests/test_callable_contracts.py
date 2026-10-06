from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from cbe.callable_contracts import contracts_for, prompt_contract, render_contract
from cbe.parser import ParserSet
from cbe.ir import FileIR


def parsed(path, source):
    value = ParserSet().parse_file(Path("."), path, source.encode())
    assert isinstance(value, FileIR), value
    return [s for s in value.symbols if s.extra.get("callable_contract")]


def test_python_complete_declaration_does_not_execute_defaults():
    source = '''@unknown_decorator
async def f(
 a: int, /, b=explode(), *items: str,
 required: bool, optional="a  b", **options
) -> list[str]:
 return []
g = lambda x, *, y=3: x + y
'''
    symbols = parsed("x.py", source)
    f = symbols[0].extra["callable_contract"]
    assert f["async"] and f["runtime_contract"] == "unknown"
    assert f["header"].startswith("async def f(\n")
    assert "unknown_decorator" not in f["header"] and "return []" not in f["header"]
    assert [p["kind"] for p in f["parameters"]] == ["positional_only", "positional_or_keyword", "var_positional", "keyword_only", "keyword_only", "var_keyword"]
    assert f["parameters"][1]["default_expr"] == "explode()"
    assert f["parameters"][3]["required_in_declaration"] is True
    assert f["parameters"][4]["default_expr"] == '"a  b"'
    assert f["return_annotation"] == "list[str]"
    lam = symbols[1].extra["callable_contract"]
    assert lam["header"] == "lambda x, *, y=3:"
    assert "x + y" not in symbols[1].signature
    assert "header" not in prompt_contract(f)


@pytest.mark.parametrize("suffix", ["ts", "js"])
def test_ecma_long_multiline_destructuring_default_rest_and_no_body(suffix):
    annotation = ": {value: number}" if suffix == "ts" else ""
    long_default = '"' + "long " * 80 + '"'
    source = f'''async function f(
 {{value}}{annotation}, text={long_default}, ...rest
) {{ return value; }}
const arrow = x => x + 1;
'''
    symbols = parsed("x." + suffix, source)
    f = symbols[0].extra["callable_contract"]
    assert len(f["header"]) > 240 and f["async"]
    assert "return value" not in f["header"]
    assert f["parameters"][0]["name"] == "{value}"
    assert f["parameters"][1]["default_expr"] == long_default
    assert f["parameters"][2]["kind"] == "rest"
    assert symbols[1].extra["callable_contract"]["header"] == "x =>"


def test_ts_overloads_optional_and_generics_are_declarations():
    symbols = parsed("x.ts", '''declare function f<T>(x?: T): T;
function g(x: string): string;
function g(x: number): number;
function g(x: any) { return x; }
interface I { method(x?: number): string; }
''')
    f = symbols[0].extra["callable_contract"]
    assert f["generics"] == "<T>" and f["return_annotation"] == ": T"
    assert f["parameters"][0]["optional_in_declaration"]
    assert len([s for s in symbols if s.name == "g"]) == 3
    assert all(s.extra["callable_contract"]["runtime_contract"] == "unknown" for s in symbols)


def test_historical_projection_is_hash_bound_and_leaves_inventory_unchanged(tmp_path):
    from cbe.inventory import build_inventory
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.py").write_text("def f(a, /, *, b=1):\n return a\n")
    inventory = build_inventory(repo).to_dict()
    # Simulate an old inventory without the newly derived metadata.
    for symbol in inventory["symbols"].values():
        symbol["extra"].pop("callable_contract", None)
    ledger = {"repo_root": str(repo), "source_revision": "rev-old", "inventory": inventory}
    before = copy.deepcopy(ledger)
    contracts = contracts_for(ledger)
    assert ledger == before
    assert len(contracts) == 1
    value = next(iter(contracts.values()))
    assert value["source_revision"] == "rev-old"
    assert value["content_hash"] == hashlib.sha256((repo / "x.py").read_bytes()).hexdigest()
    assert "def f(a, /, *, b=1):" in render_contract(value)
    (repo / "x.py").write_text("def f(a):\n return a\n")
    from cbe.packets import PacketSourceError
    with pytest.raises(PacketSourceError, match="hash conflict"):
        contracts_for(ledger)


def test_native_assignment_query_members_render_and_history_consumption(tmp_path):
    from test_native_handoff import _run, _record, _business_result
    from cbe.native_handoff import next_work
    from cbe.store import LedgerStore
    from cbe.runner import query
    from cbe.module_first_render import page_module_members, resolve_module_reader_target
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    ledger = LedgerStore(run).open()
    sid = next(sid for sid, s in ledger["inventory"]["symbols"].items() if s["name"] == "twice")
    early = query(run, sid)
    assert early["type"] == "symbol" and early["callable_syntax"]["runtime_contract"] == "unknown"
    packet = json.loads(Path(ledger["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
    assignment = next(a for a in packet["assignments"] if a["canonical_symbol_id"] == sid)
    assert assignment["callable_syntax"]["parameters"][0][:2] == ["value", "positional_or_keyword"]
    assert "header" not in assignment["callable_syntax"]
    for _ in range(20):
        _record(tmp_path, run, item, "started")
        _record(tmp_path, run, item, "completed", _business_result(run, item))
        result = next_work(run, owner="controller")
        if result["status"] == "complete":
            break
        item = result["items"][0]
    else:
        pytest.fail("fixture did not complete")
    before = LedgerStore(run).open()
    accepted = query(run, sid)
    assert accepted["type"] == "fact"
    assert accepted["callable_syntax"] == early["callable_syntax"]
    assert accepted["explanation_state"] != "syntax_evidenced"
    plan = json.loads((run / "module_plan.json").read_text())
    member = next(m for m in page_module_members(before, plan, accepted["module_id"])["items"] if m["symbol_id"] == sid)
    assert member["callable_syntax"] == accepted["callable_syntax"]
    target = resolve_module_reader_target(before, plan, sid)
    page = Path(result["reader_index"]).parent / target.partition("#")[0]
    assert page.read_text().count("### twice") == 1
    assert page.read_text().count("(value):") == 1
    assert result["token_budget"]["effective_document_tokens"] >= result["token_budget"]["published_tokens"]
    assert before["reader_render_diagnostics"]["syntax_projection_accounting"]["contracts"][sid]["structured_from_published_header"]
    assert LedgerStore(run).open()["calls"] == before["calls"]


def test_existing_graph_and_shared_literal_locators_do_not_assert_runtime_identity(tmp_path):
    from cbe.inventory import build_inventory
    from cbe.callable_contracts import reader_references
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.py").write_text('CHOICES = ("first", "second")\n'
                              'def helper(x):\n return x in CHOICES\n'
                              'def main(x):\n return helper(x) or x in CHOICES\n')
    (repo / "y.py").write_text('CHOICES = ("first", "second")\n'
                              'def shadow(CHOICES):\n return CHOICES\n')
    inventory = build_inventory(repo).to_dict()
    from cbe.runner import analyze
    ledger = analyze(repo, tmp_path / "run", documentation_profile="module-first-v2")
    ids = {s["name"]: sid for sid, s in inventory["symbols"].items()}
    refs = reader_references(ledger)
    assert refs[ids["main"]]["callees"][0]["target_id"] == ids["helper"]
    assert refs[ids["main"]]["callees"][0]["runtime_relation"] == "unknown"
    assert refs[ids["main"]]["declarations"] == refs[ids["helper"]]["declarations"]
    assert refs[ids["main"]]["declarations"][0]["runtime_binding"] == "unknown"
    assert not refs.get(ids["shadow"], {}).get("declarations")


def test_assignment_alias_is_lossless_for_normal_and_fragment_ids():
    from cbe.module_facts import compact_assignments
    rows = [{"symbol_id": "normal", "canonical_symbol_id": "normal", "name": "f"},
            {"symbol_id": "fragment:1", "canonical_symbol_id": "normal", "name": "f"}]
    before = copy.deepcopy(rows)
    projected = compact_assignments(rows)
    assert "canonical_symbol_id" not in projected[0]
    assert projected[1]["canonical_symbol_id"] == "normal"
    restored = [{**row, "canonical_symbol_id": row.get("canonical_symbol_id", row["symbol_id"])}
                for row in projected]
    assert restored == rows == before


def test_literal_draft_hash_alias_is_rejected_by_existing_binding(tmp_path):
    from test_native_handoff import _run, _record, _business_result
    from cbe.native_handoff import next_work, _normalize_result
    from cbe.store import LedgerStore, StaleWriteError
    run = _run(tmp_path)
    author = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, author, "started")
    _record(tmp_path, run, author, "completed", _business_result(run, author))
    review = next_work(run, owner="controller")["items"][0]
    assert review["role"] == "fact_review"
    ledger = LedgerStore(run).open()
    call = ledger["calls"][review["call_id"]]
    packet = json.loads(Path(call["extra"]["packet_path"]).read_text())
    from cbe.module_facts import _message_projection
    assert "Draft content_sha256 = envelope.input_hash" in _message_projection(packet).decode()
    bad = tmp_path / "bad-hash.json"
    bad.write_text(json.dumps({"verdict": "accepted", "checked_ids": packet["assigned_ids"],
                               "findings": [], "content_sha256": "envelope.input_hash"}))
    with pytest.raises(StaleWriteError, match="conflicting content_sha256"):
        _normalize_result(run, review["task_id"], review["call_id"], bad, packet,
                          ledger["tasks"][review["task_id"]])
    assert LedgerStore(run).open() == ledger


def test_budget_counts_true_query_semantics_without_double_counting_header(tmp_path):
    from test_module_first_render import _fixture
    from cbe.module_first_render import render_module_plan
    from cbe.token_budget import count_text_tokens
    ledger, plan = _fixture(tmp_path)
    sid = next(sid for sid, s in ledger["inventory"]["symbols"].items() if s["name"] == "first")
    detail = {"behavior": "Returns the input plus one.", "inputs_outputs": "Query-only input contract.",
              "effects": "Query-only effects.", "failures": "Query-only failures.",
              "dependencies": "Query-only dependency.", "unresolved": "Query-only uncertainty."}
    ledger["details"] = {sid: detail}
    ledger["fact_reviews"] = {sid: {"state": "source_checked", "content_sha256": hashlib.sha256(
        json.dumps(detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}}
    report = render_module_plan(ledger, plan, tmp_path / "docs", run_dir=tmp_path / "run")
    account = report["syntax_projection_accounting"]
    assert account["syntax_query_only_tokens"] == 0
    assert all(row["structured_from_published_header"] for row in account["contracts"].values())
    assert report["token_budget"]["query_only_tokens"] >= sum(
        count_text_tokens(detail[k]) for k in ("inputs_outputs", "effects", "failures", "dependencies", "unresolved"))
    from cbe.callable_contracts import query_only_syntax
    c = next(iter(contracts_for(ledger).values()))
    assert query_only_syntax(c, published=True) == {}
    assert query_only_syntax(c, published=False)["header"] == c["header"]
    limited = {**c, "status": "limited", "limitation": "unsupported parameter node"}
    assert query_only_syntax(limited, published=True)


def test_null_call_locations_have_one_public_authority_but_real_ranges_count(tmp_path):
    from test_module_first_render import _fixture
    from cbe.module_first_render import render_module_plan
    ledger, plan = _fixture(tmp_path)
    report = render_module_plan(ledger, plan, tmp_path / "docs", run_dir=tmp_path / "run")
    account = report["syntax_projection_accounting"]
    assert account["reference_query_only_tokens"] == 0
    pages = "\n".join(p.read_text() for p in (tmp_path / "docs/files").glob("*.md"))
    assert "Call-site path/range: unspecified unless shown" in pages
    edge = next(edge for edge in ledger["graph"]["edges"] if edge["kind"] == "call")
    edge.update(path="service.py", span={"start": 100, "end": 105})
    report = render_module_plan(ledger, plan, tmp_path / "located", run_dir=tmp_path / "run")
    row = report["syntax_projection_accounting"]["references"][edge["subject_id"]]
    assert row["query_only_tokens"] > 0
    assert row["query_only_fields"] == ["callee_source_ranges"]


def test_final_layout_behavior_allocation_does_not_charge_syntax_twice():
    from cbe.callable_contracts import behavior_token_recommendation
    syntax = parsed("x.py", "def f(a, b=3):\n return a\n")[0].extra["callable_contract"]
    assert behavior_token_recommendation({"tier": "deep", "suggested_output_tokens": 90,
        "allocation_basis": "behavior_display"}, syntax) == 90
    assert behavior_token_recommendation({"tier": "deep", "suggested_output_tokens": 90}, syntax) < 90


def test_ast_compact_header_preserves_strings_and_parameter_kinds():
    import ast
    source = '''async def f(
 a: str = "a  b\\n c", /,
 *, required: tuple[int, str], optional=(1, "x  y")
) -> "Result":
 return a
'''
    value = parsed("x.py", source)[0].extra["callable_contract"]
    assert value["compact_header_verified"]
    original = ast.parse(source).body[0]
    compact = ast.parse(value["compact_header"] + "\n    pass").body[0]
    assert ast.dump(original.args, include_attributes=False) == ast.dump(compact.args, include_attributes=False)
    assert ast.dump(original.returns, include_attributes=False) == ast.dump(compact.returns, include_attributes=False)
    assert value["parameters"][0]["default_expr"] == '"a  b\\n c"'
    assert "a  b" in value["compact_header"]
    commented = parsed("x.py", 'def f(\n x, # this parameter is special\n y\n):\n return x\n')[0].extra["callable_contract"]
    assert not commented["compact_header_verified"]
    assert commented["compact_header"] == commented["header"]


def test_fresh_behavior_recommendation_reserves_declared_syntax_without_gate():
    from cbe.callable_contracts import behavior_token_recommendation
    from cbe.token_budget import count_text_tokens
    contract = parsed("x.py", "def f(x: str, *, option=1) -> str:\n return x\n")[0].extra["callable_contract"]
    policy = {"tier": "deep", "suggested_output_tokens": 180}
    before = copy.deepcopy(policy)
    assert behavior_token_recommendation(policy, contract) == 180 - count_text_tokens(render_contract(contract))
    assert policy == before
    assert behavior_token_recommendation({"tier": "deep", "suggested_output_tokens": 1}, contract) == 30
    assert behavior_token_recommendation(policy, None) == 180


def test_name_bound_parameter_tail_reassembles_complete_async_declaration():
    from cbe.callable_contracts import publication_projection
    value = parsed("x.py", "async def f(x: int, /, *, option='a  b') -> str:\n return x\n")[0].extra["callable_contract"]
    projection = publication_projection(value, "f")
    assert projection["verified"] is True
    assert "a  b" in projection["text"]
    assert "async def f" + projection["text"].removeprefix("async ") == value["compact_header"]
    assert publication_projection(value, "different-local-id")["representation"] == "full_head"
    lambda_value = parsed("x.py", "fn = lambda x=1: x + 1\n")[0].extra["callable_contract"]
    assert publication_projection(lambda_value, "lambda")["representation"] == "full_head"
