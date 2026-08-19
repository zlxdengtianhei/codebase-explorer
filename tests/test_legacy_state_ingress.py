"""Fresh-process acceptance controls for the frozen P5L legacy ingress."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.state.run_lifecycle import prior_receipt, read_active_receipt, resolve_active_run


_RUNNER = r'''
import asyncio, hashlib, json, os, time
from pathlib import Path
from unittest.mock import MagicMock

from src.parser.codebase import CodebaseParser
from src.state.json_store import JsonRunStore

repo = Path(os.environ["P5L_REPO"])
out = Path(os.environ["P5L_OUT"])
operation = os.environ["P5L_OPERATION"]
record_path = Path(os.environ["P5L_RECORD"])

records = []
for name in ("begin_run", "lease_task", "submit_legacy_analysis", "submit_artifact"):
    original = getattr(JsonRunStore, name)
    def wrapper(self, _original=original, _name=name, **kwargs):
        try:
            before = self.snapshot().store_revision
        except Exception:
            before = 0
        result = _original(self, **kwargs)
        try:
            after = self.snapshot().store_revision
        except Exception:
            after = before
        records.append({
            "operation": _name,
            "actor": kwargs.get("actor"),
            "producer": kwargs.get("producer"),
            "lease_id": kwargs.get("lease_id"),
            "issued_lease_id": getattr(getattr(result, "lease", None), "lease_id", None),
            "target": kwargs.get("target") or kwargs.get("task_id"),
            "expected_revision": kwargs.get("expected_revision"),
            "before_revision": before,
            "after_revision": after,
            "run_id": kwargs.get("run_id"),
            "artifact_hash": kwargs.get("artifact_hash"),
        })
        return result
    setattr(JsonRunStore, name, wrapper)

import src.server as server

if operation == "crash_pre_v2":
    def injected_pre_v2_crash(*args, **kwargs):
        raise RuntimeError("INJECTED_AFTER_PUBLISH_BEFORE_V2")
    server.write_v2_rollback_projection = injected_pre_v2_crash

race_dir = os.environ.get("P5L_RACE_DIR")
if race_dir:
    original_promote = server.promote_active_receipt
    def synchronized_promote(*args, **kwargs):
        marker = Path(race_dir) / str(os.getpid())
        marker.write_text("ready")
        deadline = time.monotonic() + 10
        while len(list(Path(race_dir).iterdir())) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        return original_promote(*args, **kwargs)
    server.promote_active_receipt = synchronized_promote

ctx = MagicMock()
ctx.request_context.lifespan_context = {"parser": CodebaseParser()}

async def main():
    if operation in {"analyze", "cache", "force", "crash_pre_v2"}:
        languages = json.loads(os.environ.get("P5L_LANGUAGES", '["python"]'))
        return await server.analyze_codebase(
            path=str(repo), languages=languages, output_dir=str(out),
            force_reindex=(operation != "cache"),
            include_tests=os.environ.get("P5L_INCLUDE_TESTS") == "1", ctx=ctx,
        )
    selected = server.resolve_active_run(out)
    task_id = next(task.task_id for task in selected.snapshot.legacy_submission.tasks
                   if task.status == "pending")
    if operation == "submit":
        detail = repo / ".codebase-docs" / "fixture" / "DETAIL.md"
        detail.parent.mkdir(parents=True, exist_ok=True)
        detail.write_text("# Detail\n<!-- index-fragment:fixture -->\nsummary\n")
        return await server.submit_analysis(
            task_id=task_id, detail_paths=[str(detail)], snippet_paths=[],
            tokens_used=7, source_files_covered=["app.py"], output_dir=str(out),
        )
    if operation == "update":
        return await server.doc_operation(operation="update_index", output_dir=str(out))
    if operation == "stale":
        original = JsonRunStore.lease_task
        def stale_lease(self, **kwargs):
            if kwargs.get("actor") == "orchestrator/legacy-mcp/submit_analysis":
                kwargs["expected_revision"] = max(0, kwargs["expected_revision"] - 1)
            return original(self, **kwargs)
        JsonRunStore.lease_task = stale_lease
        detail = repo / ".codebase-docs" / "stale" / "DETAIL.md"
        detail.parent.mkdir(parents=True, exist_ok=True)
        detail.write_text("# stale\n")
        try:
            await server.submit_analysis(
                task_id=task_id, detail_paths=[str(detail)], snippet_paths=[],
                tokens_used=1, output_dir=str(out),
            )
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}
        raise AssertionError("stale submission unexpectedly succeeded")
    raise AssertionError(operation)

try:
    result = asyncio.run(main())
    status = 0
except Exception as exc:
    result = {"error": str(exc), "type": type(exc).__name__}
    status = 1
record_path.write_text(json.dumps(records, sort_keys=True))
print("P5L_RESULT=" + json.dumps(result, sort_keys=True))
raise SystemExit(status)
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protected(output: Path) -> dict[str, str]:
    return {
        str(path.relative_to(output)): _sha(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and not path.name.endswith(".lock")
    }


def _fresh(
    repo: Path,
    output: Path,
    operation: str,
    tmp_path: Path,
    *,
    race_dir: Path | None = None,
    extra_env: dict[str, str] | None = None,
    check: bool = True,
) -> tuple[subprocess.CompletedProcess[str], dict, list[dict]]:
    record = tmp_path / f"record-{operation}-{os.urandom(4).hex()}.json"
    env = os.environ.copy()
    env.update(
        P5L_REPO=str(repo),
        P5L_OUT=str(output),
        P5L_OPERATION=operation,
        P5L_RECORD=str(record),
    )
    if race_dir is not None:
        env["P5L_RACE_DIR"] = str(race_dir)
    if extra_env is not None:
        env.update(extra_env)
    process = subprocess.run(
        [sys.executable, "-c", _RUNNER],
        cwd=Path(__file__).parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if check and process.returncode:
        pytest.fail(f"fresh process failed: {process.stdout}\n{process.stderr}")
    marker = next(line for line in process.stdout.splitlines() if line.startswith("P5L_RESULT="))
    return process, json.loads(marker.removeprefix("P5L_RESULT=")), json.loads(record.read_text())


@pytest.fixture
def legacy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def main():\n    return 1\n")
    return repo


def test_fresh_process_real_ingress_and_immutable_v2(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A1..A5/A8: all real ingress writes are typed, monotonic and V2-safe."""
    out = tmp_path / "analysis"
    _, analyzed, begin_records = _fresh(legacy_repo, out, "analyze", tmp_path)
    v2_hash = _sha(out / "state.json")
    selected = resolve_active_run(out)
    initial_revision = selected.snapshot.store_revision
    _, submitted, submit_records = _fresh(legacy_repo, out, "submit", tmp_path)
    _, updated, update_records = _fresh(legacy_repo, out, "update", tmp_path)

    assert analyzed["status"] == submitted["status"] == updated["status"] == "success"
    assert type(analyzed["cached"]) is bool and analyzed["cached"] is False
    assert json.loads((out / "state.json").read_text())["documentation"][
        "output_dir"
    ] == str(out)
    assert _sha(out / "state.json") == v2_hash
    assert resolve_active_run(out).snapshot.store_revision > initial_revision
    assert [r["operation"] for r in begin_records] == ["begin_run"]
    mutations = submit_records + update_records
    assert [r["operation"] for r in mutations] == [
        "lease_task", "submit_legacy_analysis", "lease_task", "submit_artifact"
    ]
    for record in mutations:
        assert record["expected_revision"] == record["before_revision"]
        assert record["after_revision"] > record["before_revision"]
    assert {r["actor"] for r in submit_records} == {
        "orchestrator/legacy-mcp/submit_analysis"
    }
    assert submit_records[-1]["producer"] == "legacy-mcp/submit_analysis"
    assert {r["actor"] for r in update_records} == {
        "orchestrator/legacy-mcp/doc_operation:update_index"
    }
    assert update_records[-1]["producer"] == "legacy-mcp/doc_operation:update_index"
    assert submit_records[1]["lease_id"] == submit_records[0]["issued_lease_id"]
    assert update_records[1]["lease_id"] == update_records[0]["issued_lease_id"]
    assert submit_records[0]["target"] == submit_records[1]["target"]
    assert update_records[0]["target"] == update_records[1]["target"] == "index"
    assert {record["run_id"] for record in mutations} == {selected.receipt.run_id}
    assert all(source.state == "discovered" for source in selected.snapshot.sources)


