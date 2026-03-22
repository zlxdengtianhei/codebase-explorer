"""State management layer for Codebase Explorer.

Provides SQLite-backed persistence for analysis state, checkpoints,
and documentation tree information.

Public API:
    - Database: Async SQLite CRUD operations with WAL mode.
    - CheckpointManager: Checkpoint save/restore for session resume.
    - Models: Immutable Pydantic data models (frozen=True).
"""

from .checkpoint import CheckpointManager
from .database import Database
from .models import (
    AnalysisPhase,
    AnalysisResult,
    AnalysisTask,
    CheckpointRecord,
    CheckpointStatus,
    DocNode,
    DocNodeStatus,
    ModuleRecord,
    ProjectRecord,
    ProjectStatus,
    TaskStatus,
)

__all__ = [
    # Core classes
    "Database",
    "CheckpointManager",
    # Models
    "ProjectRecord",
    "ModuleRecord",
    "AnalysisTask",
    "AnalysisResult",
    "CheckpointRecord",
    "DocNode",
    # Type aliases
    "ProjectStatus",
    "TaskStatus",
    "CheckpointStatus",
    "AnalysisPhase",
    "DocNodeStatus",
]
