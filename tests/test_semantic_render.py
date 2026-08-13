"""Deterministic four-level readable documentation projection tests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
import pytest

from src.semantic.models import (
    FileStatus,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticResidual,
    SemanticSymbolKind,
    SemanticSymbolRecord,
    SemanticTotals,
)
from src.semantic.render import render_semantic_docs


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _symbol(
    *,
    path: str,
    qualified_name: str,
    kind: SemanticSymbolKind,
    body: str,
    explanation_text: str | None,
    explanation_body: str | None = None,
    cited_symbol_ids: tuple[str, ...] = (),
    module_id: str | None,
) -> SemanticSymbolRecord:
    explanation = None
    if explanation_text is not None:
        explanation = SemanticExplanation(
            text=explanation_text,
            explained_content_hash=_hash(explanation_body or body),
            cited_symbol_ids=cited_symbol_ids,
            producer="codex-render-test",
            created_at=datetime(2026, 8, 13, tzinfo=UTC),
        )
    return SemanticSymbolRecord(
        path=path,
        qualified_name=qualified_name,
        kind=kind,
        span=(1, 3),
        content_hash=_hash(body),
        explanation=explanation,
        module_id=module_id,
    )


def _ledger(repo: Path) -> tuple[SemanticLedger, dict[str, str]]:
    leaf = _symbol(
        path="pkg/core.py",
        qualified_name="leaf",
        kind=SemanticSymbolKind.FUNCTION,
        body="leaf-v2",
        explanation_text="Returns the canonical core value. It has no stateful side effects.",
        module_id="Core Runtime",
    )
    caller = _symbol(
        path="pkg/api.py",
        qualified_name="Api.run",
        kind=SemanticSymbolKind.METHOD,
        body="caller-v2",
        explanation_text="Builds the public response from the core leaf. It returns the converted value.",
        cited_symbol_ids=(leaf.symbol_id,),
        module_id="Public API",
    )
    stale = _symbol(
        path="pkg/core.py",
        qualified_name="legacy",
        kind=SemanticSymbolKind.FUNCTION,
        body="legacy-v2",
        explanation_body="legacy-v1",
        explanation_text="Describes the previous legacy behavior and is intentionally stale now.",
        module_id="Core Runtime",
    )
    pending = _symbol(
        path="pkg/api.py",
        qualified_name="pending",
        kind=SemanticSymbolKind.FUNCTION,
        body="pending-v1",
        explanation_text=None,
        module_id="Public API",
    )
    symbols = {
        record.symbol_id: record
        for record in (leaf, caller, stale, pending)
    }
    residuals = (
        SemanticResidual(symbol_id=stale.symbol_id, reason="source content hash changed"),
        SemanticResidual(symbol_id=pending.symbol_id, reason="pending semantic explanation"),
    )
    ledger = SemanticLedger(
        repo_root=repo.as_posix(),
        source_revision=_hash("revision"),
        files={
            "pkg/api.py": SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason="one symbol awaits explanation",
            ),
            "pkg/core.py": SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason="one explanation is stale",
            ),
            "pkg/empty.py": SemanticFileRecord(status=FileStatus.NO_SYMBOLS),
        },
        symbols=symbols,
        order=(leaf.symbol_id, caller.symbol_id),
        residuals=residuals,
        totals=SemanticTotals(symbols=4, explained=2, stale=1, uncovered=2, residual=2),
        coverage_percent=50.0,
        uncovered_symbols=tuple(sorted((stale.symbol_id, pending.symbol_id))),
    )
    return ledger, {
        "leaf": leaf.symbol_id,
        "caller": caller.symbol_id,
        "stale": stale.symbol_id,
        "pending": pending.symbol_id,
    }


def _docs_snapshot(repo: Path) -> dict[str, bytes]:
    docs = repo / ".codebase-docs"
    return {
        path.relative_to(docs).as_posix(): path.read_bytes()
        for path in sorted(docs.rglob("*"))
        if path.is_file()
    }


def test_render_semantic_docs_projects_all_four_levels_and_explicit_gaps(
    tmp_path: Path,
) -> None:
    ledger, ids = _ledger(tmp_path)
    graph = nx.DiGraph()
    graph.add_nodes_from(ledger.symbols)
    graph.add_edge(ids["caller"], ids["leaf"])

    result = render_semantic_docs(tmp_path, ledger, graph=graph)

    assert json.loads(json.dumps(result)) == result
    assert result["index_path"] == (tmp_path / ".codebase-docs/INDEX.md").as_posix()
    assert result["detail_paths"] == [
        (tmp_path / ".codebase-docs/core-runtime/DETAIL.md").as_posix(),
        (tmp_path / ".codebase-docs/public-api/DETAIL.md").as_posix(),
        (tmp_path / ".codebase-docs/unclassified/DETAIL.md").as_posix(),
    ]

    index = Path(result["index_path"]).read_text(encoding="utf-8")
    assert "# test_render_semantic_docs_proj0" in index
    assert "项目概览" in index
    assert "(core-runtime/DETAIL.md)" in index
    assert "(public-api/DETAIL.md)" in index
    assert "(unclassified/DETAIL.md)" in index
    assert "public_api --> core_runtime" in index
    assert ids["stale"] in index
    assert ids["pending"] in index

    detail_blob = "\n".join(
        Path(path).read_text(encoding="utf-8") for path in result["detail_paths"]
    )
    assert "模块概览" in detail_blob
    assert "## `pkg/api.py`" in detail_blob
    assert detail_blob.count(f"<!-- symbol:{ids['leaf']} -->") == 1
    assert detail_blob.count(f"<!-- symbol:{ids['caller']} -->") == 1
    assert f"<!-- symbol:{ids['stale']} -->" not in detail_blob
    assert f"<!-- symbol:{ids['pending']} -->" not in detail_blob
    assert "stale" in detail_blob
    assert "pending semantic explanation" in detail_blob
    assert "Returns the canonical core value." in detail_blob
    assert "Builds the public response from the core leaf." in detail_blob


def test_render_is_byte_stable_and_replaces_the_previous_generated_tree(
    tmp_path: Path,
) -> None:
    ledger, _ = _ledger(tmp_path)
    first = render_semantic_docs(tmp_path, ledger)
    before = _docs_snapshot(tmp_path)
    obsolete = tmp_path / ".codebase-docs/obsolete/DETAIL.md"
    obsolete.parent.mkdir(parents=True)
    obsolete.write_text("obsolete generated projection", encoding="utf-8")

    second = render_semantic_docs(tmp_path, ledger)

    assert second == first
    assert _docs_snapshot(tmp_path) == before
    assert not obsolete.exists()


def test_render_rejects_a_ledger_for_another_repository(tmp_path: Path) -> None:
    ledger, _ = _ledger(tmp_path)
    other = tmp_path / "other"
    other.mkdir()

    with pytest.raises(ValueError, match="repo_root"):
        render_semantic_docs(other, ledger)


def test_directory_summaries_bound_long_explanations_without_punctuation(
    tmp_path: Path,
) -> None:
    ledger, ids = _ledger(tmp_path)
    caller = ledger.symbols[ids["caller"]]
    long_text = "semantic behavior and dependency context " * 30
    explanation = caller.explanation
    assert explanation is not None
    symbols = dict(ledger.symbols)
    symbols[ids["caller"]] = caller.model_copy(
        update={"explanation": explanation.model_copy(update={"text": long_text})}
    )
    bounded = ledger.model_copy(update={"symbols": symbols})

    result = render_semantic_docs(tmp_path, bounded)

    details = "\n".join(
        Path(path).read_text(encoding="utf-8") for path in result["detail_paths"]
    )
    summary_lines = [
        line
        for line in details.splitlines()
        if line.startswith("- [`Api.run`](#symbol-")
    ]
    assert summary_lines
    assert all(len(line) < 400 for line in summary_lines)
    assert any("…" in line for line in summary_lines)
