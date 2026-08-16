"""L1 判据的负对照：每条检查各喂一个**已知该红**的输入，确认它真的红。

r003 的教训逐字：七条判据没有一条在「已知该红」的产物上跑过，
**一条从不变红的判据，它的绿不携带信息**。

所以每条检查配一对样本：
- `negative` —— 已知该红。它变绿 = 这条检查是装饰。
- `positive` —— 已知该绿。它变红 = 这条检查会误伤，同样不可用。

只有两侧都如预期，这条检查才算**有判别力**（discriminating）。一个 `return True`
的空壳检查会在 negative 上露馅，一个 `return False` 的会在 positive 上露馅。

跑法（两条等价，第二条同时把读数落盘）::

    .venv/bin/python -m pytest tests/test_l1_negative_control.py -q
    .venv/bin/python tests/test_l1_negative_control.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.semantic.gates import (  # noqa: E402
    GateBlocked,
    assert_prompt_dispatchable,
    collect_gate3_result,
    scan_text,
)
from src.semantic.l1_facts import (  # noqa: E402
    Effect,
    L1SymbolFact,
    check_l1a_identifier_closure,
    check_l1b_name_restatement,
    check_l1c_gap_consistency,
    check_l1d_schema,
)
from src.semantic.l1_packet import (  # noqa: E402
    L1PacketError,
    L1PacketSymbol,
    assert_packet_fields,
)


EVIDENCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "runs"
    / "r004_20260816_layered_architecture"
    / "evidence"
    / "core"
    / "negative_control_L1.json"
)

_SOURCE_BODY = (
    "def handle_request(self, environ, start_response):\n"
    "    ctx = self.request_context(environ)\n"
    "    ctx.push()\n"
    "    return self.full_dispatch_request()\n"
)
_QUALIFIED_NAME = "Flask.handle_request"


def _fact(**overrides: Any) -> L1SymbolFact:
    base: dict[str, Any] = {
        "symbol_id": "app.py::Flask.handle_request",
        "one_liner": "把 WSGI environ 包成请求上下文压栈后交给完整分发流程",
        "behavior": "构造 request_context，压入上下文栈，再调用完整分发流程返回响应。",
        "effects": (Effect.MUTATES_SELF,),
        "inputs_outputs": "输入 environ 与 start_response，输出分发结果。",
        "failure_modes": ("上下文压栈失败时向上抛出",),
        "identifiers_used": ("request_context", "full_dispatch_request"),
        "unresolved": (),
        "confidence": "high",
    }
    base.update(overrides)
    return L1SymbolFact(**base)


def _packet_row(**overrides: Any) -> dict[str, Any]:
    row = L1PacketSymbol(
        symbol_id="app.py::Flask.handle_request",
        path="app.py",
        kind="method",
        span=(1, 4),
        source_body=_SOURCE_BODY,
        content_hash="sha256:" + "0" * 64,
        callee_signatures=(("app.py::Flask.full_dispatch_request", "def full_dispatch_request(self)"),),
        language="python",
        syntax_diagnostics=(),
    ).to_payload()
    row.update(overrides)
    return row


# --- 每条检查的一对样本：negative 该红，positive 该绿 -------------------------


def _control_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def record(check: str, case: str, description: str, red: bool, detail: str) -> None:
        expected_red = case == "negative"
        rows.append(
            {
                "check": check,
                "case": case,
                "input": description,
                "expected": "RED" if expected_red else "GREEN",
                "observed": "RED" if red else "GREEN",
                "as_expected": red == expected_red,
                "detail": detail,
            }
        )

    # 闸 1 结构闸
    try:
        assert_packet_fields([_packet_row(module_id="flask.app")])
        record("gate1", "negative", "packet row 多带 module_id", False, "未抛异常")
    except L1PacketError as exc:
        record("gate1", "negative", "packet row 多带 module_id", True, str(exc))
    try:
        assert_packet_fields([_packet_row()])
        record("gate1", "positive", "packet row 恰好九字段", False, "")
    except L1PacketError as exc:  # pragma: no cover - 只在回归时触发
        record("gate1", "positive", "packet row 恰好九字段", True, str(exc))

    missing_row = _packet_row()
    missing_row.pop("callee_signatures")
    try:
        assert_packet_fields([missing_row])
        record("gate1", "negative", "packet row 少了 callee_signatures", False, "未抛异常")
    except L1PacketError as exc:
        record("gate1", "negative", "packet row 少了 callee_signatures", True, str(exc))

    # 闸 2 提问闸
    blocked_prompt = "逐符号阅读源码，给出可观察行为、系统角色、输入输出与副作用。"
    try:
        assert_prompt_dispatchable(blocked_prompt, subject="negative-control")
        record("gate2", "negative", "prompt 含「系统角色」", False, "未抛异常")
    except GateBlocked as exc:
        record("gate2", "negative", "prompt 含「系统角色」", True, str(exc))
    clean_prompt = "逐符号阅读源码，给出这段代码做什么、输入输出与副作用、失败条件。"
    verdict = scan_text(clean_prompt)
    record(
        "gate2",
        "positive",
        "prompt 只问局部行为",
        verdict.blocked,
        f"decision={verdict.decision}",
    )

    # L1-a 标识符封闭
    negative_a = check_l1a_identifier_closure(
        _fact(identifiers_used=("request_context", "totally_absent_helper")),
        source_body=_SOURCE_BODY,
    )
    record("L1-a", "negative", "identifiers_used 含源码里不存在的名字", not negative_a.passed, negative_a.detail)
    positive_a = check_l1a_identifier_closure(_fact(), source_body=_SOURCE_BODY)
    record("L1-a", "positive", "identifiers_used 全部出现在源码里", not positive_a.passed, positive_a.detail)

    # L1-b 名字复述
    negative_b = check_l1b_name_restatement(
        _fact(one_liner="本函数处理与请求相关的逻辑"), qualified_name=_QUALIFIED_NAME
    )
    record("L1-b", "negative", "one_liner 只复述符号名与通用动词", not negative_b.passed, negative_b.detail)
    positive_b = check_l1b_name_restatement(_fact(), qualified_name=_QUALIFIED_NAME)
    record("L1-b", "positive", "one_liner 说了名字以外的东西", not positive_b.passed, positive_b.detail)
    exempt_b = check_l1b_name_restatement(
        _fact(one_liner="本函数处理与请求相关的逻辑"), qualified_name=_QUALIFIED_NAME, tier="T0"
    )
    record("L1-b", "positive", "T0 模板层豁免（同一句复述在 T0 应放行）", not exempt_b.passed, exempt_b.detail)

    # L1-c 空缺一致
    negative_c = check_l1c_gap_consistency(_fact(confidence="low", unresolved=()))
    record("L1-c", "negative", "confidence=low 而 unresolved 为空", not negative_c.passed, negative_c.detail)
    positive_c = check_l1c_gap_consistency(
        _fact(confidence="low", unresolved=("LOCAL_SEMANTICS_UNCLEAR",))
    )
    record("L1-c", "positive", "confidence=low 且写明空缺", not positive_c.passed, positive_c.detail)

    # L1-d schema
    leaked = _fact().to_payload()
    leaked["role"] = "核心调度入口"
    negative_d = check_l1d_schema(leaked)
    record("L1-d", "negative", "输出面多带 role 字段", not negative_d.passed, negative_d.detail)
    truncated = _fact().to_payload()
    truncated.pop("unresolved")
    negative_d2 = check_l1d_schema(truncated)
    record("L1-d", "negative", "输出面少了 unresolved 字段", not negative_d2.passed, negative_d2.detail)
    positive_d = check_l1d_schema(_fact().to_payload())
    record("L1-d", "positive", "输出面恰好九字段", not positive_d.passed, positive_d.detail)

    # 闸 3 语义抽检的折账逻辑
    gate3_negative = collect_gate3_result(
        [{"index": 1, "verdict": "有", "quote": "是整个框架的核心入口"}], ["app.py::Flask.handle_request"]
    )
    record(
        "gate3",
        "negative",
        "判定者判「有」并引原句",
        gate3_negative.violation_rate > 0,
        json.dumps(gate3_negative.as_dict(), ensure_ascii=False),
    )
    gate3_positive = collect_gate3_result(
        [{"index": 1, "verdict": "无", "quote": ""}], ["app.py::Flask.handle_request"]
    )
    record(
        "gate3",
        "positive",
        "判定者判「无」",
        gate3_positive.violation_rate > 0,
        json.dumps(gate3_positive.as_dict(), ensure_ascii=False),
    )
    gate3_unquoted = collect_gate3_result(
        [{"index": 1, "verdict": "有", "quote": ""}], ["app.py::Flask.handle_request"]
    )
    record(
        "gate3",
        "positive",
        "判「有」但不引原句 → 降级为判不了（不可复算的判决不驱动升档）",
        gate3_unquoted.violation_rate > 0,
        json.dumps(gate3_unquoted.as_dict(), ensure_ascii=False),
    )

    return rows


def build_report() -> dict[str, Any]:
    rows = _control_rows()
    by_check: dict[str, dict[str, bool]] = {}
    for row in rows:
        slot = by_check.setdefault(row["check"], {"negative_red": False, "positive_green": False})
        if row["case"] == "negative" and row["observed"] == "RED":
            slot["negative_red"] = True
        if row["case"] == "positive" and row["observed"] == "GREEN":
            slot["positive_green"] = True
    discriminating = {
        check: bool(slot["negative_red"] and slot["positive_green"]) for check, slot in by_check.items()
    }
    return {
        "doc": (
            "每条 L1 判据的负对照（已知该红）与正对照（已知该绿）实测读数。"
            "discriminating=false 的检查不可用：要么是装饰（永不变红），要么会误伤（永远变红）。"
        ),
        "controls": rows,
        "discriminating": discriminating,
        "summary": {
            "total_cases": len(rows),
            "as_expected": sum(row["as_expected"] for row in rows),
            "all_checks_discriminating": all(discriminating.values()),
        },
    }


# --- pytest -----------------------------------------------------------------


@pytest.mark.parametrize("row", _control_rows(), ids=lambda row: f"{row['check']}-{row['case']}-{row['input'][:18]}")
def test_control_behaves_as_expected(row: dict[str, Any]) -> None:
    assert row["as_expected"], f"{row['check']} {row['case']} expected {row['expected']}, got {row['observed']}: {row['detail']}"


def test_every_check_is_discriminating() -> None:
    report = build_report()
    non_discriminating = [check for check, ok in report["discriminating"].items() if not ok]
    assert not non_discriminating, f"checks without discriminating power: {non_discriminating}"


def main() -> int:
    report = build_report()
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"] | {"discriminating": report["discriminating"]}, ensure_ascii=False, indent=2))
    print(f"written: {EVIDENCE_PATH}")
    return 0 if report["summary"]["all_checks_discriminating"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
