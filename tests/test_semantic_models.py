"""Contract tests for the probe-compatible semantic ledger values."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.semantic.models import (
    FileStatus,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticResidual,
    SemanticSymbolKind,
    SemanticSymbolRecord,
    SemanticTotals,
    semantic_symbol_id,
)


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _symbol(*, content: str = "current", explanation_hash: str | None = None) -> SemanticSymbolRecord:
    explanation = (
        SemanticExplanation(
            text="Explains responsibility, inputs, outputs, and the important failure boundary.",
            explained_content_hash=explanation_hash,
            producer="codex-test",
            created_at=datetime(2026, 8, 13, tzinfo=UTC),
        )
        if explanation_hash is not None
        else None
    )
    return SemanticSymbolRecord(
        path="pkg/app.py",
        qualified_name="App.run",
        kind=SemanticSymbolKind.METHOD,
        span=(3, 8),
        content_hash=_hash(content),
        explanation=explanation,
    )


def test_empty_ledger_has_probe_schema_and_zero_percent_coverage(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ledger = SemanticLedger(
        repo_root=tmp_path.as_posix(),
        source_revision=_hash("revision"),
        files={"empty.py": SemanticFileRecord(status=FileStatus.NO_SYMBOLS)},
        symbols={},
        totals=SemanticTotals(symbols=0, explained=0, stale=0, uncovered=0, residual=0),
        coverage_percent=0.0,
    )
    dumped = ledger.model_dump(mode="json")
    assert dumped["schema"] == "cbe-semantic-ledger/3"
    assert dumped["files"]["empty.py"] == {"status": "no_symbols", "reason": ""}
    assert dumped["coverage_percent"] == 0.0


def test_v3_ledger_exposes_one_binding_namespace_and_completion_is_derived(tmp_path) -> None:  # type: ignore[no-untyped-def]
    ledger = SemanticLedger(
        repo_root=tmp_path.as_posix(),
        source_revision=_hash("revision"),
        files={"empty.py": SemanticFileRecord(status=FileStatus.NO_SYMBOLS)},
        symbols={},
        totals=SemanticTotals(symbols=0, explained=0, stale=0, uncovered=0, residual=0),
        coverage_percent=0.0,
    )
    dumped = ledger.model_dump(mode="json")
    assert dumped["schema"] == "cbe-semantic-ledger/3"
    assert ledger.bindings.source_revision_id.startswith("rev_")
    assert ledger.bindings.edge_protocol_ids == {
        "inbound": "cbe-inbound-call/1",
        "ir": "cbe-ir/3",
        "reverse": "cbe-reverse-edges/3",
    }
    assert ledger.product_complete is False


def test_v3_payload_without_bindings_is_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValidationError, match="bindings"):
        SemanticLedger.model_validate(
            {
                "schema": "cbe-semantic-ledger/3",
                "ledger_revision": 0,
                "repo_root": tmp_path.as_posix(),
                "files": {},
                "symbols": {},
                "order": [],
                "residuals": [],
                "accepted_submissions": {},
                "review": {"status": "none"},
                "legacy_import": {"status": "open", "scan_root": tmp_path.as_posix()},
                "totals": {"symbols": 0, "explained": 0, "stale": 0, "uncovered": 0, "residual": 0},
                "coverage_percent": 0.0,
                "uncovered_symbols": [],
            }
        )


def test_stale_is_derived_only_from_the_two_content_hashes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    symbol = _symbol(explanation_hash=_hash("previous"))
    symbol_id = symbol.symbol_id
    ledger = SemanticLedger(
        repo_root=tmp_path.as_posix(),
        source_revision=_hash("revision"),
        files={
            "pkg/app.py": SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason="stale semantic explanation",
            )
        },
        symbols={symbol_id: symbol},
        residuals=(SemanticResidual(symbol_id=symbol_id, reason="source changed"),),
        totals=SemanticTotals(symbols=1, explained=0, stale=1, uncovered=1, residual=1),
        coverage_percent=0.0,
        uncovered_symbols=(symbol_id,),
    )
    assert symbol.is_explained
    assert not symbol.is_fresh
    assert ledger.totals.stale == 1


def test_ledger_rejects_self_reported_denominators_and_dangling_references(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fresh = _symbol(content="current", explanation_hash=_hash("current"))
    symbol_id = fresh.symbol_id
    common = {
        "repo_root": tmp_path.as_posix(),
        "source_revision": _hash("revision"),
        "files": {"pkg/app.py": {"status": "covered", "reason": ""}},
        "symbols": {symbol_id: fresh.model_dump(mode="json")},
        "order": [symbol_id],
        "residuals": [],
        "coverage_percent": 100.0,
        "uncovered_symbols": [],
    }
    with pytest.raises(ValidationError, match="totals"):
        SemanticLedger.model_validate(
            {
                **common,
                "totals": {"symbols": 99, "explained": 1, "stale": 0, "uncovered": 0, "residual": 0},
            }
        )

    dangling = fresh.model_copy(
        update={
            "explanation": fresh.explanation.model_copy(
                update={"cited_symbol_ids": ("missing.py::callee",)}
            )
        }
    )
    with pytest.raises(ValidationError, match="dangling"):
        SemanticLedger.model_validate(
            {
                **common,
                "symbols": {symbol_id: dangling.model_dump(mode="json")},
                "totals": {"symbols": 1, "explained": 1, "stale": 0, "uncovered": 0, "residual": 0},
            }
        )


@pytest.mark.parametrize("path", ["/abs.py", "../escape.py", "pkg\\win.py", "pkg/./alias.py"])
def test_symbol_identity_rejects_noncanonical_paths(path: str) -> None:
    with pytest.raises(ValueError):
        semantic_symbol_id(path, "fn")


def test_explanation_rejects_thin_text_non_hash_and_non_utc_time() -> None:
    with pytest.raises(ValidationError, match="at least"):
        SemanticExplanation(
            text="too short",
            explained_content_hash=_hash("body"),
            producer="test",
            created_at=datetime.now(UTC),
        )
    with pytest.raises(ValidationError, match="sha256"):
        SemanticExplanation(
            text="A sufficiently detailed explanation of responsibility and behavior.",
            explained_content_hash="not-a-hash",
            producer="test",
            created_at=datetime.now(UTC),
        )
    with pytest.raises(ValidationError, match="UTC"):
        SemanticExplanation(
            text="A sufficiently detailed explanation of responsibility and behavior.",
            explained_content_hash=_hash("body"),
            producer="test",
            created_at=datetime.now(timezone(timedelta(hours=2))),
        )


def test_symbol_key_must_equal_path_and_lexical_qualified_name(tmp_path) -> None:  # type: ignore[no-untyped-def]
    symbol = _symbol()
    with pytest.raises(ValidationError, match="symbol key"):
        SemanticLedger(
            repo_root=tmp_path.as_posix(),
            source_revision=_hash("revision"),
            files={
                "pkg/app.py": SemanticFileRecord(
                    status=FileStatus.RESIDUAL,
                    reason="pending",
                )
            },
            symbols={"pkg/app.py::run": symbol},
            residuals=(SemanticResidual(symbol_id="pkg/app.py::run", reason="pending"),),
            totals=SemanticTotals(symbols=1, explained=0, stale=0, uncovered=1, residual=1),
            coverage_percent=0.0,
            uncovered_symbols=("pkg/app.py::run",),
        )
