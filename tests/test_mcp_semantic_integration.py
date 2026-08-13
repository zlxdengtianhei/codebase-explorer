"""End-to-end semantic lifecycle tests through the real MCP transport."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from mcp import types
from mcp.shared.memory import create_connected_server_and_client_session

from src.semantic.service import (
    REVIEW_EVENTS_RELPATH,
    REVIEW_VERDICT_RELPATH,
    SemanticService,
)
from src.server import mcp


EXPECTED_TOOL_NAMES = {
    "analyze_codebase",
    "get_semantic_progress",
    "claim_semantic_batch",
    "submit_semantic_batch",
    "get_semantic_review_batch",
    "submit_semantic_review",
    "get_structure",
    "get_modules",
    "get_function_deps",
    "doc_operation",
    "get_dependency_graph",
    "get_progress",
    "get_file_tokens",
    "submit_analysis",
}
REVIEW_CRITERIA = (
    "function",
    "role",
    "io_side_effects",
    "dependencies",
)


def _write_real_repo(root: Path) -> None:
    """Create source with class, method, and caller/callee relationships."""

    (root / "app.py").write_text(
        textwrap.dedent(
            """\
            class Counter:
                def __init__(self, value: int = 0) -> None:
                    self.value = value

                def increment(self, step: int = 1) -> int:
                    self.value += step
                    return self.value


            def seed_value() -> int:
                return 2


            def run() -> int:
                counter = Counter(seed_value())
                return counter.increment()
            """
        ),
        encoding="utf-8",
    )


def _tool_json(result: types.CallToolResult) -> dict:
    """Reject protocol errors and decode FastMCP's JSON TextContent response."""

    assert not result.isError, [
        item.text for item in result.content if isinstance(item, types.TextContent)
    ]
    text_items = [
        item.text for item in result.content if isinstance(item, types.TextContent)
    ]
    assert len(text_items) == 1, result.content
    payload = json.loads(text_items[0])
    assert isinstance(payload, dict)
    return payload


async def _call(client, name: str, arguments: dict) -> dict:  # type: ignore[no-untyped-def]
    return _tool_json(await client.call_tool(name, arguments))


def _all_sufficient_verdicts(samples: list[dict]) -> list[dict]:
    return [
        {
            "sample": item["sample"],
            "verdicts": {
                criterion: {
                    "decision": "充分",
                    "reason": f"独立检查确认 {criterion} 与给定源码和解释一致",
                }
                for criterion in REVIEW_CRITERIA
            },
        }
        for item in samples
    ]


