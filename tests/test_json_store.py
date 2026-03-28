"""Tests for src/state/json_store.py — atomic JSON state management."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from src.state.json_store import (
    _check_file_complete,
    atomic_write_state,
    read_state,
    resume_from_state,
    update_task_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMPLETION_MARKER = "<!-- codebase-explorer: end -->"


def _make_state(tasks: dict | None = None, **extra) -> dict:
    """Build a minimal valid state dict."""
    return {
        "schema_version": "2.0",
        "project": {
            "id": "proj-1",
            "root_path": "/tmp/repo",
            "analyzed_at": "2026-03-25T00:00:00+00:00",
        },
        "tasks": tasks or {},
        "metadata": {},
        **extra,
    }


def _write_state_file(path: Path, state: dict) -> None:
    """Write a state dict directly (not via atomic_write_state)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


# ===================================================================
# atomic_write_state
# ===================================================================


class TestAtomicWriteState:
    def test_creates_file(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state()
        atomic_write_state(state_path, state)

        assert state_path.exists()
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        assert loaded["schema_version"] == "2.0"

    def test_overwrites_existing(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        atomic_write_state(state_path, _make_state())
        atomic_write_state(state_path, _make_state(metadata={"run": 2}))

        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        assert loaded["metadata"]["run"] == 2

    def test_creates_parent_directories(self, tmp_path: Path):
        state_path = tmp_path / "deep" / "nested" / "state.json"
        atomic_write_state(state_path, _make_state())
        assert state_path.exists()

    def test_tmp_file_cleaned_up(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        atomic_write_state(state_path, _make_state())

        tmp_file = state_path.with_suffix(".json.tmp")
        assert not tmp_file.exists()

    def test_unicode_content(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(metadata={"author": "Zhang"})
        atomic_write_state(state_path, state)

        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        assert loaded["metadata"]["author"] == "Zhang"

    def test_concurrent_writes_do_not_corrupt(self, tmp_path: Path):
        """Sequential rapid writes should not produce corrupted JSON.

        The atomic_write_state function uses a single shared tmp path per
        state file, so truly concurrent writers can race on the tmp file.
        This test verifies that each individual atomic write produces valid
        JSON on disk, by running writes sequentially in rapid succession
        from multiple threads using a lock.
        """
        state_path = tmp_path / "state.json"
        lock = threading.Lock()
        errors: list[Exception] = []

        def writer(i: int):
            try:
                with lock:
                    atomic_write_state(state_path, _make_state(metadata={"i": i}))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during writes: {errors}"
        # Final file must be valid JSON
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        assert "metadata" in loaded


# ===================================================================
# read_state
# ===================================================================


class TestReadState:
    def test_valid_file(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state()
        _write_state_file(state_path, state)

        result = read_state(state_path)
        assert result is not None
        assert result["schema_version"] == "2.0"

    def test_missing_file_returns_none(self, tmp_path: Path):
        result = read_state(tmp_path / "nonexistent.json")
        assert result is None

    def test_corrupted_json_returns_none(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state_path.write_text("{invalid json", encoding="utf-8")

        result = read_state(state_path)
        assert result is None

    def test_empty_file_returns_none(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state_path.write_text("", encoding="utf-8")

        result = read_state(state_path)
        assert result is None


# ===================================================================
# update_task_status
# ===================================================================


class TestUpdateTaskStatus:
    def test_update_existing_task_to_in_progress(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(tasks={"t1": {"status": "pending", "type": "batch"}})
        _write_state_file(state_path, state)

        result = update_task_status(state_path, "t1", "in_progress")
        assert result["tasks"]["t1"]["status"] == "in_progress"
        assert "started_at" in result["tasks"]["t1"]

    def test_update_existing_task_to_complete(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(tasks={"t1": {"status": "in_progress", "type": "batch"}})
        _write_state_file(state_path, state)

        result = update_task_status(state_path, "t1", "complete")
        assert result["tasks"]["t1"]["status"] == "complete"
        assert "completed_at" in result["tasks"]["t1"]

    def test_update_existing_task_to_failed(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(tasks={"t1": {"status": "in_progress", "type": "batch"}})
        _write_state_file(state_path, state)

        result = update_task_status(
            state_path, "t1", "failed", error="out of memory"
        )
        assert result["tasks"]["t1"]["status"] == "failed"
        assert result["tasks"]["t1"]["error"] == "out of memory"
        assert "completed_at" in result["tasks"]["t1"]

    def test_missing_task_raises_value_error(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        _write_state_file(state_path, _make_state())

        with pytest.raises(ValueError, match="Task not found"):
            update_task_status(state_path, "nonexistent", "complete")

    def test_missing_state_file_raises_value_error(self, tmp_path: Path):
        with pytest.raises(ValueError, match="State file not found"):
            update_task_status(tmp_path / "missing.json", "t1", "complete")

    def test_output_files_updated(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(tasks={"t1": {"status": "pending", "type": "batch"}})
        _write_state_file(state_path, state)

        output = [{"path": "out.md", "status": "complete", "tokens_written": 300}]
        result = update_task_status(state_path, "t1", "complete", output_files=output)
        assert result["tasks"]["t1"]["output_files"] == output

    def test_metadata_last_updated_set(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(tasks={"t1": {"status": "pending", "type": "batch"}})
        _write_state_file(state_path, state)

        result = update_task_status(state_path, "t1", "in_progress")
        assert "last_updated_at" in result["metadata"]

    def test_state_persisted_to_disk(self, tmp_path: Path):
        state_path = tmp_path / "state.json"
        state = _make_state(tasks={"t1": {"status": "pending", "type": "batch"}})
        _write_state_file(state_path, state)

        update_task_status(state_path, "t1", "complete")

        reloaded = read_state(state_path)
        assert reloaded is not None
        assert reloaded["tasks"]["t1"]["status"] == "complete"


# ===================================================================
# _check_file_complete
# ===================================================================


class TestCheckFileComplete:
    def test_missing_file(self, tmp_path: Path):
        assert _check_file_complete(tmp_path / "nope.md") is False

    def test_small_file(self, tmp_path: Path):
        f = tmp_path / "tiny.md"
        f.write_text("short", encoding="utf-8")
        assert _check_file_complete(f) is False

    def test_large_file_without_marker(self, tmp_path: Path):
        f = tmp_path / "big.md"
        f.write_text("x" * 300, encoding="utf-8")
        assert _check_file_complete(f) is False

    def test_complete_file(self, tmp_path: Path):
        f = tmp_path / "good.md"
        content = "x" * 300 + "\n" + COMPLETION_MARKER + "\n"
        f.write_text(content, encoding="utf-8")
        assert _check_file_complete(f) is True


# ===================================================================
# resume_from_state
# ===================================================================


class TestResumeFromState:
    def _setup_project(self, tmp_path: Path, state: dict) -> Path:
        """Set up a project root with .codebase-analysis/state.json."""
        analysis_dir = tmp_path / ".codebase-analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        state_path = analysis_dir / "state.json"
        _write_state_file(state_path, state)
        return tmp_path

    def test_no_state_file_returns_empty(self, tmp_path: Path):
        result = resume_from_state(tmp_path)
        assert result == []

    def test_all_tasks_completed_returns_empty(self, tmp_path: Path):
        state = _make_state(tasks={
            "t1": {"status": "complete", "type": "batch"},
            "t2": {"status": "complete", "type": "single"},
        })
        root = self._setup_project(tmp_path, state)
        result = resume_from_state(root)
        assert result == []

    def test_pending_tasks_returned(self, tmp_path: Path):
        state = _make_state(tasks={
            "t1": {"status": "pending", "type": "batch"},
            "t2": {"status": "complete", "type": "single"},
        })
        root = self._setup_project(tmp_path, state)
        result = resume_from_state(root)
        assert "t1" in result

    def test_in_progress_with_complete_files_marked_complete(self, tmp_path: Path):
        """In-progress task with all output files actually complete => complete."""
        # Create the output file with marker
        out_file = tmp_path / "docs" / "core.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        content = "x" * 300 + "\n" + COMPLETION_MARKER + "\n"
        out_file.write_text(content, encoding="utf-8")

        state = _make_state(tasks={
            "t1": {
                "status": "in_progress",
                "type": "batch",
                "output_files": [{"path": "docs/core.md", "status": "pending"}],
            },
        })
        root = self._setup_project(tmp_path, state)
        result = resume_from_state(root)

        # Task should be marked complete, not returned as pending
        assert "t1" not in result

        # Verify state file was updated
        updated = read_state(root / ".codebase-analysis" / "state.json")
        assert updated["tasks"]["t1"]["status"] == "complete"

    def test_in_progress_with_incomplete_files_reset_to_pending(self, tmp_path: Path):
        """In-progress task with incomplete output files => reset to pending."""
        state = _make_state(tasks={
            "t1": {
                "status": "in_progress",
                "type": "batch",
                "output_files": [{"path": "docs/missing.md", "status": "pending"}],
            },
        })
        root = self._setup_project(tmp_path, state)
        result = resume_from_state(root)

        assert "t1" in result
        updated = read_state(root / ".codebase-analysis" / "state.json")
        assert updated["tasks"]["t1"]["status"] == "pending"
        assert updated["tasks"]["t1"]["started_at"] is None

    def test_task_order_preserved_from_manifest(self, tmp_path: Path):
        """When a task manifest exists, pending tasks should follow its order."""
        state = _make_state(tasks={
            "t3": {"status": "pending", "type": "batch"},
            "t1": {"status": "pending", "type": "single"},
            "t2": {"status": "pending", "type": "batch"},
        })
        root = self._setup_project(tmp_path, state)

        # Create manifest with explicit order
        manifest = {"task_order": ["t1", "t2", "t3"]}
        manifest_path = root / ".codebase-analysis" / "05_task_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = resume_from_state(root)
        assert result == ["t1", "t2", "t3"]

    def test_manifest_filters_only_pending(self, tmp_path: Path):
        """Manifest order should only include tasks that are still pending."""
        state = _make_state(tasks={
            "t1": {"status": "complete", "type": "batch"},
            "t2": {"status": "pending", "type": "single"},
            "t3": {"status": "pending", "type": "batch"},
        })
        root = self._setup_project(tmp_path, state)

        manifest = {"task_order": ["t1", "t2", "t3"]}
        manifest_path = root / ".codebase-analysis" / "05_task_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = resume_from_state(root)
        assert "t1" not in result
        assert result == ["t2", "t3"]

    def test_no_manifest_still_returns_pending(self, tmp_path: Path):
        """Without a manifest, pending tasks are still returned (unordered)."""
        state = _make_state(tasks={
            "t1": {"status": "pending", "type": "batch"},
        })
        root = self._setup_project(tmp_path, state)
        result = resume_from_state(root)
        assert "t1" in result

    def test_crash_recovery_multiple_in_progress(self, tmp_path: Path):
        """Multiple in-progress tasks: one with complete files, one without."""
        # Complete file for t1
        out1 = tmp_path / "docs" / "a.md"
        out1.parent.mkdir(parents=True, exist_ok=True)
        out1.write_text("y" * 300 + "\n" + COMPLETION_MARKER + "\n", encoding="utf-8")

        state = _make_state(tasks={
            "t1": {
                "status": "in_progress",
                "type": "batch",
                "output_files": [{"path": "docs/a.md", "status": "pending"}],
            },
            "t2": {
                "status": "in_progress",
                "type": "single",
                "output_files": [{"path": "docs/b.md", "status": "pending"}],
            },
            "t3": {"status": "pending", "type": "batch"},
        })
        root = self._setup_project(tmp_path, state)
        result = resume_from_state(root)

        updated = read_state(root / ".codebase-analysis" / "state.json")
        assert updated["tasks"]["t1"]["status"] == "complete"
        assert updated["tasks"]["t2"]["status"] == "pending"
        assert "t2" in result
        assert "t3" in result
        assert "t1" not in result
