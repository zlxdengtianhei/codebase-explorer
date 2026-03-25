"""Unit tests for the state management layer.

Covers: models (immutability, field validation).

Note: Database and Checkpoint tests are excluded because the Database module
depends on src.state._schema which does not exist in the current codebase.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.state.models import (
    AnalysisResult,
    AnalysisTask,
    DocNode,
    ModuleRecord,
    ProjectRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(project_id: str = "proj_1", path: str = "/fake") -> ProjectRecord:
    return ProjectRecord(
        id=project_id,
        path=path,
        created_at=datetime.now(UTC),
        status="pending",
        languages=["python"],
        file_count=10,
        function_count=20,
        class_count=5,
        total_lines=1000,
    )


def _module(
    project_id: str = "proj_1",
    name: str = "core",
    module_id: str | None = None,
) -> ModuleRecord:
    return ModuleRecord(
        id=module_id or f"mod_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        name=name,
        files=["a.py", "b.py"],
        file_count=2,
        line_count=200,
        function_count=10,
        class_count=3,
    )


# ===========================================================================
# Models tests
# ===========================================================================


class TestProjectRecord:
    """ProjectRecord is frozen (immutable)."""

    def test_project_record_immutable(self):
        proj = _project()
        with pytest.raises(Exception):
            proj.status = "indexed"  # type: ignore[misc]

    def test_project_record_fields(self):
        proj = _project()
        assert proj.id == "proj_1"
        assert proj.languages == ["python"]
        assert proj.file_count == 10


class TestModuleRecord:
    """ModuleRecord field presence."""

    def test_module_record_fields(self):
        mod = _module()
        assert mod.project_id == "proj_1"
        assert mod.name == "core"
        assert mod.files == ["a.py", "b.py"]
        assert mod.file_count == 2
        assert mod.line_count == 200
        assert mod.function_count == 10
        assert mod.class_count == 3
        assert mod.is_utility is False
        assert mod.description is None


class TestDocNode:
    """DocNode creation."""

    def test_doc_node_creation(self):
        node = DocNode(
            id="dn_1",
            project_id="proj_1",
            path="core/OVERVIEW.md",
            level=1,
            target="core",
            token_budget=1200,
            parent_path="INDEX.md",
            children_paths=["core/detail1.md"],
            status="planned",
        )
        assert node.level == 1
        assert node.token_budget == 1200
        assert node.parent_path == "INDEX.md"
        assert node.children_paths == ["core/detail1.md"]
        assert node.content is None
        assert node.actual_tokens is None
