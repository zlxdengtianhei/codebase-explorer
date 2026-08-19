"""Real MCP pipeline connectivity, atomicity, and reconnect recovery.

The explanations and reviewer verdict in this test are fixtures. This test does
not claim or assert semantic quality.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from mcp import types
from mcp.shared.memory import create_connected_server_and_client_session

from src.semantic.service import SemanticService
from src.server import HOST_SESSION_ENV_REGISTRY, mcp

REVIEW_CRITERIA = (
    "function",
    "role",
    "io_side_effects",
    "dependencies",
)
HOST_IDENTITY_ENV_KEYS = tuple(variable for _, variable in HOST_SESSION_ENV_REGISTRY)


def _write_temporary_repo(root: Path) -> None:
    (root / "helpers.py").write_text(
        textwrap.dedent("""\
            def normalize(value: int) -> int:
                return max(value, 0)
            """),
        encoding="utf-8",
    )
    (root / "app.py").write_text(
        textwrap.dedent("""\
            from helpers import normalize


            class Counter:
                def __init__(self, value: int = 0) -> None:
                    self.value = normalize(value)

                def increment(self, step: int = 1) -> int:
                    self.value = normalize(self.value + step)
                    return self.value


            def run(value: int) -> int:
                return Counter(value).increment()
            """),
        encoding="utf-8",
    )


def _tool_json(result: types.CallToolResult) -> dict:
    assert not result.isError, [
        item.text for item in result.content if isinstance(item, types.TextContent)
    ]
    text_items = [
        item.text for item in result.content if isinstance(item, types.TextContent)
    ]
    assert len(text_items) == 1
    payload = json.loads(text_items[0])
    assert isinstance(payload, dict)
    return payload


async def _call(client, name: str, arguments: dict) -> dict:  # type: ignore[no-untyped-def]
    return _tool_json(await client.call_tool(name, arguments))


def _projection_snapshot(repo: Path) -> tuple[bytes, dict[str, bytes]]:
    ledger = (repo / ".codebase-analysis" / "semantic_ledger.json").read_bytes()
    docs_root = repo / ".codebase-docs"
    docs = {
        path.relative_to(docs_root).as_posix(): path.read_bytes()
        for path in sorted(docs_root.rglob("*"))
        if path.is_file()
    }
    return ledger, docs


def _fixture_explanations(packet: dict) -> list[dict[str, str]]:
    return [
        {
            "symbol_id": symbol["symbol_id"],
            "text": (
                "Pipeline fixture explanation for "
                f"{symbol['symbol_id']} at content hash {symbol['content_hash']}; "
                "its only purpose is exercising atomic transport and recovery."
            ),
        }
        for symbol in packet["symbols"]
    ]


def _fixture_producer_runner(packet: dict) -> tuple[list[dict], dict]:
    """Return the server-owned producer output without using vendor quota."""

    explanations = [
        {"symbol_id": row["symbol_id"], "text": row["draft_explanation"]}
        for row in packet["symbols"]
        if row["draft_explanation"] is not None
    ]
    residuals = [
        {"symbol_id": row["symbol_id"], "reason": row["draft_residual"]}
        for row in packet["symbols"]
        if row["draft_residual"] is not None
    ]
    return (
        [{"type": "thread.started", "thread_id": "fixture-semantic-producer"}],
        {"explanations": explanations, "residuals": residuals},
    )


def _fixture_review_runner(packet: dict) -> tuple[list[dict], dict]:
    reviewer = "fixture-reviewer-independent-from-producer"
    verdict = {
        "samples": [
            {
                "sample": item["sample"],
                "verdicts": {
                    criterion: {
                        "decision": "充分",
                        "reason": f"fixture verdict for pipeline criterion {criterion}",
                    }
                    for criterion in REVIEW_CRITERIA
                },
            }
            for item in packet["samples"]
        ]
    }
    return ([{"type": "thread.started", "thread_id": reviewer}], verdict)


@pytest.mark.asyncio
async def test_semantic_disclosure_pipeline_is_atomic_and_recoverable_after_reconnect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Traverse analyze, claim/submit, render, and review through real MCP."""

    _write_temporary_repo(tmp_path)
    output_dir = tmp_path / ".codebase-analysis"
    session_id = "fixture-producer-real-thread-id"
    lease_owner = f"generic:{session_id}"
    producer = "codex:fixture-semantic-producer"
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.setenv("CBE_HOST_SESSION_ID", session_id)
    monkeypatch.setattr(
        SemanticService,
        "_run_codex_producer",
        staticmethod(_fixture_producer_runner),
    )
    monkeypatch.setattr(
        SemanticService,
        "_run_codex_reviewer",
        staticmethod(_fixture_review_runner),
    )

    async with create_connected_server_and_client_session(mcp) as client:
        analyzed = await _call(
            client,
            "analyze_codebase",
            {
                "path": str(tmp_path),
                "languages": ["python"],
                "output_dir": str(output_dir),
                "force_reindex": True,
            },
        )
        assert analyzed["status"] == "success"
        graph = await _call(
            client,
            "get_dependency_graph",
            {"scope": "project", "output_dir": str(output_dir)},
        )
        assert graph["status"] == "success"
        initial = await _call(
            client,
            "get_semantic_progress",
            {"output_dir": str(output_dir)},
        )
        assert initial["totals"]["symbols"] > 0

        claim = await _call(
            client,
            "claim_semantic_batch",
            {
                "max_context_tokens": 16_000,
                "lease_seconds": 300,
                "output_dir": str(output_dir),
            },
        )
        assert claim["done"] is False
        saved_packet = claim["packet"]
        assert saved_packet["lease_owner"] == lease_owner

    before_rejection = _projection_snapshot(tmp_path)
    incomplete = _fixture_explanations(saved_packet)[:-1]
    async with create_connected_server_and_client_session(mcp) as client:
        rejected = await client.call_tool(
            "submit_semantic_batch",
            {
                "batch_id": saved_packet["batch_id"],
                "source_revision": saved_packet["source_revision"],
                "explanations": incomplete,
                "residuals": [],
                "output_dir": str(output_dir),
            },
        )
        assert rejected.isError
        assert "entire batch" in rejected.content[0].text

    assert _projection_snapshot(tmp_path) == before_rejection

    async with create_connected_server_and_client_session(mcp) as client:
        recovered_submit = await _call(
            client,
            "submit_semantic_batch",
            {
                "batch_id": saved_packet["batch_id"],
                "source_revision": saved_packet["source_revision"],
                "explanations": _fixture_explanations(saved_packet),
                "residuals": [],
                "output_dir": str(output_dir),
            },
        )
        assert recovered_submit["batch_released"] is True

        while True:
            progress = await _call(
                client,
                "get_semantic_progress",
                {"output_dir": str(output_dir)},
            )
            if not progress["uncovered_symbols"]:
                break
            claimed = await _call(
                client,
                "claim_semantic_batch",
                {
                    "max_context_tokens": 16_000,
                    "lease_seconds": 300,
                    "output_dir": str(output_dir),
                },
            )
            assert claimed["done"] is False
            packet = claimed["packet"]
            explanations = _fixture_explanations(packet)
            await _call(
                client,
                "submit_semantic_batch",
                {
                    "batch_id": packet["batch_id"],
                    "source_revision": packet["source_revision"],
                    "explanations": explanations,
                    "residuals": [],
                    "output_dir": str(output_dir),
                },
            )

        assert progress["coverage_percent"] == 100.0
        assert progress["stale_symbols"] == []

        rendered = await _call(
            client,
            "doc_operation",
            {
                "operation": "render_semantic_docs",
                "output_dir": str(output_dir),
            },
        )
        assert Path(rendered["index_path"]).is_file()
        assert rendered["detail_paths"]
        assert all(Path(path).is_file() for path in rendered["detail_paths"])

        review = await _call(
            client,
            "get_semantic_review_batch",
            {"output_dir": str(output_dir)},
        )
        accepted = await _call(
            client,
            "submit_semantic_review",
            {
                "review_batch_id": review["review_batch_id"],
                "output_dir": str(output_dir),
            },
        )
        assert accepted["status"] == "accepted"
        assert accepted["revision_symbol_ids"] == []

        terminal = await _call(
            client,
            "get_semantic_progress",
            {"output_dir": str(output_dir)},
        )
        assert terminal["coverage_percent"] == 100.0
        assert terminal["review_verdict_present"] is True

        ledger = json.loads(
            (tmp_path / ".codebase-analysis" / "semantic_ledger.json").read_text(
                encoding="utf-8"
            )
        )
        producers = {
            symbol["explanation"]["producer_session_id"]
            for symbol in ledger["symbols"].values()
            if symbol["explanation"] is not None
        }
        assert producers == {producer}


