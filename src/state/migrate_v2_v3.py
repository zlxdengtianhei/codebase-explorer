"""Fail-closed, side-by-side V2 ingress and immutable rollback projection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.state.json_store import JsonRunStore, _canonical_snapshot_bytes
from src.state.models import RunSnapshot, StateFile


class MigrationError(RuntimeError):
    pass


class AmbiguousV2State(MigrationError):
    pass


class MigrationConflict(MigrationError):
    pass


@dataclass(frozen=True)
class MigrationPlan:
    v2_path: Path
    v3_path: Path
    legacy_hash: str
    legacy_projection: dict[str, Any]
    canonical_terminal_truth_inferred: bool = False


@dataclass(frozen=True)
class MigrationReceipt:
    v2_path: Path
    v3_path: Path
    v2_hash: str
    v3_hash: str
    run_id: str
    source_revision: str


@dataclass(frozen=True)
class RollbackProjectionReceipt:
    path: Path
    v2_hash: str
    v3_hash: str
    run_id: str


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_unambiguous_v2(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
        state = StateFile.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise AmbiguousV2State(f"V2 state is corrupt or invalid: {exc}") from exc
    if not state.schema_version.startswith("2."):
        raise AmbiguousV2State(f"unsupported legacy schema: {state.schema_version}")
    completion_signals: list[str] = []
    if state.project.analysis_status != "pending":
        completion_signals.append(f"project.analysis_status={state.project.analysis_status}")
    completion_signals.extend(
        f"tasks.{task_id}.status={task.status}"
        for task_id, task in state.tasks.items()
        if task.status != "pending"
    )
    docs = state.documentation
    if docs.index_written:
        completion_signals.append("documentation.index_written=true")
    if docs.source_files_covered or docs.source_file_coverage_percent:
        completion_signals.append("legacy coverage fields are non-empty")
    if payload.get("metadata", {}).get("completion_marker_seen"):
        completion_signals.append("legacy completion marker present")
    if completion_signals:
        raise AmbiguousV2State(
            "V2 completion/coverage signals cannot establish canonical truth: "
            + ", ".join(completion_signals)
        )
    return payload, raw


def dry_run_v2_to_v3(
    v2_path: str | Path,
    *,
    repo_root: str | Path,
    v3_path: str | Path | None = None,
) -> MigrationPlan:
    """Validate legacy input and return a write-free migration plan."""

    source = Path(v2_path)
    payload, raw = _load_unambiguous_v2(source)
    target = Path(v3_path) if v3_path is not None else source.with_name("state-v3.json")
    return MigrationPlan(
        v2_path=source,
        v3_path=target,
        legacy_hash=_sha(raw),
        legacy_projection=payload,
    )


def initialize_v3_side_by_side(
    v2_path: str | Path,
    *,
    repo_root: str | Path,
    actor: str,
    v3_path: str | Path | None = None,
    requested_languages: tuple[str, ...] = ("python", "typescript", "javascript"),
    now: datetime | None = None,
) -> MigrationReceipt:
    """Create V3 beside immutable V2, linking both by SHA-256."""

    plan = dry_run_v2_to_v3(v2_path, repo_root=repo_root, v3_path=v3_path)
    before_v2 = plan.v2_path.read_bytes()
    if plan.v3_path.exists():
        existing = plan.v3_path.read_bytes()
        try:
            snapshot = RunSnapshot.model_validate_json(existing)
        except Exception as exc:
            raise MigrationConflict(f"existing V3 is not the linked snapshot: {exc}") from exc
        if snapshot.metadata.get("legacy_v2_hash") != plan.legacy_hash:
            raise MigrationConflict("existing V3 has different V2 linkage")
        return MigrationReceipt(
            v2_path=plan.v2_path,
            v3_path=plan.v3_path,
            v2_hash=plan.legacy_hash,
            v3_hash=_sha(existing),
            run_id=snapshot.run_id,
            source_revision=snapshot.revisions.source,
        )
    instant = now or datetime.now(UTC)
    run_id = f"migrated-{plan.legacy_hash[:24]}"
    store = JsonRunStore(plan.v3_path)
    bootstrap = store.issue_bootstrap_lease(
        run_id=run_id,
        actor=actor,
        ttl=timedelta(minutes=5),
        now=instant,
    )
    result = store.begin_run(
        run_id=run_id,
        repo_root=repo_root,
        requested_languages=requested_languages,
        actor=actor,
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        initial_metadata={
            "legacy_v2_hash": plan.legacy_hash,
            "legacy_v2_path": str(plan.v2_path),
            "legacy_completion_inferred": "false",
        },
        now=instant,
    )
    if plan.v2_path.read_bytes() != before_v2:
        raise MigrationConflict("V2 bytes changed during side-by-side initialization")
    v3_bytes = plan.v3_path.read_bytes()
    return MigrationReceipt(
        v2_path=plan.v2_path,
        v3_path=plan.v3_path,
        v2_hash=plan.legacy_hash,
        v3_hash=_sha(v3_bytes),
        run_id=run_id,
        source_revision=result.snapshot.revisions.source,
    )


def write_v2_rollback_projection(
    target_path: str | Path,
    projection: dict[str, Any],
    *,
    snapshot: RunSnapshot,
) -> RollbackProjectionReceipt:
    """Create a canonical-linked V2 read projection once; never overwrite."""

    target = Path(target_path)
    payload = json.loads(json.dumps(projection))
    metadata = payload.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        raise AmbiguousV2State("V2 projection metadata must be an object")
    v3_hash = _sha(_canonical_snapshot_bytes(snapshot))
    metadata.update(
        {
            "canonical_v3_hash": v3_hash,
            "canonical_run_id": snapshot.run_id,
            "canonical_source_revision": snapshot.revisions.source,
            "rollback_projection_immutable": True,
        }
    )
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    digest = _sha(encoded)
    receipt = RollbackProjectionReceipt(
        path=target,
        v2_hash=digest,
        v3_hash=v3_hash,
        run_id=snapshot.run_id,
    )
    if target.exists():
        if target.read_bytes() != encoded:
            raise MigrationConflict("existing V2 projection has different hash or linkage")
        return receipt
    JsonRunStore._atomic_replace_bytes(target, encoded)
    return receipt


def read_rollback_projection(
    path: str | Path, *, expected_hash: str
) -> dict[str, Any]:
    """Read a V2 rollback projection only when its complete bytes match."""

    target = Path(path)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise MigrationConflict(f"rollback projection is unavailable: {exc}") from exc
    actual = _sha(raw)
    if actual != expected_hash:
        raise MigrationConflict(
            f"rollback projection hash mismatch: expected={expected_hash} actual={actual}"
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MigrationConflict(f"rollback projection is corrupt: {exc}") from exc
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict) or not metadata.get("canonical_v3_hash"):
        raise MigrationConflict("rollback projection lacks canonical V3 linkage")
    return payload
