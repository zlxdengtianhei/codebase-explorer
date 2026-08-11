"""Side-by-side V2/V3 initialization and rollback tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.state.migrate_v2_v3 import (
    AmbiguousV2State,
    MigrationConflict,
    dry_run_v2_to_v3,
    initialize_v3_side_by_side,
    read_rollback_projection,
    write_v2_rollback_projection,
)
from src.state.models import RunSnapshot


FIXTURES = Path(__file__).parent / "fixtures" / "state" / "v2"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dry_run_never_writes_and_never_infers_completion(tmp_path: Path):
    v2 = tmp_path / "state.json"
    v2.write_bytes((FIXTURES / "valid_incomplete.json").read_bytes())
    before = _sha(v2)
    plan = dry_run_v2_to_v3(v2, repo_root=tmp_path / "repo")
    assert _sha(v2) == before
    assert not plan.v3_path.exists()
    assert plan.legacy_hash == before
    assert plan.canonical_terminal_truth_inferred is False
    assert plan.legacy_projection["tasks"]["task-1"]["status"] == "pending"


@pytest.mark.parametrize("fixture", ["corrupt.json", "ambiguous_complete.json"])
def test_corrupt_or_ambiguous_v2_fails_closed(tmp_path: Path, fixture: str):
    v2 = tmp_path / "state.json"
    v2.write_bytes((FIXTURES / fixture).read_bytes())
    before = v2.read_bytes()
    with pytest.raises(AmbiguousV2State):
        dry_run_v2_to_v3(v2, repo_root=tmp_path / "repo")
    assert v2.read_bytes() == before
    assert not (tmp_path / "state-v3.json").exists()


def test_side_by_side_initialization_preserves_v2_bytes_and_hash_links(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1", encoding="utf-8")
    v2 = tmp_path / "state.json"
    v2.write_bytes((FIXTURES / "valid_incomplete.json").read_bytes())
    before = v2.read_bytes()
    receipt = initialize_v3_side_by_side(v2, repo_root=repo, actor="orchestrator/migration")
    assert v2.read_bytes() == before
    assert receipt.v2_hash == hashlib.sha256(before).hexdigest()
    assert receipt.v3_path.exists()
    snapshot = RunSnapshot.model_validate_json(receipt.v3_path.read_bytes())
    assert snapshot.metadata["legacy_v2_hash"] == receipt.v2_hash
    assert receipt.v3_hash == _sha(receipt.v3_path)


def test_existing_v3_conflict_leaves_both_sides_unchanged(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    v2 = tmp_path / "state.json"
    v2.write_bytes((FIXTURES / "valid_incomplete.json").read_bytes())
    v3 = tmp_path / "state-v3.json"
    v3.write_text("unrelated", encoding="utf-8")
    before_v2, before_v3 = v2.read_bytes(), v3.read_bytes()
    with pytest.raises(MigrationConflict):
        initialize_v3_side_by_side(v2, repo_root=repo, actor="orchestrator/migration")
    assert v2.read_bytes() == before_v2
    assert v3.read_bytes() == before_v3


def test_v2_rollback_projection_is_create_once_and_hash_verified(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source_v2 = tmp_path / "source-state.json"
    source_v2.write_bytes((FIXTURES / "valid_incomplete.json").read_bytes())
    receipt = initialize_v3_side_by_side(
        source_v2, repo_root=repo, actor="orchestrator/migration"
    )
    snapshot = RunSnapshot.model_validate_json(receipt.v3_path.read_bytes())
    target = tmp_path / "rollback" / "state.json"
    projection = json.loads(source_v2.read_text(encoding="utf-8"))
    link = write_v2_rollback_projection(target, projection, snapshot=snapshot)
    original = target.read_bytes()
    same = write_v2_rollback_projection(target, projection, snapshot=snapshot)
    assert same == link
    assert target.read_bytes() == original
    loaded = read_rollback_projection(target, expected_hash=link.v2_hash)
    assert loaded["metadata"]["canonical_v3_hash"] == link.v3_hash


def test_v2_projection_mismatch_does_not_overwrite(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source_v2 = tmp_path / "source-state.json"
    source_v2.write_bytes((FIXTURES / "valid_incomplete.json").read_bytes())
    receipt = initialize_v3_side_by_side(
        source_v2, repo_root=repo, actor="orchestrator/migration"
    )
    snapshot = RunSnapshot.model_validate_json(receipt.v3_path.read_bytes())
    target = tmp_path / "state.json"
    target.write_text("do not overwrite", encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(MigrationConflict):
        write_v2_rollback_projection(target, {}, snapshot=snapshot)
    assert target.read_bytes() == before


def test_rollback_hash_mismatch_fails_closed(tmp_path: Path):
    target = tmp_path / "state.json"
    target.write_text('{"schema_version":"2.0"}', encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(MigrationConflict, match="hash"):
        read_rollback_projection(target, expected_hash="0" * 64)
    assert target.read_bytes() == before