@pytest.mark.asyncio
async def test_mcp_semantic_lifecycle_writes_ledger_docs_and_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise analysis, writeback, rendering, and blind review over MCP."""

    _write_real_repo(tmp_path)
    analysis_dir = tmp_path / ".codebase-analysis"
    producer = "019ff8a0-0000-7000-8000-producerc300"
    reviewer = "independent-reviewer-session-c3"
    monkeypatch.setenv("CODEX_THREAD_ID", producer)

    def isolated_producer_runner(packet: dict) -> tuple[list[dict], dict]:
        return (
            [{"type": "thread.started", "thread_id": producer}],
            {
                "explanations": [
                    {
                        "symbol_id": row["symbol_id"],
                        "text": row["draft_explanation"],
                    }
                    for row in packet["symbols"]
                    if row["draft_explanation"] is not None
                ],
                "residuals": [],
            },
        )

    def isolated_review_runner(packet: dict) -> tuple[list[dict], dict]:
        return (
            [{"type": "thread.started", "thread_id": reviewer}],
            {"samples": _all_sufficient_verdicts(packet["samples"])},
        )

    monkeypatch.setattr(
        SemanticService,
        "_run_codex_producer",
        staticmethod(isolated_producer_runner),
    )
    monkeypatch.setattr(
        SemanticService,
        "_run_codex_reviewer",
        staticmethod(isolated_review_runner),
    )

    async with create_connected_server_and_client_session(mcp) as client:
        listed = await client.list_tools()
        tools_by_name = {tool.name: tool for tool in listed.tools}
        assert set(tools_by_name) == EXPECTED_TOOL_NAMES
        assert len(tools_by_name) == 14
        doc_schema = tools_by_name["doc_operation"].inputSchema
        assert "render_semantic_docs" in doc_schema["properties"]["operation"]["enum"]
        producer_schema = tools_by_name["submit_semantic_batch"].inputSchema
        assert "producer_rollout_path" not in producer_schema["properties"]
        assert "actor" not in producer_schema["properties"]
        assert "producer_events" not in producer_schema["properties"]
        claim_schema = tools_by_name["claim_semantic_batch"].inputSchema
        assert "actor" not in claim_schema["properties"]
        review_schema = tools_by_name["submit_semantic_review"].inputSchema
        assert set(review_schema["properties"]) == {"review_batch_id", "output_dir"}
        assert "review_batch_id" in review_schema["required"]

        missing = await client.call_tool(
            "get_semantic_progress",
            {"output_dir": str(tmp_path / "missing-analysis")},
        )
        assert missing.isError
        assert "does not exist" in missing.content[0].text

        blank = await client.call_tool(
            "get_semantic_progress",
            {"output_dir": ""},
        )
        assert blank.isError
        assert "non-empty path or null" in blank.content[0].text

        analyzed = await _call(
            client,
            "analyze_codebase",
            {
                "path": str(tmp_path),
                "languages": ["python"],
                "output_dir": str(analysis_dir),
                "force_reindex": True,
            },
        )
        assert analyzed["status"] == "success"
        assert analyzed["semantic"]["totals"]["symbols"] >= 4

        initial = await _call(
            client,
            "get_semantic_progress",
            {"output_dir": str(analysis_dir)},
        )
        assert initial["coverage_percent"] == 0.0
        source_revision = initial["source_revision"]

        submitted_ids: set[str] = set()
        for _ in range(initial["totals"]["symbols"] + 1):
            progress = await _call(
                client,
                "get_semantic_progress",
                {"output_dir": str(analysis_dir)},
            )
            if not progress["uncovered_symbols"]:
                break
            claimed = await _call(
                client,
                "claim_semantic_batch",
                {
                    "max_context_tokens": 16_000,
                    "lease_seconds": 300,
                    "output_dir": str(analysis_dir),
                },
            )
            assert not claimed["done"]
            packet = claimed["packet"]
            assert packet["source_revision"] == source_revision
            explanations = [
                {
                    "symbol_id": symbol["symbol_id"],
                    "text": (
                        f"{symbol['symbol_id']} 的语义解释：读取该符号的真实源码，"
                        f"说明其功能、输入输出、副作用以及依赖关系；内容锚为 "
                        f"{symbol['content_hash'][-16:]}。"
                    ),
                }
                for symbol in packet["symbols"]
            ]
            submitted = await _call(
                client,
                "submit_semantic_batch",
                {
                    "batch_id": packet["batch_id"],
                    "source_revision": packet["source_revision"],
                    "explanations": explanations,
                    "residuals": [],
                    "output_dir": str(analysis_dir),
                },
            )
            assert submitted["status"] == "success"
            submitted_ids.update(submitted["accepted_symbol_ids"])
        else:  # pragma: no cover - bounded-loop diagnostic
            pytest.fail("semantic scheduler did not reach a terminal state")

        final_progress = await _call(
            client,
            "get_semantic_progress",
            {"output_dir": str(analysis_dir)},
        )
        assert final_progress["coverage_percent"] == 100.0
        assert final_progress["uncovered_symbols"] == []
        assert final_progress["stale_symbols"] == []
        assert len(submitted_ids) == final_progress["totals"]["symbols"]

        repaired = await _call(
            client,
            "doc_operation",
            {
                "operation": "render_semantic_docs",
                "output_dir": str(analysis_dir),
            },
        )
        assert repaired["status"] == "success"
        assert repaired["operation"] == "render_semantic_docs"
        assert repaired["repaired"] is True

        review_packet = await _call(
            client,
            "get_semantic_review_batch",
            {"output_dir": str(analysis_dir)},
        )
        assert review_packet["samples"]
        assert all(set(item) == {"sample", "source", "explanation"} for item in review_packet["samples"])
        accepted = await _call(
            client,
            "submit_semantic_review",
            {
                "review_batch_id": review_packet["review_batch_id"],
                "output_dir": str(analysis_dir),
            },
        )
        assert accepted["status"] == "accepted"
        assert accepted["reviewer_session_id"] == f"codex:{reviewer}"
        assert accepted["revision_symbol_ids"] == []

    ledger_path = analysis_dir / "semantic_ledger.json"
    index_path = tmp_path / ".codebase-docs" / "INDEX.md"
    detail_paths = sorted((tmp_path / ".codebase-docs").rglob("DETAIL.md"))
    verdict_path = tmp_path / REVIEW_VERDICT_RELPATH
    review_events_path = tmp_path / REVIEW_EVENTS_RELPATH
    assert ledger_path.is_file()
    assert index_path.is_file()
    assert detail_paths
    assert verdict_path.is_file()
    assert review_events_path.is_file()

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    fresh_ids = {
        symbol_id
        for symbol_id, symbol in ledger["symbols"].items()
        if symbol["explanation"] is not None
        and symbol["explanation"]["explained_content_hash"] == symbol["content_hash"]
        and symbol["invalidation_reason"] is None
    }
    assert fresh_ids == set(ledger["symbols"]) == submitted_ids
    detail_blob = "\n".join(path.read_text(encoding="utf-8") for path in detail_paths)
    for symbol_id in fresh_ids:
        assert f"<!-- symbol:{symbol_id} -->" in detail_blob
        assert f"<!-- end:symbol:{symbol_id} -->" in detail_blob

    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    review_events = [
        json.loads(line)
        for line in review_events_path.read_text(encoding="utf-8").splitlines()
    ]
    assert verdict["reviewer_session_id"] == f"codex:{reviewer}"
    assert review_events == [{"type": "thread.started", "thread_id": reviewer}]
    assert {item["sample"] for item in verdict["samples"]} == {
        item["sample"] for item in review_packet["samples"]
    }
