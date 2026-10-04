"""Concurrent work claims only the number of tasks it can execute."""

from __future__ import annotations

import threading
from pathlib import Path

from cbe import runner
from cbe.store import LedgerStore


def test_release_cli_is_reachable_for_recovery() -> None:
    from cbe.cli import build_parser

    args = build_parser().parse_args([
        "release", "--run-dir", "/tmp/cbe-run",
        "--task-ids-file", "/tmp/cbe-ids.json",
    ])
    assert args.command == "release"
    assert args.cancel is False


def test_parallel_work_keeps_a_bounded_claim_window(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for index in range(5):
        (repo / f"part_{index}.py").write_text(
            f"def action_{index}(value):\n    return value + {index}\n", encoding="utf-8"
        )
    run_dir = tmp_path / "run"
    runner.analyze(repo, run_dir, documentation_profile="legacy-v1")
    started = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    state = {"count": 0, "result": None, "error": None}

    def pretend_to_run(_store, _run_dir, task, **_kwargs):
        with lock:
            state["count"] += 1
            if state["count"] >= 2:
                started.set()
        assert release.wait(timeout=10)
        return {"task_id": task.task_id, "state": "mocked"}

    monkeypatch.setattr(runner, "_run_one", pretend_to_run)

    def run_work() -> None:
        try:
            state["result"] = runner.work(run_dir, model="mock", jobs=2, limit=5)
        except BaseException as exc:
            state["error"] = exc

    thread = threading.Thread(target=run_work, daemon=True)
    thread.start()
    try:
        assert started.wait(timeout=10)
        ledger = LedgerStore(run_dir).open()
        leased = [task for task in ledger["tasks"].values() if task["state"] == "leased"]
        assert len(leased) == 2
    finally:
        release.set()
        thread.join(timeout=10)
    assert not thread.is_alive()
    assert state["error"] is None
    assert len(state["result"]["ran"]) == 5