@pytest.mark.asyncio
async def test_claim_semantic_batch_fails_closed_without_host_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An MCP caller cannot claim work when server process identity is absent."""

    _write_temporary_repo(tmp_path)
    output_dir = tmp_path / ".codebase-analysis"
    for key in HOST_IDENTITY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    async with create_connected_server_and_client_session(mcp) as client:
        await _call(
            client,
            "analyze_codebase",
            {
                "path": str(tmp_path),
                "languages": ["python"],
                "output_dir": str(output_dir),
                "force_reindex": True,
            },
        )
        rejected = await client.call_tool(
            "claim_semantic_batch",
            {
                "max_context_tokens": 16_000,
                "lease_seconds": 300,
                "output_dir": str(output_dir),
            },
        )

    assert rejected.isError
    error_text = rejected.content[0].text
    for key in HOST_IDENTITY_ENV_KEYS:
        assert key in error_text


@pytest.mark.asyncio
async def test_claim_semantic_batch_uses_first_registered_host_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registered priority is deterministic when several host keys exist."""

    _write_temporary_repo(tmp_path)
    output_dir = tmp_path / ".codebase-analysis"
    monkeypatch.setenv("CODEX_THREAD_ID", "codex-first")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "claude-second")
    monkeypatch.setenv("CBE_HOST_SESSION_ID", "generic-third")

    async with create_connected_server_and_client_session(mcp) as client:
        await _call(
            client,
            "analyze_codebase",
            {
                "path": str(tmp_path),
                "languages": ["python"],
                "output_dir": str(output_dir),
                "force_reindex": True,
            },
        )
        claimed = await _call(
            client,
            "claim_semantic_batch",
            {
                "max_context_tokens": 16_000,
                "lease_seconds": 300,
                "output_dir": str(output_dir),
            },
        )

    assert claimed["packet"]["lease_owner"] == "codex:codex-first"
