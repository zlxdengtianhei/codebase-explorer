from __future__ import annotations

import pytest

from cbe.group_projection import PROJECTION_VERSION, page_group_edges, project_group_evidence


def _detail(symbol_id: str, **changes: object) -> dict:
    record = {
        "symbol_id": symbol_id,
        "behavior": "Returns a stored result.",
        "inputs_outputs": [],
        "effects": [],
        "failures": [],
        "dependencies": [],
        "unresolved": [],
        "nav_sentence": "Returns a stored result.",
        "source_spans": [{"path": "worker.py", "start_line": 10, "end_line": 12}],
        "packet_id": "packet-1",
        "input_hash": "long-hash-that-does-not-help-grouping",
        "revision": 2,
        "provenance": {"producer": "worker", "large_metadata": "x" * 200},
    }
    record.update(changes)
    return {"type": "detail", "id": symbol_id, "record": record}


def test_trivial_detail_shrinks_but_retains_stable_identity() -> None:
    document = _detail("symbol:worker.load")
    result = project_group_evidence([document], max_chars=1_000)

    assert result.ok
    assert result.payload is not None
    assert result.payload["projection_version"] == PROJECTION_VERSION
    assert result.payload["children"] == [{
        "type": "detail",
        "id": "symbol:worker.load",
        "revision": 2,
        "behavior": "Returns a stored result.",
        "inputs_outputs": [],
        "effects": [],
        "failures": [],
        "dependencies": [],
        "unresolved": [],
    }]
    assert "large_metadata" not in str(result.payload)


def test_failure_effect_and_unknown_remain_explicit() -> None:
    document = _detail(
        "symbol:worker.retry",
        behavior="Retries the request after a delay.",
        effects=["Writes the retry counter before sending a message."],
        failures=["Raises Reject when the request was revoked."],
        unresolved=None,
    )
    result = project_group_evidence([document], max_chars=2_000)

    assert result.ok
    assert result.payload is not None
    child = result.payload["children"][0]
    assert child["effects"] == ["Writes the retry counter before sending a message."]
    assert child["failures"] == ["Raises Reject when the request was revoked."]
    assert "unresolved" in child and child["unresolved"] is None


def test_group_uses_structured_evidence_and_not_recursive_body() -> None:
    document = {
        "type": "group",
        "id": "group:worker-runtime",
        "record": {
            "group_id": "group:worker-runtime",
            "version": 3,
            "question_answered": "How are requests executed?",
            "body": "Detailed child prose. " * 100,
            "member_ids": ["symbol:worker.retry"],
            "children": ["group:trace"],
            "entry_routes": ["symbol:worker.retry"],
            "relations": [{"kind": "call", "subject_id": "symbol:worker.retry", "target_id": "symbol:trace.run"}],
            "extra": {"evidence_summary": {
                "behavior": "Coordinates worker requests and traces.",
                "effects": ["Acknowledges completed requests."],
                "failures": ["Rejects revoked requests."],
                "unresolved": None,
            }},
        },
    }
    result = project_group_evidence([document], max_chars=3_000)

    assert result.ok
    assert result.payload is not None
    child = result.payload["children"][0]
    assert child["id"] == "group:worker-runtime"
    assert child["behavior"] == "Coordinates worker requests and traces."
    assert child["failures"] == ["Rejects revoked requests."]
    assert child["unresolved"] is None
    assert "Detailed child prose" not in str(result.payload)
    assert child["member_count"] == 1
    assert child["child_count"] == 1


def test_group_without_summary_returns_gap_instead_of_guessing() -> None:
    document = {
        "type": "group",
        "id": "group:opaque",
        "record": {"group_id": "group:opaque", "question_answered": "Why?", "body": "Raises when cancelled."},
    }
    result = project_group_evidence([document], max_chars=1_000)

    assert result.payload is None
    assert result.residual == ({"code": "missing_group_evidence_summary", "id": "group:opaque"},)


def test_missing_failure_field_in_group_summary_is_a_gap() -> None:
    document = {
        "type": "group",
        "id": "group:incomplete",
        "record": {
            "group_id": "group:incomplete",
            "extra": {"evidence_summary": {
                "behavior": "Runs requests.", "effects": [], "unresolved": None,
            }},
        },
    }
    result = project_group_evidence([document], max_chars=1_000)

    assert result.payload is None
    assert result.residual == ({
        "code": "incomplete_group_evidence_summary",
        "id": "group:incomplete",
        "fields": ["failures"],
    },)


def test_long_input_and_edges_report_exact_over_budget_without_truncation() -> None:
    document = _detail("symbol:large", behavior="Necessary detail. " * 100)
    edges = {"internal": [
        {"kind": "call", "subject_id": "symbol:large", "target_id": f"symbol:{i}", "status": "resolved"}
        for i in range(30)
    ]}
    result = project_group_evidence([document], edges=edges, max_chars=180)

    assert result.payload is None
    assert result.chars > 180
    assert result.residual[0]["code"] == "group_projection_over_budget"
    assert result.residual[0]["required_chars"] == result.chars
    assert result.residual[0]["child_ids"] == ["symbol:large"]
    assert result.residual[0]["edge_counts"] == {"internal": 30}


