"""State management layer for Codebase Explorer.

Provides data models for analysis state and documentation tree information.

Public API:
    - Models: Immutable Pydantic data models (frozen=True).
"""

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
