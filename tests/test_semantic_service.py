"""Transactional semantic writeback and independent-review service tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

import pytest

from src.ir import EntityKind, SourceUnit, SourceUnitState, deterministic_entity_id
from src.parser.adapters.base import FileIR
from src.parser.adapters.python import PythonLanguageAdapter
from src.parser.backend import PythonAstBackend, SyntaxArtifact
from src.semantic.service import (
    REVIEW_ACCEPTANCE_RECEIPT_RELPATH,
    REVIEW_BATCH_RECEIPT_RELPATH,
    REVIEW_HIDDEN_MAP_RELPATH,
    REVIEW_PACKET_RELPATH,
    REVIEW_VERDICT_RELPATH,
    SEMANTIC_EVENTS_RELPATH,
    TRANSACTION_JOURNAL_RELPATH,
    SemanticReviewError,
    SemanticService,
    SemanticServiceError,
    SemanticSubmissionError,
)
from src.semantic.scheduler import SemanticScheduler


_IR_REVISION = "rev_" + "8" * 64


def _test_renderer(repo_root, ledger, *, graph=None):  # type: ignore[no-untyped-def]
    """Small deterministic projection used to isolate the service transaction."""

    docs = Path(repo_root) / ".codebase-docs"
    detail = docs / "unclassified" / "DETAIL.md"
    detail.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for symbol_id, symbol in sorted(ledger.symbols.items()):
        if not symbol.is_fresh or symbol.explanation is None:
            continue
        blocks.append(
            f"<!-- symbol:{symbol_id} -->\n"
            f"### `{symbol.qualified_name}`\n\n"
            f"{symbol.explanation.text}\n"
            f"<!-- end:symbol:{symbol_id} -->"
        )
    detail.write_text("# unclassified\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
    index = docs / "INDEX.md"
    index.write_text(
        "# Project\n\n[unclassified](unclassified/DETAIL.md)\n",
        encoding="utf-8",
    )
    return {
        "index_path": index.as_posix(),
        "detail_paths": [detail.as_posix()],
    }


def _source_repo(root: Path) -> None:
    (root / "app.py").write_text(
        "def leaf(value=1):\n"
        "    return value\n\n"
        "def caller():\n"
        "    return leaf()\n",
        encoding="utf-8",
    )


def _python_ir(root: Path):  # type: ignore[no-untyped-def]
    adapter = PythonLanguageAdapter(root)
    symbols = []
    relations = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        unit = SourceUnit(
            id=deterministic_entity_id(
                _IR_REVISION,
                relative,
                EntityKind.SOURCE_UNIT,
                relative,
            ),
            source_revision_id=_IR_REVISION,
            path=relative,
            language="python",
            content_hash=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            state=SourceUnitState.DISCOVERED,
            backend_id="python_ast",
            backend_version="test",
        )
        artifact = PythonAstBackend(root=root).parse(unit)
        assert isinstance(artifact, SyntaxArtifact)
        result = adapter.normalize(artifact)
        assert isinstance(result, FileIR)
        symbols.extend(result.symbols)
        relations.extend(result.relations)
    return tuple(symbols), tuple(relations)


def _explanation(symbol_id: str) -> str:
    return (
        f"{symbol_id} returns its computed value to its caller, preserves external state, "
        "and propagates any exception raised by the dependency it invokes."
    )


def _thread_events(thread_id: str, *extra: object) -> list[object]:
    return [{"type": "thread.started", "thread_id": thread_id}, *extra]


@pytest.fixture(autouse=True)
def _isolated_codex_producer(monkeypatch: pytest.MonkeyPatch) -> None:
    def producer(packet: dict[str, object]) -> tuple[list[dict], dict]:
        rows = packet["symbols"]
        assert isinstance(rows, list)
        explanations = []
        residuals = []
        for row in rows:
            assert isinstance(row, dict)
            if row.get("draft_explanation") is not None:
                explanations.append(
                    {"symbol_id": row["symbol_id"], "text": row["draft_explanation"]}
                )
            else:
                residuals.append(
                    {"symbol_id": row["symbol_id"], "reason": row["draft_residual"]}
                )
        return (
            [
                {
                    "type": "thread.started",
                    "thread_id": f"codex-producer-{packet['batch_id']}",
                }
            ],
            {"explanations": explanations, "residuals": residuals},
        )

    monkeypatch.setattr(
        SemanticService,
        "_run_codex_producer",
        staticmethod(producer),
    )


def _submit_semantic_batch(
    service: SemanticService,
    *,
    batch_id: str,
    source_revision: str,
    producer: str,
    explanations: dict[str, str],
    residuals: dict[str, str] | None = None,
    producer_events: object | None = None,
) -> object:
    del producer_events
    return service.submit_semantic_batch(
        batch_id=batch_id,
        actor=producer,
        source_revision=source_revision,
        explanations=explanations,
        residuals=residuals,
    )


def _install_review_runner(
    service: SemanticService,
    verdict: dict[str, object],
    *,
    reviewer: str = "independent-reviewer-thread",
    extra_events: tuple[object, ...] = (),
) -> None:
    service.review_runner = lambda _packet: (
        _thread_events(reviewer, *extra_events),
        verdict,
    )


def _explain_all(service: SemanticService, producer: str = "producer-thread") -> None:
    while service.get_semantic_progress()["uncovered_symbols"]:
        packet = service.claim_semantic_batch(
            actor=producer,
            max_context_tokens=20_000,
        )
        assert packet is not None
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer=producer,
            producer_events=_thread_events(producer),
            explanations={
                symbol.symbol_id: _explanation(symbol.symbol_id)
                for symbol in packet.symbols
            },
        )


def _sufficient_verdict(packet: dict[str, object]) -> dict[str, object]:
    samples = packet["samples"]
    assert isinstance(samples, list)
    return {
        "samples": [
            {
                "sample": sample["sample"],
                "verdicts": {
                    criterion: {
                        "decision": "充分",
                        "reason": f"源码与解释足以核实 {criterion}。",
                    }
                    for criterion in (
                        "function",
                        "role",
                        "io_side_effects",
                        "dependencies",
                    )
                },
            }
            for sample in samples
        ]
    }


def _race_bootstraps_after_staging(
    first: SemanticService,
    second: SemanticService,
    *,
    before_second_cas=None,  # type: ignore[no-untyped-def]
):  # type: ignore[no-untyped-def]
    """Deterministically hold two services after render staging, before CAS."""

    second_staged = Event()
    release_second = Event()
    first_renderer = first.renderer
    second_renderer = second.renderer

    def render_first(repo_root, ledger, *, graph=None):  # type: ignore[no-untyped-def]
        result = first_renderer(repo_root, ledger, graph=graph)
        assert second_staged.wait(timeout=5)
        return result

    def render_second(repo_root, ledger, *, graph=None):  # type: ignore[no-untyped-def]
        result = second_renderer(repo_root, ledger, graph=graph)
        second_staged.set()
        assert release_second.wait(timeout=5)
        return result

    first.renderer = render_first
    second.renderer = render_second
    with ThreadPoolExecutor(max_workers=2) as pool:
        second_future = pool.submit(second.bootstrap_semantic)
        first_future = pool.submit(first.bootstrap_semantic)
        first_result = first_future.result(timeout=10)
        if before_second_cas is not None:
            before_second_cas()
        release_second.set()
        try:
            second_result = second_future.result(timeout=10)
        except BaseException as exc:
            second_result = exc
    return first_result, second_result


def test_identical_concurrent_bootstraps_converge_on_canonical_ledger_and_docs(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    first = SemanticService(tmp_path, renderer=_test_renderer)
    second = SemanticService(tmp_path, renderer=_test_renderer)

    first_result, second_result = _race_bootstraps_after_staging(first, second)

    assert second_result == first_result
    assert first.store.reopen() == first_result
    assert (tmp_path / ".codebase-docs/INDEX.md").read_bytes() == (
        b"# Project\n\n[unclassified](unclassified/DETAIL.md)\n"
    )
    assert (tmp_path / ".codebase-docs/unclassified/DETAIL.md").read_bytes() == (
        b"# unclassified\n\n\n"
    )


def test_concurrent_bootstrap_candidate_divergence_remains_fail_closed(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    first = SemanticService(tmp_path, renderer=_test_renderer)
    second = SemanticService(
        tmp_path,
        renderer=_test_renderer,
        module_by_file={"app.py": "different-module"},
    )

    first_result, second_result = _race_bootstraps_after_staging(first, second)

    assert isinstance(second_result, SemanticServiceError)
    assert "changed concurrently" in str(second_result)
    assert first.store.reopen() == first_result


def test_concurrent_bootstrap_source_drift_remains_fail_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    first = SemanticService(tmp_path, renderer=_test_renderer)
    second = SemanticService(tmp_path, renderer=_test_renderer)

    def mutate_source() -> None:
        (tmp_path / "app.py").write_text(
            "def changed():\n    return 2\n",
            encoding="utf-8",
        )

    _first_result, second_result = _race_bootstraps_after_staging(
        first,
        second,
        before_second_cas=mutate_source,
    )

    assert isinstance(second_result, SemanticServiceError)
    assert "source changed" in str(second_result)


def test_concurrent_bootstrap_canonical_doc_mismatch_remains_fail_closed(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    first = SemanticService(tmp_path, renderer=_test_renderer)

    def divergent_renderer(repo_root, ledger, *, graph=None):  # type: ignore[no-untyped-def]
        result = _test_renderer(repo_root, ledger, graph=graph)
        Path(result["index_path"]).write_text("# divergent staged docs\n", encoding="utf-8")
        return result

    second = SemanticService(tmp_path, renderer=divergent_renderer)

    first_result, second_result = _race_bootstraps_after_staging(first, second)

    assert isinstance(second_result, SemanticServiceError)
    assert "changed concurrently" in str(second_result)
    assert first.store.reopen() == first_result
    assert (tmp_path / ".codebase-docs/INDEX.md").read_text(encoding="utf-8") == (
        "# Project\n\n[unclassified](unclassified/DETAIL.md)\n"
    )


def test_concurrent_bootstrap_corrupt_winner_ledger_remains_fail_closed(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    first = SemanticService(tmp_path, renderer=_test_renderer)
    second = SemanticService(tmp_path, renderer=_test_renderer)

    def corrupt_ledger() -> None:
        first.store.path.write_text("{not-json", encoding="utf-8")

    _first_result, second_result = _race_bootstraps_after_staging(
        first,
        second,
        before_second_cas=corrupt_ledger,
    )

    assert isinstance(second_result, Exception)
    assert "corrupt" in str(second_result)


def test_identical_concurrent_non_bootstrap_projection_remains_rejected(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    setup = SemanticService(tmp_path, renderer=_test_renderer)
    setup.bootstrap_semantic()
    first = SemanticService(tmp_path, renderer=_test_renderer)
    second = SemanticService(tmp_path, renderer=_test_renderer)

    first_result, second_result = _race_bootstraps_after_staging(first, second)
    assert second_result == first_result

    expected = first.store.reopen()
    first._commit_projection(
        expected=expected,
        candidate=expected,
        graph=first._scheduler_snapshot().graph,
    )
    with pytest.raises(SemanticServiceError, match="changed concurrently"):
        second._commit_projection(
            expected=None,
            candidate=expected,
            graph=second._scheduler_snapshot().graph,
        )


@pytest.mark.parametrize(
    "side_effects",
    (
        {"artifact_payloads": {Path(".codebase-analysis/side-effect.json"): {"x": 1}}},
        {"event_row": {"event": "side-effect"}},
        {
            "consume_once": (
                Path(".codebase-analysis/consume-once.json"),
                "identity",
                "bootstrap",
                SemanticServiceError,
                "already consumed",
            )
        },
        {"lease_guard": (object(), object())},
    ),
    ids=("artifact", "event", "consume-once", "lease-guard"),
)
def test_equivalent_bootstrap_gate_rejects_transactions_with_side_effects(
    tmp_path,
    side_effects,
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    candidate = service.bootstrap_semantic()

    with pytest.raises(SemanticServiceError, match="changed concurrently"):
        service._commit_projection(
            expected=None,
            candidate=candidate,
            graph=service._scheduler_snapshot().graph,
            allow_equivalent_bootstrap=True,
            **side_effects,
        )

    assert not (tmp_path / ".codebase-analysis/side-effect.json").exists()
    assert not (tmp_path / ".codebase-analysis/consume-once.json").exists()
    assert not (tmp_path / SEMANTIC_EVENTS_RELPATH).exists()


def test_bootstrap_progress_claim_and_submit_generate_real_ledger_and_docs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)

    ledger = service.bootstrap_semantic()
    progress = service.get_semantic_progress()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )

    assert ledger.totals.symbols == 2
    assert progress["totals"]["uncovered"] == 2
    assert packet is not None
    assert [item.symbol_id for item in packet.symbols] == ["app.py::leaf"]
    submitted = _submit_semantic_batch(service,
        batch_id=packet.batch_id,
        source_revision=packet.source_revision,
        producer="producer-thread",
        producer_events=_thread_events("producer-thread"),
        explanations={"app.py::leaf": _explanation("app.py::leaf")},
    )

    assert submitted.symbols["app.py::leaf"].is_fresh
    assert submitted.order == ("app.py::leaf",)
    assert (tmp_path / ".codebase-analysis/semantic_ledger.json").is_file()
    detail = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    assert "<!-- symbol:app.py::leaf -->" in detail.read_text(encoding="utf-8")

    caller_packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert caller_packet is not None
    assert caller_packet.symbols[0].callee_explanations
    events = [
        json.loads(line)
        for line in (tmp_path / SEMANTIC_EVENTS_RELPATH).read_text(encoding="utf-8").splitlines()
    ]
    assert {row["event"] for row in events} >= {"claim", "submit"}
    assert service.get_semantic_progress()["render_pending"] is False


def test_default_renderer_is_compatible_with_off_path_transaction_staging(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, module_by_file={"app.py": "application-core"})
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    submitted = _submit_semantic_batch(service,
        batch_id=packet.batch_id,
        source_revision=packet.source_revision,
        producer="producer-thread",
        producer_events=_thread_events("producer-thread"),
        explanations={"app.py::leaf": _explanation("app.py::leaf")},
    )

    index = (tmp_path / ".codebase-docs/INDEX.md").read_text(encoding="utf-8")
    detail = (tmp_path / ".codebase-docs/application-core/DETAIL.md").read_text(encoding="utf-8")
    assert f"# {tmp_path.name} 代码语义索引" in index
    assert "<!-- symbol:app.py::leaf -->" in detail
    assert submitted.symbols["app.py::leaf"].module_id == "application-core"


def test_service_preserves_ir_bridge_for_cross_file_callee_explanations(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "leaf.py").write_text(
        "def leaf():\n    return 1\n",
        encoding="utf-8",
    )
    (tmp_path / "caller.py").write_text(
        "from leaf import leaf\n\ndef caller():\n    return leaf()\n",
        encoding="utf-8",
    )
    ir_symbols, relations = _python_ir(tmp_path)
    service = SemanticService(
        tmp_path,
        ir_symbols=ir_symbols,
        relations=relations,
        renderer=_test_renderer,
    )
    service.bootstrap_semantic()

    leaf_packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert leaf_packet is not None
    assert [item.symbol_id for item in leaf_packet.symbols] == ["leaf.py::leaf"]
    _submit_semantic_batch(service,
        batch_id=leaf_packet.batch_id,
        source_revision=leaf_packet.source_revision,
        producer="producer-thread",
        producer_events=_thread_events("producer-thread"),
        explanations={"leaf.py::leaf": _explanation("leaf.py::leaf")},
    )

    caller_packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert caller_packet is not None
    assert caller_packet.symbols[0].symbol_id == "caller.py::caller"
    assert caller_packet.symbols[0].callee_ids == ("leaf.py::leaf",)
    assert caller_packet.symbols[0].callee_explanations == (
        ("leaf.py::leaf", _explanation("leaf.py::leaf")),
    )


def test_render_semantic_docs_repairs_only_docs_from_canonical_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    _submit_semantic_batch(service,
        batch_id=packet.batch_id,
        source_revision=packet.source_revision,
        producer="producer-thread",
        producer_events=_thread_events("producer-thread"),
        explanations={"app.py::leaf": _explanation("app.py::leaf")},
    )
    ledger_before = service.store.path.read_bytes()
    review = tmp_path / REVIEW_VERDICT_RELPATH
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text('{"sentinel":true}\n', encoding="utf-8")
    review_before = review.read_bytes()
    (tmp_path / ".codebase-docs/INDEX.md").write_text("corrupt\n", encoding="utf-8")

    result = service.render_semantic_docs()

    assert Path(result["index_path"]).read_text(encoding="utf-8").startswith(
        "<!-- generated:codebase-explorer-semantic-docs -->"
    )
    assert service.store.path.read_bytes() == ledger_before
    assert review.read_bytes() == review_before


def test_progress_marks_corrupted_docs_pending_and_invalidates_review(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    _install_review_runner(service, _sufficient_verdict(packet))
    service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    assert service.get_semantic_progress()["review_verdict_present"] is True

    detail = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    detail.write_text("CORRUPTED\n", encoding="utf-8")
    progress = service.get_semantic_progress()

    assert progress["render_pending"] is True
    assert progress["review_verdict_present"] is False


def test_submit_validation_failures_leave_ledger_and_docs_byte_identical(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    ledger_path = tmp_path / ".codebase-analysis/semantic_ledger.json"
    detail_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    before = (ledger_path.read_bytes(), detail_path.read_bytes())

    bad_calls = (
        {
            "batch_id": packet.batch_id,
            "source_revision": "sha256:" + "0" * 64,
            "producer": "producer-thread",
            "producer_events": _thread_events("producer-thread"),
            "explanations": {"app.py::leaf": _explanation("app.py::leaf")},
        },
        {
            "batch_id": packet.batch_id,
            "source_revision": packet.source_revision,
            "producer": "producer-thread",
            "producer_events": _thread_events("producer-thread"),
            "explanations": {},
        },
    )
    for kwargs in bad_calls:
        with pytest.raises(SemanticSubmissionError):
            _submit_semantic_batch(service, **kwargs)
        assert (ledger_path.read_bytes(), detail_path.read_bytes()) == before

    original_source = (tmp_path / "app.py").read_text(encoding="utf-8")
    (tmp_path / "app.py").write_text(original_source.replace("return value", "return value + 1"), encoding="utf-8")
    with pytest.raises(SemanticSubmissionError, match="source changed"):
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            producer_events=_thread_events("producer-thread"),
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )
    assert (ledger_path.read_bytes(), detail_path.read_bytes()) == before


def test_renderer_failure_rolls_back_the_entire_submit_and_keeps_lease(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    ledger_path = tmp_path / ".codebase-analysis/semantic_ledger.json"
    docs_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    before = (ledger_path.read_bytes(), docs_path.read_bytes())

    def failing_renderer(repo_root, ledger, *, graph=None):  # type: ignore[no-untyped-def]
        _test_renderer(repo_root, ledger, graph=graph)
        raise OSError("simulated render failure")

    service.renderer = failing_renderer
    with pytest.raises(OSError, match="simulated render failure"):
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            producer_events=_thread_events("producer-thread"),
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )

    assert (ledger_path.read_bytes(), docs_path.read_bytes()) == before
    assert service.recover_semantic_batch(packet.batch_id) == packet


def test_producer_identity_comes_only_from_server_owned_runner_events(
    tmp_path: Path,
) -> None:
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    before = service.store.path.read_bytes()
    explanations = {"app.py::leaf": _explanation("app.py::leaf")}
    produced = {
        "explanations": [
            {"symbol_id": "app.py::leaf", "text": explanations["app.py::leaf"]}
        ],
        "residuals": [],
    }
    service.producer_runner = lambda _packet: ([], produced)
    with pytest.raises(SemanticSubmissionError, match="non-empty"):
        service.submit_semantic_batch(
            batch_id=packet.batch_id,
            actor="producer-thread",
            source_revision=packet.source_revision,
            explanations=explanations,
        )
    service.producer_runner = lambda _packet: (
        _thread_events("real-server-owned-producer"),
        produced,
    )
    submitted = service.submit_semantic_batch(
        batch_id=packet.batch_id,
        actor="producer-thread",
        source_revision=packet.source_revision,
        explanations=explanations,
    )
    assert submitted.symbols["app.py::leaf"].explanation is not None
    assert (
        submitted.symbols["app.py::leaf"].explanation.producer
        == "codex:real-server-owned-producer"
    )
    assert service.store.path.read_bytes() != before


def test_submit_rejects_a_different_host_lease_owner_before_producer_dispatch(
    tmp_path: Path,
) -> None:
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="trusted-host-a",
        max_context_tokens=20_000,
    )
    assert packet is not None
    producer_called = False

    def producer(_packet):  # type: ignore[no-untyped-def]
        nonlocal producer_called
        producer_called = True
        raise AssertionError("producer must not run for a mismatched lease owner")

    service.producer_runner = producer
    with pytest.raises(SemanticSubmissionError, match="owner mismatch"):
        service.submit_semantic_batch(
            batch_id=packet.batch_id,
            actor="trusted-host-b",
            source_revision=packet.source_revision,
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )
    assert producer_called is False


def test_concurrent_submit_dispatches_one_server_owned_producer(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    setup = SemanticService(tmp_path, renderer=_test_renderer)
    setup.bootstrap_semantic()
    packet = setup.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    producer_started = Event()
    producer_release = Event()
    producer_calls = 0

    def producer(producer_packet):  # type: ignore[no-untyped-def]
        nonlocal producer_calls
        producer_calls += 1
        producer_started.set()
        assert producer_release.wait(timeout=5)
        row = producer_packet["symbols"][0]
        return (
            _thread_events("only-producer"),
            {
                "explanations": [
                    {
                        "symbol_id": row["symbol_id"],
                        "text": row["draft_explanation"],
                    }
                ],
                "residuals": [],
            },
        )

    services = (
        SemanticService(tmp_path, renderer=_test_renderer, producer_runner=producer),
        SemanticService(tmp_path, renderer=_test_renderer, producer_runner=producer),
    )

    def submit(service):  # type: ignore[no-untyped-def]
        try:
            return service.submit_semantic_batch(
                batch_id=packet.batch_id,
                actor="producer-thread",
                source_revision=packet.source_revision,
                explanations={"app.py::leaf": _explanation("app.py::leaf")},
            )
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(submit, services[0])
        assert producer_started.wait(timeout=5)
        second = pool.submit(submit, services[1]).result(timeout=5)
        producer_release.set()
        first_result = first.result(timeout=5)

    assert not isinstance(first_result, Exception)
    assert isinstance(second, SemanticSubmissionError)
    assert "already in progress" in str(second)
    assert producer_calls == 1


def test_review_packet_is_deterministic_anonymous_and_identity_gated(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)

    packet = service.get_semantic_review_batch()
    assert packet == service.get_semantic_review_batch()
    samples = packet["samples"]
    assert len(samples) == 2
    assert all(set(sample) == {"sample", "source", "explanation"} for sample in samples)
    packet_on_disk = json.loads((tmp_path / REVIEW_PACKET_RELPATH).read_text(encoding="utf-8"))
    hidden = json.loads((tmp_path / REVIEW_HIDDEN_MAP_RELPATH).read_text(encoding="utf-8"))
    assert packet_on_disk == {"samples": samples}
    assert {sample["sample"] for sample in samples} == set(hidden)
    assert all(set(value) == {"symbol_id", "producer_session_id"} for value in hidden.values())

    verdict = _sufficient_verdict(packet)
    ledger_before = (tmp_path / ".codebase-analysis/semantic_ledger.json").read_bytes()
    actual_producer = next(iter(hidden.values()))["producer_session_id"].removeprefix(
        "codex:"
    )
    _install_review_runner(service, verdict, reviewer=actual_producer)
    with pytest.raises(SemanticReviewError, match="different"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    assert (tmp_path / ".codebase-analysis/semantic_ledger.json").read_bytes() == ledger_before
    assert not (tmp_path / REVIEW_VERDICT_RELPATH).exists()

    _install_review_runner(service, verdict)
    accepted = service.submit_semantic_review(
        review_batch_id=packet["review_batch_id"]
    )
    assert accepted["revision_symbol_ids"] == []
    artifact = json.loads((tmp_path / REVIEW_VERDICT_RELPATH).read_text(encoding="utf-8"))
    assert artifact["reviewer_session_id"] == "codex:independent-reviewer-thread"
    assert service.get_semantic_progress()["review_verdict_present"] is True


def test_review_binding_rejects_tampering_wrong_batch_and_replay(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    receipt = json.loads(
        (tmp_path / REVIEW_BATCH_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    assert receipt["review_batch_id"] == packet["review_batch_id"]
    verdict = _sufficient_verdict(packet)
    _install_review_runner(service, verdict)

    with pytest.raises(SemanticReviewError, match="binding"):
        service.submit_semantic_review(review_batch_id="sha256:" + "0" * 64)

    packet_path = tmp_path / REVIEW_PACKET_RELPATH
    original = packet_path.read_bytes()
    tampered = json.loads(original)
    tampered["samples"][0]["explanation"] += " tampered"
    packet_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(SemanticReviewError, match="binding"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    packet_path.write_bytes(original)

    service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    with pytest.raises(SemanticReviewError, match="already been consumed"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])


def test_concurrent_review_submit_consumes_one_batch_exactly_once(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    setup = SemanticService(tmp_path, renderer=_test_renderer)
    setup.bootstrap_semantic()
    _explain_all(setup)
    packet = setup.get_semantic_review_batch()
    verdict = _sufficient_verdict(packet)
    reviewer_started = Event()
    reviewer_release = Event()
    runner_calls = 0

    def runner(_packet):  # type: ignore[no-untyped-def]
        nonlocal runner_calls
        runner_calls += 1
        reviewer_started.set()
        assert reviewer_release.wait(timeout=5)
        return _thread_events("concurrent-independent-reviewer"), verdict

    services = (
        SemanticService(tmp_path, renderer=_test_renderer, review_runner=runner),
        SemanticService(tmp_path, renderer=_test_renderer, review_runner=runner),
    )

    def submit(service):  # type: ignore[no-untyped-def]
        try:
            return service.submit_semantic_review(
                review_batch_id=packet["review_batch_id"]
            )
        except Exception as exc:  # captured so both contenders are asserted
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(submit, services[0])
        assert reviewer_started.wait(timeout=5)
        second = pool.submit(submit, services[1])
        second_outcome = second.result(timeout=5)
        reviewer_release.set()
        outcomes = [first.result(timeout=5), second_outcome]

    successes = [item for item in outcomes if isinstance(item, dict)]
    failures = [item for item in outcomes if isinstance(item, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], SemanticReviewError)
    assert "already in progress" in str(failures[0])
    assert runner_calls == 1
    events = [
        json.loads(line)
        for line in (tmp_path / SEMANTIC_EVENTS_RELPATH).read_text(encoding="utf-8").splitlines()
    ]
    assert sum(row["event"] == "review_submit" for row in events) == 1


@pytest.mark.parametrize(
    "events,match",
    [
        (
            [
                {"type": "thread.started", "thread_id": "reviewer-a"},
                {"type": "thread.started", "thread_id": "reviewer-b"},
            ],
            "exactly one",
        ),
        (
            [
                {"type": "thread.started", "thread_id": "reviewer-a"},
                {"type": "item.completed", "item": {"type": "mcp_tool_call"}},
            ],
            "forbidden tool",
        ),
        ([{"type": "item.completed"}], "exactly one"),
    ],
)
def test_reviewer_codex_events_are_strictly_validated(
    tmp_path, events, match
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    verdict = _sufficient_verdict(packet)
    service.review_runner = lambda _packet: (events, verdict)

    with pytest.raises(SemanticReviewError, match=match):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    assert not (tmp_path / REVIEW_VERDICT_RELPATH).exists()


def test_accepted_review_becomes_non_current_after_any_ledger_update(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    _install_review_runner(service, _sufficient_verdict(packet))
    service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    assert service.get_semantic_progress()["review_verdict_present"] is True

    source = (tmp_path / "app.py").read_text(encoding="utf-8")
    (tmp_path / "app.py").write_text(
        source.replace("return value", "return value + 1"),
        encoding="utf-8",
    )
    service.reconcile_semantic()

    assert service.get_semantic_progress()["review_verdict_present"] is False
    assert (tmp_path / REVIEW_VERDICT_RELPATH).is_file()


def test_non_sufficient_review_invalidates_sample_and_reverse_callers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    hidden = json.loads((tmp_path / REVIEW_HIDDEN_MAP_RELPATH).read_text(encoding="utf-8"))
    leaf_sample = next(
        sample for sample, value in hidden.items() if value["symbol_id"] == "app.py::leaf"
    )
    verdict = _sufficient_verdict(packet)
    leaf_verdict = next(item for item in verdict["samples"] if item["sample"] == leaf_sample)
    leaf_verdict["verdicts"]["dependencies"] = {
        "decision": "部分",
        "reason": "解释遗漏了调用者依赖该返回值的关系。",
    }

    _install_review_runner(service, verdict)
    accepted = service.submit_semantic_review(
        review_batch_id=packet["review_batch_id"]
    )
    ledger = service.store.reopen()

    assert accepted["revision_symbol_ids"] == ["app.py::leaf"]
    assert ledger.symbols["app.py::leaf"].explanation is None
    assert ledger.symbols["app.py::caller"].explanation is None
    assert set(ledger.uncovered_symbols) == {"app.py::leaf", "app.py::caller"}
    assert ledger.order == ()
    detail = (tmp_path / ".codebase-docs/unclassified/DETAIL.md").read_text(encoding="utf-8")
    assert "<!-- symbol:app.py::leaf -->" not in detail
    assert "<!-- symbol:app.py::caller -->" not in detail
    assert (tmp_path / REVIEW_VERDICT_RELPATH).is_file()


def test_review_verdict_publish_failure_rolls_back_ledger_docs_and_old_verdict(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    sufficient = _sufficient_verdict(packet)
    _install_review_runner(
        service,
        sufficient,
        reviewer="first-independent-reviewer",
    )
    service.submit_semantic_review(review_batch_id=packet["review_batch_id"])

    source = (tmp_path / "app.py").read_text(encoding="utf-8")
    (tmp_path / "app.py").write_text(
        source.replace("return value", "return value + 1"),
        encoding="utf-8",
    )
    service.reconcile_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()

    hidden = json.loads((tmp_path / REVIEW_HIDDEN_MAP_RELPATH).read_text(encoding="utf-8"))
    leaf_sample = next(
        sample for sample, value in hidden.items() if value["symbol_id"] == "app.py::leaf"
    )
    revise = _sufficient_verdict(packet)
    leaf_verdict = next(item for item in revise["samples"] if item["sample"] == leaf_sample)
    leaf_verdict["verdicts"]["role"] = {
        "decision": "不充分",
        "reason": "解释没有说明这个函数为何服务于调用链。",
    }
    ledger_path = tmp_path / ".codebase-analysis/semantic_ledger.json"
    detail_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    verdict_path = tmp_path / REVIEW_VERDICT_RELPATH
    acceptance_path = tmp_path / REVIEW_ACCEPTANCE_RECEIPT_RELPATH
    before = (
        ledger_path.read_bytes(),
        detail_path.read_bytes(),
        verdict_path.read_bytes(),
        acceptance_path.read_bytes(),
    )

    def fail_publish(_staged, _target):  # type: ignore[no-untyped-def]
        raise OSError("simulated verdict publish failure")

    monkeypatch.setattr(service, "_publish_review_artifact", fail_publish)
    _install_review_runner(
        service,
        revise,
        reviewer="second-independent-reviewer",
    )
    with pytest.raises(OSError, match="simulated verdict publish failure"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])

    assert (
        ledger_path.read_bytes(),
        detail_path.read_bytes(),
        verdict_path.read_bytes(),
        acceptance_path.read_bytes(),
    ) == before
    assert service.store.reopen().coverage_percent == 100.0


def test_all_pass_review_artifacts_publish_as_one_transaction(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    _install_review_runner(service, _sufficient_verdict(packet))

    ledger_path = tmp_path / ".codebase-analysis/semantic_ledger.json"
    detail_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    before = (ledger_path.read_bytes(), detail_path.read_bytes())
    original_publish = service._publish_review_artifact
    publish_count = 0

    def fail_second_publish(staged, target):  # type: ignore[no-untyped-def]
        nonlocal publish_count
        publish_count += 1
        if publish_count == 2:
            raise OSError("simulated second review artifact failure")
        original_publish(staged, target)

    monkeypatch.setattr(service, "_publish_review_artifact", fail_second_publish)
    with pytest.raises(OSError, match="second review artifact failure"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])

    assert publish_count == 2
    assert (ledger_path.read_bytes(), detail_path.read_bytes()) == before
    assert not (tmp_path / REVIEW_VERDICT_RELPATH).exists()
    assert not (tmp_path / REVIEW_ACCEPTANCE_RECEIPT_RELPATH).exists()
    assert not (tmp_path / TRANSACTION_JOURNAL_RELPATH).exists()
    assert service.get_semantic_progress()["review_verdict_present"] is False


def test_submit_event_staging_failure_rolls_back_and_keeps_lease(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    ledger_path = service.store.path
    detail_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    events_path = tmp_path / SEMANTIC_EVENTS_RELPATH
    before = (ledger_path.read_bytes(), detail_path.read_bytes(), events_path.read_bytes())

    def fail_event_stage(*_args):  # type: ignore[no-untyped-def]
        raise OSError("simulated semantic event append failure")

    monkeypatch.setattr(service, "_stage_event_append", fail_event_stage)
    with pytest.raises(OSError, match="event append failure"):
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            producer_events=_thread_events("producer-thread"),
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )

    assert (ledger_path.read_bytes(), detail_path.read_bytes(), events_path.read_bytes()) == before
    assert not (tmp_path / service._submission_receipt_path(packet.batch_id)).exists()
    assert service.recover_semantic_batch(packet.batch_id) == packet


def test_claim_event_failure_rolls_back_the_new_lease(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    original_append = service._append_event_unlocked

    def fail_claim_event(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("simulated claim evidence failure")

    monkeypatch.setattr(service, "_append_event_unlocked", fail_claim_event)
    with pytest.raises(OSError, match="claim evidence failure"):
        service.claim_semantic_batch(
            actor="producer-thread",
            max_context_tokens=20_000,
        )

    monkeypatch.setattr(service, "_append_event_unlocked", original_append)
    replacement = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert replacement is not None


def test_service_init_releases_a_crash_orphan_claim_without_event(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    setup = SemanticService(tmp_path, renderer=_test_renderer)
    setup.bootstrap_semantic()
    scheduler = setup._scheduler_snapshot()
    orphan = scheduler.claim_semantic_batch(
        lease_owner="producer-thread",
        max_context_tokens=20_000,
        now=setup._now(),
    )
    assert orphan is not None

    recovered = SemanticService(tmp_path, renderer=_test_renderer)

    assert recovered.recover_semantic_batch(orphan.batch_id) is None
    replacement = recovered.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert replacement is not None


def test_producer_result_is_rejected_if_lease_expires_while_running(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    current = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    service = SemanticService(
        tmp_path,
        renderer=_test_renderer,
        clock=lambda: current,
    )
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
        lease_seconds=1,
    )
    assert packet is not None
    original = service.producer_runner

    def expires_during_production(producer_packet):  # type: ignore[no-untyped-def]
        nonlocal current
        current += timedelta(seconds=2)
        return original(producer_packet)

    service.producer_runner = expires_during_production
    with pytest.raises(SemanticSubmissionError, match="while the Codex producer"):
        _submit_semantic_batch(
            service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )
    assert service.store.reopen().symbols["app.py::leaf"].explanation is None


def test_review_event_staging_failure_rolls_back_artifacts_and_can_retry(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    _install_review_runner(service, _sufficient_verdict(packet))
    ledger_before = service.store.path.read_bytes()
    events_path = tmp_path / SEMANTIC_EVENTS_RELPATH
    events_before = events_path.read_bytes()
    original_stage = service._stage_event_append

    def fail_event_stage(*_args):  # type: ignore[no-untyped-def]
        raise OSError("simulated review event append failure")

    monkeypatch.setattr(service, "_stage_event_append", fail_event_stage)
    with pytest.raises(OSError, match="review event append failure"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])

    assert service.store.path.read_bytes() == ledger_before
    assert events_path.read_bytes() == events_before
    assert not (tmp_path / REVIEW_VERDICT_RELPATH).exists()
    assert not (tmp_path / REVIEW_ACCEPTANCE_RECEIPT_RELPATH).exists()

    monkeypatch.setattr(service, "_stage_event_append", original_stage)
    accepted = service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    assert accepted["revision_symbol_ids"] == []


def test_semantic_events_symlink_rejects_submit_without_mutation_or_escape(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    ledger_before = service.store.path.read_bytes()
    detail_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    detail_before = detail_path.read_bytes()
    outside = tmp_path.parent / f"{tmp_path.name}-outside-events.jsonl"
    outside.write_bytes(b'{"outside":true}\n')
    events_path = tmp_path / SEMANTIC_EVENTS_RELPATH
    events_path.unlink()
    events_path.symlink_to(outside)

    with pytest.raises(SemanticServiceError, match="symlink"):
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            producer_events=_thread_events("producer-thread"),
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )

    assert service.store.path.read_bytes() == ledger_before
    assert detail_path.read_bytes() == detail_before
    assert outside.read_bytes() == b'{"outside":true}\n'
    events_path.unlink()
    assert service.recover_semantic_batch(packet.batch_id) == packet


def test_lease_cleanup_failure_does_not_turn_committed_submit_into_retry(
    tmp_path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None

    def fail_release(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("simulated scheduler cleanup failure")

    monkeypatch.setattr(SemanticScheduler, "release_batch", fail_release)
    submitted = _submit_semantic_batch(service,
        batch_id=packet.batch_id,
        source_revision=packet.source_revision,
        producer="producer-thread",
        producer_events=_thread_events("producer-thread"),
        explanations={"app.py::leaf": _explanation("app.py::leaf")},
    )
    assert submitted.symbols["app.py::leaf"].is_fresh

    with pytest.raises(SemanticSubmissionError, match="already been submitted"):
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            producer_events=_thread_events("producer-thread"),
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )


def test_expired_lease_rejects_submit_without_mutation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    current = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    service = SemanticService(tmp_path, renderer=_test_renderer, clock=lambda: current)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
        lease_seconds=10,
    )
    assert packet is not None
    before = (tmp_path / ".codebase-analysis/semantic_ledger.json").read_bytes()
    current += timedelta(seconds=11)

    with pytest.raises(SemanticSubmissionError, match="expired"):
        _submit_semantic_batch(service,
            batch_id=packet.batch_id,
            source_revision=packet.source_revision,
            producer="producer-thread",
            producer_events=_thread_events("producer-thread"),
            explanations={"app.py::leaf": _explanation("app.py::leaf")},
        )
    assert (tmp_path / ".codebase-analysis/semantic_ledger.json").read_bytes() == before


def test_review_artifact_symlink_parent_is_rejected_without_outside_write(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path, renderer=_test_renderer)
    service.bootstrap_semantic()
    _explain_all(service)
    packet = service.get_semantic_review_batch()
    verdict = _sufficient_verdict(packet)
    _install_review_runner(service, verdict)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-review"
    outside.mkdir()
    reviews = tmp_path / ".codebase-analysis/semantic_reviews"
    reviews.symlink_to(outside, target_is_directory=True)

    with pytest.raises(SemanticServiceError, match="symlink"):
        service.submit_semantic_review(review_batch_id=packet["review_batch_id"])
    assert list(outside.iterdir()) == []


def test_process_crash_recovers_old_ledger_docs_and_emits_checkpoint(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _source_repo(tmp_path)
    service = SemanticService(tmp_path)
    service.bootstrap_semantic()
    packet = service.claim_semantic_batch(
        actor="producer-thread",
        max_context_tokens=20_000,
    )
    assert packet is not None
    ledger_path = service.store.path
    detail_path = tmp_path / ".codebase-docs/unclassified/DETAIL.md"
    before = (ledger_path.read_bytes(), detail_path.read_bytes())
    project_root = Path(__file__).parents[1]
    script = """
