from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.state.json_store import JsonRunStore
from src.state.models import LegacySubmissionSeed
from src.state.run_lifecycle import (
    ACTIVE_RECEIPT_SCHEMA,
    REQUIRED_ARTIFACTS,
    ActiveRunReceipt,
    LifecycleConflict,
    LifecycleIntegrityError,
    analysis_input_fingerprint,
    artifact_manifest,
    promote_active_receipt,
    publish_generation,
    read_active_receipt,
    recover_interrupted_initial_activation,
    resolve_active_run,
    validate_active_receipt,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _begin_store(generation: Path, repo: Path, run_id: str = "run-a") -> JsonRunStore:
    store = JsonRunStore(generation / "state-v3.json")
    now = datetime(2030, 1, 1, tzinfo=UTC)
    bootstrap = store.issue_bootstrap_lease(
        run_id=run_id,
        actor="orchestrator/legacy-mcp/analyze_codebase",
        ttl=timedelta(hours=1),
        now=now,
    )
    store.begin_run(
        run_id=run_id,
        repo_root=repo,
        requested_languages=("python",),
        actor=bootstrap.actor,
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        route_keys=("submit_analysis", "doc_operation:update_index"),
        legacy_submission_seed=LegacySubmissionSeed(
            task_ids=("task-1",), source_file_count=1
        ),
        initial_metadata={"project_id": "project-a"},
        now=now,
    )
    return store


def _stage(root: Path, repo: Path, run_id: str = "run-a") -> Path:
    stage = root / ".staging" / run_id
    stage.mkdir(parents=True)
    for index, name in enumerate(REQUIRED_ARTIFACTS, start=1):
        (stage / name).write_text(json.dumps({"index": index}) + "\n")
    _begin_store(stage, repo, run_id)
    return stage


def _receipt(root: Path, repo: Path, generation: Path, run_id: str = "run-a") -> ActiveRunReceipt:
    state_path = generation / "state-v3.json"
    snapshot = JsonRunStore(state_path).snapshot()
    seed = LegacySubmissionSeed(task_ids=("task-1",), source_file_count=1)
    return ActiveRunReceipt(
        schema_id=ACTIVE_RECEIPT_SCHEMA,
        activation_generation=1,
        run_id=run_id,
        generation_path=f".runs/{run_id}",
        state_path=f".runs/{run_id}/state-v3.json",
        repo_root=str(repo.resolve()),
        analysis_input_fingerprint=analysis_input_fingerprint(
            languages=("python",), exclude_paths=(), include_tests=False
        ),
        source_revision=snapshot.revisions.source,
        v2_sha256=_sha(root / "state.json"),
        artifacts=artifact_manifest(generation),
        legacy_seed_sha256=hashlib.sha256(
            seed.model_dump_json().encode("utf-8")
        ).hexdigest(),
        route_keys=("submit_analysis", "doc_operation:update_index"),
        prior_receipt_sha256="",
    )


def test_receipt_is_typed_locator_without_domain_truth(tmp_path: Path) -> None:
    root = tmp_path / "analysis"
    repo = tmp_path / "repo"
    root.mkdir()
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    (root / "state.json").write_text('{"project_id":"project-a"}\n')
    stage = _stage(root, repo)
    generation = publish_generation(root, stage, "run-a")

    receipt = _receipt(root, repo, generation)
    payload = receipt.model_dump(mode="json")

    assert receipt.schema_id == "cbe-active-run-1"
    assert tuple(item.path for item in receipt.artifacts) == REQUIRED_ARTIFACTS
    assert not ({"tasks", "sources", "artifacts_records", "store_revision"} & payload.keys())


def test_selector_compare_and_swap_has_one_winner(tmp_path: Path) -> None:
    root = tmp_path / "analysis"
    repo = tmp_path / "repo"
    root.mkdir()
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    (root / "state.json").write_text('{"project_id":"project-a"}\n')
    generation = publish_generation(root, _stage(root, repo), "run-a")
    first = _receipt(root, repo, generation)

    promoted = promote_active_receipt(
        root, first, expected_prior_hash="", expected_generation=0
    )
    assert promoted == first
    assert read_active_receipt(root) == first

    loser = first.model_copy(update={"run_id": "run-b", "activation_generation": 2})
    with pytest.raises(LifecycleConflict, match="selector compare-and-swap"):
        promote_active_receipt(
            root, loser, expected_prior_hash="", expected_generation=0
        )
    assert read_active_receipt(root) == first


def test_validation_rejects_manifest_corruption_without_selecting_orphan(
    tmp_path: Path,
) -> None:
    root = tmp_path / "analysis"
    repo = tmp_path / "repo"
    root.mkdir()
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    (root / "state.json").write_text('{"project_id":"project-a"}\n')
    generation = publish_generation(root, _stage(root, repo), "run-a")
    receipt = _receipt(root, repo, generation)
    promote_active_receipt(root, receipt, expected_prior_hash="", expected_generation=0)

    orphan = root / ".runs" / "run-orphan"
    orphan.mkdir(parents=True)
    (orphan / "state-v3.json").write_text("{}")
    (generation / REQUIRED_ARTIFACTS[0]).write_text("corrupt\n")

    with pytest.raises(LifecycleIntegrityError, match="manifest hash mismatch"):
        validate_active_receipt(root, receipt, now=datetime(2030, 1, 1, tzinfo=UTC))
    with pytest.raises(LifecycleIntegrityError):
        resolve_active_run(root, now=datetime(2030, 1, 1, tzinfo=UTC))
    assert read_active_receipt(root).run_id == "run-a"


def test_analysis_fingerprint_is_order_stable_and_input_sensitive() -> None:
    first = analysis_input_fingerprint(
        languages=("typescript", "python"),
        exclude_paths=("vendor", "generated"),
        include_tests=False,
    )
    reordered = analysis_input_fingerprint(
        languages=("python", "typescript"),
        exclude_paths=("generated", "vendor"),
        include_tests=False,
    )
    changed = analysis_input_fingerprint(
        languages=("python", "typescript"),
        exclude_paths=("generated", "vendor"),
        include_tests=True,
    )

    assert first == reordered
    assert changed != first


def test_initial_recovery_rejects_zero_candidates_without_writes(tmp_path: Path) -> None:
    root = tmp_path / "analysis"
    repo = tmp_path / "repo"
    (root / ".runs").mkdir(parents=True)
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    before = tuple(root.rglob("*"))

    with pytest.raises(LifecycleIntegrityError, match="not unique"):
        recover_interrupted_initial_activation(
            root,
            expected_repo_root=repo,
            expected_input_fingerprint=analysis_input_fingerprint(
                languages=("python",), exclude_paths=(), include_tests=False
            ),
        )
    assert tuple(root.rglob("*")) == before
