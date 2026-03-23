"""JSON-based state management with atomic writes and resume support.

This module replaces the SQLite-based state management from V1.
All state is stored in a single state.json file with atomic write operations.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal


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
    state = read_state(state_path)
    if state is None:
        raise ValueError(f"State file not found: {state_path}")

    if task_id not in state["tasks"]:
        raise ValueError(f"Task not found: {task_id}")

    # Update task status
    state["tasks"][task_id]["status"] = status

    # Update timestamp
    if status == "in_progress":
        state["tasks"][task_id]["started_at"] = datetime.now(UTC).isoformat()
    elif status in ["complete", "failed"]:
        state["tasks"][task_id]["completed_at"] = datetime.now(UTC).isoformat()

    # Update output files if provided
    if output_files is not None:
        state["tasks"][task_id]["output_files"] = output_files

    # Update error if provided
    if error is not None:
        state["tasks"][task_id]["error"] = error

    # Update metadata
    state["metadata"]["last_updated_at"] = datetime.now(UTC).isoformat()

    # Atomic write
    atomic_write_state(state_path, state)

    return state


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
    """Resume from previous state, handling incomplete tasks.

    This function:
    1. Reads state.json
    2. For in_progress tasks, checks if output files are complete
    3. If complete, marks task as complete
    4. Otherwise, resets to pending
    5. Returns ordered list of pending task IDs

    Args:
        project_root: Root directory of the codebase

    Returns:
        List of pending task IDs in execution order
    """
    state_path = project_root / ".codebase-analysis" / "state.json"
    state = read_state(state_path)

    if state is None:
        return []

    tasks = state.get("tasks", {})
    modified = False

    # Step 1: Handle in_progress tasks
    for task_id, task in tasks.items():
        if task.get("status") != "in_progress":
            continue

        # Check all output files
        output_files = task.get("output_files", [])
        all_complete = True

        for output_file in output_files:
            file_path = project_root / output_file["path"]
            if not _check_file_complete(file_path):
                all_complete = False
                break

        if all_complete:
            # Files complete, just missing submit_analysis call
            task["status"] = "complete"
            task["completed_at"] = datetime.now(UTC).isoformat()
            for output_file in output_files:
                output_file["status"] = "complete"
            modified = True
        else:
            # Files incomplete, reset to pending
            task["status"] = "pending"
            task["started_at"] = None
            for output_file in output_files:
                output_file["status"] = "pending"
            modified = True

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

    # Write updated state if modified
    if modified:
        state["metadata"]["last_updated_at"] = datetime.now(UTC).isoformat()
        atomic_write_state(state_path, state)

    return ordered_pending