def test_graph_overflow_keeps_child_facts_and_returns_queryable_summary() -> None:
    document = _detail(
        "symbol:worker.retry",
        behavior="Retries a request.",
        failures=["Raises Reject when revoked."],
    )
    edges = {
        "internal": [
            {"kind": "call", "subject_id": "symbol:worker.retry", "target_id": f"symbol:helper.{i}", "status": "resolved"}
            for i in range(30)
        ],
        "boundary": [
            {"kind": "call", "subject_id": "symbol:worker.retry", "target_id": "symbol:external", "status": "unknown"}
        ],
    }
    result = project_group_evidence([document], edges=edges, max_chars=1_300)

    assert result.payload is not None
    assert result.chars <= 1_300
    assert result.payload["children"][0]["failures"] == ["Raises Reject when revoked."]
    summary = result.payload["edges"]
    assert summary["mode"] == "summary"
    assert summary["sections"]["internal"]["total"] == 30
    assert summary["sections"]["boundary"]["by_status"] == {"unknown": 1}
    assert summary["per_child"]["symbol:worker.retry"] == {"boundary": 1, "internal": 30}
    assert "symbol:helper.29" not in str(summary)
    gap = result.residual[0]
    assert gap["code"] == "group_edges_summarized"
    assert gap["omitted_edge_count"] == 31
    assert gap["exact_evidence_request"]["input_ids"] == ["symbol:worker.retry"]
    assert gap["exact_evidence_request"]["pages"]["internal"] == {"offset": 0, "limit": 100, "total": 30}


def test_group_leaf_mapping_makes_per_child_edge_counts_exact() -> None:
    group = {
        "type": "group", "id": "group:worker",
        "record": {
            "group_id": "group:worker", "version": 1, "member_ids": ["symbol:worker.retry"],
            "children": [], "relations": [], "entry_routes": ["symbol:worker.retry"],
            "extra": {"evidence_summary": {
                "behavior": "Runs worker requests.", "effects": [], "failures": [], "unresolved": None,
            }},
        },
    }
    edges = {"internal": [
        {"kind": "call", "subject_id": "symbol:worker.retry", "target_id": f"symbol:helper.{i}"}
        for i in range(25)
    ]}
    result = project_group_evidence(
        [group], edges=edges, child_members={"group:worker": ["symbol:worker.retry"]}, max_chars=1_250
    )

    assert result.payload is not None
    assert result.payload["edges"]["per_child"]["group:worker"] == {"internal": 25}
    assert result.payload["edges"]["unmapped_group_ids"] == []


def test_token_budget_uses_exact_supplied_counter() -> None:
    result = project_group_evidence(
        [_detail("symbol:x")],
        max_chars=10_000,
        max_tokens=12,
        count_tokens=len,
    )
    assert result.payload is None
    assert result.tokens == result.chars
    assert result.residual[0]["code"] == "group_projection_over_budget"
    assert result.residual[0]["required_tokens"] == result.tokens


def test_edges_deduplicate_without_dropping_counts_or_unknown_reason() -> None:
    edge = {
        "kind": "call", "subject_id": "symbol:x", "target_id": None,
        "status": "unknown", "reason": "Dynamic target cannot be resolved",
    }
    result = project_group_evidence(
        [_detail("symbol:x")],
        edges={"unknown": [edge, edge]},
        max_chars=3_000,
    )

    assert result.ok
    assert result.payload is not None
    projected = result.payload["edges"]["unknown"]
    assert projected["total"] == 2
    assert projected["items"] == [{**edge, "count": 2}]


def test_malformed_relation_is_explicit_gap() -> None:
    result = project_group_evidence(
        [_detail("symbol:x")], edges={"internal": ["symbol:x -> symbol:y"]}, max_chars=1_000
    )

    assert result.payload is None
    assert result.residual == ({"code": "invalid_group_edge", "section": "internal", "index": 0},)


def test_exact_edge_page_filters_group_leaves_and_exposes_next_page() -> None:
    ledger = {
        "source_revision": "frozen-revision",
        "details": {ident: {} for ident in ("a", "b", "c")},
        "groups": {"g": {"member_ids": ["a", "b"], "children": []}},
        "graph": {
            "edges": [
                {"kind": "call", "subject_id": "b", "target_id": "c"},
                {"kind": "call", "subject_id": "a", "target_id": "b"},
                {"kind": "call", "subject_id": "c", "target_id": "b"},
            ],
            "unknown_edges": [
                {"kind": "call", "subject_id": "a", "target_id": None, "reason": "dynamic target"},
            ],
        },
    }
    first = page_group_edges(ledger, input_ids=["g"], section="boundary", offset=0, limit=1)
    second = page_group_edges(ledger, input_ids=["g"], section="boundary", offset=1, limit=1)
    internal = page_group_edges(ledger, input_ids=["g"], section="internal")
    unknown = page_group_edges(ledger, input_ids=["g"], section="unknown")

    assert first["source_revision"] == "frozen-revision"
    assert first["input_ids"] == ["g"]
    assert first["total"] == 2
    assert first["next_offset"] == 1
    assert second["next_offset"] is None
    assert {item["subject_id"] for item in first["items"] + second["items"]} == {"b", "c"}
    assert internal["total"] == 1
    assert internal["items"][0]["target_id"] == "b"
    assert unknown["total"] == 1
    assert unknown["items"][0]["reason"] == "dynamic target"


def test_exact_edge_page_rejects_missing_or_cyclic_membership() -> None:
    ledger = {
        "details": {"a": {}},
        "groups": {"g": {"member_ids": ["missing"], "children": []}},
        "graph": {"edges": []},
    }
    with pytest.raises(ValueError, match="unknown group member"):
        page_group_edges(ledger, input_ids=["g"], section="internal")
    ledger["groups"]["g"] = {"member_ids": [], "children": ["g"]}
    with pytest.raises(ValueError, match="cycle"):
        page_group_edges(ledger, input_ids=["g"], section="internal")