import os
import sys
from src.semantic.service import SemanticService

def producer(packet):
    return (
        [{"type": "thread.started", "thread_id": "crash-producer"}],
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

class CrashService(SemanticService):
    def _transaction_checkpoint(self, phase):
        if phase == "after_artifact_publish:.codebase-analysis/semantic_events.jsonl":
            os._exit(91)

service = CrashService(sys.argv[1], producer_runner=producer)
service.submit_semantic_batch(
    batch_id=sys.argv[2],
    actor="producer-thread",
    source_revision=sys.argv[3],
    explanations={"app.py::leaf": (
        "app.py::leaf returns its computed value to its caller, preserves external state, "
        "and propagates any exception raised by the dependency it invokes."
    )},
)
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            tmp_path.as_posix(),
            packet.batch_id,
            packet.source_revision,
        ],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": project_root.as_posix()},
        check=False,
    )
    assert completed.returncode == 91
    assert (tmp_path / TRANSACTION_JOURNAL_RELPATH).is_file()
    assert service.get_semantic_progress()["render_pending"] is True

    recovered = SemanticService(tmp_path)

    assert (ledger_path.read_bytes(), detail_path.read_bytes()) == before
    assert not (tmp_path / TRANSACTION_JOURNAL_RELPATH).exists()
    assert not (tmp_path / service._submission_receipt_path(packet.batch_id)).exists()
    events = [
        json.loads(line)
        for line in (tmp_path / SEMANTIC_EVENTS_RELPATH).read_text(encoding="utf-8").splitlines()
    ]
    assert {row["event"] for row in events} >= {"claim", "recovery"}
    assert all(row["event"] != "submit" for row in events)
    assert recovered.recover_semantic_batch(packet.batch_id) == packet
