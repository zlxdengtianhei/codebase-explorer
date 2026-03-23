"""Tests for json_store module.

Tests cover:
- atomic_write_state: atomic write operations
- read_state: read operations
- update_task_status: task status updates
- resume_from_state: crash recovery scenarios
"""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.state.json_store import (
    atomic_write_state,
    read_state,
    resume_from_state,
    update_task_status,
)


class TestAtomicWriteState:
    """Test atomic write operations."""

    def test_write_new_file(self, tmp_path):
        """Test writing to a new file."""
        state_path = tmp_path / "state.json"
        state = {
            "schema_version": "2.0",
            "project": {"id": "test123"},
            "tasks": {}
        }

        atomic_write_state(state_path, state)

        assert state_path.exists()
        with open(state_path) as f:
            loaded = json.load(f)
        assert loaded == state

    def test_overwrite_existing_file(self, tmp_path):
        """Test overwriting an existing file."""
        state_path = tmp_path / "state.json"
        state_v1 = {"schema_version": "2.0", "project": {"id": "v1"}}
        state_v2 = {"schema_version": "2.0", "project": {"id": "v2"}}

        # Write v1
        atomic_write_state(state_path, state_v1)
        assert state_path.exists()

        # Write v2 (should replace v1)
        atomic_write_state(state_path, state_v2)

        with open(state_path) as f:
            loaded = json.load(f)
        assert loaded == state_v2

    def test_atomic_write_creates_parent_dir(self, tmp_path):
        """Test that parent directories are created if needed."""
        state_path = tmp_path / "subdir1/subdir2/state.json"
        state = {"schema_version": "2.0"}

        atomic_write_state(state_path, state)

        assert state_path.parent.exists()

    def test_tmp_file_removed_on_success(self, tmp_path):
        """Test that .tmp file is cleaned up after successful write."""
        state_path = tmp_path / "state.json"
        tmp_file = tmp_path / "state.json.tmp"
        state = {"schema_version": "2.0"}

        # Write should not leave tmp file
        atomic_write_state(state_path, state)

        assert not tmp_file.exists()
        assert state_path.exists()


class TestReadState:
    """Test read operations."""

    def test_read_existing_file(self, tmp_path):
        """Test reading an existing state file."""
        state_path = tmp_path / "state.json"
        state = {
            "schema_version": "2.0",
            "project": {"id": "test123"}
        }

        # Write state
        atomic_write_state(state_path, state)

        # Read it back
        loaded = read_state(state_path)
        assert loaded == state

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading a non-existent file returns None."""
        state_path = tmp_path / "nonexistent.json"
        result = read_state(state_path)
        assert result is None

    def test_read_corrupted_json(self, tmp_path):
        """Test reading corrupted JSON returns None."""
        state_path = tmp_path / "state.json"
        state_path.write_text("not valid json {{{")

        result = read_state(state_path)
        assert result is None


class TestUpdateTaskStatus:
    """Test task status updates."""

    def test_update_pending_to_in_progress(self, tmp_path):
        """Test updating task from pending to in_progress."""
        state_path = tmp_path / "state.json"
        initial_state = {
            "schema_version": "2.0",
            "project": {"id": "test123"},
            "tasks": {
                "task_001": {
                    "status": "pending",
                    "output_files": []
                }
            },
            "metadata": {"last_updated_at": "2026-01-01T00:00:00Z"}
        }

        atomic_write_state(state_path, initial_state)

        # Update status
        updated = update_task_status(
            state_path,
            "task_001",
            "in_progress"
        )

        assert updated["tasks"]["task_001"]["status"] == "in_progress"
        assert "started_at" in updated["tasks"]["task_001"]

    def test_update_to_complete_with_output_files(self, tmp_path):
        """Test updating task to complete with output files."""
        state_path = tmp_path / "state.json"
        initial_state = {
            "schema_version": "2.0",
            "project": {"id": "test123"},
            "tasks": {
                "task_001": {
                "status": "in_progress",
                "output_files": []
            }
            },
            "metadata": {"last_updated_at": "2026-01-01T00:00:00Z"}
        }

        atomic_write_state(state_path, initial_state)

        output_files = [
            {
                "path": ".codebase-docs/test/DETAIL.md",
                "tokens_written": 1000,
                "status": "complete"
            }
        ]

        # Update status
        updated = update_task_status(
            state_path,
            "task_001",
            "complete",
            output_files=output_files
        )

        assert updated["tasks"]["task_001"]["status"] == "complete"
        assert updated["tasks"]["task_001"]["output_files"] == output_files
        assert "completed_at" in updated["tasks"]["task_001"]


class TestResumeFromState:
    """Test crash recovery scenarios."""

    def create_complete_file(self, path: Path) -> None:
        """Create a file with completion marker."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x" * 201 + "\n<!-- codebase-explorer: end -->\n")

    def test_resume_with_complete_files(self, tmp_path):
        """Test resume when all files are complete."""
        state_path = tmp_path / ".codebase-analysis" / "state.json"

        # Create output directory
        docs_dir = tmp_path / ".codebase-docs"
        docs_dir.mkdir(parents=True)

        # Create complete output files
        detail_file = docs_dir / "test" / "DETAIL.md"
        snippet_file = docs_dir / "test" / "SNIPPET.md"
        self.create_complete_file(detail_file)
        self.create_complete_file(snippet_file)

        # Create state with in_progress task
        state = {
            "schema_version": "2.0",
            "project": {"id": "test123"},
            "tasks": {
                "task_001": {
                    "status": "in_progress",
                    "started_at": "2026-03-23T10:00:00Z",
                    "output_files": [
                        {
                            "path": ".codebase-docs/test/DETAIL.md",
                            "status": "pending"
                        },
                        {
                            "path": ".codebase-docs/test/SNIPPET.md",
                            "status": "pending"
                        }
                    ]
                }
            },
            "metadata": {"last_updated_at": "2026-03-23T10:00:00Z"}
        }

        atomic_write_state(state_path, state)

        # Resume
        pending = resume_from_state(tmp_path)

        # Task should be marked as complete (files exist)
        updated_state = read_state(state_path)
        assert updated_state["tasks"]["task_001"]["status"] == "complete"

    def test_resume_with_incomplete_files(self, tmp_path):
        """Test resume when files are incomplete (missing marker)."""
        state_path = tmp_path / ".codebase-analysis" / "state.json"

        # Create output directory
        docs_dir = tmp_path / ".codebase-docs"
        docs_dir.mkdir(parents=True)

        # Create incomplete output file (no marker)
        detail_file = docs_dir / "test" / "DETAIL.md"
        detail_file.parent.mkdir(parents=True, exist_ok=True)
        detail_file.write_text("x" * 100)  # No marker

        # Create state with in_progress task
        state = {
            "schema_version": "2.0",
            "project": {"id": "test123"},
            "tasks": {
                "task_001": {
                    "status": "in_progress",
                    "started_at": "2026-03-23T10:00:00Z",
                    "output_files": [
                        {
                            "path": ".codebase-docs/test/DETAIL.md",
                            "status": "pending"
                        }
                    ]
                }
            },
            "metadata": {"last_updated_at": "2026-03-23T10:00:00Z"}
        }

        atomic_write_state(state_path, state)

        # Resume
        pending = resume_from_state(tmp_path)

        # Task should be reset to pending (file incomplete)
        updated_state = read_state(state_path)
        assert updated_state["tasks"]["task_001"]["status"] == "pending"
        assert updated_state["tasks"]["task_001"]["started_at"] is None
