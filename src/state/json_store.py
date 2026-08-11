"""JSON-based state management with atomic writes and resume support.

This module replaces the SQLite-based state management from V1.
All state is stored in a single state.json file with atomic write operations.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Protocol

from src.state.models import (
    ArtifactRecord,
    LegacyProjectionMetadata,
    LegacySubmissionSeed,
    LegacySubmissionState,
    LegacyTaskProgressRecord,
    LeaseRecord,
    RunSnapshot,
    SourceProvenance,
    SourceRecord,
    StateRevisions,
)
from src.state.universe import SourceOutcome, build_source_universe, enumerate_source_universe


_ROUTE_PARENT_POLICY: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "submit_analysis": (
            "capability:route-parent:submit_analysis",
            "orchestrator/legacy-mcp/submit_analysis",
        ),
        "doc_operation:update_index": (
            "capability:route-parent:doc_operation:update_index",
            "orchestrator/legacy-mcp/doc_operation:update_index",
        ),
    }
)

_ROUTE_PRODUCER_POLICY: Mapping[str, str] = MappingProxyType(
    {
        "orchestrator/legacy-mcp/submit_analysis": "legacy-mcp/submit_analysis",
        "orchestrator/legacy-mcp/doc_operation:update_index": (
            "legacy-mcp/doc_operation:update_index"
        ),
    }
)
_LEGACY_SUBMIT_ACTOR = "orchestrator/legacy-mcp/submit_analysis"
_LEGACY_SUBMIT_PRODUCER = "legacy-mcp/submit_analysis"


class RunStoreError(RuntimeError):
    """Base error for fail-closed RunStore operations."""


class RevisionConflict(RunStoreError):
    pass


class LeaseRejected(RunStoreError):
    pass


class ArtifactHashMismatch(RunStoreError):
    pass


class LegacySubmissionRejected(RunStoreError):
    pass


class RecoveryError(RunStoreError):
    pass


class RunStore(Protocol):
    """Storage-agnostic mutation contract implemented by concrete backends."""

    def issue_bootstrap_lease(
        self, *, run_id: str, actor: str, ttl: timedelta, now: datetime | None = None
    ) -> LeaseRecord: ...

    def begin_run(self, **kwargs: object) -> "BeginRunResult": ...

    def commit_source_outcomes(
        self,
        *,
        run_id: str,
        actor: str,
        lease_id: str,
        expected_revision: int,
        expected_source_revision: str,
        outcomes: Mapping[str, SourceOutcome],
        now: datetime | None = None,
    ) -> RunSnapshot: ...

    def lease_task(self, **kwargs: object) -> "LeaseResult": ...

    def submit_artifact(self, **kwargs: object) -> RunSnapshot: ...

    def submit_legacy_analysis(self, **kwargs: object) -> "LegacySubmissionResult": ...

    def commit_index(self, **kwargs: object) -> RunSnapshot: ...

    def record_verdict(self, **kwargs: object) -> RunSnapshot: ...

    def transition_run(self, **kwargs: object) -> RunSnapshot: ...

    def snapshot(self) -> RunSnapshot: ...

    def snapshot_for_verifier(self) -> RunSnapshot: ...


@dataclass(frozen=True)
class BeginRunResult:
    snapshot: RunSnapshot
    orchestrator_lease: LeaseRecord
    route_leases: Mapping[str, LeaseRecord] = MappingProxyType({})


@dataclass(frozen=True)
class LeaseResult:
    snapshot: RunSnapshot
    lease: LeaseRecord


@dataclass(frozen=True)
class LegacySubmissionProjection:
    status: Literal["success"]
    task_id: str
    tasks_remaining: int
    progress_percent: float
    source_file_coverage_percent: float
    details_written: int
    snippets_written: int
    source_files_covered: tuple[str, ...]


@dataclass(frozen=True)
class LegacySubmissionResult:
    snapshot: RunSnapshot
    artifact: ArtifactRecord
    projection: LegacySubmissionProjection


def _canonical_snapshot_bytes(snapshot: RunSnapshot) -> bytes:
    payload = snapshot.model_dump(mode="json", round_trip=True, warnings="error")
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def legacy_submission_projection(
    snapshot: RunSnapshot, task_id: str
) -> LegacySubmissionProjection:
    """Rebuild the legacy submit response solely from canonical typed state."""

    legacy = snapshot.legacy_submission
    if legacy is None:
        raise LegacySubmissionRejected("legacy submission state is not initialized")
    if not any(task.task_id == task_id for task in legacy.tasks):
        raise LegacySubmissionRejected("legacy task is unknown")
    complete = tuple(task for task in legacy.tasks if task.status == "complete")
    tasks_remaining = len(legacy.tasks) - len(complete)
    total = len(legacy.tasks)
    progress_percent = round(len(complete) / total * 100, 2) if total else 0.0
    metadata = legacy.projection_metadata
    coverage = (
        len(metadata.source_files_covered) / metadata.source_file_count * 100
        if metadata.source_file_count
        else 0.0
    )
    return LegacySubmissionProjection(
        status="success",
        task_id=task_id,
        tasks_remaining=tasks_remaining,
        progress_percent=progress_percent,
        source_file_coverage_percent=coverage,
        details_written=sum(task.details_written for task in complete),
        snippets_written=sum(task.snippets_written for task in complete),
        source_files_covered=metadata.source_files_covered,
    )


class JsonRunStore:
    """JSON V3 backend for the storage-agnostic :class:`RunStore` contract."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.backup_path = self.path.with_name(f"{self.path.name}.bak")
        self.backup_hash_path = self.backup_path.with_name(
            f"{self.backup_path.name}.sha256"
        )
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")
        self._bootstrap_leases: dict[str, LeaseRecord] = {}

    def issue_bootstrap_lease(
        self,
        *,
        run_id: str,
        actor: str,
        ttl: timedelta,
        now: datetime | None = None,
    ) -> LeaseRecord:
        """Issue an in-memory lease without mutating persistent state."""

        self._require_orchestrator(actor)
        instant = now or datetime.now(UTC)
        if ttl <= timedelta(0):
            raise ValueError("bootstrap lease ttl must be positive")
        lease = LeaseRecord(
            lease_id=f"bootstrap-{uuid.uuid4().hex}",
            run_id=run_id,
            target="bootstrap",
            actor=actor,
            expires_at=instant + ttl,
        )
        self._bootstrap_leases[lease.lease_id] = lease
        return lease

    def begin_run(
        self,
        *,
        run_id: str,
        repo_root: str | Path,
        requested_languages: tuple[str, ...],
        actor: str,
        lease_id: str,
        expected_revision: int,
        exclude_globs: tuple[str, ...] = (),
        product_output_roots: tuple[str | Path, ...] = (),
        route_keys: tuple[str, ...] = (),
        legacy_submission_seed: LegacySubmissionSeed | None = None,
        initial_metadata: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> BeginRunResult:
        self._require_orchestrator(actor)
        instant = now or datetime.now(UTC)
        if expected_revision != 0:
            raise RevisionConflict(
                f"run {run_id}: expected absent revision 0, got {expected_revision}"
            )
        lease = self._bootstrap_leases.get(lease_id)
        self._validate_lease(
            lease,
            run_id=run_id,
            target="bootstrap",
            actor=actor,
            now=instant,
        )
        validated_legacy_seed = self._validated_legacy_seed(legacy_submission_seed)
        route_policy = self._validated_route_policy(actor, route_keys)
        root = Path(repo_root).resolve()
        store_parent = self.path.resolve().parent
        configured_roots = list(product_output_roots)
        if store_parent != root:
            configured_roots.append(store_parent)
        enumeration = enumerate_source_universe(
            repo_root,
            requested_languages=requested_languages,
            exclude_globs=exclude_globs,
            product_output_roots=tuple(configured_roots),
        )
        sources = tuple(
            SourceRecord(
                path=source.path,
                language=source.language,
                content_hash=source.content_hash,
                state=source.state,
                provenance=SourceProvenance(
                    backend_id="enumerator",
                    backend_version="1",
                    evidence=source.enumeration_evidence,
                ),
            )
            for source in enumeration.sources
        )
        orchestrator_lease = LeaseRecord(
            lease_id=f"run-{uuid.uuid4().hex}",
            run_id=run_id,
            target="*",
            actor=actor,
            expires_at=lease.expires_at,
        )
        route_leases = {
            key: LeaseRecord(
                lease_id=f"route-{uuid.uuid4().hex}",
                run_id=run_id,
                target=target,
                actor=route_actor,
                expires_at=lease.expires_at,
            )
            for key, target, route_actor in route_policy
        }
        all_leases = (orchestrator_lease, *route_leases.values())
        if len({item.lease_id for item in all_leases}) != len(all_leases):
            raise ValueError("route policy generated duplicate lease ids")
        metadata = dict(initial_metadata or {})
        metadata.update(
            {
                "requested_languages": json.dumps(sorted(requested_languages)),
                "exclude_globs": json.dumps(sorted(exclude_globs)),
                "source_policy": enumeration.policy_serialization,
                "source_policy_hash": enumeration.policy_hash,
            }
        )
        snapshot = RunSnapshot(
            run_id=run_id,
            repo_root=enumeration.repo_root,
            store_revision=1,
            revisions=StateRevisions(source=enumeration.source_revision),
            sources=sources,
            leases=all_leases,
            legacy_submission=(
                LegacySubmissionState(
                    tasks=tuple(
                        LegacyTaskProgressRecord(task_id=task_id)
                        for task_id in validated_legacy_seed.task_ids
                    ),
                    projection_metadata=LegacyProjectionMetadata(
                        source_file_count=validated_legacy_seed.source_file_count
                    ),
                )
                if validated_legacy_seed is not None
                else None
            ),
            metadata=metadata,
        )
        with self._locked():
            if self.path.exists():
                raise RevisionConflict(f"run store already exists: {self.path}")
            self._promote(snapshot)
        self._bootstrap_leases.pop(lease_id, None)
        return BeginRunResult(
            snapshot=snapshot,
            orchestrator_lease=orchestrator_lease,
            route_leases=MappingProxyType(dict(route_leases)),
        )

    def snapshot(self) -> RunSnapshot:
        with self._locked():
            return self._read_snapshot()

    def snapshot_for_verifier(self) -> RunSnapshot:
        """Return the same immutable snapshot without granting mutation authority."""

        return self.snapshot()

    def commit_source_outcomes(
        self,
        *,
        run_id: str,
        actor: str,
        lease_id: str,
        expected_revision: int,
        expected_source_revision: str,
        outcomes: Mapping[str, SourceOutcome],
        now: datetime | None = None,
    ) -> RunSnapshot:
        """Atomically replace the frozen enumeration with terminal P2 outcomes."""

        self._require_orchestrator(actor)
        instant = now or datetime.now(UTC)
        with self._locked():
            current = self._read_snapshot()
            self._validate_mutation_context(
                current,
                run_id=run_id,
                actor=actor,
                lease_id=lease_id,
                target="*",
                expected_revision=expected_revision,
                now=instant,
            )
            if expected_source_revision != current.revisions.source:
                raise RevisionConflict(
                    f"source revision conflict: expected={expected_source_revision} "
                    f"current={current.revisions.source}"
                )
            if current.metadata.get("source_outcomes_committed") == "true":
                raise RevisionConflict("source outcomes are already committed")
            live = enumerate_source_universe(
                current.repo_root,
                requested_languages=(),
                frozen_policy=current.metadata["source_policy"],
            )
            if live.source_revision != current.revisions.source:
                raise RevisionConflict(
                    f"source revision changed: expected={current.revisions.source} "
                    f"current={live.source_revision}"
                )
            universe = build_source_universe(live, outcomes)
            metadata = dict(current.metadata)
            metadata["source_outcomes_committed"] = "true"
            metadata["source_outcomes_actor"] = actor
            updated = self._updated(
                current,
                store_revision=current.store_revision + 1,
                sources=universe.records,
                metadata=metadata,
            )
            self._promote(updated)
            return updated

    def lease_task(
        self,
        *,
        run_id: str,
        target: str,
        actor: str,
        lease_id: str,
        expected_revision: int,
        now: datetime | None = None,
        assignee: str | None = None,
        ttl: timedelta = timedelta(minutes=5),
    ) -> LeaseResult:
        self._require_orchestrator(actor)
        instant = now or datetime.now(UTC)
        if ttl <= timedelta(0):
            raise ValueError("lease ttl must be positive")
        with self._locked():
            current = self._read_snapshot()
            parent = self._validate_parent_context(
                current,
                run_id=run_id,
                actor=actor,
                lease_id=lease_id,
                expected_revision=expected_revision,
                now=instant,
            )
            assigned_actor = assignee or actor
            if parent.target == "*":
                self._require_orchestrator(assigned_actor)
            else:
                route_actors = {
                    target: route_actor
                    for target, route_actor in _ROUTE_PARENT_POLICY.values()
                }
                expected_actor = route_actors.get(parent.target)
                if target == "*" or target in route_actors:
                    raise LeaseRejected(
                        "route parent cannot issue a child with a reserved parent target"
                    )
                if (
                    expected_actor is None
                    or parent.actor != expected_actor
                    or actor != expected_actor
                    or assigned_actor != expected_actor
                ):
                    raise LeaseRejected(
                        "route parent cannot be reused or delegate to a different actor"
                    )
            lease = LeaseRecord(
                lease_id=f"task-{uuid.uuid4().hex}",
                run_id=run_id,
                target=target,
                actor=assigned_actor,
                expires_at=instant + ttl,
            )
            updated = self._updated(
                current,
                store_revision=current.store_revision + 1,
                leases=current.leases + (lease,),
            )
            self._promote(updated)
            return LeaseResult(snapshot=updated, lease=lease)

    def submit_artifact(
        self,
        *,
        run_id: str,
        target: str,
        actor: str,
        producer: str,
        lease_id: str,
        expected_revision: int,
        artifact_bytes: bytes,
        artifact_hash: str,
        revision_kind: Literal["index", "document", "verification"] = "document",
        now: datetime | None = None,
    ) -> RunSnapshot:
        self._require_orchestrator(actor)
        self._validate_route_producer(actor, producer)
        instant = now or datetime.now(UTC)
        actual_hash = hashlib.sha256(artifact_bytes).hexdigest()
        if actual_hash != artifact_hash:
            raise ArtifactHashMismatch(
                f"artifact hash mismatch: expected={artifact_hash} actual={actual_hash}"
            )
        with self._locked():
            current = self._read_snapshot()
            self._validate_mutation_context(
                current,
                run_id=run_id,
                actor=actor,
                lease_id=lease_id,
                target=target,
                expected_revision=expected_revision,
                now=instant,
            )
            if (
                current.legacy_submission is not None
                and actor == _LEGACY_SUBMIT_ACTOR
                and producer == _LEGACY_SUBMIT_PRODUCER
                and target
                in {task.task_id for task in current.legacy_submission.tasks}
            ):
                raise LegacySubmissionRejected(
                    "generic artifact ingress cannot complete a legacy task"
                )
            next_store_revision = current.store_revision + 1
            revision_value = hashlib.sha256(
                f"{revision_kind}\x1f{actual_hash}\x1f{next_store_revision}".encode("ascii")
            ).hexdigest()
            revisions = current.revisions.model_copy(
                update={revision_kind: revision_value}
            )
            artifact = ArtifactRecord(
                target=target,
                actor=actor,
                producer=producer,
                content_hash=actual_hash,
                revision_kind=revision_kind,
                accepted_at=instant,
            )
            updated = self._updated(
                current,
                store_revision=next_store_revision,
                revisions=revisions,
                artifacts=current.artifacts + (artifact,),
            )
            self._promote(updated)
            return updated

    def submit_legacy_analysis(
        self,
        *,
        run_id: str,
        task_id: str,
        actor: str,
        producer: str,
        lease_id: str,
        expected_revision: int,
        artifact_bytes: bytes,
        artifact_hash: str,
        details_written: int,
        snippets_written: int,
        source_files_covered: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> LegacySubmissionResult:
        self._require_orchestrator(actor)
        if actor != _LEGACY_SUBMIT_ACTOR:
            raise LeaseRejected("legacy submission requires the exact submit route actor")
        self._validate_route_producer(actor, producer)
        if (
            type(details_written) is not int
            or details_written < 0
            or type(snippets_written) is not int
            or snippets_written < 0
        ):
            raise LegacySubmissionRejected(
                "legacy submission counters must be non-negative integers"
            )
        if not isinstance(source_files_covered, tuple) or any(
            not isinstance(value, str) for value in source_files_covered
        ):
            raise LegacySubmissionRejected(
                "legacy covered source values must be a tuple of strings"
            )
        actual_hash = hashlib.sha256(artifact_bytes).hexdigest()
        if actual_hash != artifact_hash:
            raise ArtifactHashMismatch(
                f"artifact hash mismatch: expected={artifact_hash} actual={actual_hash}"
            )
        instant = now or datetime.now(UTC)
        with self._locked():
            current = self._read_snapshot()
            self._validate_mutation_context(
                current,
                run_id=run_id,
                actor=actor,
                lease_id=lease_id,
                target=task_id,
                expected_revision=expected_revision,
                now=instant,
            )
            legacy = current.legacy_submission
            if legacy is None:
                raise LegacySubmissionRejected(
                    "legacy submission state is not initialized"
                )
            task_index = next(
                (
                    index
                    for index, task in enumerate(legacy.tasks)
                    if task.task_id == task_id
                ),
                None,
            )
            if task_index is None:
                raise LegacySubmissionRejected("legacy task is unknown")
            task = legacy.tasks[task_index]
            if task.status != "pending":
                raise LegacySubmissionRejected("legacy task is already complete")

            artifact = ArtifactRecord(
                target=task_id,
                actor=actor,
                producer=producer,
                content_hash=actual_hash,
                revision_kind="document",
                accepted_at=instant,
            )
            completed_task = LegacyTaskProgressRecord(
                task_id=task_id,
                status="complete",
                artifact_hash=actual_hash,
                details_written=details_written,
                snippets_written=snippets_written,
                completed_at=instant,
            )
            tasks = list(legacy.tasks)
            tasks[task_index] = completed_task
            covered = tuple(
                dict.fromkeys(
                    (
                        *legacy.projection_metadata.source_files_covered,
                        *source_files_covered,
                    )
                )
            )
            updated_legacy = LegacySubmissionState(
                tasks=tuple(tasks),
                projection_metadata=LegacyProjectionMetadata(
                    source_file_count=legacy.projection_metadata.source_file_count,
                    source_files_covered=covered,
                ),
            )
            next_store_revision = current.store_revision + 1
            document_revision = hashlib.sha256(
                f"document\x1f{actual_hash}\x1f{next_store_revision}".encode("ascii")
            ).hexdigest()
            updated = self._updated(
                current,
                store_revision=next_store_revision,
                revisions=current.revisions.model_copy(
                    update={"document": document_revision}
                ),
                artifacts=current.artifacts + (artifact,),
                legacy_submission=updated_legacy,
            )
            self._promote(updated)
            return LegacySubmissionResult(
                snapshot=updated,
                artifact=artifact,
                projection=legacy_submission_projection(updated, task_id),
            )

    def commit_index(
        self,
        *,
        run_id: str,
        actor: str,
        producer: str,
        lease_id: str,
        expected_revision: int,
        expected_source_revision: str,
        index_payload: bytes,
        now: datetime | None = None,
    ) -> RunSnapshot:
        self._require_orchestrator(actor)
        instant = now or datetime.now(UTC)
        with self._locked():
            current = self._read_snapshot()
            self._validate_mutation_context(
                current,
                run_id=run_id,
                actor=actor,
                lease_id=lease_id,
                target="*",
                expected_revision=expected_revision,
                now=instant,
            )
            if expected_source_revision != current.revisions.source:
                raise RevisionConflict(
                    f"source revision conflict: expected={expected_source_revision} "
                    f"current={current.revisions.source}"
                )
            live = enumerate_source_universe(
                current.repo_root,
                requested_languages=(),
                frozen_policy=current.metadata["source_policy"],
            )
            if live.source_revision != current.revisions.source:
                raise RevisionConflict(
                    f"source revision changed: expected={current.revisions.source} "
                    f"current={live.source_revision}"
                )
            digest = hashlib.sha256(index_payload).hexdigest()
            next_revision = current.store_revision + 1
            index_revision = hashlib.sha256(
                f"index\x1f{current.revisions.source}\x1f{digest}\x1f{next_revision}".encode(
                    "ascii"
                )
            ).hexdigest()
            updated = self._updated(
                current,
                store_revision=next_revision,
                revisions=current.revisions.model_copy(update={"index": index_revision}),
                artifacts=current.artifacts
                + (
                    ArtifactRecord(
                        target="index",
                        actor=actor,
                        producer=producer,
                        content_hash=digest,
                        revision_kind="index",
                        accepted_at=instant,
                    ),
                ),
            )
            self._promote(updated)
            return updated

    def record_verdict(self, **kwargs: object) -> RunSnapshot:
        """Record a verifier artifact through the ordinary lease/CAS authority."""

        kwargs["revision_kind"] = "verification"
        return self.submit_artifact(**kwargs)  # type: ignore[arg-type]

    def transition_run(
        self,
        *,
        run_id: str,
        actor: str,
        lease_id: str,
        expected_revision: int,
        run_state: Literal["verified_full", "verified_with_residuals", "failed"],
        now: datetime | None = None,
    ) -> RunSnapshot:
        """Apply the sole running-to-terminal state transition under CAS."""

        self._require_orchestrator(actor)
        instant = now or datetime.now(UTC)
        with self._locked():
            current = self._read_snapshot()
            self._validate_mutation_context(
                current,
                run_id=run_id,
                actor=actor,
                lease_id=lease_id,
                target="*",
                expected_revision=expected_revision,
                now=instant,
            )
            if current.run_state != "running":
                raise RevisionConflict(
                    f"run is already terminal: {current.run_state}"
                )
            if run_state.startswith("verified_") and not current.revisions.verification:
                raise RevisionConflict("verified transition requires a verification revision")
            updated = self._updated(
                current,
                store_revision=current.store_revision + 1,
                run_state=run_state,
            )
            self._promote(updated)
            return updated

    def recover(self) -> RunSnapshot:
        """Recover a corrupt primary only from a hash-linked valid backup."""

        with self._locked():
            try:
                return self._read_snapshot()
            except RecoveryError:
                pass
            if not self.backup_path.exists() or not self.backup_hash_path.exists():
                raise RecoveryError("no hash-linked backup is available")
            backup = self.backup_path.read_bytes()
            expected = self.backup_hash_path.read_text(encoding="ascii").strip()
            actual = hashlib.sha256(backup).hexdigest()
            if actual != expected:
                raise RecoveryError(
                    f"backup hash mismatch: expected={expected} actual={actual}"
                )
            try:
                snapshot = RunSnapshot.model_validate_json(backup)
            except Exception as exc:
                raise RecoveryError(f"backup is not a complete V3 snapshot: {exc}") from exc
            self._atomic_replace_bytes(self.path, backup)
            return snapshot

    def _updated(self, current: RunSnapshot, **changes: object) -> RunSnapshot:
        payload = current.model_dump(mode="python", round_trip=True)
        payload.update(changes)
        return RunSnapshot.model_validate(payload)

    def _read_snapshot(self) -> RunSnapshot:
        if not self.path.exists():
            raise RecoveryError(f"run store does not exist: {self.path}")
        try:
            return RunSnapshot.model_validate_json(self.path.read_bytes())
        except Exception as exc:
            raise RecoveryError(f"primary is not a complete V3 snapshot: {exc}") from exc

    def _validate_mutation_context(
        self,
        snapshot: RunSnapshot,
        *,
        run_id: str,
        actor: str,
        lease_id: str,
        target: str,
        expected_revision: int,
        now: datetime,
    ) -> None:
        if snapshot.run_id != run_id:
            raise RevisionConflict(
                f"run id conflict: expected={run_id} current={snapshot.run_id}"
            )
        if snapshot.store_revision != expected_revision:
            raise RevisionConflict(
                f"run {run_id}: expected revision {expected_revision}, "
                f"current revision {snapshot.store_revision}; retry from current snapshot"
            )
        lease = next(
            (candidate for candidate in snapshot.leases if candidate.lease_id == lease_id),
            None,
        )
        self._validate_lease(
            lease, run_id=run_id, target=target, actor=actor, now=now
        )

    @staticmethod
    def _validated_legacy_seed(
        seed: LegacySubmissionSeed | None,
    ) -> LegacySubmissionSeed | None:
        if seed is None:
            return None
        if isinstance(seed, LegacySubmissionSeed):
            return seed
        try:
            return LegacySubmissionSeed.model_validate(seed)
        except Exception as exc:
            raise ValueError(f"invalid legacy submission seed: {exc}") from exc

    @staticmethod
    def _validate_route_producer(actor: str, producer: str) -> None:
        required = _ROUTE_PRODUCER_POLICY.get(actor)
        if required is not None and producer != required:
            raise LegacySubmissionRejected(
                "route actor requires its exact logical producer"
            )

    @staticmethod
    def _validated_route_policy(
        begin_actor: str, route_keys: tuple[str, ...]
    ) -> tuple[tuple[str, str, str], ...]:
        if not isinstance(route_keys, tuple):
            raise ValueError("route_keys must be a tuple")
        if any(not isinstance(key, str) or not key for key in route_keys):
            raise ValueError("route keys must be non-empty strings")
        if len(set(route_keys)) != len(route_keys):
            raise ValueError("route keys must be unique")
        if any(key not in _ROUTE_PARENT_POLICY for key in route_keys):
            raise ValueError("route key is not in the state-owned allowlist")
        policy_items = tuple(_ROUTE_PARENT_POLICY.items())
        targets = [target for _, (target, _) in policy_items]
        actors = [actor for _, (_, actor) in policy_items]
        if len(set(targets)) != len(targets):
            raise ValueError("route policy capability targets must be unique")
        if len(set(actors)) != len(actors):
            raise ValueError("route policy actors must be unique")
        for key, (target, actor) in policy_items:
            if target != f"capability:route-parent:{key}":
                raise ValueError("route policy capability target is invalid")
            if not actor.startswith("orchestrator/"):
                raise ValueError("route policy actor must be an orchestrator identity")
        selected = tuple(
            (key, *_ROUTE_PARENT_POLICY[key])
            for key in route_keys
        )
        if any(route_actor == begin_actor for _, _, route_actor in selected):
            raise ValueError("route policy actor collides with begin actor")
        return selected

    @staticmethod
    def _validate_parent_context(
        snapshot: RunSnapshot,
        *,
        run_id: str,
        actor: str,
        lease_id: str,
        expected_revision: int,
        now: datetime,
    ) -> LeaseRecord:
        if snapshot.run_id != run_id:
            raise RevisionConflict(
                f"run id conflict: expected={run_id} current={snapshot.run_id}"
            )
        if snapshot.store_revision != expected_revision:
            raise RevisionConflict(
                f"run {run_id}: expected revision {expected_revision}, "
                f"current revision {snapshot.store_revision}; retry from current snapshot"
            )
        parent = next(
            (candidate for candidate in snapshot.leases if candidate.lease_id == lease_id),
            None,
        )
        if parent is None:
            raise LeaseRejected("lease is missing or was not issued by this RunStore")
        if parent.run_id != run_id or parent.actor != actor:
            raise LeaseRejected("lease is bound to a different run or actor")
        if parent.expires_at <= now:
            raise LeaseRejected("lease has expired")
        if parent.target != "*" and parent.target not in {
            target for target, _ in _ROUTE_PARENT_POLICY.values()
        }:
            raise LeaseRejected("lease target is not a parent capability")
        return parent

    @staticmethod
    def _validate_lease(
        lease: LeaseRecord | None,
        *,
        run_id: str,
        target: str,
        actor: str,
        now: datetime,
    ) -> None:
        if lease is None:
            raise LeaseRejected("lease is missing or was not issued by this RunStore")
        if lease.run_id != run_id or lease.target != target or lease.actor != actor:
            raise LeaseRejected(
                "lease is bound to a different run, target, or actor"
            )
        if lease.expires_at <= now:
            raise LeaseRejected("lease has expired")

    @staticmethod
    def _require_orchestrator(actor: str) -> None:
        if not actor.startswith("orchestrator/"):
            raise ValueError("state mutations require an orchestrator identity")

    def _promote(self, snapshot: RunSnapshot) -> None:
        new_bytes = _canonical_snapshot_bytes(snapshot)
        pre_bytes = self.path.read_bytes() if self.path.exists() else None
        backup_bytes = pre_bytes if pre_bytes is not None else new_bytes
        try:
            self._atomic_replace_bytes(self.backup_path, backup_bytes)
            self._atomic_replace_bytes(
                self.backup_hash_path,
                (hashlib.sha256(backup_bytes).hexdigest() + "\n").encode("ascii"),
            )
            self._atomic_replace_bytes(self.path, new_bytes)
        except Exception:
            self._restore_failed_promotion(pre_bytes)
            raise

    def _restore_failed_promotion(self, pre_bytes: bytes | None) -> None:
        """Restore one complete, hash-linked pre-state after promotion fails."""

        surfaces = (self.path, self.backup_path, self.backup_hash_path)
        if pre_bytes is None:
            for path in surfaces:
                path.unlink(missing_ok=True)
            if any(path.exists() for path in surfaces):
                raise RecoveryError("failed promotion left persistent state behind")
            return

        backup_hash = (
            hashlib.sha256(pre_bytes).hexdigest() + "\n"
        ).encode("ascii")
        self._atomic_replace_bytes(self.path, pre_bytes)
        self._atomic_replace_bytes(self.backup_path, pre_bytes)
        self._atomic_replace_bytes(self.backup_hash_path, backup_hash)
        restored = tuple(path.read_bytes() for path in surfaces)
        if restored != (pre_bytes, pre_bytes, backup_hash):
            raise RecoveryError("failed promotion could not restore a complete pre-state")

    @staticmethod
    def _atomic_replace_bytes(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_name, path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def _locked(self):
        return _FileLock(self.lock_path)


class _FileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a+")
        fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        assert self._stream is not None
        fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        self._stream.close()


def atomic_write_state(state_path: Path, state: dict) -> None:
    """Atomically write state to JSON file.

    Uses write-then-rename pattern for POSIX atomicity:
    1. Write to .tmp file
    2. os.replace() to final path (atomic on POSIX)

    Args:
        state_path: Path to state.json file
        state: State dictionary to write
    """
    tmp_path = state_path.with_suffix(".json.tmp")

    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file
    tmp_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Atomic replace
    os.replace(tmp_path, state_path)


def locked_read_modify_write(state_path: Path, update_fn) -> dict:
    """Atomically read-modify-write state.json with file locking."""
    lock_path = state_path.with_suffix(".lock")
    lock_path.touch(exist_ok=True)
    with open(lock_path, "r+") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            state = update_fn(state)
            atomic_write_state(state_path, state)
            return state
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def read_state(state_path: Path) -> dict | None:
    """Read state from JSON file.

    Args:
        state_path: Path to state.json file

    Returns:
        State dictionary, or None if file doesn't exist
    """
    if not state_path.exists():
        return None

    content = state_path.read_text(encoding="utf-8")
    try:
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None


def update_task_status(
    state_path: Path,
    task_id: str,
    status: Literal["pending", "in_progress", "complete", "failed"],
    output_files: list[dict] | None = None,
    error: str | None = None,
) -> dict:
    """Atomically update a task's status in state.json.

    Args:
        state_path: Path to state.json file
        task_id: Task identifier
        status: New task status
        output_files: Optional list of output file info
        error: Optional error message

    Returns:
        Updated state dictionary

    Raises:
        ValueError: If state file doesn't exist or task not found
    """
    if read_state(state_path) is None:
        raise ValueError(f"State file not found: {state_path}")

    def update(state: dict) -> dict:
        if task_id not in state.get("tasks", {}):
            raise ValueError(f"Task not found: {task_id}")
        state["tasks"][task_id]["status"] = status
        if status == "in_progress":
            state["tasks"][task_id]["started_at"] = datetime.now(UTC).isoformat()
        elif status in ["complete", "failed"]:
            state["tasks"][task_id]["completed_at"] = datetime.now(UTC).isoformat()
        if output_files is not None:
            state["tasks"][task_id]["output_files"] = output_files
        if error is not None:
            state["tasks"][task_id]["error"] = error
        state.setdefault("metadata", {})["last_updated_at"] = datetime.now(UTC).isoformat()
        state["metadata"]["state_authority"] = "legacy_v2_non_authoritative"
        return state

    return locked_read_modify_write(state_path, update)


def _check_file_complete(file_path: Path) -> bool:
    """Check if an output file is complete.

    A file is considered complete if:
    1. File exists
    2. File size > 200 bytes
    3. File ends with completion marker

    Args:
        file_path: Path to the file

    Returns:
        True if file is complete, False otherwise
    """
    if not file_path.exists():
        return False

    if file_path.stat().st_size < 200:
        return False

    # Check for completion marker in last 10 lines
    content = file_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    last_lines = lines[-10:] if len(lines) >= 10 else lines

    return any("<!-- codebase-explorer: end -->" in line for line in last_lines)


def resume_from_state(project_root: Path) -> list[str]:
    """Read the legacy V2 projection without inferring canonical completion.

    This compatibility symbol remains importable until P5L.  It can reset an
    interrupted legacy task to pending, but file size/end markers never assign
    completion truth.  Canonical recovery belongs to :class:`RunStore`.

    Args:
        project_root: Root directory of the codebase

    Returns:
        List of pending task IDs in execution order
    """
    state_path = project_root / ".codebase-analysis" / "state.json"
    state = read_state(state_path)

    if state is None:
        return []

    def reset_interrupted(current: dict) -> dict:
        for task in current.get("tasks", {}).values():
            if task.get("status") != "in_progress":
                continue
            task["status"] = "pending"
            task["started_at"] = None
            for output_file in task.get("output_files", []):
                output_file["status"] = "pending"
        current.setdefault("metadata", {})["state_authority"] = (
            "legacy_v2_non_authoritative"
        )
        current["metadata"]["last_updated_at"] = datetime.now(UTC).isoformat()
        return current

    if any(task.get("status") == "in_progress" for task in state.get("tasks", {}).values()):
        state = locked_read_modify_write(state_path, reset_interrupted)

    tasks = state.get("tasks", {})

    # Step 2: Collect pending tasks
    pending_tasks = []
    for task_id, task in tasks.items():
        if task.get("status") == "pending":
            pending_tasks.append(task_id)

    # Step 3: Restore execution order from task_manifest
    manifest_path = project_root / ".codebase-analysis" / "05_task_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        task_order = manifest.get("task_order", [])
        # Filter pending tasks by manifest order
        ordered_pending = [t for t in task_order if t in set(pending_tasks)]
    else:
        ordered_pending = pending_tasks

    return ordered_pending
