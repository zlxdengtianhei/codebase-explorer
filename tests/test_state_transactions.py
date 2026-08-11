"""Transactional, lease, CAS, and recovery tests for JSON V3 RunStore."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest

from src.ir.models import SourceUnitState
from src.parser.backend import (
    BackendHealth,
    BackendStatus,
    FailureCode,
    PythonAstBackend,
    SyntaxArtifact,
    TypedFailure,
)
from src.state.json_store import (
    ArtifactHashMismatch,
    JsonRunStore,
    LegacySubmissionRejected,
    LeaseRejected,
    RecoveryError,
    RevisionConflict,
)
from src.state import json_store as store_module
from src.state import models as state_models
from src.state.models import ArtifactRecord, RunSnapshot
from src.state.universe import SourceOutcome, enumerate_source_universe


NOW = datetime(2026, 8, 11, 8, 0, tzinfo=UTC)
SUBMIT_ROUTE = "submit_analysis"
UPDATE_ROUTE = "doc_operation:update_index"
SUBMIT_ACTOR = "orchestrator/legacy-mcp/submit_analysis"
UPDATE_ACTOR = "orchestrator/legacy-mcp/doc_operation:update_index"
SUBMIT_CAPABILITY = "capability:route-parent:submit_analysis"
UPDATE_CAPABILITY = "capability:route-parent:doc_operation:update_index"


def _begin(
    store: JsonRunStore, repo: Path, *, exclude_globs: tuple[str, ...] = ()
):
    lease = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    return store.begin_run(
        run_id="run-1",
        repo_root=repo,
        requested_languages=("python",),
        actor="orchestrator/main",
        lease_id=lease.lease_id,
        expected_revision=0,
        exclude_globs=exclude_globs,
        now=NOW,
    )


def _source_fixture(repo: Path) -> dict[str, SourceOutcome]:
    for name, content in {
        "indexed.py": "x = 1\n",
        "parse.py": "def broken(:\n",
        "unavailable.py": "x = 2\n",
        "notes.md": "notes\n",
        "skip.py": "x = 3\n",
    }.items():
        (repo / name).write_text(content, encoding="utf-8")
    enumeration = enumerate_source_universe(
        repo,
        requested_languages=("python",),
        exclude_globs=("skip.py",),
    )
    indexed_source = next(source for source in enumeration.sources if source.path == "indexed.py")
    artifact = PythonAstBackend(root=repo).parse(
        indexed_source.to_source_unit(enumeration.source_revision)
    )
    assert isinstance(artifact, SyntaxArtifact)
    healthy = BackendHealth(
        backend_id="python_ast",
        backend_version="3.13",
        status=BackendStatus.HEALTHY,
        supported_languages=("python",),
        semantic_tier="heuristic",
        toolchain_conditions=("python=3.13",),
        limitations=(),
    )
    unavailable = replace(
        healthy,
        status=BackendStatus.UNAVAILABLE,
        limitations=("toolchain offline",),
    )
    return {
        "indexed.py": SourceOutcome.syntax(artifact),
        "parse.py": SourceOutcome.failure(
            TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message="syntax error",
                backend_id="python_ast",
                language="python",
            ),
            health=healthy,
        ),
        "unavailable.py": SourceOutcome.failure(
            TypedFailure(
                code=FailureCode.BACKEND_UNAVAILABLE,
                message="backend unavailable",
                backend_id="python_ast",
                language="python",
                details=("receipt=p2-unavailable-1",),
            ),
            health=unavailable,
        ),
    }


def _route_begin(store: JsonRunStore, repo: Path):
    bootstrap = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    return store.begin_run(
        run_id="run-1",
        repo_root=repo,
        requested_languages=("python",),
        actor="orchestrator/main",
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        route_keys=(SUBMIT_ROUTE, UPDATE_ROUTE),
        now=NOW,
    )


def _persistent_bytes(store: JsonRunStore) -> tuple[bytes | None, bytes | None, bytes | None]:
    return tuple(
        path.read_bytes() if path.exists() else None
        for path in (store.path, store.backup_path, store.backup_hash_path)
    )  # type: ignore[return-value]


def test_route_parents_are_atomic_persisted_and_returned_read_only(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)

    assert begun.snapshot.store_revision == 1
    assert tuple((lease.target, lease.actor) for lease in begun.snapshot.leases) == (
        ("*", "orchestrator/main"),
        (SUBMIT_CAPABILITY, SUBMIT_ACTOR),
        (UPDATE_CAPABILITY, UPDATE_ACTOR),
    )
    assert len({lease.lease_id for lease in begun.snapshot.leases}) == 3
    assert all(
        lease.expires_at == begun.orchestrator_lease.expires_at
        for lease in begun.snapshot.leases
    )
    assert tuple(begun.route_leases) == (SUBMIT_ROUTE, UPDATE_ROUTE)
    assert tuple(begun.route_leases.values()) == begun.snapshot.leases[1:]
    with pytest.raises(TypeError):
        begun.route_leases[SUBMIT_ROUTE] = begun.orchestrator_lease  # type: ignore[index]


@pytest.mark.parametrize(
    "route,actor,target,assignee",
    [
        (SUBMIT_ROUTE, SUBMIT_ACTOR, "legacy-task", None),
        (UPDATE_ROUTE, UPDATE_ACTOR, "index", UPDATE_ACTOR),
    ],
)
def test_each_route_parent_issues_only_its_actor_target_lease(
    tmp_path: Path, route: str, actor: str, target: str, assignee: str | None
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    result = store.lease_task(
        run_id="run-1",
        target=target,
        actor=actor,
        lease_id=begun.route_leases[route].lease_id,
        expected_revision=1,
        assignee=assignee,
        now=NOW,
    )
    assert result.snapshot.store_revision == 2
    assert result.lease.actor == actor
    assert result.lease.target == target


@pytest.mark.parametrize(
    "parent_route,caller,assignee",
    [
        (SUBMIT_ROUTE, UPDATE_ACTOR, None),
        (UPDATE_ROUTE, SUBMIT_ACTOR, None),
        (SUBMIT_ROUTE, SUBMIT_ACTOR, UPDATE_ACTOR),
        (UPDATE_ROUTE, UPDATE_ACTOR, SUBMIT_ACTOR),
    ],
)
def test_direct_and_delegated_cross_route_use_rejects_all_persistent_writes(
    tmp_path: Path, parent_route: str, caller: str, assignee: str | None
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    before = _persistent_bytes(store)
    with pytest.raises(LeaseRejected):
        store.lease_task(
            run_id="run-1",
            target="target",
            actor=caller,
            lease_id=begun.route_leases[parent_route].lease_id,
            expected_revision=1,
            assignee=assignee,
            now=NOW,
        )
    assert _persistent_bytes(store) == before


@pytest.mark.parametrize(
    "parent_route,actor",
    [(SUBMIT_ROUTE, SUBMIT_ACTOR), (UPDATE_ROUTE, UPDATE_ACTOR)],
)
@pytest.mark.parametrize(
    "reserved_target", ["*", SUBMIT_CAPABILITY, UPDATE_CAPABILITY]
)
def test_route_parent_cannot_issue_reserved_target_parent_scope_child(
    tmp_path: Path, parent_route: str, actor: str, reserved_target: str
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    before = _persistent_bytes(store)
    with pytest.raises(RevisionConflict):
        store.lease_task(
            run_id="run-1", target=reserved_target, actor=actor,
            lease_id=begun.route_leases[parent_route].lease_id,
            expected_revision=0, now=NOW,
        )
    assert _persistent_bytes(store) == before
    with pytest.raises(LeaseRejected, match="reserved"):
        store.lease_task(
            run_id="run-1", target=reserved_target, actor=actor,
            lease_id=begun.route_leases[parent_route].lease_id,
            expected_revision=1, now=NOW,
        )
    assert _persistent_bytes(store) == before


@pytest.mark.parametrize(
    "parent_route,actor,cross_actor",
    [
        (SUBMIT_ROUTE, SUBMIT_ACTOR, UPDATE_ACTOR),
        (UPDATE_ROUTE, UPDATE_ACTOR, SUBMIT_ACTOR),
    ],
)
def test_reserved_target_rejection_survives_reopen_and_recovery(
    tmp_path: Path, parent_route: str, actor: str, cross_actor: str
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    parent_id = begun.route_leases[parent_route].lease_id
    reopened = JsonRunStore(store.path)
    before = _persistent_bytes(reopened)
    with pytest.raises(LeaseRejected, match="reserved"):
        reopened.lease_task(
            run_id="run-1", target="*", actor=actor, assignee=actor,
            lease_id=parent_id, expected_revision=1, now=NOW,
        )
    assert _persistent_bytes(reopened) == before
    reopened.lease_task(
        run_id="run-1", target="ordinary-artifact", actor=actor,
        lease_id=parent_id, expected_revision=1, now=NOW,
    )
    reopened.path.write_bytes(b"corrupt")
    recovered = reopened.recover()
    assert recovered.store_revision == 1
    before = _persistent_bytes(reopened)
    with pytest.raises(LeaseRejected, match="reserved"):
        reopened.lease_task(
            run_id="run-1", target="*", actor=actor, assignee=cross_actor,
            lease_id=parent_id, expected_revision=1, now=NOW,
        )
    assert _persistent_bytes(reopened) == before


@pytest.mark.parametrize("route_keys", [("",), ("unknown",), (SUBMIT_ROUTE, SUBMIT_ROUTE)])
def test_invalid_route_keys_fail_before_create_and_bootstrap_remains_reusable(
    tmp_path: Path, route_keys: tuple[str, ...]
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    bootstrap = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    before = _persistent_bytes(store)
    with pytest.raises(ValueError, match="route"):
        store.begin_run(
            run_id="run-1", repo_root=repo, requested_languages=("python",),
            actor="orchestrator/main", lease_id=bootstrap.lease_id,
            expected_revision=0, route_keys=route_keys, now=NOW,
        )
    assert _persistent_bytes(store) == before
    retry = store.begin_run(
        run_id="run-1", repo_root=repo, requested_languages=("python",),
        actor="orchestrator/main", lease_id=bootstrap.lease_id,
        expected_revision=0, route_keys=(), now=NOW,
    )
    assert retry.snapshot.store_revision == 1


@pytest.mark.parametrize("defect", ["duplicate_target", "non_orchestrator", "actor_collision"])
def test_route_policy_defects_fail_before_create_and_do_not_consume_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
):
    import src.state.json_store as store_module

    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    bootstrap = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    original = store_module._ROUTE_PARENT_POLICY
    policy = dict(original)
    if defect == "duplicate_target":
        policy[UPDATE_ROUTE] = (SUBMIT_CAPABILITY, UPDATE_ACTOR)
    elif defect == "non_orchestrator":
        policy[UPDATE_ROUTE] = (UPDATE_CAPABILITY, "worker/update-index")
    else:
        policy[UPDATE_ROUTE] = (UPDATE_CAPABILITY, "orchestrator/main")
    monkeypatch.setattr(store_module, "_ROUTE_PARENT_POLICY", policy)
    before = _persistent_bytes(store)
    with pytest.raises(ValueError, match="route"):
        store.begin_run(
            run_id="run-1", repo_root=repo, requested_languages=("python",),
            actor="orchestrator/main", lease_id=bootstrap.lease_id,
            expected_revision=0, route_keys=(UPDATE_ROUTE,), now=NOW,
        )
    assert _persistent_bytes(store) == before
    monkeypatch.setattr(store_module, "_ROUTE_PARENT_POLICY", original)
    assert store.begin_run(
        run_id="run-1", repo_root=repo, requested_languages=("python",),
        actor="orchestrator/main", lease_id=bootstrap.lease_id,
        expected_revision=0, now=NOW,
    ).snapshot.store_revision == 1


def test_route_parent_stale_expired_wrong_run_and_nonparent_reject_before_write(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    submit_parent = begun.route_leases[SUBMIT_ROUTE]
    for kwargs, error in (
        ({"expected_revision": 0}, RevisionConflict),
        ({"run_id": "wrong-run"}, RevisionConflict),
        ({"now": NOW + timedelta(minutes=6)}, LeaseRejected),
    ):
        call = dict(
            run_id="run-1", target="legacy-task", actor=SUBMIT_ACTOR,
            lease_id=submit_parent.lease_id, expected_revision=1, now=NOW,
        )
        call.update(kwargs)
        before = _persistent_bytes(store)
        with pytest.raises(error):
            store.lease_task(**call)
        assert _persistent_bytes(store) == before
    child = store.lease_task(
        run_id="run-1", target="legacy-task", actor=SUBMIT_ACTOR,
        lease_id=submit_parent.lease_id, expected_revision=1, now=NOW,
    )
    before = _persistent_bytes(store)
    with pytest.raises(LeaseRejected):
        store.lease_task(
            run_id="run-1", target="nested", actor=SUBMIT_ACTOR,
            lease_id=child.lease.lease_id,
            expected_revision=2, now=NOW,
        )
    assert _persistent_bytes(store) == before


def test_route_classification_survives_reopen_and_hash_linked_recovery(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    reopened = JsonRunStore(store.path)
    loaded = reopened.snapshot()
    assert loaded.leases == begun.snapshot.leases
    before = _persistent_bytes(reopened)
    with pytest.raises(LeaseRejected):
        reopened.lease_task(
            run_id="run-1", target="legacy-task", actor=SUBMIT_ACTOR,
            assignee=UPDATE_ACTOR,
            lease_id=begun.route_leases[SUBMIT_ROUTE].lease_id,
            expected_revision=1, now=NOW,
        )
    assert _persistent_bytes(reopened) == before
    reopened.lease_task(
        run_id="run-1", target="legacy-task", actor=SUBMIT_ACTOR,
        lease_id=begun.route_leases[SUBMIT_ROUTE].lease_id,
        expected_revision=1, now=NOW,
    )
    reopened.path.write_bytes(b"corrupt")
    recovered = reopened.recover()
    assert recovered.store_revision == 1
    assert recovered.leases == begun.snapshot.leases
    before = _persistent_bytes(reopened)
    with pytest.raises(LeaseRejected):
        reopened.lease_task(
            run_id="run-1", target="legacy-task", actor=SUBMIT_ACTOR,
            assignee=UPDATE_ACTOR,
            lease_id=begun.route_leases[SUBMIT_ROUTE].lease_id,
            expected_revision=1, now=NOW,
        )
    assert _persistent_bytes(reopened) == before


def test_empty_route_profile_preserves_ordinary_cross_actor_delegation(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    assert begun.snapshot.store_revision == 1
    assert begun.snapshot.leases == (begun.orchestrator_lease,)
    assert begun.route_leases == {}
    delegated = store.lease_task(
        run_id="run-1", target="task", actor="orchestrator/main",
        assignee=SUBMIT_ACTOR, lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=1, now=NOW,
    )
    assert delegated.lease.actor == SUBMIT_ACTOR


def test_existing_model_rejects_duplicate_route_lease_ids_and_no_runtime_mint_api(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    begun = _route_begin(JsonRunStore(tmp_path / "state-v3.json"), repo)
    duplicate = begun.snapshot.leases[2].model_copy(
        update={"lease_id": begun.snapshot.leases[1].lease_id}
    )
    with pytest.raises(ValueError, match="lease ids"):
        RunSnapshot.model_validate(
            begun.snapshot.model_copy(
                update={"leases": begun.snapshot.leases[:2] + (duplicate,)}
            ).model_dump(mode="python")
        )
    assert not hasattr(JsonRunStore, "issue_route_lease")
    assert not hasattr(JsonRunStore, "mint_route_parent")
def test_v3_round_trip_and_distinct_revisions(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1", encoding="utf-8")
    store = JsonRunStore(tmp_path / "state-v3.json")
    result = _begin(store, repo)
    loaded = JsonRunStore(tmp_path / "state-v3.json").snapshot()
    assert loaded == result.snapshot
    assert loaded.schema_version == "3.0"
    assert loaded.revisions.source
    assert loaded.revisions.index == ""
    assert loaded.revisions.document == ""
    assert loaded.revisions.verification == ""


def test_fresh_store_source_outcome_to_legacy_artifact_bridge(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outcomes = _source_fixture(repo)
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo, exclude_globs=("skip.py",))

    terminal = store.commit_source_outcomes(
        run_id="run-1",
        actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision,
        expected_source_revision=begun.snapshot.revisions.source,
        outcomes=outcomes,
        now=NOW,
    )

    assert terminal.store_revision == begun.snapshot.store_revision + 1
    assert SourceUnitState.DISCOVERED not in {source.state for source in terminal.sources}
    counts = {
        state: sum(source.state is state for source in terminal.sources)
        for state in (
            SourceUnitState.INDEXED,
            SourceUnitState.PARSE_ERROR,
            SourceUnitState.UNSUPPORTED,
            SourceUnitState.UNAVAILABLE,
            SourceUnitState.EXCLUDED,
        )
    }
    assert counts == {state: 1 for state in counts}
    unavailable = next(
        source for source in terminal.sources if source.state is SourceUnitState.UNAVAILABLE
    )
    assert unavailable.provenance.failure_code == FailureCode.BACKEND_UNAVAILABLE.value
    assert unavailable.provenance.backend_id == "python_ast"
    assert unavailable.provenance.backend_version == "3.13"
    assert unavailable.provenance.toolchain_conditions == ("python=3.13",)
    assert unavailable.provenance.evidence == ("receipt=p2-unavailable-1",)

    leased = store.lease_task(
        run_id="run-1",
        target="legacy-task",
        actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=terminal.store_revision,
        assignee="orchestrator/legacy-mcp/submit_analysis",
        now=NOW,
    )
    payload = b"legacy analysis"
    submitted = store.submit_artifact(
        run_id="run-1",
        target="legacy-task",
        actor="orchestrator/legacy-mcp/submit_analysis",
        producer="legacy-mcp/submit_analysis",
        lease_id=leased.lease.lease_id,
        expected_revision=leased.snapshot.store_revision,
        artifact_bytes=payload,
        artifact_hash=hashlib.sha256(payload).hexdigest(),
        now=NOW,
    )
    artifact = submitted.artifacts[-1]
    assert artifact.actor == "orchestrator/legacy-mcp/submit_analysis"
    assert artifact.producer == "legacy-mcp/submit_analysis"
    assert begun.snapshot.store_revision < terminal.store_revision < leased.snapshot.store_revision
    assert leased.snapshot.store_revision < submitted.store_revision


@pytest.mark.parametrize(
    "case,expected_error",
    [
        ("missing", ValueError),
        ("extra", ValueError),
        ("alias", ValueError),
        ("stale_store", RevisionConflict),
        ("stale_source", RevisionConflict),
        ("wrong_actor", ValueError),
        ("wrong_target", LeaseRejected),
        ("expired", LeaseRejected),
        ("live_mutation", RevisionConflict),
        ("provenance_mismatch", ValueError),
    ],
)
def test_source_outcome_controls_reject_before_bytes_change(
    tmp_path: Path, case: str, expected_error: type[Exception]
):
    repo = tmp_path / "repo"
    repo.mkdir()
    outcomes = _source_fixture(repo)
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo, exclude_globs=("skip.py",))
    actor = "orchestrator/main"
    lease_id = begun.orchestrator_lease.lease_id
    expected_revision = begun.snapshot.store_revision
    expected_source_revision = begun.snapshot.revisions.source
    now = NOW

    if case == "missing":
        outcomes.pop("parse.py")
    elif case == "extra":
        outcomes["missing.py"] = outcomes["indexed.py"]
    elif case == "alias":
        outcomes["pkg/../indexed.py"] = outcomes.pop("indexed.py")
    elif case == "stale_store":
        expected_revision -= 1
    elif case == "stale_source":
        expected_source_revision = "rev_stale"
    elif case == "wrong_actor":
        actor = "legacy-mcp/submit_analysis"
    elif case == "wrong_target":
        leased = store.lease_task(
            run_id="run-1",
            target="wrong-target",
            actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision,
            assignee="orchestrator/main",
            now=NOW,
        )
        lease_id = leased.lease.lease_id
        expected_revision = leased.snapshot.store_revision
    elif case == "expired":
        now = NOW + timedelta(minutes=6)
    elif case == "live_mutation":
        (repo / "indexed.py").write_text("x = 99\n", encoding="utf-8")
    elif case == "provenance_mismatch":
        enumeration = enumerate_source_universe(
            repo,
            requested_languages=("python",),
            exclude_globs=("skip.py",),
        )
        indexed = next(source for source in enumeration.sources if source.path == "indexed.py")
        artifact = PythonAstBackend(root=repo).parse(
            indexed.to_source_unit("rev_" + "0" * 64)
        )
        assert isinstance(artifact, SyntaxArtifact)
        outcomes["indexed.py"] = SourceOutcome.syntax(artifact)

    before = store.path.read_bytes()
    with pytest.raises(expected_error):
        store.commit_source_outcomes(
            run_id="run-1",
            actor=actor,
            lease_id=lease_id,
            expected_revision=expected_revision,
            expected_source_revision=expected_source_revision,
            outcomes=outcomes,
            now=now,
        )
    assert store.path.read_bytes() == before


def test_source_outcomes_can_only_be_committed_once(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outcomes = _source_fixture(repo)
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo, exclude_globs=("skip.py",))
    terminal = store.commit_source_outcomes(
        run_id="run-1",
        actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision,
        expected_source_revision=begun.snapshot.revisions.source,
        outcomes=outcomes,
        now=NOW,
    )
    before = store.path.read_bytes()
    with pytest.raises(RevisionConflict, match="already committed"):
        store.commit_source_outcomes(
            run_id="run-1",
            actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=terminal.store_revision,
            expected_source_revision=terminal.revisions.source,
            outcomes=outcomes,
            now=NOW,
        )
    assert store.path.read_bytes() == before


@pytest.mark.parametrize(
    "actor",
    (
        "orchestrator/legacy-mcp/submit_analysis",
        "orchestrator/legacy-mcp/doc_operation:update_index",
    ),
)
def test_frozen_legacy_orchestrator_identities_are_authorized(
    tmp_path: Path, actor: str
):
    store = JsonRunStore(tmp_path / "state-v3.json")
    lease = store.issue_bootstrap_lease(
        run_id="run-1", actor=actor, ttl=timedelta(minutes=1), now=NOW
    )
    assert lease.actor == actor


def test_artifact_actor_and_logical_producer_are_distinct_required_identities():
    record = ArtifactRecord(
        target="legacy-task",
        actor="orchestrator/legacy-mcp/submit_analysis",
        producer="legacy-mcp/submit_analysis",
        content_hash="0" * 64,
        revision_kind="document",
        accepted_at=NOW,
    )
    assert record.actor != record.producer
    with pytest.raises(ValueError, match="producer"):
        ArtifactRecord(
            target="legacy-task",
            actor="orchestrator/legacy-mcp/submit_analysis",
            producer="orchestrator/legacy-mcp/submit_analysis",
            content_hash="0" * 64,
            revision_kind="document",
            accepted_at=NOW,
        )
    with pytest.raises(ValueError, match="actor"):
        ArtifactRecord(
            target="legacy-task",
            actor="legacy-mcp/submit_analysis",
            producer="legacy-mcp/submit_analysis",
            content_hash="0" * 64,
            revision_kind="document",
            accepted_at=NOW,
        )


def test_actor_producer_confusion_rejects_before_artifact_bytes_change(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    leased = store.lease_task(
        run_id="run-1",
        target="legacy-task",
        actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision,
        assignee="orchestrator/legacy-mcp/submit_analysis",
        now=NOW,
    )
    payload = b"artifact"
    before = store.path.read_bytes()
    with pytest.raises(LegacySubmissionRejected, match="producer"):
        store.submit_artifact(
            run_id="run-1",
            target="legacy-task",
            actor="orchestrator/legacy-mcp/submit_analysis",
            producer="orchestrator/legacy-mcp/submit_analysis",
            lease_id=leased.lease.lease_id,
            expected_revision=leased.snapshot.store_revision,
            artifact_bytes=payload,
            artifact_hash=hashlib.sha256(payload).hexdigest(),
            now=NOW,
        )
    assert store.path.read_bytes() == before
    with pytest.raises(ValueError, match="orchestrator"):
        store.submit_artifact(
            run_id="run-1",
            target="legacy-task",
            actor="legacy-mcp/submit_analysis",
            producer="legacy-mcp/submit_analysis",
            lease_id=leased.lease.lease_id,
            expected_revision=leased.snapshot.store_revision,
            artifact_bytes=payload,
            artifact_hash=hashlib.sha256(payload).hexdigest(),
            now=NOW,
        )
    assert store.path.read_bytes() == before


def test_snapshot_is_deeply_immutable(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _begin(JsonRunStore(tmp_path / "state-v3.json"), repo)
    snapshot = JsonRunStore(tmp_path / "state-v3.json").snapshot()
    with pytest.raises(Exception):
        snapshot.store_revision = 99
    with pytest.raises(TypeError):
        snapshot.metadata["x"] = "y"


def test_every_mutation_requires_orchestrator_actor_lease_and_expected_revision(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    with pytest.raises(ValueError, match="orchestrator"):
        store.lease_task(
            run_id="run-1", target="task-1", actor="worker/a",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision, now=NOW,
        )
    with pytest.raises(LeaseRejected):
        store.lease_task(
            run_id="run-1", target="task-1", actor="orchestrator/main",
            lease_id="missing", expected_revision=begun.snapshot.store_revision, now=NOW,
        )
    with pytest.raises(RevisionConflict):
        store.lease_task(
            run_id="run-1", target="task-1", actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=0, now=NOW,
        )


def test_target_actor_and_expiry_are_bound_before_write(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    leased = store.lease_task(
        run_id="run-1", target="task-1", actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision, now=NOW,
        assignee="orchestrator/task-1", ttl=timedelta(seconds=1),
    )
    before = store.path.read_bytes()
    digest = hashlib.sha256(b"artifact").hexdigest()
    for actor, target, now in (
        ("orchestrator/wrong", "task-1", NOW),
        ("orchestrator/task-1", "task-2", NOW),
        ("orchestrator/task-1", "task-1", NOW + timedelta(seconds=2)),
    ):
        with pytest.raises(LeaseRejected):
            store.submit_artifact(
                run_id="run-1", target=target, actor=actor,
                producer="worker/task-1",
                lease_id=leased.lease.lease_id,
                expected_revision=leased.snapshot.store_revision,
                artifact_bytes=b"artifact", artifact_hash=digest, now=now,
            )
        assert store.path.read_bytes() == before


def test_hash_mismatch_fails_before_write(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    leased = store.lease_task(
        run_id="run-1", target="task-1", actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision, now=NOW,
        assignee="orchestrator/task-1",
    )
    before = store.path.read_bytes()
    with pytest.raises(ArtifactHashMismatch):
        store.submit_artifact(
            run_id="run-1", target="task-1", actor="orchestrator/task-1",
            producer="worker/task-1",
            lease_id=leased.lease.lease_id,
            expected_revision=leased.snapshot.store_revision,
            artifact_bytes=b"actual", artifact_hash="0" * 64, now=NOW,
        )
    assert store.path.read_bytes() == before


def test_successful_mutations_are_monotonic_and_advance_only_target_revision(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    leased = store.lease_task(
        run_id="run-1", target="task-1", actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision, now=NOW,
        assignee="orchestrator/task-1",
    )
    payload = b"artifact"
    submitted = store.submit_artifact(
        run_id="run-1", target="task-1", actor="orchestrator/task-1",
        producer="worker/task-1",
        lease_id=leased.lease.lease_id,
        expected_revision=leased.snapshot.store_revision,
        artifact_bytes=payload, artifact_hash=hashlib.sha256(payload).hexdigest(),
        revision_kind="document", now=NOW,
    )
    assert begun.snapshot.store_revision < leased.snapshot.store_revision < submitted.store_revision
    assert submitted.revisions.source == begun.snapshot.revisions.source
    assert submitted.revisions.document
    assert submitted.revisions.index == ""


def test_verdict_and_terminal_transition_share_lease_cas_authority(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    leased = store.lease_task(
        run_id="run-1", target="verdict", actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision, now=NOW,
        assignee="orchestrator/verdict",
    )
    verdict = b'{"verdict":"pass"}'
    recorded = store.record_verdict(
        run_id="run-1", target="verdict", actor="orchestrator/verdict",
        producer="verifier/verdict",
        lease_id=leased.lease.lease_id,
        expected_revision=leased.snapshot.store_revision,
        artifact_bytes=verdict, artifact_hash=hashlib.sha256(verdict).hexdigest(),
        now=NOW,
    )
    terminal = store.transition_run(
        run_id="run-1", actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=recorded.store_revision,
        run_state="verified_full", now=NOW,
    )
    assert recorded.revisions.verification
    assert terminal.run_state == "verified_full"
    assert store.snapshot_for_verifier() == terminal


def test_verified_transition_without_verdict_fails_before_write(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    before = store.path.read_bytes()
    with pytest.raises(RevisionConflict, match="verification revision"):
        store.transition_run(
            run_id="run-1", actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision,
            run_state="verified_full", now=NOW,
        )
    assert store.path.read_bytes() == before


def _legacy_seed(
    task_ids: tuple[str, ...] = ("task-a", "task-b"), source_file_count: int = 2
):
    return state_models.LegacySubmissionSeed(
        task_ids=task_ids, source_file_count=source_file_count
    )


def _legacy_begin(
    store: JsonRunStore,
    repo: Path,
    *,
    task_ids: tuple[str, ...] = ("task-a", "task-b"),
    source_file_count: int = 2,
):
    bootstrap = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    return store.begin_run(
        run_id="run-1",
        repo_root=repo,
        requested_languages=("python",),
        actor="orchestrator/main",
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        route_keys=(SUBMIT_ROUTE, UPDATE_ROUTE),
        legacy_submission_seed=_legacy_seed(task_ids, source_file_count),
        now=NOW,
    )


def _legacy_child(
    store: JsonRunStore, begun, task_id: str, *, expected_revision: int | None = None
):
    return store.lease_task(
        run_id="run-1",
        target=task_id,
        actor=SUBMIT_ACTOR,
        lease_id=begun.route_leases[SUBMIT_ROUTE].lease_id,
        expected_revision=(
            store.snapshot().store_revision
            if expected_revision is None
            else expected_revision
        ),
        now=NOW,
    )


def _legacy_submit(
    store: JsonRunStore,
    child,
    task_id: str,
    *,
    payload: bytes = b'{"receipt":"task"}',
    details_written: int = 1,
    snippets_written: int = 2,
    source_files_covered: tuple[str, ...] = ("a.py",),
    expected_revision: int | None = None,
):
    return store.submit_legacy_analysis(
        run_id="run-1",
        task_id=task_id,
        actor=SUBMIT_ACTOR,
        producer="legacy-mcp/submit_analysis",
        lease_id=child.lease.lease_id,
        expected_revision=(
            child.snapshot.store_revision
            if expected_revision is None
            else expected_revision
        ),
        artifact_bytes=payload,
        artifact_hash=hashlib.sha256(payload).hexdigest(),
        details_written=details_written,
        snippets_written=snippets_written,
        source_files_covered=source_files_covered,
        now=NOW,
    )


@pytest.mark.parametrize(
    "seed_kwargs",
    [
        {"task_ids": ["task-a"], "source_file_count": 1},
        {"task_ids": ("",), "source_file_count": 1},
        {"task_ids": ("task-a", "task-a"), "source_file_count": 1},
        {"task_ids": ("task-a",), "source_file_count": -1},
        {"task_ids": ("task-a",), "source_file_count": True},
    ],
)
def test_legacy_submission_seed_rejects_malformed_values(seed_kwargs: dict[str, object]):
    with pytest.raises(ValueError):
        state_models.LegacySubmissionSeed(**seed_kwargs)


def test_legacy_seed_is_atomic_with_begin_and_preserves_order(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(
        store, repo, task_ids=("task-z", "task-a"), source_file_count=7
    )
    legacy = begun.snapshot.legacy_submission
    assert begun.snapshot.store_revision == 1
    assert tuple(legacy_task.task_id for legacy_task in legacy.tasks) == (
        "task-z",
        "task-a",
    )
    assert all(task.status == "pending" for task in legacy.tasks)
    assert legacy.projection_metadata.source_file_count == 7
    assert tuple(begun.route_leases) == (SUBMIT_ROUTE, UPDATE_ROUTE)
    assert JsonRunStore(store.path).snapshot() == begun.snapshot


def test_legacy_seed_failure_precedes_enumeration_and_bootstrap_is_reusable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    bootstrap = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    called = False

    def forbidden_enumeration(*args: object, **kwargs: object):
        nonlocal called
        called = True
        raise AssertionError("seed validation must precede enumeration")

    monkeypatch.setattr(store_module, "enumerate_source_universe", forbidden_enumeration)
    before = _persistent_bytes(store)
    with pytest.raises(ValueError):
        store.begin_run(
            run_id="run-1", repo_root=repo, requested_languages=("python",),
            actor="orchestrator/main", lease_id=bootstrap.lease_id,
            expected_revision=0,
            legacy_submission_seed={"task_ids": ["task-a"], "source_file_count": 1},
            now=NOW,
        )
    assert not called
    assert _persistent_bytes(store) == before

    monkeypatch.undo()
    result = store.begin_run(
        run_id="run-1", repo_root=repo, requested_languages=("python",),
        actor="orchestrator/main", lease_id=bootstrap.lease_id,
        expected_revision=0, legacy_submission_seed=_legacy_seed(("task-a",), 1), now=NOW,
    )
    assert result.snapshot.store_revision == 1


def test_legacy_submission_success_is_one_atomic_revision_and_exact_projection(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    before_sources = child.snapshot.sources
    before_source_revision = child.snapshot.revisions.source
    result = _legacy_submit(
        store,
        child,
        "task-a",
        details_written=3,
        snippets_written=4,
        source_files_covered=("a.py", "a.py", "/abs.py", ""),
    )
    task = result.snapshot.legacy_submission.tasks[0]
    assert result.snapshot.store_revision == child.snapshot.store_revision + 1
    assert result.artifact == result.snapshot.artifacts[-1]
    assert (task.status, task.artifact_hash, task.completed_at) == (
        "complete",
        result.artifact.content_hash,
        NOW,
    )
    assert (task.details_written, task.snippets_written) == (3, 4)
    assert result.projection.status == "success"
    assert result.projection.task_id == "task-a"
    assert result.projection.tasks_remaining == 1
    assert result.projection.progress_percent == 50.0
    assert result.projection.source_file_coverage_percent == 150.0
    assert result.projection.details_written == 3
    assert result.projection.snippets_written == 4
    assert result.projection.source_files_covered == ("a.py", "/abs.py", "")
    assert result.snapshot.sources == before_sources
    assert result.snapshot.revisions.source == before_source_revision
    assert result.snapshot.revisions.index == ""


def test_legacy_projection_accumulates_and_rebuilds_after_reopen_and_recovery(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo, source_file_count=2)
    first = _legacy_submit(
        store,
        _legacy_child(store, begun, "task-a"),
        "task-a",
        details_written=2,
        snippets_written=3,
        source_files_covered=("a.py", "alias.py"),
    )
    reopened = JsonRunStore(store.path)
    second_child = _legacy_child(reopened, begun, "task-b")
    second = _legacy_submit(
        reopened,
        second_child,
        "task-b",
        details_written=5,
        snippets_written=7,
        source_files_covered=("alias.py", "b.py"),
    )
    expected = second.projection
    assert expected.tasks_remaining == 0
    assert expected.progress_percent == 100.0
    assert expected.source_file_coverage_percent == 150.0
    assert (expected.details_written, expected.snippets_written) == (7, 10)
    assert expected.source_files_covered == ("a.py", "alias.py", "b.py")
    assert store_module.legacy_submission_projection(
        JsonRunStore(store.path).snapshot(), "task-b"
    ) == expected

    _legacy_child(reopened, begun, "later-audit")
    reopened.path.write_bytes(b"corrupt")
    recovered = reopened.recover()
    assert store_module.legacy_submission_projection(recovered, "task-b") == expected


@pytest.mark.parametrize("duplicate_payload", [b'{"receipt":"task"}', b"different"])
def test_duplicate_legacy_task_rejects_without_persistent_changes(
    tmp_path: Path, duplicate_payload: bytes
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    first_child = _legacy_child(store, begun, "task-a")
    _legacy_submit(store, first_child, "task-a")
    duplicate_child = _legacy_child(store, begun, "task-a")
    before = _persistent_bytes(store)
    rejected = getattr(store_module, "LegacySubmissionRejected", RuntimeError)
    with pytest.raises(rejected):
        _legacy_submit(store, duplicate_child, "task-a", payload=duplicate_payload)
    assert _persistent_bytes(store) == before


@pytest.mark.parametrize("task_id", ["unknown", "task-a"])
def test_legacy_task_state_checks_follow_cas_and_leave_bytes_unchanged(
    tmp_path: Path, task_id: str
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo) if task_id == "unknown" else _route_begin(store, repo)
    child = _legacy_child(store, begun, task_id)
    before = _persistent_bytes(store)
    with pytest.raises(RevisionConflict):
        _legacy_submit(store, child, task_id, expected_revision=0)
    assert _persistent_bytes(store) == before
    rejected = getattr(store_module, "LegacySubmissionRejected", RuntimeError)
    with pytest.raises(rejected):
        _legacy_submit(store, child, task_id)
    assert _persistent_bytes(store) == before


@pytest.mark.parametrize(
    "actor,producer,details,snippets,expected_error",
    [
        ("worker/submit", "legacy-mcp/submit_analysis", 0, 0, ValueError),
        ("orchestrator/main", "legacy-mcp/submit_analysis", 0, 0, LeaseRejected),
        (SUBMIT_ACTOR, "wrong-producer", 0, 0, RuntimeError),
        (SUBMIT_ACTOR, "legacy-mcp/submit_analysis", -1, 0, RuntimeError),
        (SUBMIT_ACTOR, "legacy-mcp/submit_analysis", 0, True, RuntimeError),
    ],
)
def test_legacy_pure_input_identity_and_counter_controls_precede_writes(
    tmp_path: Path,
    actor: str,
    producer: str,
    details: int,
    snippets: int,
    expected_error: type[Exception],
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    before = _persistent_bytes(store)
    if expected_error is RuntimeError:
        expected_error = getattr(store_module, "LegacySubmissionRejected", RuntimeError)
    payload = b"secret-artifact-bytes"
    with pytest.raises(expected_error) as caught:
        store.submit_legacy_analysis(
            run_id="run-1", task_id="task-a", actor=actor, producer=producer,
            lease_id=child.lease.lease_id,
            expected_revision=child.snapshot.store_revision,
            artifact_bytes=payload, artifact_hash=hashlib.sha256(payload).hexdigest(),
            details_written=details, snippets_written=snippets, now=NOW,
        )
    assert payload.decode() not in str(caught.value)
    assert _persistent_bytes(store) == before


@pytest.mark.parametrize(
    "case,expected_error",
    [
        ("hash", ArtifactHashMismatch),
        ("wrong_run", RevisionConflict),
        ("missing", LeaseRejected),
        ("wrong_target", LeaseRejected),
        ("expired", LeaseRejected),
        ("cross_route", LeaseRejected),
    ],
)
def test_legacy_hash_run_and_exact_lease_controls_leave_all_bytes_unchanged(
    tmp_path: Path, case: str, expected_error: type[Exception]
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    run_id = "run-1"
    task_id = "task-a"
    lease_id = child.lease.lease_id
    expected_revision = child.snapshot.store_revision
    now = NOW
    if case == "wrong_run":
        run_id = "wrong-run"
    elif case == "missing":
        lease_id = "missing"
    elif case == "wrong_target":
        task_id = "task-b"
    elif case == "expired":
        now = NOW + timedelta(minutes=6)
    elif case == "cross_route":
        cross = store.lease_task(
            run_id="run-1", target="task-a", actor=UPDATE_ACTOR,
            lease_id=begun.route_leases[UPDATE_ROUTE].lease_id,
            expected_revision=expected_revision, now=NOW,
        )
        lease_id = cross.lease.lease_id
        expected_revision = cross.snapshot.store_revision
    payload = b"secret-legacy-receipt"
    digest = "0" * 64 if case == "hash" else hashlib.sha256(payload).hexdigest()
    before = _persistent_bytes(store)
    with pytest.raises(expected_error) as caught:
        store.submit_legacy_analysis(
            run_id=run_id, task_id=task_id, actor=SUBMIT_ACTOR,
            producer="legacy-mcp/submit_analysis", lease_id=lease_id,
            expected_revision=expected_revision, artifact_bytes=payload,
            artifact_hash=digest, details_written=1, snippets_written=1,
            now=now,
        )
    assert payload.decode() not in str(caught.value)
    assert _persistent_bytes(store) == before


def test_recovered_away_legacy_child_handle_is_rejected_without_writes(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    store.path.write_bytes(b"corrupt")
    recovered = store.recover()
    assert recovered.store_revision == begun.snapshot.store_revision
    before = _persistent_bytes(store)
    with pytest.raises(LeaseRejected):
        _legacy_submit(
            store,
            child,
            "task-a",
            expected_revision=recovered.store_revision,
        )
    assert _persistent_bytes(store) == before


def test_seeded_generic_exact_submit_bypass_rejects_then_dedicated_retry_succeeds(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    payload = b"receipt"
    before = _persistent_bytes(store)
    rejected = getattr(store_module, "LegacySubmissionRejected", RuntimeError)
    with pytest.raises(rejected):
        store.submit_artifact(
            run_id="run-1", target="task-a", actor=SUBMIT_ACTOR,
            producer="legacy-mcp/submit_analysis", lease_id=child.lease.lease_id,
            expected_revision=child.snapshot.store_revision, artifact_bytes=payload,
            artifact_hash=hashlib.sha256(payload).hexdigest(), now=NOW,
        )
    assert _persistent_bytes(store) == before
    result = _legacy_submit(store, child, "task-a", payload=payload)
    assert result.snapshot.legacy_submission.tasks[0].status == "complete"


def test_seed_none_exact_submit_artifact_remains_reopen_and_recovery_compatible(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _route_begin(store, repo)
    child = _legacy_child(store, begun, "legacy-task")
    payload = b"old-compatible-artifact"
    submitted = store.submit_artifact(
        run_id="run-1", target="legacy-task", actor=SUBMIT_ACTOR,
        producer="legacy-mcp/submit_analysis", lease_id=child.lease.lease_id,
        expected_revision=child.snapshot.store_revision, artifact_bytes=payload,
        artifact_hash=hashlib.sha256(payload).hexdigest(), now=NOW,
    )
    assert submitted.legacy_submission is None
    assert JsonRunStore(store.path).snapshot() == submitted
    _legacy_child(store, begun, "later")
    store.path.write_bytes(b"corrupt")
    assert store.recover() == submitted


def test_exact_route_producers_and_update_index_generic_ingress(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    update_child = store.lease_task(
        run_id="run-1", target="index", actor=UPDATE_ACTOR,
        lease_id=begun.route_leases[UPDATE_ROUTE].lease_id,
        expected_revision=begun.snapshot.store_revision, now=NOW,
    )
    payload = b"# Index"
    before = _persistent_bytes(store)
    rejected = getattr(store_module, "LegacySubmissionRejected", RuntimeError)
    with pytest.raises(rejected):
        store.submit_artifact(
            run_id="run-1", target="index", actor=UPDATE_ACTOR,
            producer="wrong-producer", lease_id=update_child.lease.lease_id,
            expected_revision=update_child.snapshot.store_revision,
            artifact_bytes=payload, artifact_hash=hashlib.sha256(payload).hexdigest(),
            now=NOW,
        )
    assert _persistent_bytes(store) == before
    first = store.submit_artifact(
        run_id="run-1", target="index", actor=UPDATE_ACTOR,
        producer="legacy-mcp/doc_operation:update_index",
        lease_id=update_child.lease.lease_id,
        expected_revision=update_child.snapshot.store_revision,
        artifact_bytes=payload, artifact_hash=hashlib.sha256(payload).hexdigest(), now=NOW,
    )
    second_child = store.lease_task(
        run_id="run-1", target="index", actor=UPDATE_ACTOR,
        lease_id=begun.route_leases[UPDATE_ROUTE].lease_id,
        expected_revision=first.store_revision, now=NOW,
    )
    second = store.submit_artifact(
        run_id="run-1", target="index", actor=UPDATE_ACTOR,
        producer="legacy-mcp/doc_operation:update_index",
        lease_id=second_child.lease.lease_id,
        expected_revision=second_child.snapshot.store_revision,
        artifact_bytes=payload, artifact_hash=hashlib.sha256(payload).hexdigest(), now=NOW,
    )
    assert len([artifact for artifact in second.artifacts if artifact.target == "index"]) == 2
    assert all(task.status == "pending" for task in second.legacy_submission.tasks)


def test_legacy_model_cross_invariants_are_conditional_and_fail_closed(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    result = _legacy_submit(store, child, "task-a")
    payload = result.snapshot.model_dump(mode="python", round_trip=True)
    payload["legacy_submission"]["tasks"][0]["artifact_hash"] = "0" * 64
    with pytest.raises(ValueError):
        RunSnapshot.model_validate(payload)

    old_payload = result.snapshot.model_dump(mode="python", round_trip=True)
    old_payload.pop("legacy_submission")
    assert RunSnapshot.model_validate(old_payload).legacy_submission is None


def test_legacy_submit_calls_promote_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    original = store._promote
    calls: list[RunSnapshot] = []

    def counted(snapshot: RunSnapshot) -> None:
        calls.append(snapshot)
        original(snapshot)

    monkeypatch.setattr(store, "_promote", counted)
    result = _legacy_submit(store, child, "task-a")
    assert calls == [result.snapshot]


@pytest.mark.parametrize("failure_phase", ["before", "after"])
@pytest.mark.parametrize("failed_replace", [1, 2, 3])
def test_legacy_submit_replace_boundary_fault_restores_recoverable_before_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_replace: int,
    failure_phase: str,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _legacy_begin(store, repo)
    child = _legacy_child(store, begun, "task-a")
    before_snapshot = child.snapshot
    before_bytes = store.path.read_bytes()
    original = store._atomic_replace_bytes
    call_count = 0

    def interrupted(path: Path, payload: bytes) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == failed_replace and failure_phase == "before":
            raise OSError(f"simulated legacy promotion interruption {failed_replace}")
        original(path, payload)
        if call_count == failed_replace and failure_phase == "after":
            raise OSError(f"simulated legacy promotion interruption {failed_replace}")

    monkeypatch.setattr(store, "_atomic_replace_bytes", interrupted)
    with pytest.raises(OSError, match="simulated legacy promotion interruption"):
        _legacy_submit(store, child, "task-a")
    primary, backup, backup_hash = _persistent_bytes(store)
    expected_hash = hashlib.sha256(before_bytes).hexdigest().encode("ascii") + b"\n"
    assert (primary, backup, backup_hash) == (
        before_bytes,
        before_bytes,
        expected_hash,
    )
    reopened_store = JsonRunStore(store.path)
    reopened = reopened_store.snapshot()
    assert reopened == before_snapshot
    assert reopened.legacy_submission.tasks[0].status == "pending"
    assert not any(artifact.target == "task-a" for artifact in reopened.artifacts)
    projection = store_module.legacy_submission_projection(reopened, "task-a")
    assert (projection.tasks_remaining, projection.details_written, projection.snippets_written) == (
        2,
        0,
        0,
    )
    reopened_store.path.write_bytes(b"corrupt")
    recovered = reopened_store.recover()
    assert recovered == before_snapshot
    assert store_module.legacy_submission_projection(recovered, "task-a") == projection


@pytest.mark.parametrize("failure_phase", ["before", "after"])
@pytest.mark.parametrize("failed_replace", [1, 2, 3])
def test_first_promotion_fault_restores_absent_surfaces_and_bootstrap_is_reusable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_replace: int,
    failure_phase: str,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    bootstrap = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    original = store._atomic_replace_bytes
    call_count = 0

    def interrupted(path: Path, payload: bytes) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == failed_replace and failure_phase == "before":
            raise OSError(f"simulated first promotion interruption {failed_replace}")
        original(path, payload)
        if call_count == failed_replace and failure_phase == "after":
            raise OSError(f"simulated first promotion interruption {failed_replace}")

    monkeypatch.setattr(store, "_atomic_replace_bytes", interrupted)
    with pytest.raises(OSError, match="simulated first promotion interruption"):
        store.begin_run(
            run_id="run-1",
            repo_root=repo,
            requested_languages=("python",),
            actor="orchestrator/main",
            lease_id=bootstrap.lease_id,
            expected_revision=0,
            now=NOW,
        )
    assert _persistent_bytes(store) == (None, None, None)

    monkeypatch.setattr(store, "_atomic_replace_bytes", original)
    begun = store.begin_run(
        run_id="run-1",
        repo_root=repo,
        requested_languages=("python",),
        actor="orchestrator/main",
        lease_id=bootstrap.lease_id,
        expected_revision=0,
        now=NOW,
    )
    reopened = JsonRunStore(store.path)
    assert reopened.snapshot() == begun.snapshot
    reopened.path.write_bytes(b"corrupt")
    assert reopened.recover() == begun.snapshot


def test_concurrent_cas_has_exactly_one_winner(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def mutate(target: str) -> None:
        barrier.wait()
        try:
            store.lease_task(
                run_id="run-1", target=target, actor="orchestrator/main",
                lease_id=begun.orchestrator_lease.lease_id,
                expected_revision=begun.snapshot.store_revision, now=NOW,
                assignee=f"orchestrator/{target}",
            )
            outcomes.append("ok")
        except RevisionConflict:
            outcomes.append("conflict")

    threads = [threading.Thread(target=mutate, args=(f"task-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["conflict", "ok"]


def test_source_mutation_rejects_stale_source_revision(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "a.py"
    source.write_text("x = 1", encoding="utf-8")
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    source.write_text("x = 2", encoding="utf-8")
    before = store.path.read_bytes()
    with pytest.raises(RevisionConflict, match="source revision"):
        store.commit_index(
            run_id="run-1", actor="orchestrator/main",
            producer="indexer/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision,
            expected_source_revision=begun.snapshot.revisions.source,
            index_payload=b"index", now=NOW,
        )
    assert store.path.read_bytes() == before


def _single_indexed_outcome(repo: Path, source_revision: str) -> dict[str, SourceOutcome]:
    enumeration = enumerate_source_universe(repo, requested_languages=("python",))
    source = next(source for source in enumeration.sources if source.path == "a.py")
    artifact = PythonAstBackend(root=repo).parse(
        source.to_source_unit(source_revision)
    )
    assert isinstance(artifact, SyntaxArtifact)
    return {"a.py": SourceOutcome.syntax(artifact)}


def test_in_repo_product_outputs_do_not_change_revision_or_block_first_commit(
    tmp_path: Path,
):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    store = JsonRunStore(repo / ".codebase-analysis" / "state-v3.json")
    begun = _begin(store, repo)
    for name in (
        "01-metadata.json",
        "02-structure.json",
        "03-symbols.json",
        "04-graph.json",
        "05-cones.json",
        "06-tasks.json",
        "state.json",
    ):
        (repo / ".codebase-analysis" / name).write_text("{}\n", encoding="utf-8")
    docs = repo / ".codebase-docs" / "nested"
    docs.mkdir(parents=True)
    (docs / "x.md").write_text("generated\n", encoding="utf-8")

    terminal = store.commit_source_outcomes(
        run_id="run-1",
        actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision,
        expected_source_revision=begun.snapshot.revisions.source,
        outcomes=_single_indexed_outcome(repo, begun.snapshot.revisions.source),
        now=NOW,
    )

    assert [source.path for source in terminal.sources] == ["a.py"]
    assert terminal.sources[0].state is SourceUnitState.INDEXED


@pytest.mark.parametrize("mutation", ["content", "add", "delete", "rename"])
def test_frozen_policy_still_detects_real_source_mutations(tmp_path: Path, mutation: str):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    outcomes = _single_indexed_outcome(repo, begun.snapshot.revisions.source)
    if mutation == "content":
        source.write_text("x = 2\n", encoding="utf-8")
    elif mutation == "add":
        (repo / "b.py").write_text("y = 1\n", encoding="utf-8")
    elif mutation == "delete":
        source.unlink()
    else:
        source.rename(repo / "renamed.py")
    before = store.path.read_bytes()

    with pytest.raises(RevisionConflict, match="source revision"):
        store.commit_source_outcomes(
            run_id="run-1",
            actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision,
            expected_source_revision=begun.snapshot.revisions.source,
            outcomes=outcomes,
            now=NOW,
        )
    assert store.path.read_bytes() == before


def test_frozen_effective_policy_replays_after_defaults_change_and_fresh_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import src.state.universe as universe_module

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    policy_json = begun.snapshot.metadata["source_policy"]
    assert json.loads(policy_json)["schema_version"] == "source-policy-1"
    assert hashlib.sha256(policy_json.encode("utf-8")).hexdigest() == begun.snapshot.metadata[
        "source_policy_hash"
    ]
    monkeypatch.setattr(universe_module, "_DEFAULT_NON_SOURCE_ROOTS", ("changed-default",))
    fresh = JsonRunStore(store.path)

    terminal = fresh.commit_source_outcomes(
        run_id="run-1",
        actor="orchestrator/main",
        lease_id=begun.orchestrator_lease.lease_id,
        expected_revision=begun.snapshot.store_revision,
        expected_source_revision=begun.snapshot.revisions.source,
        outcomes=_single_indexed_outcome(repo, begun.snapshot.revisions.source),
        now=NOW,
    )
    assert terminal.metadata["source_policy"] == policy_json
    assert terminal.metadata["source_policy_hash"] == begun.snapshot.metadata["source_policy_hash"]


def test_custom_product_roots_are_portable_and_in_repo_root_is_pruned(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    inside = repo / "generated" / "cbe"
    outside = tmp_path / "external-output"
    inside.mkdir(parents=True)
    outside.mkdir()
    (inside / "generated.py").write_text("generated = True\n", encoding="utf-8")
    store = JsonRunStore(tmp_path / "state-v3.json")
    lease = store.issue_bootstrap_lease(
        run_id="run-1", actor="orchestrator/main", ttl=timedelta(minutes=5), now=NOW
    )
    begun = store.begin_run(
        run_id="run-1",
        repo_root=repo,
        requested_languages=("python",),
        actor="orchestrator/main",
        lease_id=lease.lease_id,
        expected_revision=0,
        product_output_roots=(inside, outside),
        now=NOW,
    )
    policy = json.loads(begun.snapshot.metadata["source_policy"])
    internal_only = enumerate_source_universe(
        repo,
        requested_languages=("python",),
        product_output_roots=(inside,),
    )
    internal_plus_external = enumerate_source_universe(
        repo,
        requested_languages=("python",),
        product_output_roots=(inside, outside),
    )

    assert [source.path for source in begun.snapshot.sources] == ["a.py"]
    assert policy["product_roots"] == ["generated/cbe"]
    assert str(outside) not in begun.snapshot.metadata["source_policy"]
    assert internal_plus_external.policy_hash == internal_only.policy_hash
    assert internal_plus_external.source_revision == internal_only.source_revision


def test_defensive_outcome_validation_rejects_before_store_bytes_change(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    outcome = _single_indexed_outcome(repo, begun.snapshot.revisions.source)["a.py"]
    object.__setattr__(
        outcome,
        "typed_failure",
        TypedFailure(
            code=FailureCode.PARSE_ERROR,
            message="contradictory",
            backend_id="python_ast",
            language="python",
        ),
    )
    before = store.path.read_bytes()
    with pytest.raises(ValueError, match="exactly one"):
        store.commit_source_outcomes(
            run_id="run-1",
            actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision,
            expected_source_revision=begun.snapshot.revisions.source,
            outcomes={"a.py": outcome},
            now=NOW,
        )
    assert store.path.read_bytes() == before


def test_atomic_replace_failure_leaves_old_complete_bytes(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    begun = _begin(store, repo)
    old = store.path.read_bytes()

    def killed(_src, _dst):
        raise OSError("simulated kill before promotion")

    monkeypatch.setattr("src.state.json_store.os.replace", killed)
    with pytest.raises(OSError, match="simulated kill"):
        store.lease_task(
            run_id="run-1", target="task-1", actor="orchestrator/main",
            lease_id=begun.orchestrator_lease.lease_id,
            expected_revision=begun.snapshot.store_revision, now=NOW,
        )
    assert store.path.read_bytes() == old
    assert RunSnapshot.model_validate_json(old)


def test_corrupt_primary_recovers_only_from_hash_linked_backup(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    _begin(store, repo)
    good = store.path.read_bytes()
    store.path.write_text('{"partial":', encoding="utf-8")
    recovered = store.recover()
    assert recovered == RunSnapshot.model_validate_json(good)
    assert store.path.read_bytes() == good


def test_corrupt_primary_and_backup_fail_closed_without_promotion(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = JsonRunStore(tmp_path / "state-v3.json")
    _begin(store, repo)
    store.path.write_text('{"partial":', encoding="utf-8")
    store.backup_path.write_text('{"also":', encoding="utf-8")
    corrupt = store.path.read_bytes()
    with pytest.raises(RecoveryError):
        store.recover()
    assert store.path.read_bytes() == corrupt
