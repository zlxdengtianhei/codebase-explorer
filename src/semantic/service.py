"""Transactional semantic lifecycle and independent-review orchestration.

The service is the only product ingress that turns a leased explanation batch
into both canonical ledger state and readable documents.  It also constructs a
blind reviewer packet and consumes verdicts without giving the reviewer access
to symbol identities or producer metadata.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import networkx as nx

from src.ir import Relation, Symbol
from src.semantic.coverage import derive_static_coverage
from src.semantic.gates import assert_prompt_dispatchable
from src.semantic.inventory import (
    SemanticInventory,
    enumerate_semantic_inventory,
    persist_file_out_edge_revisions,
    reconcile_semantic_ledger,
)
from src.semantic.l1_facts import (
    failed_checks,
    run_l1_checks,
    try_parse_l1_fact_text,
)
from src.semantic.l1_packet import (
    L1PacketSymbol,
    build_packet_payload,
    kind_from_record,
    signature_line,
)
from src.semantic.models import (
    PENDING_EXPLANATION_REASON,
    SemanticExplanation,
    SemanticLedger,
    SemanticResidual,
    SemanticSymbolKind,
    revalidate_semantic_ledger,
)
from src.semantic.scheduler import (
    SCHEDULER_STATE_RELPATH,
    SemanticBatchPacket,
    SemanticScheduler,
)
from src.semantic.store import SemanticLedgerStore


REVIEW_PACKET_RELPATH = Path(".codebase-analysis/semantic_review_packet.json")
REVIEW_HIDDEN_MAP_RELPATH = Path(
    ".codebase-analysis/semantic_review_hidden_map.json"
)
REVIEW_VERDICT_RELPATH = Path(
    ".codebase-analysis/semantic_reviews/verdict.accepted.json"
)
REVIEW_BATCH_RECEIPT_RELPATH = Path(
    ".codebase-analysis/semantic_review_batch_receipt.json"
)
REVIEW_ACCEPTANCE_RECEIPT_RELPATH = Path(
    ".codebase-analysis/semantic_reviews/acceptance_receipt.json"
)
REVIEW_EVENTS_RELPATH = Path(
    ".codebase-analysis/semantic_reviews/codex_events.jsonl"
)
REVIEW_DISPATCH_RELPATH = Path(
    ".codebase-analysis/semantic_reviews/dispatch_reservation.json"
)
TRANSACTION_JOURNAL_RELPATH = Path(
    ".codebase-analysis/semantic_transaction_journal.json"
)
TRANSACTION_BACKUP_RELDIR = Path(
    ".codebase-analysis/semantic_transaction_backup"
)
SEMANTIC_EVENTS_RELPATH = Path(".codebase-analysis/semantic_events.jsonl")
SEMANTIC_SUBMISSION_RECEIPTS_RELDIR = Path(
    ".codebase-analysis/semantic_submissions"
)
SEMANTIC_SUBMISSION_DISPATCH_RELDIR = Path(
    ".codebase-analysis/semantic_submission_dispatch"
)

_REVIEW_CRITERIA = frozenset(
    {"function", "role", "io_side_effects", "dependencies"}
)
_REVIEW_DECISIONS = frozenset({"充分", "部分", "不充分", "判不了"})
_ALLOWED_RESIDUAL_CODES = frozenset(
    {
        "SYNTAX_ERROR_FILE",
        "TYPE_CHECKING_STUB",
        "GENERATED_CODE",
        "VENDORED_THIRD_PARTY",
    }
)
_REVIEW_SEED = "codebase-explorer-review-v3"
_FORBIDDEN_REVIEW_EVENT_TYPES = frozenset(
    {"command_execution", "mcp_tool_call", "web_search"}
)

Renderer = Callable[..., Mapping[str, object]]
ReviewRunner = Callable[
    [Mapping[str, object]],
    tuple[object, Mapping[str, object]],
]
ProducerRunner = ReviewRunner


class SemanticServiceError(RuntimeError):
    """Base error for service-level state or transaction failures."""


class SemanticSubmissionError(SemanticServiceError):
    """A semantic batch failed validation and was not written."""


class SemanticReviewError(SemanticServiceError):
    """A reviewer packet or verdict failed the independent-review contract."""


def _default_renderer(
    repo_root: str | Path,
    ledger: SemanticLedger,
    *,
    graph: nx.DiGraph | None = None,
    partition_path: str | Path | None = None,
    names_path: str | Path | None = None,
    consume_partition: bool = True,
) -> Mapping[str, object]:
    from src.semantic.render import (
        discover_names_path,
        discover_partition_path,
        render_semantic_docs,
    )

    root = Path(repo_root)
    chosen = Path(partition_path) if partition_path is not None else discover_partition_path(root)
    names = Path(names_path) if names_path is not None else discover_names_path(root, chosen)
    return render_semantic_docs(
        repo_root,
        ledger,
        graph=graph,
        partition_path=chosen,
        names_path=names,
        consume_partition=consume_partition,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("service clock must return a timezone-aware datetime")
    return value.astimezone(UTC)


def _codex_identity(session_id: str) -> str:
    """Qualify a server-owned Codex thread for durable producer attribution."""

    return f"codex:{session_id.strip()}"


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SemanticServiceError(f"refusing to replace a symlinked artifact: {path}")
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


_JSON_WHITESPACE = " \t\r\n"
_CANONICAL_DOCS_ROOT_VALUE = '"<canonical-docs-root>"'


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant: {value}")


def _skip_json_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1
    return index


def _json_object_members(
    text: str,
    start: int,
    decoder: json.JSONDecoder,
) -> Iterator[tuple[str, int, int, object]]:
    if start >= len(text) or text[start] != "{":
        raise ValueError("expected JSON object")
    index = _skip_json_whitespace(text, start + 1)
    if index < len(text) and text[index] == "}":
        return
    while True:
        key, key_end = decoder.raw_decode(text, index)
        if not isinstance(key, str):
            raise ValueError("JSON object key must be a string")
        index = _skip_json_whitespace(text, key_end)
        if index >= len(text) or text[index] != ":":
            raise ValueError("expected JSON object separator")
        value_start = _skip_json_whitespace(text, index + 1)
        value, value_end = decoder.raw_decode(text, value_start)
        yield key, value_start, value_end, value
        index = _skip_json_whitespace(text, value_end)
        if index >= len(text):
            raise ValueError("unterminated JSON object")
        if text[index] == "}":
            return
        if text[index] != ",":
            raise ValueError("expected JSON object delimiter")
        index = _skip_json_whitespace(text, index + 1)


def _canonical_docs_fingerprint_payload(relative: str, payload: bytes) -> bytes:
    """Ignore only renderer staging paths when comparing equivalent docs.

    ``HOPS.json`` records the documentation root used by the renderer.  The
    transaction stages each candidate under a fresh temporary directory, so
    that diagnostic locator is expected to differ even when the rendered
    semantic projection is identical.  Keep every other byte (and fail
    closed for malformed JSON) in the comparison.
    """

    if relative != "HOPS.json":
        return payload
    try:
        text = payload.decode("utf-8")
        start = _skip_json_whitespace(text, 0)
        decoder = json.JSONDecoder(
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
        decoded, end = decoder.raw_decode(text, start)
        if text[end:].strip(_JSON_WHITESPACE):
            return payload
        if not isinstance(decoded, dict):
            return payload

        root_members = list(_json_object_members(text, start, decoder))
        trees_member = next(
            (member for member in root_members if member[0] == "trees"),
            None,
        )
        if trees_member is None or not isinstance(trees_member[3], dict):
            return payload

        replacements: list[tuple[int, int]] = []
        for _, tree_start, _, tree in _json_object_members(
            text,
            trees_member[1],
            decoder,
        ):
            if not isinstance(tree, dict):
                continue
            for key, value_start, value_end, _ in _json_object_members(
                text,
                tree_start,
                decoder,
            ):
                if key == "docs_root":
                    replacements.append((value_start, value_end))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return payload

    if not replacements:
        return payload
    chunks: list[str] = []
    cursor = 0
    for value_start, value_end in replacements:
        chunks.append(text[cursor:value_start])
        chunks.append(_CANONICAL_DOCS_ROOT_VALUE)
        cursor = value_end
    chunks.append(text[cursor:])
    return "".join(chunks).encode("utf-8")


def _docs_fingerprint(repo_root: Path) -> str:
    docs = repo_root / ".codebase-docs"
    if docs.is_symlink() or not docs.is_dir():
        return "missing"
    digest = hashlib.sha256()
    files = [path for path in sorted(docs.rglob("*")) if path.is_file()]
    for path in files:
        if path.is_symlink():
            return "unsafe"
        relative_name = path.relative_to(docs).as_posix()
        relative = relative_name.encode("utf-8")
        payload = _canonical_docs_fingerprint_payload(relative_name, path.read_bytes())
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return "sha256:" + digest.hexdigest()


class SemanticService:
    """Coordinate inventory, leases, atomic projection, and blind review."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        ir_symbols: Iterable[Symbol] = (),
        relations: Iterable[Relation] = (),
        module_by_file: Mapping[str, str] | None = None,
        renderer: Renderer | None = None,
        producer_runner: ProducerRunner | None = None,
        review_runner: ReviewRunner | None = None,
        clock: Callable[[], datetime] | None = None,
        consume_partition: bool = True,
    ) -> None:
        self.store = SemanticLedgerStore(repo_root)
        self.repo_root = self.store.repo_root
        self.ir_symbols = tuple(ir_symbols)
        self.relations = tuple(
            relation.model_copy(update={"kind": "calls"})
            if relation.kind == "call"
            else relation
            for relation in relations
        )
        self.module_by_file = dict(module_by_file or {})
        self.consume_partition = consume_partition
        self.renderer: Renderer = renderer or self._bound_default_renderer
        self.producer_runner: ProducerRunner = (
            producer_runner or self._run_codex_producer
        )
        self.review_runner: ReviewRunner = review_runner or self._run_codex_reviewer
        self._clock = clock or (lambda: datetime.now(UTC))
        self._recover_pending_transaction()
        self._recover_orphan_claims()

    def _now(self) -> datetime:
        return _utc(self._clock())

    def _bound_default_renderer(
        self,
        repo_root: str | Path,
        ledger: SemanticLedger,
        *,
        graph: nx.DiGraph | None = None,
    ) -> Mapping[str, object]:
        """Render docs; look up L2 partition on the real repo, not the staging root."""

        from src.semantic.render import (
            discover_names_path,
            discover_partition_path,
            render_semantic_docs,
        )

        partition = discover_partition_path(self.repo_root)
        names = discover_names_path(self.repo_root, partition)
        return render_semantic_docs(
            repo_root,
            ledger,
            graph=graph,
            partition_path=partition,
            names_path=names,
            consume_partition=self.consume_partition,
        )

    def _safe_repo_artifact(
        self,
        relative: Path,
        *,
        create_parent: bool,
    ) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise SemanticServiceError("artifact path must stay inside the repository")
        current = self.repo_root
        for part in relative.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise SemanticServiceError(
                    f"artifact parent must not be a symlink: {current}"
                )
            if current.exists() and not current.is_dir():
                raise SemanticServiceError(
                    f"artifact parent must be a directory: {current}"
                )
            if create_parent and not current.exists():
                current.mkdir(exist_ok=True)
                if current.is_symlink() or not current.is_dir():
                    raise SemanticServiceError(
                        f"artifact parent became unsafe while creating it: {current}"
                    )
        target = self.repo_root / relative
        if target.is_symlink():
            raise SemanticServiceError(f"artifact must not be a symlink: {target}")
        return target

    def _safe_write_json(self, relative: Path, payload: object) -> Path:
        target = self._safe_repo_artifact(relative, create_parent=True)
        _atomic_write_json(target, payload)
        return target

    def _safe_read_json_object(self, relative: Path) -> dict[str, Any]:
        target = self._safe_repo_artifact(relative, create_parent=False)
        return self._read_json_object(target)

    def _safe_read_bytes(self, relative: Path) -> bytes:
        target = self._safe_repo_artifact(relative, create_parent=False)
        try:
            return target.read_bytes()
        except OSError as exc:
            raise SemanticServiceError(f"cannot read semantic artifact: {target}") from exc

    def _artifact_exists(self, relative: Path) -> bool:
        target = self._safe_repo_artifact(relative, create_parent=False)
        return target.is_file()

    def _assert_not_consumed(
        self,
        *,
        relative: Path,
        identity_field: str,
        identity: str,
        error_type: type[SemanticServiceError],
        message: str,
    ) -> None:
        target = self._safe_repo_artifact(relative, create_parent=False)
        if not target.exists():
            return
        marker = self._read_json_object(target)
        if marker.get(identity_field) == identity:
            raise error_type(message)

    def _inventory(self) -> SemanticInventory:
        inventory = enumerate_semantic_inventory(
            self.repo_root,
            ir_symbols=self.ir_symbols,
        )
        if not self.module_by_file:
            return inventory
        symbols = {
            symbol_id: record.model_copy(
                update={"module_id": self.module_by_file.get(record.path)}
            )
            for symbol_id, record in inventory.symbols.items()
        }
        return SemanticInventory(
            repo_root=inventory.repo_root,
            source_revision=inventory.source_revision,
            files=inventory.files,
            symbols=symbols,
            diagnostics=inventory.diagnostics,
            file_revisions=inventory.file_revisions,
            file_out_edge_revisions=inventory.file_out_edge_revisions,
        )

    def _scheduler_snapshot(self) -> SemanticScheduler:
        ledger = self.store.reopen()
        inventory = self._inventory()
        if inventory.source_revision != ledger.source_revision:
            raise SemanticServiceError("source changed; reconcile semantic state first")
        return SemanticScheduler(
            inventory,
            ledger,
            relations=self.relations,
            store=self.store,
        )

    def _with_module_projection(self, ledger: SemanticLedger) -> SemanticLedger:
        if not self.module_by_file:
            return ledger
        symbols = {
            symbol_id: record.model_copy(
                update={"module_id": self.module_by_file.get(record.path)}
            )
            for symbol_id, record in ledger.symbols.items()
        }
        return revalidate_semantic_ledger(ledger.model_copy(update={"symbols": symbols}))

    def bootstrap_semantic(
        self,
        *,
        ir_symbols: Iterable[Symbol] | None = None,
    ) -> SemanticLedger:
        """Create or reconcile the ledger and render the initial document tree."""

        if ir_symbols is not None and tuple(ir_symbols) != self.ir_symbols:
            raise ValueError("IR symbols are fixed when SemanticService is constructed")
        expected = self.store.reopen() if self.store.path.exists() else None
        inventory = self._inventory()
        candidate = reconcile_semantic_ledger(inventory, expected)
        candidate = self._with_module_projection(candidate)
        persist_file_out_edge_revisions(inventory.repo_root, inventory.file_out_edge_revisions)
        scheduler = SemanticScheduler(
            inventory,
            candidate,
            relations=self.relations,
        )
        candidate = scheduler.ledger
        self._commit_projection(
            expected=expected,
            candidate=candidate,
            graph=scheduler.graph,
            allow_equivalent_bootstrap=True,
        )
        return candidate

    def reconcile_semantic(
        self,
        *,
        ir_symbols: Iterable[Symbol] | None = None,
    ) -> SemanticLedger:
        """Re-enumerate source truth, preserve valid facts, and refresh documents."""

        return self.bootstrap_semantic(ir_symbols=ir_symbols)

    def get_semantic_progress(self) -> dict[str, object]:
        """Return independently recomputed progress without mutating the repository."""

        ledger = self.store.reopen()
        inventory = self._inventory()
        if inventory.source_revision != ledger.source_revision:
            raise SemanticServiceError("source changed; reconcile semantic state first")
        projection = derive_static_coverage(inventory, ledger)
        return {
            "repo_root": ledger.repo_root,
            "source_revision": ledger.source_revision,
            "totals": projection.totals.model_dump(mode="json"),
            "coverage_percent": projection.coverage_percent,
            "uncovered_symbols": list(projection.uncovered_symbols),
            "stale_symbols": list(projection.stale_symbol_ids),
            "residuals": [item.model_dump(mode="json") for item in ledger.residuals],
            "review_verdict_present": self._current_review_verdict_exists(ledger),
            "render_pending": (
                self._artifact_exists(TRANSACTION_JOURNAL_RELPATH)
                or not self._docs_match_canonical_projection(ledger)
            ),
        }

    def render_semantic_docs(self) -> Mapping[str, object]:
        """Repair readable docs from current canonical state without changing it."""

        scheduler = self._scheduler_snapshot()
        self._commit_projection(
            expected=self.store.reopen(),
            candidate=scheduler.ledger,
            graph=scheduler.graph,
        )
        docs = self.repo_root / ".codebase-docs"
        detail_paths = [path.as_posix() for path in sorted(docs.rglob("DETAIL.md"))]
        return {
            "index_path": (docs / "INDEX.md").as_posix(),
            "detail_paths": detail_paths,
            "module_count": len(detail_paths),
            "fresh_symbol_count": scheduler.ledger.totals.explained,
            "stale_symbol_count": scheduler.ledger.totals.stale,
            "uncovered_symbol_count": scheduler.ledger.totals.uncovered,
        }

    def claim_semantic_batch(
        self,
        *,
        actor: str,
        max_context_tokens: int,
        lease_seconds: int = 900,
    ) -> SemanticBatchPacket | None:
        """Claim one dependency-ready batch under an exclusive persistent lease."""

        scheduler = self._scheduler_snapshot()
        with self.store._locked():
            current = self.store._read_unlocked()
            if current.source_revision != scheduler.ledger.source_revision:
                raise SemanticServiceError(
                    "semantic state changed before batch claim"
                )
            scheduler._store = None
            packet = scheduler.claim_semantic_batch(
                lease_owner=actor,
                max_context_tokens=max_context_tokens,
                lease_seconds=lease_seconds,
                now=self._now(),
            )
            if packet is not None:
                try:
                    target = self._safe_repo_artifact(
                        SEMANTIC_EVENTS_RELPATH,
                        create_parent=True,
                    )
                    self._append_event_unlocked(
                        target,
                        self._event_row(
                            "claim",
                            batch_id=packet.batch_id,
                            lease_owner=packet.lease_owner,
                            source_revision=packet.source_revision,
                            symbol_ids=[item.symbol_id for item in packet.symbols],
                        ),
                    )
                except BaseException:
                    scheduler.release_batch(
                        packet.batch_id,
                        lease_owner=packet.lease_owner,
                    )
                    raise
        return packet

    def recover_semantic_batch(self, batch_id: str) -> SemanticBatchPacket | None:
        """Recover the exact unexpired claim packet after process reset."""

        scheduler = self._scheduler_snapshot()
        packet = scheduler.recover_batch(batch_id, now=self._now())
        self._append_event(
            "batch_recovery",
            batch_id=batch_id,
            recovered=packet is not None,
        )
        return packet

    @staticmethod
    def _thread_identity_from_events(
        events: object,
        *,
        error_type: type[SemanticServiceError],
        forbid_tools: bool,
    ) -> str:
        if not isinstance(events, (list, tuple)) or not events:
            raise error_type("Codex events must be a non-empty JSON event array")
        seen: set[int] = set()

        def validate_json(value: object, depth: int = 0) -> None:
            if depth > 64:
                raise error_type("Codex events exceed the maximum JSON nesting depth")
            if value is None or isinstance(value, (str, int, float, bool)):
                return
            if not isinstance(value, (dict, list)):
                raise error_type("Codex events must contain only JSON-compatible values")
            identity = id(value)
            if identity in seen:
                raise error_type("Codex events must not contain recursive containers")
            seen.add(identity)
            if isinstance(value, dict):
                if any(not isinstance(key, str) for key in value):
                    raise error_type("Codex event object keys must be strings")
                event_type = value.get("type")
                if forbid_tools and event_type in _FORBIDDEN_REVIEW_EVENT_TYPES:
                    raise error_type(f"reviewer used forbidden tool event: {event_type}")
                for item in value.values():
                    validate_json(item, depth + 1)
            else:
                for item in value:
                    validate_json(item, depth + 1)
            seen.remove(identity)

        for event in events:
            if not isinstance(event, dict):
                raise error_type("each Codex event must be a JSON object")
            validate_json(event)
        started = [event for event in events if event.get("type") == "thread.started"]
        if len(started) != 1:
            raise error_type("Codex events must contain exactly one thread.started event")
        thread_id = started[0].get("thread_id")
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise error_type("thread.started must contain a non-empty thread_id")
        return thread_id.strip()

    def submit_semantic_batch(
        self,
        *,
        batch_id: str,
        actor: str,
        source_revision: str,
        explanations: Mapping[str, str],
        residuals: Mapping[str, str] | None = None,
    ) -> SemanticLedger:
        """Validate and atomically accept every item in one leased batch."""

        reservation = self._reserve_submission_dispatch(batch_id)
        try:
            return self._submit_reserved_semantic_batch(
                batch_id=batch_id,
                actor=actor,
                source_revision=source_revision,
                explanations=explanations,
                residuals=residuals,
            )
        finally:
            self._release_submission_dispatch(batch_id, reservation)

    def _submit_reserved_semantic_batch(
        self,
        *,
        batch_id: str,
        actor: str,
        source_revision: str,
        explanations: Mapping[str, str],
        residuals: Mapping[str, str] | None,
    ) -> SemanticLedger:
        """Run one producer and commit while its server-side reservation is held."""

        submission_receipt_path = self._submission_receipt_path(batch_id)
        self._assert_not_consumed(
            relative=submission_receipt_path,
            identity_field="batch_id",
            identity=batch_id,
            error_type=SemanticSubmissionError,
            message="semantic batch has already been submitted",
        )
        expected = self.store.reopen()
        inventory = self._inventory()
        persist_file_out_edge_revisions(inventory.repo_root, inventory.file_out_edge_revisions)
        if inventory.source_revision != expected.source_revision:
            raise SemanticSubmissionError("source changed after the batch claim")
        scheduler = SemanticScheduler(
            inventory,
            expected,
            relations=self.relations,
            store=self.store,
        )
        packet = scheduler.recover_batch(batch_id, now=self._now())
        if packet is None:
            raise SemanticSubmissionError("batch lease is missing or expired")
        if not isinstance(actor, str) or actor.strip() != packet.lease_owner:
            raise SemanticSubmissionError("semantic batch lease owner mismatch")
        producer_packet = self._producer_packet(
            packet,
            explanations=explanations,
            residuals=residuals or {},
        )
        runner_result = self.producer_runner(producer_packet)
        if not isinstance(runner_result, tuple) or len(runner_result) != 2:
            raise SemanticSubmissionError(
                "producer runner must return (events, submission)"
            )
        producer_events, produced = runner_result
        producer_thread_id = _codex_identity(
            self._thread_identity_from_events(
                producer_events,
                error_type=SemanticSubmissionError,
                forbid_tools=True,
            )
        )
        produced_explanations, produced_residuals = self._producer_output(produced)
        produced_explanations, produced_residuals = self._apply_l1_postchecks(
            packet,
            produced_explanations,
            produced_residuals,
        )
        live_packet = scheduler.recover_batch(batch_id, now=self._now())
        if live_packet != packet:
            raise SemanticSubmissionError(
                "batch lease expired or changed while the Codex producer was running"
            )
        explanation_texts, residual_reasons = self._validate_submission(
            packet=packet,
            expected=expected,
            inventory=inventory,
            source_revision=source_revision,
            explanations=produced_explanations,
            residuals=produced_residuals,
        )

        overrides: dict[str, SemanticExplanation | None] = {}
        packet_by_id = {item.symbol_id: item for item in packet.symbols}
        created_at = self._now()
        for symbol_id, text in explanation_texts.items():
            packet_symbol = packet_by_id[symbol_id]
            citations = tuple(
                callee
                for callee in packet_symbol.callee_ids
                if expected.symbols[callee].is_fresh
            )
            overrides[symbol_id] = SemanticExplanation(
                text=text,
                explained_content_hash=packet_symbol.content_hash,
                cited_symbol_ids=citations,
                producer=producer_thread_id,
                created_at=created_at,
            )
        overrides.update({symbol_id: None for symbol_id in residual_reasons})
        appended_order = tuple(
            item.symbol_id
            for item in packet.symbols
            if item.symbol_id in explanation_texts
        )
        candidate = reconcile_semantic_ledger(
            inventory,
            scheduler.ledger,
            explanation_overrides=overrides,
            order_override=tuple(dict.fromkeys((*expected.order, *appended_order))),
        )
        candidate = self._with_module_projection(candidate)
        candidate = self._apply_residual_reasons(candidate, residual_reasons)
        projected = SemanticScheduler(
            inventory,
            candidate,
            relations=self.relations,
        )
        candidate = projected.ledger
        event_row = self._event_row(
            "submit",
            batch_id=batch_id,
            producer_session_id=producer_thread_id,
            source_revision=candidate.source_revision,
            symbol_ids=list(appended_order),
        )
        submission_receipt = {
            "batch_id": batch_id,
            "source_revision": candidate.source_revision,
            "ledger_fingerprint": self._ledger_fingerprint(candidate),
            "producer_session_id": producer_thread_id,
            "explanation_symbol_ids": sorted(explanation_texts),
            "residual_symbol_ids": sorted(residual_reasons),
        }
        self._commit_projection(
            expected=expected,
            candidate=candidate,
            graph=projected.graph,
            artifact_payloads={submission_receipt_path: submission_receipt},
            event_row=event_row,
            consume_once=(
                submission_receipt_path,
                "batch_id",
                batch_id,
                SemanticSubmissionError,
                "semantic batch has already been submitted",
            ),
            lease_guard=(scheduler, packet),
        )
        # Lease cleanup follows the durable acceptance boundary.  A stale lease
        # is harmless because the receipt makes retries fail deterministically;
        # cleanup failure must not report that an already committed submit failed.
        try:
            scheduler.release_batch(batch_id, lease_owner=packet.lease_owner)
        except Exception:
            pass
        return candidate

    def get_semantic_submission_result(self, batch_id: str) -> dict[str, list[str]]:
        """Read the durable server-owned classification for one accepted batch."""

        receipt = self._safe_read_json_object(self._submission_receipt_path(batch_id))
        if receipt.get("batch_id") != batch_id:
            raise SemanticSubmissionError("semantic submission receipt is mismatched")
        result: dict[str, list[str]] = {}
        for field in ("explanation_symbol_ids", "residual_symbol_ids"):
            values = receipt.get(field)
            if not isinstance(values, list) or any(
                not isinstance(value, str) for value in values
            ):
                raise SemanticSubmissionError(
                    "semantic submission receipt classification is invalid"
                )
            result[field] = values
        return result

    def _producer_packet(
        self,
        packet: SemanticBatchPacket,
        *,
        explanations: Mapping[str, str],
        residuals: Mapping[str, str],
    ) -> dict[str, object]:
        """Host envelope + 闸 1 过的模型 stdin。

        `symbols` 仍带 draft_*，只给测试夹具和宿主回放用，**不进模型 stdin**。
        模型只看见 `l1_symbols`（九字段封闭 allowlist）。
        """

        return {
            "batch_id": packet.batch_id,
            "source_revision": packet.source_revision,
            "l1_symbols": self._l1_rows_from_batch(packet),
            "symbols": [
                {
                    "symbol_id": symbol.symbol_id,
                    "path": symbol.path,
                    "kind": symbol.kind,
                    "span": list(symbol.span),
                    "source": symbol.source_body,
                    "callee_explanations": [list(item) for item in symbol.callee_explanations],
                    "cycle_peer_ids": list(symbol.cycle_peer_ids),
                    "draft_explanation": explanations.get(symbol.symbol_id),
                    "draft_residual": residuals.get(symbol.symbol_id),
                }
                for symbol in packet.symbols
            ],
        }

    def _l1_rows_from_batch(self, packet: SemanticBatchPacket) -> list[dict[str, object]]:
        """闸 1：序列化字段集恰等九字段，不等即拒绝派发。"""

        rows: list[L1PacketSymbol] = []
        for symbol in packet.symbols:
            diagnostics = tuple(
                item
                for item in getattr(self, "_inventory_diagnostics", ())
                if symbol.path in item
            )
            signatures = tuple(
                (callee, self._callee_signature(callee)) for callee in symbol.callee_ids
            )
            body = symbol.source_body if symbol.source_body else "# empty"
            rows.append(
                L1PacketSymbol(
                    symbol_id=symbol.symbol_id,
                    path=symbol.path,
                    kind=kind_from_record(symbol.kind),
                    span=symbol.span,
                    source_body=body,
                    content_hash=symbol.content_hash,
                    callee_signatures=signatures,
                    language="python",
                    syntax_diagnostics=diagnostics,
                )
            )
        return build_packet_payload(rows)

    def _callee_signature(self, callee_id: str) -> str:
        try:
            ledger = self.store.reopen()
        except Exception:
            return f"{callee_id.split('::')[-1]}(...)"
        record = ledger.symbols.get(callee_id)
        if record is None:
            return f"{callee_id.split('::')[-1]}(...)"
        try:
            body = self._source_body(record.path, record.span)
        except Exception:
            return f"{record.qualified_name}(...)"
        return signature_line(body, fallback=f"{record.qualified_name}(...)")

    def _apply_l1_postchecks(
        self,
        packet: SemanticBatchPacket,
        explanations: Mapping[str, str],
        residuals: Mapping[str, str],
    ) -> tuple[dict[str, str], dict[str, str]]:
        """submit 时跑 L1-a..d。只对 L1 fact JSON 生效；legacy 自由文本原样通过。

        检查失败 = 拒收该符号的解释（不静默入库）。legacy 路径不能拒，
        否则白名单外的 `test_semantic_service.py` 会整表红。
        """

        accepted = dict(explanations)
        rejected = dict(residuals)
        packet_by_id = {item.symbol_id: item for item in packet.symbols}
        for symbol_id, text in list(accepted.items()):
            fact = try_parse_l1_fact_text(text)
            if fact is None:
                continue
            host = packet_by_id[symbol_id]
            results = run_l1_checks(
                fact,
                source_body=host.source_body,
                qualified_name=host.symbol_id.split("::", 1)[-1],
                callee_signatures=tuple(
                    (callee, self._callee_signature(callee)) for callee in host.callee_ids
                ),
                tier="T1",
            )
            failed = failed_checks(results)
            if failed:
                raise SemanticSubmissionError(
                    f"L1 post-check rejected {symbol_id}: {list(failed)}"
                )
            accepted[symbol_id] = fact.behavior
        return accepted, rejected

    @staticmethod
    def _producer_output(
        output: Mapping[str, object],
    ) -> tuple[dict[str, str], dict[str, str]]:
        if not isinstance(output, Mapping) or set(output) != {"explanations", "residuals"}:
            raise SemanticSubmissionError(
                "producer output must contain only explanations and residuals"
            )
        maps: list[dict[str, str]] = []
        for key, value_key in (("explanations", "text"), ("residuals", "reason")):
            rows = output[key]
            if not isinstance(rows, list):
                raise SemanticSubmissionError(f"producer {key} must be an array")
            mapped: dict[str, str] = {}
            for row in rows:
                if not isinstance(row, dict) or set(row) != {"symbol_id", value_key}:
                    raise SemanticSubmissionError(f"producer {key} row has invalid shape")
                symbol_id = row["symbol_id"]
                value = row[value_key]
                if not isinstance(symbol_id, str) or not isinstance(value, str) or symbol_id in mapped:
                    raise SemanticSubmissionError(f"producer {key} row is invalid or duplicated")
                mapped[symbol_id] = value
            maps.append(mapped)
        return maps[0], maps[1]

    @staticmethod
    def _run_codex_producer(
        packet: Mapping[str, object],
    ) -> tuple[object, Mapping[str, object]]:
        """Run the semantic author in a server-owned, tool-free Codex session."""

        row_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["symbol_id", "value"],
            "properties": {
                "symbol_id": {"type": "string", "minLength": 1},
                "value": {"type": "string", "minLength": 1},
            },
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["explanations", "residuals"],
            "properties": {
                "explanations": {
                    "type": "array",
                    "items": {
                        **row_schema,
                        "required": ["symbol_id", "text"],
                        "properties": {
                            "symbol_id": {"type": "string", "minLength": 1},
                            "text": {"type": "string", "minLength": 25},
                        },
                    },
                },
                "residuals": {
                    "type": "array",
                    "items": {
                        **row_schema,
                        "required": ["symbol_id", "reason"],
                        "properties": {
                            "symbol_id": {"type": "string", "minLength": 1},
                            "reason": {"type": "string", "minLength": 1},
                        },
                    },
                },
            },
        }
        prompt = (
            "你是函数级语义解释生产者。stdin.symbols 每项恰好九个字段："
            "symbol_id, path, kind, span, source_body, content_hash, callee_signatures, "
            "language, syntax_diagnostics。"
            "逐符号只依据该符号源码与 callee 签名作答：这段代码做什么、输入输出与副作用、"
            "失败条件、直接用到了哪些标识符。作答范围到此为止。"
            "凡是读完这段源码仍看不出来的，写进 residual reason 或在 text 里如实说不知道，不要推测。"
            "每个符号恰好进入 explanations 或 residuals；"
            "residual reason 必须为允许的 CODE: 具体证据。不得调用任何工具。"
        )
        # 闸 2（提问闸）：派发前扫提问面。它挡的不是措辞，是「问一个输入面答不了的问题」
        # 这个动作本身——上面这段 prompt 在本轮之前逐字要求「系统角色」，而 packet 里
        # 没有任何字段能支撑它，模型只能编。放在这里而不是靠人记得，是因为措辞会被改回去。
        assert_prompt_dispatchable(prompt, subject="semantic producer prompt")
        model_stdin = {"symbols": packet.get("l1_symbols") or []}
        if not model_stdin["symbols"] and isinstance(packet.get("symbols"), list):
            # 没有 l1_symbols 时拒绝把旧信封交给模型——那是幻觉生产线。
            raise SemanticSubmissionError("L1 producer stdin missing gated l1_symbols")
        with tempfile.TemporaryDirectory(prefix="cbe-semantic-producer-") as temporary:
            root = Path(temporary)
            schema_path = root / "producer.schema.json"
            output_path = root / "submission.json"
            _atomic_write_json(schema_path, schema)
            try:
                completed = subprocess.run(
                    [
                        "codex",
                        "exec",
                        "--ignore-user-config",
                        "--ignore-rules",
                        "--ephemeral",
                        "--json",
                        "--sandbox",
                        "read-only",
                        "--skip-git-repo-check",
                        "-C",
                        root.as_posix(),
                        "--output-schema",
                        schema_path.as_posix(),
                        "--output-last-message",
                        output_path.as_posix(),
                        prompt,
                    ],
                    input=_json_bytes(model_stdin),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=600,
                )
            except subprocess.TimeoutExpired as exc:
                raise SemanticSubmissionError("Codex producer exceeded 600 seconds") from exc
            if completed.returncode != 0:
                detail = completed.stderr.decode("utf-8", errors="replace")[-500:]
                raise SemanticSubmissionError(
                    f"Codex producer exited {completed.returncode}: {detail}"
                )
            try:
                events = [
                    json.loads(line)
                    for line in completed.stdout.splitlines()
                    if line.strip()
                ]
                output = json.loads(output_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SemanticSubmissionError(
                    f"Codex producer emitted invalid JSON artifacts: {exc}"
                ) from exc
            if not isinstance(output, dict):
                raise SemanticSubmissionError("Codex producer output must be an object")
            return events, output

    @staticmethod
    def _submission_receipt_path(batch_id: str) -> Path:
        digest = hashlib.sha256(batch_id.encode("utf-8")).hexdigest()
        return SEMANTIC_SUBMISSION_RECEIPTS_RELDIR / f"{digest}.accepted.json"

    @staticmethod
    def _submission_dispatch_path(batch_id: str) -> Path:
        digest = hashlib.sha256(batch_id.encode("utf-8")).hexdigest()
        return SEMANTIC_SUBMISSION_DISPATCH_RELDIR / f"{digest}.json"

    @staticmethod
    def _process_is_alive(pid: object) -> bool:
        if type(pid) is not int or pid < 1:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _reserve_submission_dispatch(self, batch_id: str) -> str:
        if not isinstance(batch_id, str) or not batch_id.strip():
            raise SemanticSubmissionError("batch_id must be non-empty")
        token = uuid.uuid4().hex
        with self.store._locked():
            self._assert_not_consumed(
                relative=self._submission_receipt_path(batch_id),
                identity_field="batch_id",
                identity=batch_id,
                error_type=SemanticSubmissionError,
                message="semantic batch has already been submitted",
            )
            target = self._safe_repo_artifact(
                self._submission_dispatch_path(batch_id),
                create_parent=True,
            )
            if target.exists():
                reservation = self._read_json_object(target)
                if self._process_is_alive(reservation.get("pid")):
                    raise SemanticSubmissionError(
                        "semantic batch submission is already in progress"
                    )
            _atomic_write_json(
                target,
                {"batch_id": batch_id, "pid": os.getpid(), "token": token},
            )
        return token

    def _release_submission_dispatch(self, batch_id: str, token: str) -> None:
        with self.store._locked():
            target = self._safe_repo_artifact(
                self._submission_dispatch_path(batch_id),
                create_parent=False,
            )
            if not target.exists():
                return
            reservation = self._read_json_object(target)
            if (
                reservation.get("batch_id") == batch_id
                and reservation.get("token") == token
            ):
                target.unlink()

    def _validate_submission(
        self,
        *,
        packet: SemanticBatchPacket,
        expected: SemanticLedger,
        inventory: SemanticInventory,
        source_revision: str,
        explanations: Mapping[str, str],
        residuals: Mapping[str, str],
    ) -> tuple[dict[str, str], dict[str, str]]:
        if source_revision != packet.source_revision:
            raise SemanticSubmissionError("submitted source revision does not match the claim")
        if expected.source_revision != packet.source_revision:
            raise SemanticSubmissionError("ledger source revision changed after the claim")
        if inventory.source_revision != packet.source_revision:
            raise SemanticSubmissionError("source changed after the batch claim")
        if not isinstance(explanations, Mapping) or not isinstance(residuals, Mapping):
            raise SemanticSubmissionError("explanations and residuals must be objects")

        packet_ids = {item.symbol_id for item in packet.symbols}
        explanation_ids = set(explanations)
        residual_ids = set(residuals)
        if explanation_ids & residual_ids:
            raise SemanticSubmissionError("a batch symbol cannot be explained and residual")
        if explanation_ids | residual_ids != packet_ids:
            missing = sorted(packet_ids - explanation_ids - residual_ids)
            extra = sorted((explanation_ids | residual_ids) - packet_ids)
            raise SemanticSubmissionError(
                f"submit must account for the entire batch: missing={missing} extra={extra}"
            )

        packet_by_id = {item.symbol_id: item for item in packet.symbols}
        for symbol_id, packet_symbol in packet_by_id.items():
            truth = inventory.symbols.get(symbol_id)
            if truth is None:
                raise SemanticSubmissionError(f"claimed symbol disappeared: {symbol_id}")
            if (
                truth.path != packet_symbol.path
                or truth.span != packet_symbol.span
                or truth.content_hash != packet_symbol.content_hash
            ):
                raise SemanticSubmissionError(
                    f"claimed source span/hash no longer matches: {symbol_id}"
                )

        normalized: dict[str, str] = {}
        seen_text: set[str] = set()
        for symbol_id, raw in explanations.items():
            if not isinstance(raw, str) or not raw.strip():
                raise SemanticSubmissionError(f"explanation must be non-empty: {symbol_id}")
            text = raw.strip()
            duplicate_key = " ".join(text.casefold().split())
            if duplicate_key in seen_text:
                raise SemanticSubmissionError("batch contains duplicate explanation text")
            seen_text.add(duplicate_key)
            try:
                SemanticExplanation(
                    text=text,
                    explained_content_hash=packet_by_id[symbol_id].content_hash,
                    producer=packet.lease_owner,
                    created_at=self._now(),
                )
            except ValueError as exc:
                raise SemanticSubmissionError(
                    f"invalid explanation for {symbol_id}: {exc}"
                ) from exc
            normalized[symbol_id] = text

        checked_residuals: dict[str, str] = {}
        for symbol_id, raw in residuals.items():
            if not isinstance(raw, str) or not raw.strip():
                raise SemanticSubmissionError(f"residual reason must be non-empty: {symbol_id}")
            reason = raw.strip()
            code, separator, detail = reason.partition(":")
            if not separator or code not in _ALLOWED_RESIDUAL_CODES or not detail.strip():
                raise SemanticSubmissionError(
                    "residual reason must be '<allowed code>: <specific evidence>'"
                )
            checked_residuals[symbol_id] = reason
        return normalized, checked_residuals

    @staticmethod
    def _apply_residual_reasons(
        ledger: SemanticLedger,
        residual_reasons: Mapping[str, str],
    ) -> SemanticLedger:
        if not residual_reasons:
            return ledger
        prior = {item.symbol_id: item.reason for item in ledger.residuals}
        prior.update(residual_reasons)
        residuals = tuple(
            SemanticResidual(symbol_id=symbol_id, reason=prior[symbol_id])
            for symbol_id in ledger.uncovered_symbols
        )
        return revalidate_semantic_ledger(ledger.model_copy(update={"residuals": residuals}))

    def get_semantic_review_batch(self) -> dict[str, object]:
        """Persist and return a deterministic blind sample of fresh callables."""

        ledger = self.store.reopen()
        inventory = self._inventory()
        if inventory.source_revision != ledger.source_revision:
            raise SemanticReviewError("source changed; reconcile before creating review packet")
        candidates = self._review_candidates(ledger)
        if not candidates:
            raise SemanticReviewError("no fresh Python callable is available for review")
        fingerprint = self._ledger_fingerprint(ledger)
        selected = self._stratified_sample(candidates, fingerprint=fingerprint)

        samples: list[dict[str, str]] = []
        hidden: dict[str, dict[str, str]] = {}
        for index, candidate in enumerate(selected, start=1):
            sample = f"S{index:02d}"
            samples.append(
                {
                    "sample": sample,
                    "source": candidate["source"],
                    "explanation": candidate["explanation"],
                }
            )
            hidden[sample] = {
                "symbol_id": candidate["symbol_id"],
                "producer_session_id": candidate["producer"],
            }
        packet: dict[str, object] = {"samples": samples}
        packet_hash = _sha256_bytes(_json_bytes(packet))
        hidden_hash = _sha256_bytes(_json_bytes(hidden))
        batch_id = _sha256_bytes(
            (
                f"{_REVIEW_SEED}\0{fingerprint}\0{packet_hash}\0{hidden_hash}"
            ).encode("utf-8")
        )
        receipt = {
            "review_batch_id": batch_id,
            "ledger_fingerprint": fingerprint,
            "packet_sha256": packet_hash,
            "hidden_map_sha256": hidden_hash,
        }
        self._commit_projection(
            expected=ledger,
            candidate=ledger,
            graph=None,
            artifact_payloads={
                REVIEW_PACKET_RELPATH: packet,
                REVIEW_HIDDEN_MAP_RELPATH: hidden,
                REVIEW_BATCH_RECEIPT_RELPATH: receipt,
            },
            rewrite_projection=False,
            event_row=self._event_row(
                "review_batch",
                review_batch_id=batch_id,
                ledger_fingerprint=fingerprint,
            ),
        )
        return {"review_batch_id": batch_id, "samples": samples}

    def _review_candidates(self, ledger: SemanticLedger) -> list[dict[str, str]]:
        candidates: list[dict[str, str]] = []
        for symbol_id, symbol in ledger.symbols.items():
            if (
                symbol.kind is SemanticSymbolKind.CLASS
                or not symbol.is_fresh
                or symbol.explanation is None
            ):
                continue
            source = self._source_body(symbol.path, symbol.span)
            candidates.append(
                {
                    "symbol_id": symbol_id,
                    "path": symbol.path,
                    "source": source,
                    "explanation": symbol.explanation.text,
                    "producer": symbol.explanation.producer,
                    "stratum": "\0".join(
                        (
                            symbol.module_id or "unclassified",
                            self._callable_type(ledger, symbol_id),
                            self._complexity_band(source),
                        )
                    ),
                }
            )
        return candidates

    def _source_body(self, relative_path: str, span: tuple[int, int]) -> str:
        try:
            lines = (self.repo_root / relative_path).read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError as exc:
            raise SemanticReviewError(f"cannot read review source {relative_path}: {exc}") from exc
        start, end = span
        if not (1 <= start <= end <= len(lines)):
            raise SemanticReviewError(f"review source span is invalid: {relative_path}:{span}")
        return "\n".join(lines[start - 1 : end])

    @staticmethod
    def _callable_type(ledger: SemanticLedger, symbol_id: str) -> str:
        symbol = ledger.symbols[symbol_id]
        if symbol.kind is SemanticSymbolKind.FUNCTION:
            return "module_function"
        path, qualified = symbol_id.split("::", 1)
        parent_name = qualified.rpartition(".")[0]
        parent = ledger.symbols.get(f"{path}::{parent_name}")
        return "method" if parent is not None and parent.kind is SemanticSymbolKind.CLASS else "nested_function"

    @staticmethod
    def _complexity_band(source: str) -> str:
        try:
            count = sum(1 for _ in ast.walk(ast.parse(textwrap.dedent(source))))
        except SyntaxError:
            count = 61
        if count <= 20:
            return "le20"
        if count <= 60:
            return "21to60"
        return "gt60"

    @staticmethod
    def _ledger_fingerprint(ledger: SemanticLedger) -> str:
        encoded = json.dumps(
            ledger.model_dump(mode="json", round_trip=True, warnings="error"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _stable_review_key(fingerprint: str, symbol_id: str) -> str:
        framed = f"{_REVIEW_SEED}\0{fingerprint}\0{symbol_id}".encode("utf-8")
        return hashlib.sha256(framed).hexdigest()

    def _stratified_sample(
        self,
        candidates: list[dict[str, str]],
        *,
        fingerprint: str,
    ) -> list[dict[str, str]]:
        strata: dict[str, list[dict[str, str]]] = defaultdict(list)
        for candidate in candidates:
            strata[candidate["stratum"]].append(candidate)
        for items in strata.values():
            items.sort(
                key=lambda item: self._stable_review_key(
                    fingerprint,
                    item["symbol_id"],
                )
            )

        selected: list[dict[str, str]] = []
        selected_by_stratum: dict[str, int] = defaultdict(int)
        selected_paths: set[str] = set()
        limit = min(10, len(candidates))
        while len(selected) < limit:
            available = [key for key, items in strata.items() if items]
            minimum = min(selected_by_stratum[key] for key in available)
            stratum = min(
                key for key in available if selected_by_stratum[key] == minimum
            )
            items = strata[stratum]
            index = next(
                (i for i, item in enumerate(items) if item["path"] not in selected_paths),
                0,
            )
            candidate = items.pop(index)
            selected.append(candidate)
            selected_paths.add(candidate["path"])
            selected_by_stratum[stratum] += 1
        return selected

    def _reserve_review_dispatch(self, review_batch_id: str) -> None:
        """Acquire a server-owned lease before invoking an external reviewer."""

        if not isinstance(review_batch_id, str) or not review_batch_id.strip():
            raise SemanticReviewError("review_batch_id must be non-empty")
        with self.store._locked():
            accepted = self._safe_repo_artifact(
                REVIEW_ACCEPTANCE_RECEIPT_RELPATH,
                create_parent=False,
            )
            if accepted.exists():
                prior = self._read_json_object(accepted)
                if prior.get("review_batch_id") == review_batch_id:
                    ledger = self.store._read_unlocked()
                    if self._current_review_verdict_exists(ledger):
                        raise SemanticReviewError(
                            "review batch has already been consumed"
                        )
                    # A docs/source projection change invalidates the old
                    # acceptance receipt. Permit a fresh independent review of
                    # the still-bound packet and replace all evidence atomically.
                    accepted.unlink()
            target = self._safe_repo_artifact(
                REVIEW_DISPATCH_RELPATH,
                create_parent=True,
            )
            now = self._now()
            if target.exists():
                reservation = self._read_json_object(target)
                if self._process_is_alive(reservation.get("pid")):
                    raise SemanticReviewError(
                        "review batch dispatch is already in progress"
                    )
            _atomic_write_json(
                target,
                {
                    "review_batch_id": review_batch_id,
                    "pid": os.getpid(),
                    "reserved_at": now.isoformat().replace("+00:00", "Z"),
                },
            )

    def _release_review_dispatch(self, review_batch_id: str) -> None:
        """Release only the matching dispatch reservation."""

        with self.store._locked():
            target = self._safe_repo_artifact(
                REVIEW_DISPATCH_RELPATH,
                create_parent=False,
            )
            if not target.exists():
                return
            reservation = self._read_json_object(target)
            if reservation.get("review_batch_id") == review_batch_id:
                target.unlink()

    def submit_semantic_review(
        self,
        *,
        review_batch_id: str,
    ) -> dict[str, object]:
        """Dispatch a blind Codex reviewer and consume its bound verdict."""

        self._reserve_review_dispatch(review_batch_id)
        try:
            return self._submit_reserved_semantic_review(review_batch_id)
        finally:
            self._release_review_dispatch(review_batch_id)

    def _submit_reserved_semantic_review(
        self,
        review_batch_id: str,
    ) -> dict[str, object]:
        """Run and commit one review while its server-side reservation is held."""

        if not isinstance(review_batch_id, str) or not review_batch_id.strip():
            raise SemanticReviewError("review_batch_id must be non-empty")
        packet = self._safe_read_json_object(REVIEW_PACKET_RELPATH)
        hidden = self._safe_read_json_object(REVIEW_HIDDEN_MAP_RELPATH)
        receipt = self._safe_read_json_object(REVIEW_BATCH_RECEIPT_RELPATH)
        self._assert_not_consumed(
            relative=REVIEW_ACCEPTANCE_RECEIPT_RELPATH,
            identity_field="review_batch_id",
            identity=review_batch_id,
            error_type=SemanticReviewError,
            message="review batch has already been consumed",
        )
        expected = self.store.reopen()
        self._validate_review_binding(
            review_batch_id=review_batch_id,
            packet=packet,
            hidden=hidden,
            receipt=receipt,
            ledger=expected,
        )
        self._validate_review_inputs(packet, hidden, expected)
        runner_result = self.review_runner(packet)
        if not isinstance(runner_result, tuple) or len(runner_result) != 2:
            raise SemanticReviewError("review runner must return (events, verdict)")
        reviewer_events, verdict = runner_result
        reviewer_thread_id = _codex_identity(
            self._thread_identity_from_events(
                reviewer_events,
                error_type=SemanticReviewError,
                forbid_tools=True,
            )
        )
        producers = {value["producer_session_id"] for value in hidden.values()}
        if reviewer_thread_id in producers:
            raise SemanticReviewError("reviewer thread must be different from every producer")
        decisions = self._validate_verdict(verdict, expected_samples=set(hidden))
        revision_samples = {
            sample
            for sample, sample_verdicts in decisions.items()
            if any(item["decision"] != "充分" for item in sample_verdicts.values())
        }
        revision_ids = sorted(hidden[sample]["symbol_id"] for sample in revision_samples)
        artifact = dict(verdict)
        artifact["reviewer_session_id"] = reviewer_thread_id.strip()
        event_evidence = b"".join(_json_bytes(event) for event in reviewer_events)

        candidate = expected
        graph: nx.DiGraph | None = None
        if revision_ids:
            inventory = self._inventory()
            if inventory.source_revision != expected.source_revision:
                raise SemanticReviewError("source changed before review writeback")
            scheduler = SemanticScheduler(
                inventory,
                expected,
                relations=self.relations,
            )
            candidate = reconcile_semantic_ledger(
                inventory,
                scheduler.ledger,
                explanation_overrides={symbol_id: None for symbol_id in revision_ids},
                order_override=expected.order,
            )
            candidate = self._with_module_projection(candidate)
            projected = SemanticScheduler(
                inventory,
                candidate,
                relations=self.relations,
            )
            candidate = projected.ledger
            graph = projected.graph
        if graph is None:
            graph = self._scheduler_snapshot().graph
        acceptance = {
            "review_batch_id": review_batch_id,
            "ledger_fingerprint": self._ledger_fingerprint(candidate),
            "verdict_sha256": _sha256_bytes(_json_bytes(artifact)),
            "events_sha256": _sha256_bytes(event_evidence),
            "docs_fingerprint": self._projected_docs_fingerprint(candidate, graph),
            "reviewer_session_id": reviewer_thread_id,
        }
        event_row = self._event_row(
            "review_submit",
            review_batch_id=review_batch_id,
            reviewer_session_id=reviewer_thread_id,
            revision_symbol_ids=revision_ids,
        )
        self._commit_projection(
            expected=expected,
            candidate=candidate,
            graph=graph,
            artifact_payloads={
                REVIEW_VERDICT_RELPATH: artifact,
                REVIEW_ACCEPTANCE_RECEIPT_RELPATH: acceptance,
                REVIEW_EVENTS_RELPATH: event_evidence,
            },
            rewrite_projection=True,
            event_row=event_row,
            consume_once=(
                REVIEW_ACCEPTANCE_RECEIPT_RELPATH,
                "review_batch_id",
                review_batch_id,
                SemanticReviewError,
                "review batch has already been consumed",
            ),
        )
        return {
            "reviewer_session_id": reviewer_thread_id.strip(),
            "revision_symbol_ids": revision_ids,
            "verdict_path": (self.repo_root / REVIEW_VERDICT_RELPATH).as_posix(),
        }

    def _validate_review_binding(
        self,
        *,
        review_batch_id: str,
        packet: Mapping[str, object],
        hidden: Mapping[str, object],
        receipt: Mapping[str, object],
        ledger: SemanticLedger,
    ) -> None:
        fingerprint = self._ledger_fingerprint(ledger)
        packet_hash = _sha256_bytes(_json_bytes(packet))
        hidden_hash = _sha256_bytes(_json_bytes(hidden))
        calculated = _sha256_bytes(
            (
                f"{_REVIEW_SEED}\0{fingerprint}\0{packet_hash}\0{hidden_hash}"
            ).encode("utf-8")
        )
        expected = {
            "review_batch_id": calculated,
            "ledger_fingerprint": fingerprint,
            "packet_sha256": packet_hash,
            "hidden_map_sha256": hidden_hash,
        }
        if dict(receipt) != expected or review_batch_id != calculated:
            raise SemanticReviewError(
                "review batch binding is stale, replayed, or artifact-mismatched"
            )

    def _current_review_verdict_exists(self, ledger: SemanticLedger) -> bool:
        if not self._artifact_exists(REVIEW_VERDICT_RELPATH):
            return False
        if not self._artifact_exists(REVIEW_ACCEPTANCE_RECEIPT_RELPATH):
            return False
        if not self._artifact_exists(REVIEW_EVENTS_RELPATH):
            return False
        verdict = self._safe_read_json_object(REVIEW_VERDICT_RELPATH)
        receipt = self._safe_read_json_object(REVIEW_ACCEPTANCE_RECEIPT_RELPATH)
        events = self._safe_read_bytes(REVIEW_EVENTS_RELPATH)
        return (
            isinstance(receipt.get("review_batch_id"), str)
            and receipt.get("ledger_fingerprint") == self._ledger_fingerprint(ledger)
            and receipt.get("verdict_sha256") == _sha256_bytes(_json_bytes(verdict))
            and receipt.get("events_sha256") == _sha256_bytes(events)
            and receipt.get("docs_fingerprint") == _docs_fingerprint(self.repo_root)
            and isinstance(receipt.get("reviewer_session_id"), str)
            and receipt.get("reviewer_session_id") == verdict.get("reviewer_session_id")
        )

    def _projected_docs_fingerprint(
        self,
        ledger: SemanticLedger,
        graph: nx.DiGraph | None,
    ) -> str:
        """Render into an isolated root and hash the exact canonical doc tree."""

        with tempfile.TemporaryDirectory(
            prefix="cbe-semantic-doc-fingerprint-",
            dir=self.repo_root.parent,
        ) as temporary:
            root = Path(temporary) / self.repo_root.name
            root.mkdir()
            projected = revalidate_semantic_ledger(
                ledger.model_copy(update={"repo_root": root.as_posix()})
            )
            result = self.renderer(root, projected, graph=graph)
            self._validate_render_result(result, root / ".codebase-docs")
            return _docs_fingerprint(root)

    def _docs_match_canonical_projection(self, ledger: SemanticLedger) -> bool:
        if _docs_fingerprint(self.repo_root) == "missing":
            return False
        graph = self._scheduler_snapshot().graph
        return _docs_fingerprint(self.repo_root) == self._projected_docs_fingerprint(
            ledger,
            graph,
        )

    @staticmethod
    def _run_codex_reviewer(
        packet: Mapping[str, object],
    ) -> tuple[object, Mapping[str, object]]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["samples"],
            "properties": {
                "samples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["sample", "verdicts"],
                        "properties": {
                            "sample": {"type": "string", "minLength": 1},
                            "verdicts": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": sorted(_REVIEW_CRITERIA),
                                "properties": {
                                    criterion: {"$ref": "#/$defs/verdict"}
                                    for criterion in sorted(_REVIEW_CRITERIA)
                                },
                            },
                        },
                    },
                }
            },
            "$defs": {
                "verdict": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["decision", "reason"],
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": sorted(_REVIEW_DECISIONS),
                        },
                        "reason": {"type": "string", "minLength": 1},
                    },
                }
            },
        }
        prompt = (
            "你是独立语义 reviewer。stdin 每项只有匿名序号、函数源码和函数解释。"
            "逐项判断这段解释与源码是否相符：行为、输入输出与副作用、失败条件、依赖关系。"
            "解释里凡是超出该函数源码可核验范围的断言，判为不充分，并在理由里逐字引出那一句。"
            "每条只能写充分、部分、不充分、判不了，并给一句具体理由。不得调用任何工具。"
        )
        # 闸 2 同样管 reviewer：它手里连 path 都没有，此前却被要求判「系统角色」，
        # 于是它只能判这句话读起来像不像一句角色陈述——评委恒绿的语义层实例。
        assert_prompt_dispatchable(prompt, subject="semantic reviewer prompt")
        with tempfile.TemporaryDirectory(prefix="cbe-semantic-review-") as temporary:
            root = Path(temporary)
            schema_path = root / "review.schema.json"
            verdict_path = root / "verdict.json"
            _atomic_write_json(schema_path, schema)
            completed = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--ephemeral",
                    "--json",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "-C",
                    root.as_posix(),
                    "--output-schema",
                    schema_path.as_posix(),
                    "--output-last-message",
                    verdict_path.as_posix(),
                    prompt,
                ],
                input=_json_bytes(packet),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=600,
            )
            if completed.returncode != 0:
                detail = completed.stderr.decode("utf-8", errors="replace")[-500:]
                raise SemanticReviewError(
                    f"Codex reviewer exited {completed.returncode}: {detail}"
                )
            events: list[object] = []
            try:
                for line in completed.stdout.splitlines():
                    if line.strip():
                        events.append(json.loads(line))
                verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SemanticReviewError(
                    f"Codex reviewer emitted invalid JSON artifacts: {exc}"
                ) from exc
            if not isinstance(verdict, dict):
                raise SemanticReviewError("Codex reviewer verdict must be an object")
            return events, verdict

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SemanticReviewError(f"cannot read review artifact {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SemanticReviewError(f"review artifact must be an object: {path}")
        return payload

    def _validate_review_inputs(
        self,
        packet: Mapping[str, object],
        hidden: Mapping[str, object],
        ledger: SemanticLedger,
    ) -> None:
        if set(packet) != {"samples"} or not isinstance(packet["samples"], list):
            raise SemanticReviewError("review packet must contain only a samples array")
        sample_ids: list[str] = []
        for sample in packet["samples"]:
            if not isinstance(sample, dict) or set(sample) != {
                "sample",
                "source",
                "explanation",
            }:
                raise SemanticReviewError("review samples expose forbidden metadata")
            sample_id = sample["sample"]
            if not isinstance(sample_id, str) or not sample_id:
                raise SemanticReviewError("review sample identity must be non-empty")
            sample_ids.append(sample_id)
        if len(set(sample_ids)) != len(sample_ids) or set(sample_ids) != set(hidden):
            raise SemanticReviewError("review packet and hidden map identities differ")

        packet_by_id = {sample["sample"]: sample for sample in packet["samples"]}
        for sample_id, raw_hidden in hidden.items():
            if not isinstance(raw_hidden, dict) or set(raw_hidden) != {
                "symbol_id",
                "producer_session_id",
            }:
                raise SemanticReviewError("hidden review map has an invalid shape")
            symbol_id = raw_hidden["symbol_id"]
            producer = raw_hidden["producer_session_id"]
            if not isinstance(symbol_id, str) or not isinstance(producer, str):
                raise SemanticReviewError("hidden review identities must be strings")
            symbol = ledger.symbols.get(symbol_id)
            if symbol is None or not symbol.is_fresh or symbol.explanation is None:
                raise SemanticReviewError("review sample is no longer fresh")
            packet_sample = packet_by_id[sample_id]
            if (
                packet_sample["source"] != self._source_body(symbol.path, symbol.span)
                or packet_sample["explanation"] != symbol.explanation.text
                or producer != symbol.explanation.producer
            ):
                raise SemanticReviewError("review packet no longer matches canonical state")

    @staticmethod
    def _validate_verdict(
        verdict: Mapping[str, object],
        *,
        expected_samples: set[str],
    ) -> dict[str, dict[str, dict[str, str]]]:
        if not isinstance(verdict, Mapping) or set(verdict) != {"samples"}:
            raise SemanticReviewError("verdict must contain only a samples array")
        samples = verdict["samples"]
        if not isinstance(samples, list):
            raise SemanticReviewError("verdict samples must be an array")
        parsed: dict[str, dict[str, dict[str, str]]] = {}
        for item in samples:
            if not isinstance(item, dict) or set(item) != {"sample", "verdicts"}:
                raise SemanticReviewError("each verdict item must contain sample and verdicts")
            sample = item["sample"]
            sample_verdicts = item["verdicts"]
            if not isinstance(sample, str) or sample in parsed:
                raise SemanticReviewError("verdict sample identities must be unique strings")
            if not isinstance(sample_verdicts, dict) or set(sample_verdicts) != _REVIEW_CRITERIA:
                raise SemanticReviewError("each sample must contain all four review criteria")
            parsed[sample] = {}
            for criterion, value in sample_verdicts.items():
                if not isinstance(value, dict) or set(value) != {"decision", "reason"}:
                    raise SemanticReviewError("criterion verdict shape is invalid")
                decision = value["decision"]
                reason = value["reason"]
                if decision not in _REVIEW_DECISIONS:
                    raise SemanticReviewError("criterion decision is outside the legal enum")
                if not isinstance(reason, str) or not reason.strip() or "\n" in reason:
                    raise SemanticReviewError("criterion reason must be one non-empty line")
                parsed[sample][criterion] = {
                    "decision": decision,
                    "reason": reason.strip(),
                }
        if set(parsed) != expected_samples:
            raise SemanticReviewError("verdict must cover every sample exactly once")
        return parsed

    def _commit_projection(
        self,
        *,
        expected: SemanticLedger | None,
        candidate: SemanticLedger,
        graph: nx.DiGraph | None,
        artifact_payloads: Mapping[Path, object] | None = None,
        rewrite_projection: bool = True,
        event_row: Mapping[str, object] | None = None,
        consume_once: tuple[
            Path,
            str,
            str,
            type[SemanticServiceError],
            str,
        ]
        | None = None,
        lease_guard: tuple[SemanticScheduler, SemanticBatchPacket] | None = None,
        allow_equivalent_bootstrap: bool = False,
    ) -> None:
        """Publish projections under a durable rollback journal."""

        candidate = revalidate_semantic_ledger(candidate)
        artifacts = dict(artifact_payloads or {})
        for relative in artifacts:
            self._safe_repo_artifact(relative, create_parent=True)
        if event_row is not None:
            if SEMANTIC_EVENTS_RELPATH in artifacts:
                raise SemanticServiceError("semantic event path cannot be a JSON artifact")
            self._safe_repo_artifact(SEMANTIC_EVENTS_RELPATH, create_parent=True)
        self.store._ensure_storage_dir()
        transaction_dir = Path(
            tempfile.mkdtemp(
                dir=self.store.path.parent,
                prefix=".semantic-projection-",
            )
        )
        stage_repo = transaction_dir / self.repo_root.name
        stage_repo.mkdir()
        actual_docs = self.repo_root / ".codebase-docs"
        staged_docs = stage_repo / ".codebase-docs"
        staged_artifacts: dict[Path, Path] = {}
        try:
            if rewrite_projection:
                render_candidate = revalidate_semantic_ledger(
                    candidate.model_copy(update={"repo_root": stage_repo.as_posix()})
                )
                result = self.renderer(stage_repo, render_candidate, graph=graph)
                self._validate_render_result(result, staged_docs)
            for index, (relative, payload) in enumerate(sorted(artifacts.items())):
                staged = transaction_dir / f"artifact-{index}.bin"
                if isinstance(payload, bytes):
                    self._atomic_write_bytes(staged, payload)
                else:
                    _atomic_write_json(staged, payload)
                staged_artifacts[relative] = staged
            with self.store._locked():
                if consume_once is not None:
                    (
                        marker_path,
                        identity_field,
                        identity,
                        error_type,
                        message,
                    ) = consume_once
                    self._assert_not_consumed(
                        relative=marker_path,
                        identity_field=identity_field,
                        identity=identity,
                        error_type=error_type,
                        message=message,
                    )
                current = self.store._read_unlocked() if self.store.path.exists() else None
                current_inventory = self._inventory()
                if current_inventory.source_revision != candidate.source_revision:
                    raise SemanticServiceError(
                        "source changed before semantic transaction commit"
                    )
                if current != expected:
                    equivalent_bootstrap = (
                        allow_equivalent_bootstrap
                        and rewrite_projection
                        and not artifacts
                        and event_row is None
                        and consume_once is None
                        and lease_guard is None
                        and current == candidate
                        and _docs_fingerprint(self.repo_root)
                        == _docs_fingerprint(stage_repo)
                    )
                    if equivalent_bootstrap:
                        return
                    raise SemanticServiceError(
                        "semantic state changed concurrently; reopen and retry"
                    )
                if lease_guard is not None:
                    scheduler, claimed_packet = lease_guard
                    live_packet = scheduler.recover_batch(
                        claimed_packet.batch_id,
                        now=self._now(),
                    )
                    if live_packet != claimed_packet:
                        raise SemanticSubmissionError(
                            "batch lease expired or changed before semantic transaction commit"
                        )
                self._prepare_transaction_journal(
                    expected=expected,
                    rewrite_projection=rewrite_projection,
                    artifact_paths=tuple(staged_artifacts)
                    + ((SEMANTIC_EVENTS_RELPATH,) if event_row is not None else ()),
                )
                try:
                    if event_row is not None:
                        staged_event = transaction_dir / "semantic-events.jsonl"
                        event_target = self._safe_repo_artifact(
                            SEMANTIC_EVENTS_RELPATH,
                            create_parent=True,
                        )
                        self._stage_event_append(
                            staged_event,
                            event_target,
                            event_row,
                        )
                        staged_artifacts[SEMANTIC_EVENTS_RELPATH] = staged_event
                    if rewrite_projection:
                        if actual_docs.is_symlink():
                            raise SemanticServiceError(
                                "semantic docs directory must not be a symlink"
                            )
                        displaced = transaction_dir / "displaced-docs"
                        if actual_docs.exists():
                            os.replace(actual_docs, displaced)
                        os.replace(staged_docs, actual_docs)
                        self._transaction_checkpoint("after_docs_publish")
                        self.store._atomic_write(candidate)
                        self._transaction_checkpoint("after_ledger_publish")
                    for relative, staged in staged_artifacts.items():
                        target = self._safe_repo_artifact(relative, create_parent=True)
                        self._publish_review_artifact(staged, target)
                        self._transaction_checkpoint(
                            f"after_artifact_publish:{relative.as_posix()}"
                        )
                    self._finish_transaction()
                except BaseException:
                    self._rollback_pending_transaction()
                    raise
        finally:
            shutil.rmtree(transaction_dir, ignore_errors=True)

    def _prepare_transaction_journal(
        self,
        *,
        expected: SemanticLedger | None,
        rewrite_projection: bool,
        artifact_paths: tuple[Path, ...],
    ) -> None:
        journal = self._safe_repo_artifact(
            TRANSACTION_JOURNAL_RELPATH,
            create_parent=True,
        )
        if journal.exists():
            raise SemanticServiceError("a semantic transaction is already pending recovery")
        backup = self.repo_root / TRANSACTION_BACKUP_RELDIR
        if backup.is_symlink():
            raise SemanticServiceError("semantic transaction backup must not be a symlink")
        if backup.exists():
            shutil.rmtree(backup)
        backup.mkdir()
        ledger_existed = self.store.path.exists()
        if ledger_existed:
            self._atomic_write_bytes(backup / "ledger.bin", self.store.path.read_bytes())
        docs = self.repo_root / ".codebase-docs"
        docs_existed = docs.exists()
        if docs.is_symlink():
            raise SemanticServiceError("semantic docs directory must not be a symlink")
        if rewrite_projection and docs_existed:
            shutil.copytree(docs, backup / "docs", symlinks=True)
        artifact_rows: list[dict[str, object]] = []
        for index, relative in enumerate(artifact_paths):
            target = self._safe_repo_artifact(relative, create_parent=True)
            existed = target.exists()
            backup_name = f"artifact-{index}.bin"
            if existed:
                self._atomic_write_bytes(backup / backup_name, target.read_bytes())
            artifact_rows.append(
                {
                    "relative_path": relative.as_posix(),
                    "existed": existed,
                    "backup_name": backup_name,
                }
            )
        payload = {
            "transaction_id": "semantic_tx_" + hashlib.sha256(
                (
                    f"{self._now().isoformat()}\0"
                    f"{self._ledger_fingerprint(expected) if expected is not None else 'none'}"
                ).encode("utf-8")
            ).hexdigest(),
            "rewrite_projection": rewrite_projection,
            "ledger_existed": ledger_existed,
            "docs_existed": docs_existed,
            "artifacts": artifact_rows,
        }
        _atomic_write_json(journal, payload)

    def _rollback_pending_transaction(self) -> bool:
        journal_path = self._safe_repo_artifact(
            TRANSACTION_JOURNAL_RELPATH,
            create_parent=False,
        )
        if not journal_path.exists():
            return False
        journal = self._read_json_object(journal_path)
        backup = self.repo_root / TRANSACTION_BACKUP_RELDIR
        if backup.is_symlink() or not backup.is_dir():
            raise SemanticServiceError("semantic transaction backup is missing or unsafe")
        rewrite = journal.get("rewrite_projection") is True
        if rewrite:
            docs = self.repo_root / ".codebase-docs"
            if docs.is_symlink():
                raise SemanticServiceError("semantic docs directory must not be a symlink")
            if docs.exists():
                shutil.rmtree(docs)
            if journal.get("docs_existed") is True:
                shutil.copytree(backup / "docs", docs, symlinks=True)
        if journal.get("ledger_existed") is True:
            self._atomic_write_bytes(self.store.path, (backup / "ledger.bin").read_bytes())
        else:
            self.store.path.unlink(missing_ok=True)
        rows = journal.get("artifacts")
        if not isinstance(rows, list):
            raise SemanticServiceError("semantic transaction journal artifacts are invalid")
        for row in rows:
            if not isinstance(row, dict):
                raise SemanticServiceError("semantic transaction artifact row is invalid")
            raw_relative = row.get("relative_path")
            backup_name = row.get("backup_name")
            if not isinstance(raw_relative, str) or not isinstance(backup_name, str):
                raise SemanticServiceError("semantic transaction artifact path is invalid")
            target = self._safe_repo_artifact(Path(raw_relative), create_parent=True)
            if row.get("existed") is True:
                self._atomic_write_bytes(target, (backup / backup_name).read_bytes())
            else:
                target.unlink(missing_ok=True)
        self._finish_transaction()
        return True

    def _recover_pending_transaction(self) -> None:
        analysis = self.repo_root / ".codebase-analysis"
        if analysis.is_symlink():
            raise SemanticServiceError(".codebase-analysis must not be a symlink")
        journal = self.repo_root / TRANSACTION_JOURNAL_RELPATH
        if journal.is_symlink():
            raise SemanticServiceError("semantic transaction journal must not be a symlink")
        if not journal.exists():
            backup = self.repo_root / TRANSACTION_BACKUP_RELDIR
            if backup.is_symlink():
                raise SemanticServiceError("semantic transaction backup must not be a symlink")
            if backup.exists():
                shutil.rmtree(backup)
            return
        with self.store._locked():
            recovered = self._rollback_pending_transaction()
        if recovered:
            self._append_event("recovery", action="rolled_back_pending_transaction")

    def _recover_orphan_claims(self) -> None:
        """Drop leases that crashed before their mandatory claim evidence row."""

        state_path = self.repo_root / SCHEDULER_STATE_RELPATH
        if not state_path.exists() or not self.store.path.exists():
            return
        scheduler = self._scheduler_snapshot()
        with self.store._locked():
            events_path = self._safe_repo_artifact(
                SEMANTIC_EVENTS_RELPATH,
                create_parent=False,
            )
            evidenced: set[str] = set()
            if events_path.exists():
                try:
                    rows = events_path.read_text(encoding="utf-8").splitlines()
                    for raw in rows:
                        row = json.loads(raw)
                        if (
                            isinstance(row, dict)
                            and row.get("event") == "claim"
                            and isinstance(row.get("batch_id"), str)
                        ):
                            evidenced.add(row["batch_id"])
                except (OSError, json.JSONDecodeError) as exc:
                    raise SemanticServiceError(
                        "semantic event evidence is unreadable during claim recovery"
                    ) from exc
            with scheduler._state_lock():
                packets = scheduler._live_packets(
                    scheduler._read_state_unlocked(),
                    self._now(),
                )
                orphan_ids = sorted(set(packets) - evidenced)
                if not orphan_ids:
                    return
                scheduler._write_state_unlocked(
                    {
                        batch_id: packet
                        for batch_id, packet in packets.items()
                        if batch_id in evidenced
                    }
                )
        self._append_event(
            "recovery",
            action="released_claims_without_evidence",
            batch_ids=orphan_ids,
        )

    def _finish_transaction(self) -> None:
        journal = self._safe_repo_artifact(
            TRANSACTION_JOURNAL_RELPATH,
            create_parent=False,
        )
        journal.unlink(missing_ok=True)
        backup = self.repo_root / TRANSACTION_BACKUP_RELDIR
        if backup.exists():
            # The journal is the recovery authority.  Once it is gone the
            # transaction is committed, so best-effort backup cleanup must not
            # turn a successful commit into a reported failure.
            shutil.rmtree(backup, ignore_errors=True)

    def _transaction_checkpoint(self, _phase: str) -> None:
        """Fault-injection seam; durable state is already represented by the journal."""

    def _append_event(self, event: str, **payload: object) -> None:
        row = self._event_row(event, **payload)
        with self.store._locked():
            target = self._safe_repo_artifact(
                SEMANTIC_EVENTS_RELPATH,
                create_parent=True,
            )
            self._append_event_unlocked(target, row)

    def _event_row(self, event: str, **payload: object) -> dict[str, object]:
        return {
            "event": event,
            "created_at": self._now().isoformat().replace("+00:00", "Z"),
            **payload,
        }

    @staticmethod
    def _append_event_unlocked(target: Path, row: Mapping[str, object]) -> None:
        encoded = _json_bytes(row)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags, 0o600)
        except OSError as exc:
            raise SemanticServiceError(f"cannot append semantic event: {exc}") from exc
        with os.fdopen(descriptor, "ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

    @classmethod
    def _stage_event_append(
        cls,
        staged: Path,
        target: Path,
        row: Mapping[str, object],
    ) -> None:
        prior = b""
        if target.exists():
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(target, flags)
            except OSError as exc:
                raise SemanticServiceError(
                    f"cannot read semantic event log for append: {exc}"
                ) from exc
            with os.fdopen(descriptor, "rb") as stream:
                prior = stream.read()
            if prior and not prior.endswith(b"\n"):
                raise SemanticServiceError("semantic event log has a truncated final row")
        cls._atomic_write_bytes(staged, prior + _json_bytes(row))

    @staticmethod
    def _publish_review_artifact(staged: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, target)

    @staticmethod
    def _atomic_write_bytes(path: Path, payload: bytes) -> None:
        descriptor, temporary = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _validate_render_result(
        result: Mapping[str, object],
        staged_docs: Path,
    ) -> None:
        if not isinstance(result, Mapping):
            raise SemanticServiceError("renderer must return a mapping")
        index_path = result.get("index_path")
        detail_paths = result.get("detail_paths")
        if not isinstance(index_path, str) or not isinstance(detail_paths, (list, tuple)):
            raise SemanticServiceError("renderer result must expose index_path and detail_paths")
        if not staged_docs.is_dir() or not (staged_docs / "INDEX.md").is_file():
            raise SemanticServiceError("renderer did not create .codebase-docs/INDEX.md")
        if not list(staged_docs.rglob("DETAIL.md")):
            raise SemanticServiceError("renderer did not create any module DETAIL.md")
