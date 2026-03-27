"""State management layer for Codebase Explorer.

Provides JSON-based state management and data models for analysis state.

Public API:
    - JSON Store: Atomic read/write operations for state.json
    - Models: Immutable Pydantic data models (frozen=True).
"""

from .json_store import (
    atomic_write_state,
    read_state,
    resume_from_state,
    update_task_status,
)
from .models import (
    AnalysisPhase,
    CheckpointStatus,
    DocNodeStatus,
    DocumentationMeta,
    OutputFileRecord,
    ProjectMeta,
    ProjectStatus,
    StateFile,
    TaskRecord,
    TaskStatus,
)

__all__ = [
    # JSON Store
    "atomic_write_state",
    "read_state",
    "update_task_status",
    "resume_from_state",
    # V5 Models
    "OutputFileRecord",
    "TaskRecord",
    "ProjectMeta",
    "DocumentationMeta",
    "StateFile",
    # Type aliases
    "ProjectStatus",
    "TaskStatus",
    "CheckpointStatus",
    "AnalysisPhase",
    "DocNodeStatus",
]