def test_stale_rejection_and_static_writer_inventory(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A6/A7: stale CAS is non-mutating and no legacy writer survives."""
    out = tmp_path / "analysis"
    _fresh(legacy_repo, out, "analyze", tmp_path)
    before = _protected(out)
    _, result, records = _fresh(legacy_repo, out, "stale", tmp_path)
    assert "expected_revision" in result["error"] or "revision" in result["error"]
    assert _protected(out) == before
    assert records == []
    server_text = (Path(__file__).parents[1] / "src/server.py").read_text()
    helper_text = (Path(__file__).parents[1] / "src/server_helpers.py").read_text()
    inventory = server_text + helper_text
    assert "update_task_status(" not in inventory
    assert "atomic_write_state(" not in inventory
    assert "commit_source_outcomes(" not in inventory
    assert "SourceOutcome(" not in inventory


def test_rollback_cache_force_and_reopen(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A9/A12/A13: rollback stays hash-linked and force is generational."""
    out = tmp_path / "analysis"
    _, first, _ = _fresh(legacy_repo, out, "analyze", tmp_path)
    first_receipt = read_active_receipt(out)
    v2_hash = _sha(out / "state.json")
    old_generation_hashes = _protected(out / first_receipt.generation_path)
    _, cached, _ = _fresh(legacy_repo, out, "cache", tmp_path)
    assert cached["cached"] is True and cached["run_id"] == first["run_id"]
    _, forced, _ = _fresh(legacy_repo, out, "force", tmp_path)
    second = read_active_receipt(out)
    assert forced["cached"] is False and second.run_id != first_receipt.run_id
    assert _sha(out / "state.json") == v2_hash
    assert _protected(out / first_receipt.generation_path) == old_generation_hashes
    assert prior_receipt(second, out) == first_receipt
    rollback = json.loads((out / "state.json").read_text())
    assert rollback["project_id"] == first["project_id"]
    assert rollback["status"] == "analysis_complete"


def test_v2_only_upgrade_and_expired_route_rebuild(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A11/A17: legacy V2 upgrades and stale authorization rebuilds."""
    source = tmp_path / "source-analysis"
    _fresh(legacy_repo, source, "analyze", tmp_path)
    legacy = tmp_path / "legacy-analysis"
    legacy.mkdir()
    shutil.copy2(source / "state.json", legacy / "state.json")
    selected = resolve_active_run(source)
    for entry in selected.receipt.artifacts:
        shutil.copy2(selected.generation_path / entry.path, legacy / entry.path)
    v2_hash = _sha(legacy / "state.json")
    _, upgraded, _ = _fresh(legacy_repo, legacy, "cache", tmp_path)
    assert upgraded["cached"] is False
    assert _sha(legacy / "state.json") == v2_hash
    assert len(list((legacy / ".runs").iterdir())) == 1
    _fresh(legacy_repo, legacy, "submit", tmp_path)
    _fresh(legacy_repo, legacy, "update", tmp_path)

    active = resolve_active_run(legacy)
    state = json.loads(active.state_path.read_text())
    for lease in state["leases"]:
        if lease["target"].startswith("capability:route-parent:"):
            lease["expires_at"] = "2000-01-01T00:00:00Z"
    active.state_path.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n")
    backup = active.state_path.with_suffix(active.state_path.suffix + ".bak")
    backup.write_bytes(active.state_path.read_bytes())
    old_run = active.receipt.run_id
    _, rebuilt, _ = _fresh(legacy_repo, legacy, "cache", tmp_path)
    assert rebuilt["cached"] is False and rebuilt["run_id"] != old_run


def test_corruption_fails_closed_and_concurrent_selector_has_one_winner(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A14/A16: protected corruption fails and selector CAS has one winner."""
    out = tmp_path / "analysis"
    _fresh(legacy_repo, out, "analyze", tmp_path)
    (out / "state.json").write_text("{}\n")
    corrupted = _protected(out)
    process, result, _ = _fresh(legacy_repo, out, "cache", tmp_path, check=False)
    assert process.returncode != 0 and "V2 hash mismatch" in result["error"]
    assert _protected(out) == corrupted

    race_out = tmp_path / "race-analysis"
    _fresh(legacy_repo, race_out, "analyze", tmp_path)
    race_dir = tmp_path / "race"
    race_dir.mkdir()
    record_paths = [tmp_path / f"race-{index}.json" for index in range(2)]
    processes = []
    for record in record_paths:
        env = os.environ.copy()
        env.update(P5L_REPO=str(legacy_repo), P5L_OUT=str(race_out),
                   P5L_OPERATION="force", P5L_RECORD=str(record),
                   P5L_RACE_DIR=str(race_dir))
        processes.append(subprocess.Popen(
            [sys.executable, "-c", _RUNNER], cwd=Path(__file__).parents[1],
            env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ))
    results = [process.communicate(timeout=90) for process in processes]
    codes = [process.returncode for process in processes]
    assert sorted(codes) == [0, 1], results
    loser_output = results[codes.index(1)][0]
    assert "activation conflict" in loser_output.lower()
    assert resolve_active_run(race_out).receipt.activation_generation == 2


def test_interrupted_initial_activation_exact_link_recovery(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A15: a sole fully-published initial orphan completes idempotently."""
    out = tmp_path / "analysis"
    _, analyzed, _ = _fresh(legacy_repo, out, "analyze", tmp_path)
    receipt = read_active_receipt(out)
    v2_hash = _sha(out / "state.json")
    generation_hashes = _protected(out / receipt.generation_path)

    # Recreate the durable bytes visible after publish/V2 creation but before
    # the selector CAS/history receipt writes.
    (out / "active-run.json").unlink()
    (out / receipt.generation_path / "active-run-receipt.json").unlink()
    _, recovered, _ = _fresh(legacy_repo, out, "cache", tmp_path)

    assert recovered["cached"] is True
    assert recovered["run_id"] == analyzed["run_id"]
    assert _sha(out / "state.json") == v2_hash
    current_generation = _protected(out / receipt.generation_path)
    for path, digest in generation_hashes.items():
        if path != "active-run-receipt.json":
            assert current_generation[path] == digest


def test_post_publish_pre_v2_crash_recovers_same_generation(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A15: restart completes the durable pre-V2 initial generation."""
    out = tmp_path / "analysis"
    process, crashed, _ = _fresh(
        legacy_repo, out, "crash_pre_v2", tmp_path, check=False
    )
    assert process.returncode != 0
    assert crashed == {
        "error": "INJECTED_AFTER_PUBLISH_BEFORE_V2",
        "type": "RuntimeError",
    }
    generations = tuple((out / ".runs").iterdir())
    assert len(generations) == 1
    crashed_run_id = generations[0].name
    durable_before = _protected(out)
    assert not (out / "state.json").exists()
    assert not (out / "active-run.json").exists()
    assert (generations[0] / "state-v3.json").exists()

    _, recovered, _ = _fresh(legacy_repo, out, "cache", tmp_path)
    assert recovered["cached"] is True
    assert recovered["run_id"] == crashed_run_id
    selected = resolve_active_run(out)
    assert selected.receipt.run_id == crashed_run_id
    assert (out / "state.json").is_file()
    for path, digest in durable_before.items():
        assert _protected(out)[path] == digest


def test_pre_v2_crash_recovery_rejects_ambiguous_or_stale_bytes(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A15: every ambiguous durable surface fails before changing bytes."""
    def rejected(
        name: str,
        expected: str,
        mutate,
        *,
        env: dict[str, str] | None = None,
    ) -> None:
        candidate = tmp_path / name
        crashed, _, _ = _fresh(
            legacy_repo, candidate, "crash_pre_v2", tmp_path, check=False
        )
        assert crashed.returncode != 0
        mutate(candidate, legacy_repo)
        before = _protected(candidate)
        failed, result, _ = _fresh(
            legacy_repo, candidate, "cache", tmp_path, extra_env=env, check=False
        )
        assert failed.returncode != 0, name
        assert expected in result["error"], (name, result)
        assert _protected(candidate) == before, name

    def add_second_generation(out: Path, _repo: Path) -> None:
        generation = next((out / ".runs").iterdir())
        shutil.copytree(generation, out / ".runs" / "second-orphan")

    rejected("multiple-orphans", "not unique", add_second_generation)
    rejected(
        "incomplete-generation",
        "required generation artifact is missing",
        lambda out, _repo: next((out / ".runs").iterdir())
        .joinpath("01_structure.json")
        .unlink(),
    )
    rejected(
        "corrupt-recovery-input",
        "recovery projection is invalid",
        lambda out, _repo: next((out / ".runs").iterdir())
        .joinpath("v2-recovery-projection.json")
        .write_bytes(b"corrupt\n"),
    )
    rejected(
        "preexisting-v2-mismatch",
        "V2 hash/link mismatch",
        lambda out, _repo: (out / "state.json").write_text("{}\n"),
    )
    rejected(
        "unrelated-root-artifact",
        "unrelated root analysis artifacts",
        lambda out, _repo: (out / "01_structure.json").write_text("{}\n"),
    )
    rejected(
        "changed-input",
        "repository/input",
        lambda _out, _repo: None,
        env={"P5L_INCLUDE_TESTS": "1"},
    )
    rejected(
        "changed-source",
        "source revision is stale",
        lambda _out, repo: (repo / "app.py").write_text("def main():\n    return 2\n"),
    )


def test_pre_v2_crash_concurrent_restart_is_idempotent(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A15: concurrent restarts converge on the exact same generation."""
    out = tmp_path / "analysis"
    crashed, _, _ = _fresh(legacy_repo, out, "crash_pre_v2", tmp_path, check=False)
    assert crashed.returncode != 0
    run_id = next((out / ".runs").iterdir()).name
    durable_before = _protected(out)
    race_dir = tmp_path / "concurrent-recovery"
    race_dir.mkdir()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                _fresh,
                legacy_repo,
                out,
                "cache",
                tmp_path,
                race_dir=race_dir,
            )
            for _ in range(2)
        ]
        recovered = [future.result()[1] for future in futures]

    assert {result["run_id"] for result in recovered} == {run_id}
    assert all(result["cached"] is True for result in recovered)
    assert recovered[0]["semantic"] == recovered[1]["semantic"]
    assert resolve_active_run(out).receipt.run_id == run_id
    for path, digest in durable_before.items():
        assert _protected(out)[path] == digest


def test_corruption_mismatch_table_and_safe_cache_misses(
    legacy_repo: Path, tmp_path: Path
) -> None:
    """P5L-A14: integrity defects fail closed; input/source drift rebuilds."""
    base = tmp_path / "base-analysis"
    _fresh(legacy_repo, base, "analyze", tmp_path)

    def rejected(name: str, mutate) -> None:
        candidate = tmp_path / name
        shutil.copytree(base, candidate)
        mutate(candidate)
        before = _protected(candidate)
        process, result, _ = _fresh(
            legacy_repo, candidate, "cache", tmp_path, check=False
        )
        assert process.returncode != 0, (name, result)
        assert _protected(candidate) == before

    rejected("bad-receipt", lambda out: (out / "active-run.json").write_text("{}\n"))

    def corrupt_manifest(out: Path) -> None:
        selected = resolve_active_run(out)
        (selected.generation_path / "01_structure.json").write_text("{}\n")

    rejected("bad-manifest", corrupt_manifest)

    def corrupt_v3(out: Path) -> None:
        receipt = read_active_receipt(out)
        generation = out / receipt.generation_path
        for path in generation.glob("state-v3.json*"):
            if path.is_file() and not path.name.endswith(".lock"):
                path.write_bytes(b"corrupt\n")

    rejected("bad-v3", corrupt_v3)

    def rewrite_snapshot(out: Path, mutation) -> None:
        selected = resolve_active_run(out)
        data = json.loads(selected.state_path.read_text())
        mutation(data)
        payload = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
        selected.state_path.write_bytes(payload)
        backup = selected.state_path.with_name("state-v3.json.bak")
        backup.write_bytes(payload)
        backup.with_name("state-v3.json.bak.sha256").write_text(
            hashlib.sha256(payload).hexdigest() + "\n"
        )

    rejected(
        "bad-routes",
        lambda out: rewrite_snapshot(
            out,
            lambda data: data.__setitem__(
                "leases",
                [
                    lease
                    for lease in data["leases"]
                    if not lease["target"].startswith("capability:route-parent:")
                ],
            ),
        ),
    )
    rejected(
        "bad-seed",
        lambda out: rewrite_snapshot(
            out,
            lambda data: data["legacy_submission"].__setitem__(
                "tasks", data["legacy_submission"]["tasks"][:-1]
            ),
        ),
    )

    input_drift = tmp_path / "input-drift"
    shutil.copytree(base, input_drift)
    old = read_active_receipt(input_drift)
    old_hashes = _protected(input_drift / old.generation_path)
    record = tmp_path / "input-drift-record.json"
    env = os.environ.copy()
    env.update(P5L_REPO=str(legacy_repo), P5L_OUT=str(input_drift),
               P5L_OPERATION="cache", P5L_RECORD=str(record),
               P5L_INCLUDE_TESTS="1")
    process = subprocess.run(
        [sys.executable, "-c", _RUNNER], cwd=Path(__file__).parents[1], env=env,
        text=True, capture_output=True, timeout=90, check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    assert read_active_receipt(input_drift).run_id != old.run_id
    assert _protected(input_drift / old.generation_path) == old_hashes

    source_drift = tmp_path / "source-drift"
    shutil.copytree(base, source_drift)
    old = read_active_receipt(source_drift)
    old_hashes = _protected(source_drift / old.generation_path)
    (legacy_repo / "new.py").write_text("VALUE = 2\n")
    _, rebuilt, _ = _fresh(legacy_repo, source_drift, "cache", tmp_path)
    assert rebuilt["cached"] is False and rebuilt["run_id"] != old.run_id
    assert _protected(source_drift / old.generation_path) == old_hashes
