"""Pydantic data models for the state management layer.

All models use frozen=True to enforce immutability.
JSON-serializable fields (lists, dicts) are stored as JSON strings in SQLite.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Status/Phase type aliases for clarity
# ---------------------------------------------------------------------------

ProjectStatus = Literal["pending", "indexing", "indexed", "failed"]
TaskStatus = Literal["pending", "in_progress", "completed", "failed", "skipped"]
CheckpointStatus = Literal["in_progress", "completed", "interrupted", "failed"]
AnalysisPhase = Literal[
    "indexing", "module_analysis", "cross_reference", "doc_generation"
]
DocNodeStatus = Literal["planned", "generated", "failed"]


# ---------------------------------------------------------------------------
# ProjectRecord
# ---------------------------------------------------------------------------


class ProjectRecord(BaseModel, frozen=True):
    """Stored project index record.

    Represents a codebase that has been (or is being) indexed.
    """

    id: str
    path: str
    created_at: datetime
    status: ProjectStatus = "pending"
    languages: list[str] = Field(default_factory=list)
    file_count: int = 0
    function_count: int = 0
    class_count: int = 0
    total_lines: int = 0


# ---------------------------------------------------------------------------
# ModuleRecord
# ---------------------------------------------------------------------------


class ModuleRecord(BaseModel, frozen=True):
    """Stored module group record.

    Represents a Louvain-detected module group containing related files.
    """

    id: str
    project_id: str
    name: str
    files: list[str] = Field(default_factory=list)
    file_count: int = 0
    line_count: int = 0
    function_count: int = 0
    class_count: int = 0
    is_utility: bool = False
    description: str | None = None


# ---------------------------------------------------------------------------
# AnalysisTask
# ---------------------------------------------------------------------------


class AnalysisTask(BaseModel, frozen=True):
    """A single analysis task in the queue.

    Tasks are created by create_analysis_plan and processed in
    topological order. Mutual exclusion is enforced at the DB level.
    """

    id: str
    project_id: str
    module_name: str
    status: TaskStatus = "pending"
    assigned_agent: str | None = None
    batch_index: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------


class AnalysisResult(BaseModel, frozen=True):
    """Submitted analysis result for a module.

    Contains structured summary, public interfaces, dependency info,
    and optional detailed analysis text and Mermaid diagram.
    """

    id: str
    task_id: str
    project_id: str
    module_name: str
    description: str
    public_interfaces: list[str] = Field(default_factory=list)
    key_data_structures: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    patterns_identified: list[str] = Field(default_factory=list)
    detailed_analysis: str | None = None
    mermaid_diagram: str | None = None
    token_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# CheckpointRecord
# ---------------------------------------------------------------------------


class CheckpointRecord(BaseModel, frozen=True):
    """Analysis checkpoint for session resume.

    Captures the progress of an analysis session so that a new session
    can continue from where the previous one left off.
    """

    id: str
    project_id: str
    status: CheckpointStatus = "in_progress"
    phase: AnalysisPhase = "indexing"
    analyzed_modules: list[str] = Field(default_factory=list)
    pending_modules: list[str] = Field(default_factory=list)
    total_modules: int = 0
    total_tokens_processed: int = 0
    errors: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# DocNode
# ---------------------------------------------------------------------------


class DocNode(BaseModel, frozen=True):
    """A node in the documentation tree.

    Represents a planned or generated documentation file at a specific
    level in the progressive-disclosure hierarchy.
    """

    id: str
    project_id: str
    path: str  # e.g. "core/OVERVIEW.md"
    level: int  # 0=INDEX, 1=OVERVIEW, 2+=DETAIL
    target: str  # module or component name
    token_budget: int
    parent_path: str | None = None
    children_paths: list[str] = Field(default_factory=list)
    content: str | None = None
    actual_tokens: int | None = None
    status: DocNodeStatus = "planned"
