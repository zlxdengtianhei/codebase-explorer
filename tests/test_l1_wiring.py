"""L1 接线：九字段 stdin、闸 1 assert、T0 回退、per-page skip、router --fallback。"""

from __future__ import annotations

import json
from pathlib import Path

from src.semantic.inventory import (
    file_out_edge_tokens,
    out_edge_revision,
    page_content_hash,
    plan_page_rewrites,
)
from src.semantic.l1_facts import (
    Effect,
    L1SymbolFact,
    failed_checks,
    run_l1_checks,
    t0_template_fact,
    try_parse_l1_fact_text,
)
from src.semantic.l1_packet import (
    ALLOWED_PACKET_FIELDS,
    L1PacketError,
    L1PacketSymbol,
    assert_packet_fields,
    build_packet_payload,
)
from src.semantic.tiering import (
    EscalationState,
    initial_tier,
    record_attempt,
    router_argv,
    should_escalate,
)


def _packet() -> L1PacketSymbol:
    return L1PacketSymbol(
        symbol_id="app.py::handle",
        path="app.py",
        kind="function",
        span=(1, 3),
        source_body="def handle(x):\n    return x\n",
        content_hash="sha256:" + "a" * 64,
        callee_signatures=(),
        language="python",
        syntax_diagnostics=(),
    )


def test_l1_packet_serialized_fields_equal_allowlist() -> None:
    rows = build_packet_payload([_packet()])
    assert set(rows[0]) == ALLOWED_PACKET_FIELDS
    assert_packet_fields(rows)


def test_l1_packet_rejects_status_fields() -> None:
    row = _packet().to_payload()
    row["module_id"] = "core"
    try:
        assert_packet_fields([row])
    except L1PacketError as exc:
        assert "module_id" in str(exc)
    else:
        raise AssertionError("expected L1PacketError")


def test_out_edge_tokens_ignore_body_literals() -> None:
    before = file_out_edge_tokens("import os\ndef f():\n    return 1\n")
    after = file_out_edge_tokens("import os\ndef f():\n    return 2\n")
    assert before == after
    changed = file_out_edge_tokens("import os\ndef f():\n    print(1)\n")
    assert out_edge_revision(before) != out_edge_revision(changed)


def test_page_rewrite_skips_unchanged_hash() -> None:
    text = "# page\nhello\n"
    digest = page_content_hash(text)
    plan = plan_page_rewrites(
        {"INDEX.md": text, "a/DETAIL.md": text + "more\n"},
        {"INDEX.md": digest},
    )
    assert plan.skip_paths == ("INDEX.md",)
    assert plan.write_paths == ("a/DETAIL.md",)


def test_t0_does_not_escalate_on_low_confidence() -> None:
    fact = t0_template_fact(
        symbol_id="app.py::f",
        source_body="def f(x):\n    return x\n",
        qualified_name="f",
        kind="function",
    )
    results = run_l1_checks(
        fact,
        source_body="def f(x):\n    return x\n",
        qualified_name="f",
        tier="T0",
    )
    assert failed_checks(results) == ()
    assert not should_escalate(
        failed_checks=(),
        confidence=fact.confidence,
        unresolved=fact.unresolved,
        tier="T0",
    )
    assert should_escalate(
        failed_checks=(),
        confidence=fact.confidence,
        unresolved=fact.unresolved,
        tier="T1",
    )


def test_escalation_keeps_attempts() -> None:
    state = EscalationState(symbol_id="app.py::f", tier="T1")
    first = record_attempt(
        state,
        failed_checks=("L1-b",),
        confidence="medium",
        unresolved=(),
        payload={"one_liner": "本函数处理请求"},
    )
    assert first.tier == "T2"
    assert len(first.attempts) == 1
    second = record_attempt(
        first,
        failed_checks=("L1-b",),
        confidence="medium",
        unresolved=(),
    )
    assert second.tier == "MANUAL"
    assert len(second.attempts) == 2
    assert second.attempts[0].payload is not None


def test_initial_tier_splits_mess_from_template() -> None:
    assert initial_tier("T3") == "T3"
    assert initial_tier("T1") == "T0"


def test_router_argv_carries_explicit_fallback() -> None:
    argv = router_argv("T1", task_name="l1-t1", workdir="/tmp")
    assert "--fallback" in argv
    assert "deepseek-go:flash" in argv
    assert router_argv("T0", task_name="l1-t0", workdir="/tmp") == ()


def test_try_parse_l1_fact_ignores_legacy_prose() -> None:
    assert try_parse_l1_fact_text("returns its computed value to its caller") is None
    fact = L1SymbolFact(
        symbol_id="app.py::f",
        one_liner="把 x 原样返回给调用方",
        behavior="恒等函数，输入 x，输出 x。",
        effects=(Effect.PURE,),
        inputs_outputs="x -> x",
        failure_modes=("无",),
        identifiers_used=("x",),
        unresolved=(),
        confidence="high",
    )
    parsed = try_parse_l1_fact_text(json.dumps(fact.to_payload(), ensure_ascii=False))
    assert parsed is not None
    assert parsed.one_liner == fact.one_liner
