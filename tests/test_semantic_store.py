"""Durability and reconcile tests for the semantic ledger store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.semantic import (
    LedgerCorruptError,
    LedgerExistsError,
    LegacyLedgerMigrationRequired,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticLedgerStore,
    SemanticStoreError,
    SemanticTotals,
    enumerate_semantic_inventory,
    reconcile_semantic_ledger,
)
from src.semantic.service import MIGRATION_RECEIPT_RELPATH, SEMANTIC_EVENTS_RELPATH, SemanticService


def _write(root, text: str) -> None:  # type: ignore[no-untyped-def]
    (root / "app.py").write_text(text, encoding="utf-8")


def _fresh_ledger(ledger: SemanticLedger) -> SemanticLedger:
    symbol_id, symbol = next(iter(ledger.symbols.items()))
    explanation = SemanticExplanation(
        text="Returns the configured value and has no external side effects or failure branch.",
        explained_content_hash=symbol.content_hash,
        producer="codex-test",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    fresh_symbol = symbol.model_copy(update={"explanation": explanation})
    return SemanticLedger(
        repo_root=ledger.repo_root,
        source_revision=ledger.source_revision,
        excluded_globs=ledger.excluded_globs,
        files={"app.py": SemanticFileRecord(status="covered")},
        symbols={symbol_id: fresh_symbol},
        order=(symbol_id,),
        residuals=(),
        totals=SemanticTotals(symbols=1, explained=1, stale=0, uncovered=0, residual=0),
        coverage_percent=100.0,
        uncovered_symbols=(),
    )


def _with_explanation(
    ledger: SemanticLedger,
    symbol_id: str,
    *,
    text: str,
    citations: tuple[str, ...] = (),
) -> SemanticLedger:
    symbol = ledger.symbols[symbol_id]
    explanation = SemanticExplanation(
        text=text,
        explained_content_hash=symbol.content_hash,
        cited_symbol_ids=citations,
        producer="codex-test",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    return reconcile_semantic_ledger(
        enumerate_semantic_inventory(ledger.repo_root),
        ledger,
        explanation_overrides={symbol_id: explanation},
    )


def test_store_creates_reopens_and_reconciles_probe_ledger_skeleton(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    created = store.create()
    reopened = store.reopen()
    reconciled = store.reconcile()
    assert created == reopened == reconciled
    assert store.path == tmp_path / ".codebase-analysis/semantic_ledger.json"
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["schema"] == "cbe-semantic-ledger/3"
    assert set(raw["files"]) == {"app.py"}
    assert set(raw["symbols"]) == {"app.py::value"}
    assert raw["uncovered_symbols"] == ["app.py::value"]
    assert raw["residuals"] == [
        {"symbol_id": "app.py::value", "reason": "pending semantic explanation"}
    ]
    with pytest.raises(LedgerExistsError):
        store.create()


def test_reconcile_preserves_explanation_and_makes_source_change_stale(tmp_path) -> None:  # type: ignore[no-untyped-def]
    original = "def value():\n    return 1\n"
    changed = "def value():\n    return 2\n"
    _write(tmp_path, original)
    store = SemanticLedgerStore(tmp_path)
    committed = store.commit(_fresh_ledger(store.create()))
    assert committed.coverage_percent == 100.0
    assert committed.order == ("app.py::value",)

    _write(tmp_path, changed)
    stale = store.reconcile()
    stale_symbol = stale.symbols["app.py::value"]
    assert stale_symbol.explanation is not None
    assert stale_symbol.explanation.explained_content_hash != stale_symbol.content_hash
    assert stale.totals == SemanticTotals(
        symbols=1,
        explained=0,
        stale=1,
        uncovered=1,
        residual=1,
    )
    assert stale.coverage_percent == 0.0
    assert stale.order == ()
    assert stale.residuals[0].reason.startswith("stale semantic explanation")

    _write(tmp_path, original)
    restored = store.reconcile()
    assert restored.symbols["app.py::value"].is_fresh
    assert restored.coverage_percent == 100.0


def test_reconcile_removes_deleted_symbols_and_adds_new_symbols(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def old():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    store.create()
    _write(tmp_path, "def new():\n    return 2\n")
    ledger = store.reconcile()
    assert set(ledger.symbols) == {"app.py::new"}
    assert ledger.uncovered_symbols == ("app.py::new",)
    assert tuple(item.symbol_id for item in ledger.residuals) == ("app.py::new",)


def test_corrupt_ledger_fails_closed_instead_of_becoming_an_empty_ledger(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    store.create()
    store.path.write_text('{"schema":', encoding="utf-8")
    with pytest.raises(LedgerCorruptError, match="corrupt"):
        store.reopen()
    with pytest.raises(LedgerCorruptError, match="corrupt"):
        store.reconcile()


def test_atomic_replace_failure_leaves_prior_complete_ledger(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    original = store.create()
    original_bytes = store.path.read_bytes()
    _write(tmp_path, "def value():\n    return 2\n")

    def interrupted(_source, _target):  # type: ignore[no-untyped-def]
        raise OSError("simulated interruption before replace")

    monkeypatch.setattr("src.semantic.store.os.replace", interrupted)
    with pytest.raises(OSError, match="simulated interruption"):
        store.reconcile()
    assert store.path.read_bytes() == original_bytes
    assert store.reopen() == original
    assert not list(store.path.parent.glob(".semantic_ledger.json.*.tmp"))


def test_commit_rejects_a_revision_that_source_has_already_outgrown(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    authored = _fresh_ledger(store.create())
    _write(tmp_path, "def value():\n    return 2\n")
    with pytest.raises(SemanticStoreError, match="source changed before commit"):
        store.commit(authored)

    # The same stale snapshot is still rejected after another process has
    # reconciled the on-disk state first.
    store.reconcile()
    with pytest.raises(SemanticStoreError, match="source revision is stale"):
        store.commit(authored)


def test_concurrent_commits_merge_distinct_symbols_without_losing_facts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def f():\n    return 1\n\ndef g():\n    return 2\n")
    store = SemanticLedgerStore(tmp_path)
    snapshot_a = store.create()
    snapshot_b = store.reopen()
    authored_a = _with_explanation(
        snapshot_a,
        "app.py::f",
        text="Returns the first fixed value without reading external mutable state.",
    )
    authored_b = _with_explanation(
        snapshot_b,
        "app.py::g",
        text="Returns the second fixed value without reading external mutable state.",
    )

    store.commit(authored_a)
    merged = store.commit(authored_b)
    assert merged.symbols["app.py::f"].is_fresh
    assert merged.symbols["app.py::g"].is_fresh
    assert merged.coverage_percent == 100.0


def test_concurrent_conflicting_explanations_fail_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    first_snapshot = store.create()
    second_snapshot = store.reopen()
    first = _with_explanation(
        first_snapshot,
        "app.py::value",
        text="Returns a stable configured value with no observable external side effects.",
    )
    second = _with_explanation(
        second_snapshot,
        "app.py::value",
        text="Produces the configured constant while leaving all external state unchanged.",
    )

    store.commit(first)
    with pytest.raises(SemanticStoreError, match="concurrent explanation conflict"):
        store.commit(second)


def test_commit_revalidates_copied_models_before_persisting(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    authored = _fresh_ledger(store.create())
    symbol_id, symbol = next(iter(authored.symbols.items()))
    assert symbol.explanation is not None
    poisoned_explanation = symbol.explanation.model_copy(update={"text": "x"})
    poisoned_symbol = symbol.model_copy(update={"explanation": poisoned_explanation})
    poisoned = authored.model_copy(update={"symbols": {symbol_id: poisoned_symbol}})

    with pytest.raises(SemanticStoreError, match="contract-invalid"):
        store.commit(poisoned)
    assert store.reopen().coverage_percent == 0.0


def test_deleted_citation_invalidates_reverse_reachable_callers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(
        tmp_path,
        "def f():\n    return g()\n\ndef g():\n    return 1\n\ndef h():\n    return f()\n",
    )
    store = SemanticLedgerStore(tmp_path)
    authored = store.create()
    authored = _with_explanation(
        authored,
        "app.py::g",
        text="Returns the leaf value consumed by the two calling functions above it.",
    )
    authored = _with_explanation(
        authored,
        "app.py::f",
        text="Delegates value production to g and returns the resulting leaf value.",
        citations=("app.py::g",),
    )
    authored = _with_explanation(
        authored,
        "app.py::h",
        text="Delegates value production to f and therefore transitively depends on g.",
        citations=("app.py::f",),
    )
    store.commit(authored)

    _write(tmp_path, "def f():\n    return 1\n\ndef h():\n    return f()\n")
    reconciled = store.reconcile()
    assert reconciled.symbols["app.py::f"].explanation is None
    assert reconciled.symbols["app.py::f"].invalidation_reason == (
        "cited symbol removed: app.py::g"
    )
    assert reconciled.symbols["app.py::h"].explanation is None
    assert reconciled.symbols["app.py::h"].invalidation_reason == (
        "cited symbol is stale or invalid"
    )
    assert reconciled.coverage_percent == 0.0


def test_store_rejects_symlinked_analysis_directory(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    outside = tmp_path.parent / f"{tmp_path.name}-outside-ledger"
    outside.mkdir()
    (tmp_path / ".codebase-analysis").symlink_to(outside, target_is_directory=True)

    store = SemanticLedgerStore(tmp_path)
    with pytest.raises(SemanticStoreError, match="must not be a symlink"):
        store.create()
    assert not (outside / "semantic_ledger.json").exists()
    assert not (outside / "semantic_ledger.json.lock").exists()


def test_create_publishes_hash_bound_commit_receipt_and_revision_zero(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    ledger = store.create()
    receipt_path = tmp_path / ".codebase-analysis/semantic_commit_receipt.json"
    assert ledger.ledger_revision == 0
    assert receipt_path.is_file()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "cbe-semantic-commit-receipt/1"
    assert receipt["ledger_revision"] == 0
    assert receipt["ledger_sha256"].startswith("sha256:")
    assert receipt["ledger_sha256"] == store.ledger_sha256()


def test_v2_accepted_review_migrates_to_revision_zero_review_none_and_incomplete(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    """The service, not a read-side store helper, owns the v2->v3 commit."""

    _write(tmp_path, "def value():\n    return 1\n")
    store = SemanticLedgerStore(tmp_path)
    v3 = store.create()
    authored = _fresh_ledger(v3)
    symbol_id, symbol = next(iter(authored.symbols.items()))
    explanation = symbol.explanation
    assert explanation is not None
    old_symbol = symbol.model_dump(mode="json")
    old_explanation = old_symbol["explanation"]
    assert isinstance(old_explanation, dict)
    old_explanation["producer"] = old_explanation.pop("producer_session_id")
    old_symbol["explanation"] = old_explanation
    raw = {
        "schema": "cbe-semantic-ledger-2",
        "repo_root": authored.repo_root,
        "source_revision": authored.source_revision,
        "file_revisions": authored.file_revisions,
        "excluded_globs": list(authored.excluded_globs),
        "files": {key: value.model_dump(mode="json") for key, value in authored.files.items()},
        "symbols": {symbol_id: old_symbol},
        "order": [symbol_id],
        "residuals": [],
        "totals": authored.totals.model_dump(mode="json"),
        "coverage_percent": authored.coverage_percent,
        "uncovered_symbols": [],
        "review": {
            "status": "accepted",
            "reviewer_session_id": "codex:old-reviewer",
            "verdict_sha256": "sha256:" + "1" * 64,
        },
    }
    store.path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
    before = store.path.read_bytes()
    with pytest.raises(LegacyLedgerMigrationRequired):
        store.reopen()
    assert store.path.read_bytes() == before

    def renderer(root, ledger, *, graph=None):  # type: ignore[no-untyped-def]
        del graph
        docs = Path(root) / ".codebase-docs"
        docs.mkdir(parents=True, exist_ok=True)
        detail = docs / "DETAIL.md"
        detail.write_text(
            "# Details\n\n"
            + "\n".join(
                f"<!-- symbol:{item.symbol_id} -->\n{item.explanation.text}\n"
                f"<!-- end:symbol:{item.symbol_id} -->"
                for item in ledger.symbols.values()
                if item.explanation is not None and item.is_fresh
            ),
            encoding="utf-8",
        )
        index = docs / "INDEX.md"
        index.write_text("# Index\n\n[Details](DETAIL.md)\n", encoding="utf-8")
        return {
            "index_path": index.as_posix(),
            "detail_paths": [detail.as_posix()],
        }
    service = SemanticService(tmp_path, renderer=renderer)
    migrated = service.bootstrap_semantic()

    assert migrated.ledger_revision == 0
    assert migrated.review.status == "none"
    assert migrated.review.bound_ledger_revision is None
    assert migrated.product_complete is False
    assert migrated.symbols[symbol_id].is_fresh
    migration = json.loads((tmp_path / MIGRATION_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    assert migration["schema"] == "cbe-semantic-legacy-import/1"
    events = [
        json.loads(line)
        for line in (tmp_path / SEMANTIC_EVENTS_RELPATH).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["reason_code"] for row in events if row.get("event") == "migrate"] == [
        "V2_REVIEW_REQUIRES_V3_REVIEW"
    ]
