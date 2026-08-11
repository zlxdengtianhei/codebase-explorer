"""Canonical generational run selection for legacy MCP consumers.

The active receipt is deliberately a locator and integrity envelope.  Mutable
task, source, lease and artifact truth remains exclusively in ``JsonRunStore``.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.state.json_store import JsonRunStore, RecoveryError
from src.state.migrate_v2_v3 import MigrationConflict, write_v2_rollback_projection
from src.state.models import LegacySubmissionSeed, RunSnapshot
from src.state.universe import enumerate_source_universe


ACTIVE_RECEIPT_SCHEMA = "cbe-active-run-1"
ACTIVE_RECEIPT_NAME = "active-run.json"
GENERATION_RECEIPT_NAME = "active-run-receipt.json"
V2_RECOVERY_PROJECTION_NAME = "v2-recovery-projection.json"
V2_RECOVERY_PROJECTION_SHA_KEY = "v2_recovery_projection_sha256"
REQUIRED_ARTIFACTS = (
    "01_structure.json",
    "02_dag.json",
    "03_feature_cones.json",
    "04_file_tokens.json",
    "05_task_manifest.json",
    "06_function_deps.json",
)
ROUTE_KEYS = ("submit_analysis", "doc_operation:update_index")


class LifecycleError(RuntimeError):
    """Base class for fail-closed lifecycle errors."""


class LifecycleConflict(LifecycleError):
    """The selector changed after the caller observed it."""


class LifecycleIntegrityError(LifecycleError):
    """A receipt or a protected generation failed integrity validation."""


class LifecycleCacheMiss(LifecycleError):
    """Recoverable input, source or authorization freshness mismatch."""


class ArtifactManifestEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    sha256: str

    @field_validator("path")
    @classmethod
    def _plain_filename(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or len(path.parts) != 1 or value not in REQUIRED_ARTIFACTS:
            raise ValueError("manifest paths must be required generation filenames")
        return value

    @field_validator("sha256")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("manifest digest must be lowercase SHA-256")
        return value


class ActiveRunReceipt(BaseModel):
    """Immutable locator/integrity receipt for one active V3 generation."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    schema_id: Literal["cbe-active-run-1"] = Field(
        default=ACTIVE_RECEIPT_SCHEMA, alias="schema"
    )
    activation_generation: int
    run_id: str
    generation_path: str
    state_path: str
    repo_root: str
    analysis_input_fingerprint: str
    source_revision: str
    v2_sha256: str
    artifacts: tuple[ArtifactManifestEntry, ...]
    legacy_seed_sha256: str
    route_keys: tuple[str, ...]
    prior_receipt_sha256: str = ""

    @field_validator("activation_generation")
    @classmethod
    def _positive_generation(cls, value: int) -> int:
        if type(value) is not int or value < 1:
            raise ValueError("activation generation must be a positive integer")
        return value

    @field_validator(
        "run_id",
        "repo_root",
        "analysis_input_fingerprint",
        "source_revision",
        "legacy_seed_sha256",
    )
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("active receipt identity fields must be non-empty")
        return value

    @field_validator(
        "analysis_input_fingerprint",
        "v2_sha256",
        "legacy_seed_sha256",
        "prior_receipt_sha256",
    )
    @classmethod
    def _digest(cls, value: str) -> str:
        if value == "":
            return value
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("receipt digest fields must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _paths_and_closed_sets(self) -> Self:
        expected_generation = f".runs/{self.run_id}"
        if self.generation_path != expected_generation:
            raise ValueError("generation path must be run-scoped and relative")
        if self.state_path != f"{expected_generation}/state-v3.json":
            raise ValueError("state path must identify the generation V3 primary")
        if tuple(item.path for item in self.artifacts) != REQUIRED_ARTIFACTS:
            raise ValueError("artifact manifest must contain exact required files in order")
        if self.route_keys != ROUTE_KEYS:
            raise ValueError("active receipt requires the two exact legacy route keys")
        return self


class ActiveRunSelection(BaseModel):
    """Validated immutable selection.  The store remains the state authority."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    receipt: ActiveRunReceipt
    analysis_root: Path
    generation_path: Path
    state_path: Path
    snapshot: RunSnapshot


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_path(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _receipt_bytes(receipt: ActiveRunReceipt) -> bytes:
    payload = receipt.model_dump(mode="json", round_trip=True, warnings="error")
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def receipt_sha256(receipt: ActiveRunReceipt) -> str:
    return _sha_bytes(_receipt_bytes(receipt))


def analysis_input_fingerprint(
    *,
    languages: tuple[str, ...],
    exclude_paths: tuple[str, ...],
    include_tests: bool,
) -> str:
    """Hash the canonical analysis inputs without depending on caller ordering."""

    payload = {
        "exclude_paths": sorted(set(exclude_paths)),
        "include_tests": bool(include_tests),
        "languages": sorted(set(languages)),
    }
    return _sha_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def legacy_seed_sha256(seed: LegacySubmissionSeed) -> str:
    payload = seed.model_dump(mode="json", round_trip=True, warnings="error")
    return _sha_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def artifact_manifest(generation_path: Path) -> tuple[ArtifactManifestEntry, ...]:
    entries: list[ArtifactManifestEntry] = []
    for name in REQUIRED_ARTIFACTS:
        path = generation_path / name
        if not path.is_file():
            raise LifecycleIntegrityError(f"required generation artifact is missing: {path}")
        entries.append(ArtifactManifestEntry(path=name, sha256=_sha_path(path)))
    return tuple(entries)


def stage_v2_recovery_projection(
    staging_path: Path, projection: dict[str, object]
) -> str:
    """Persist the exact pre-linkage V2 input inside its unpublished generation."""

    payload = (
        json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    path = staging_path / V2_RECOVERY_PROJECTION_NAME
    if path.exists() and path.read_bytes() != payload:
        raise LifecycleConflict("staged V2 recovery projection is not immutable")
    if not path.exists():
        _atomic_replace(path, payload)
    return _sha_bytes(payload)


def publish_generation(analysis_root: Path, staging_path: Path, run_id: str) -> Path:
    """Publish one complete same-directory staging tree without selecting it."""

    root = analysis_root.resolve()
    stage = staging_path.resolve()
    expected_stage = root / ".staging" / run_id
    if stage != expected_stage or stage.parent != root / ".staging":
        raise LifecycleIntegrityError("staging path is outside the run-scoped staging root")
    artifact_manifest(stage)
    JsonRunStore(stage / "state-v3.json").snapshot()
    destination = root / ".runs" / run_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise LifecycleConflict(f"generation already exists: {destination}")
    os.replace(stage, destination)
    return destination


@contextmanager
def _selector_lock(root: Path) -> Iterator[None]:
    lock_path = root / f"{ACTIVE_RECEIPT_NAME}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def read_active_receipt(analysis_root: str | Path) -> ActiveRunReceipt:
    path = Path(analysis_root).resolve() / ACTIVE_RECEIPT_NAME
    try:
        return ActiveRunReceipt.model_validate_json(path.read_bytes())
    except FileNotFoundError as exc:
        raise LifecycleIntegrityError(f"active receipt is missing: {path}") from exc
    except Exception as exc:
        raise LifecycleIntegrityError(f"active receipt is invalid: {exc}") from exc


def active_receipt_hash(analysis_root: str | Path) -> str:
    path = Path(analysis_root).resolve() / ACTIVE_RECEIPT_NAME
    return _sha_path(path) if path.exists() else ""


def promote_active_receipt(
    analysis_root: str | Path,
    receipt: ActiveRunReceipt,
    *,
    expected_prior_hash: str,
    expected_generation: int,
) -> ActiveRunReceipt:
    """Atomically select a complete generation under receipt hash/generation CAS."""

    root = Path(analysis_root).resolve()
    receipt_path = root / ACTIVE_RECEIPT_NAME
    with _selector_lock(root):
        current_hash = _sha_path(receipt_path) if receipt_path.exists() else ""
        current_generation = (
            read_active_receipt(root).activation_generation
            if receipt_path.exists()
            else 0
        )
        if (
            current_hash != expected_prior_hash
            or current_generation != expected_generation
            or receipt.prior_receipt_sha256 != expected_prior_hash
            or receipt.activation_generation != expected_generation + 1
        ):
            raise LifecycleConflict(
                "selector compare-and-swap conflict; reread active receipt and retry"
            )
        generation = root / receipt.generation_path
        if not generation.is_dir():
            raise LifecycleIntegrityError("selected generation does not exist")
        payload = _receipt_bytes(receipt)
        history_path = generation / GENERATION_RECEIPT_NAME
        if history_path.exists() and history_path.read_bytes() != payload:
            raise LifecycleIntegrityError("generation receipt is not immutable")
        if not history_path.exists():
            _atomic_replace(history_path, payload)
        _atomic_replace(receipt_path, payload)
    return receipt


def _snapshot_with_recovery(state_path: Path) -> RunSnapshot:
    store = JsonRunStore(state_path)
    try:
        return store.snapshot()
    except RecoveryError:
        return store.recover()


def _validate_snapshot_linkage(
    receipt: ActiveRunReceipt,
    snapshot: RunSnapshot,
    *,
    now: datetime,
    require_unexpired_routes: bool,
) -> None:
    if snapshot.run_id != receipt.run_id:
        raise LifecycleIntegrityError("active V3 run id does not match receipt")
    if snapshot.revisions.source != receipt.source_revision:
        raise LifecycleIntegrityError("active V3 source revision does not match receipt")
    legacy = snapshot.legacy_submission
    if legacy is None:
        raise LifecycleIntegrityError("active V3 lacks typed legacy submission seed")
    seed = LegacySubmissionSeed(
        task_ids=tuple(task.task_id for task in legacy.tasks),
        source_file_count=legacy.projection_metadata.source_file_count,
    )
    if legacy_seed_sha256(seed) != receipt.legacy_seed_sha256:
        raise LifecycleIntegrityError("typed legacy seed hash mismatch")
    expected_routes = {
        "submit_analysis": (
            "capability:route-parent:submit_analysis",
            "orchestrator/legacy-mcp/submit_analysis",
        ),
        "doc_operation:update_index": (
            "capability:route-parent:doc_operation:update_index",
            "orchestrator/legacy-mcp/doc_operation:update_index",
        ),
    }
    for key in receipt.route_keys:
        target, actor = expected_routes[key]
        matches = tuple(
            lease
            for lease in snapshot.leases
            if lease.target == target and lease.actor == actor
        )
        if len(matches) != 1:
            raise LifecycleIntegrityError(f"active V3 lacks exact route parent: {key}")
        if require_unexpired_routes and matches[0].expires_at <= now:
            raise LifecycleCacheMiss(f"active V3 route parent expired: {key}")


def validate_active_receipt(
    analysis_root: str | Path,
    receipt: ActiveRunReceipt,
    *,
    expected_repo_root: str | Path | None = None,
    expected_input_fingerprint: str | None = None,
    require_fresh_source: bool = False,
    require_unexpired_routes: bool = False,
    require_generation_receipt: bool = True,
    now: datetime | None = None,
) -> ActiveRunSelection:
    """Validate every locator/integrity link without inventing domain truth."""

    root = Path(analysis_root).resolve()
    instant = now or datetime.now(UTC)
    if expected_repo_root is not None and Path(receipt.repo_root) != Path(
        expected_repo_root
    ).resolve():
        raise LifecycleIntegrityError("active receipt repository root mismatch")
    if (
        expected_input_fingerprint is not None
        and receipt.analysis_input_fingerprint != expected_input_fingerprint
    ):
        raise LifecycleCacheMiss("analysis input fingerprint mismatch")
    v2_path = root / "state.json"
    if not v2_path.is_file() or _sha_path(v2_path) != receipt.v2_sha256:
        raise LifecycleIntegrityError("immutable V2 hash mismatch")
    generation = (root / receipt.generation_path).resolve()
    state_path = (root / receipt.state_path).resolve()
    if generation.parent != root / ".runs" or state_path.parent != generation:
        raise LifecycleIntegrityError("active receipt path escapes the generation root")
    history_path = generation / GENERATION_RECEIPT_NAME
    if require_generation_receipt and (
        not history_path.is_file() or history_path.read_bytes() != _receipt_bytes(receipt)
    ):
        raise LifecycleIntegrityError("active receipt does not match generation history")
    for entry in receipt.artifacts:
        artifact = generation / entry.path
        if not artifact.is_file():
            raise LifecycleIntegrityError(f"manifest artifact is missing: {entry.path}")
        if _sha_path(artifact) != entry.sha256:
            raise LifecycleIntegrityError(f"manifest hash mismatch: {entry.path}")
    snapshot = _snapshot_with_recovery(state_path)
    _validate_snapshot_linkage(
        receipt,
        snapshot,
        now=instant,
        require_unexpired_routes=require_unexpired_routes,
    )
    if Path(snapshot.repo_root).resolve() != Path(receipt.repo_root):
        raise LifecycleIntegrityError("active V3 repository root mismatch")
    if require_fresh_source:
        policy = snapshot.metadata.get("source_policy")
        if not policy:
            raise LifecycleIntegrityError("active V3 lacks frozen source policy")
        live = enumerate_source_universe(
            snapshot.repo_root,
            requested_languages=(),
            frozen_policy=policy,
        )
        if live.source_revision != receipt.source_revision:
            raise LifecycleCacheMiss("active source revision is stale")
    return ActiveRunSelection(
        receipt=receipt,
        analysis_root=root,
        generation_path=generation,
        state_path=state_path,
        snapshot=snapshot,
    )


def resolve_active_run(
    analysis_root: str | Path,
    **validation: object,
) -> ActiveRunSelection:
    root = Path(analysis_root).resolve()
    receipt = read_active_receipt(root)
    selected = validate_active_receipt(root, receipt, **validation)
    if receipt_sha256(receipt) != active_receipt_hash(root):
        raise LifecycleConflict("active selector changed during validation; retry")
    return selected


def prior_receipt(receipt: ActiveRunReceipt, analysis_root: str | Path) -> ActiveRunReceipt:
    """Load the hash-linked immediate predecessor for explicit rollback only."""

    if not receipt.prior_receipt_sha256:
        raise LifecycleIntegrityError("active receipt has no prior generation")
    root = Path(analysis_root).resolve()
    candidates = tuple((root / ".runs").glob(f"*/{GENERATION_RECEIPT_NAME}"))
    matches = tuple(path for path in candidates if _sha_path(path) == receipt.prior_receipt_sha256)
    if len(matches) != 1:
        raise LifecycleIntegrityError("prior active receipt is not uniquely hash-linked")
    return ActiveRunReceipt.model_validate_json(matches[0].read_bytes())


def recover_interrupted_initial_activation(
    analysis_root: str | Path,
    *,
    expected_repo_root: str | Path,
    expected_input_fingerprint: str,
) -> ActiveRunSelection:
    """Idempotently finish the sole exact-linked initial generation activation.

    This narrow recovery is only valid before any selector history exists.  It
    never chooses among generations and therefore cannot become an mtime/name
    based second selector.
    """

    root = Path(analysis_root).resolve()
    if (root / ACTIVE_RECEIPT_NAME).exists():
        raise LifecycleIntegrityError("active receipt already exists")
    runs_root = root / ".runs"
    generations = (
        tuple(path for path in runs_root.iterdir() if path.is_dir())
        if runs_root.is_dir()
        else ()
    )
    if len(generations) != 1:
        raise LifecycleIntegrityError(
            "selector is missing and interrupted generation is not unique"
        )
    generation = generations[0]
    state_path = generation / "state-v3.json"
    snapshot = _snapshot_with_recovery(state_path)
    if generation.name != snapshot.run_id:
        raise LifecycleIntegrityError("interrupted generation directory/run id mismatch")
    legacy = snapshot.legacy_submission
    if legacy is None:
        raise LifecycleIntegrityError("interrupted generation lacks legacy seed")
    expected_tasks = tuple(task.task_id for task in legacy.tasks)
    if any((root / name).exists() for name in REQUIRED_ARTIFACTS):
        raise LifecycleIntegrityError(
            "interrupted activation has unrelated root analysis artifacts"
        )
    manifest = artifact_manifest(generation)
    seed = LegacySubmissionSeed(
        task_ids=expected_tasks,
        source_file_count=legacy.projection_metadata.source_file_count,
    )
    provisional = ActiveRunReceipt(
        activation_generation=1,
        run_id=snapshot.run_id,
        generation_path=f".runs/{snapshot.run_id}",
        state_path=f".runs/{snapshot.run_id}/state-v3.json",
        repo_root=str(Path(expected_repo_root).resolve()),
        analysis_input_fingerprint=expected_input_fingerprint,
        source_revision=snapshot.revisions.source,
        v2_sha256="0" * 64,
        artifacts=manifest,
        legacy_seed_sha256=legacy_seed_sha256(seed),
        route_keys=ROUTE_KEYS,
        prior_receipt_sha256="",
    )
    instant = datetime.now(UTC)
    _validate_snapshot_linkage(
        provisional,
        snapshot,
        now=instant,
        require_unexpired_routes=True,
    )
    if (
        Path(snapshot.repo_root).resolve() != Path(expected_repo_root).resolve()
        or snapshot.metadata.get("analysis_input_fingerprint")
        != expected_input_fingerprint
    ):
        raise LifecycleIntegrityError(
            "interrupted generation is not exactly linked to repository/input"
        )
    policy = snapshot.metadata.get("source_policy")
    if not policy:
        raise LifecycleIntegrityError("interrupted V3 lacks frozen source policy")
    live = enumerate_source_universe(
        snapshot.repo_root,
        requested_languages=(),
        frozen_policy=policy,
    )
    if live.source_revision != snapshot.revisions.source:
        raise LifecycleCacheMiss("interrupted generation source revision is stale")

    projection_path = generation / V2_RECOVERY_PROJECTION_NAME
    projection_sha = snapshot.metadata.get(V2_RECOVERY_PROJECTION_SHA_KEY)
    projection: dict[str, object] | None = None
    if projection_path.exists() or projection_sha is not None:
        try:
            raw_projection = projection_path.read_bytes()
            loaded = json.loads(raw_projection)
        except (OSError, json.JSONDecodeError) as exc:
            raise LifecycleIntegrityError(
                f"interrupted V2 recovery projection is invalid: {exc}"
            ) from exc
        if not isinstance(loaded, dict) or _sha_bytes(raw_projection) != projection_sha:
            raise LifecycleIntegrityError("interrupted V2 recovery projection hash mismatch")
        projection = loaded

    v2_path = root / "state.json"
    if not v2_path.exists() and projection is None:
        raise LifecycleIntegrityError("interrupted activation lacks durable V2 recovery input")
    if projection is not None:
        documentation = projection.get("documentation")
        tasks = projection.get("tasks")
        if (
            Path(str(projection.get("path", ""))).resolve()
            != Path(expected_repo_root).resolve()
            or projection.get("project_id") != snapshot.metadata.get("project_id")
            or not isinstance(tasks, dict)
            or tuple(tasks.keys()) != expected_tasks
            or not isinstance(documentation, dict)
            or Path(str(documentation.get("output_dir", ""))).resolve() != root
        ):
            raise LifecycleIntegrityError(
                "interrupted V2 recovery projection linkage mismatch"
            )
        try:
            write_v2_rollback_projection(v2_path, projection, snapshot=snapshot)
        except MigrationConflict as exc:
            raise LifecycleIntegrityError(
                f"interrupted activation V2 hash/link mismatch: {exc}"
            ) from exc
    try:
        v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LifecycleIntegrityError(f"interrupted activation V2 is invalid: {exc}") from exc
    v2_metadata = v2.get("metadata", {})
    if (
        Path(str(v2.get("path", ""))).resolve() != Path(expected_repo_root).resolve()
        or v2.get("project_id") != snapshot.metadata.get("project_id")
        or not isinstance(v2.get("tasks"), dict)
        or tuple(v2["tasks"].keys()) != expected_tasks
        or not isinstance(v2_metadata, dict)
        or v2_metadata.get("canonical_run_id") != snapshot.run_id
        or v2_metadata.get("canonical_source_revision") != snapshot.revisions.source
    ):
        raise LifecycleIntegrityError(
            "interrupted generation is not exactly linked to V2/project"
        )
    receipt = ActiveRunReceipt(
        activation_generation=1,
        run_id=snapshot.run_id,
        generation_path=f".runs/{snapshot.run_id}",
        state_path=f".runs/{snapshot.run_id}/state-v3.json",
        repo_root=str(Path(expected_repo_root).resolve()),
        analysis_input_fingerprint=expected_input_fingerprint,
        source_revision=snapshot.revisions.source,
        v2_sha256=_sha_path(v2_path),
        artifacts=manifest,
        legacy_seed_sha256=legacy_seed_sha256(seed),
        route_keys=ROUTE_KEYS,
        prior_receipt_sha256="",
    )
    validate_active_receipt(
        root,
        receipt,
        expected_repo_root=expected_repo_root,
        expected_input_fingerprint=expected_input_fingerprint,
        require_fresh_source=True,
        require_unexpired_routes=True,
        require_generation_receipt=False,
    )
    try:
        promote_active_receipt(
            root, receipt, expected_prior_hash="", expected_generation=0
        )
    except LifecycleConflict:
        selected = resolve_active_run(
            root,
            expected_repo_root=expected_repo_root,
            expected_input_fingerprint=expected_input_fingerprint,
            require_fresh_source=True,
            require_unexpired_routes=True,
        )
        if selected.receipt.run_id != snapshot.run_id:
            raise
    return resolve_active_run(
        root,
        expected_repo_root=expected_repo_root,
        expected_input_fingerprint=expected_input_fingerprint,
        require_fresh_source=True,
        require_unexpired_routes=True,
    )
