"""Tests for src/state/models.py — all Pydantic data models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.state.models import (
    DocumentationMeta,
    OutputFileRecord,
    ProjectMeta,
    StateFile,
    TaskRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 25, 12, 0, 0, tzinfo=UTC)


def _minimal_project_meta(**overrides) -> ProjectMeta:
    defaults = dict(id="proj-1", root_path="/tmp/repo", analyzed_at=_NOW)
    return ProjectMeta(**(defaults | overrides))


def _minimal_state_file(**overrides) -> StateFile:
    defaults = dict(project=_minimal_project_meta())
    return StateFile(**(defaults | overrides))


# ===================================================================
# V2 Models
# ===================================================================


class TestOutputFileRecord:
    def test_defaults(self):
        rec = OutputFileRecord(path="docs/index.md")
        assert rec.path == "docs/index.md"
        assert rec.tokens_written is None
        assert rec.status == "pending"

    def test_full_construction(self):
        rec = OutputFileRecord(path="out.md", tokens_written=500, status="complete")
        assert rec.tokens_written == 500
        assert rec.status == "complete"

    def test_frozen_immutability(self):
        rec = OutputFileRecord(path="x.md")
        with pytest.raises(ValidationError):
            rec.path = "y.md"


class TestTaskRecord:
    def test_defaults(self):
        rec = TaskRecord(type="batch")
        assert rec.status == "pending"
        assert rec.cone_ids == []
        assert rec.estimated_tokens == 0
        assert rec.output_files == []
        assert rec.split_subtasks is None
        assert rec.depends_on is None
        assert rec.started_at is None
        assert rec.completed_at is None
        assert rec.error is None

    def test_full_construction(self):
        rec = TaskRecord(
            type="split",
            status="in_progress",
            cone_ids=["cone-a", "cone-b"],
            estimated_tokens=5000,
            output_files=[OutputFileRecord(path="a.md")],
            split_subtasks=["sub-1"],
            depends_on=["task-0"],
            started_at=_NOW,
            error="timeout",
        )
        assert rec.type == "split"
        assert len(rec.cone_ids) == 2
        assert rec.output_files[0].path == "a.md"

    def test_frozen_immutability(self):
        rec = TaskRecord(type="single")
        with pytest.raises(ValidationError):
            rec.status = "failed"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            TaskRecord(type="unknown")

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            TaskRecord(type="batch", status="running")


class TestProjectMeta:
    def test_required_fields(self):
        pm = _minimal_project_meta()
        assert pm.id == "proj-1"
        assert pm.root_path == "/tmp/repo"
        assert pm.analyzed_at == _NOW

    def test_defaults(self):
        pm = _minimal_project_meta()
        assert pm.languages == []
        assert pm.file_count == 0
        assert pm.function_count == 0
        assert pm.class_count == 0
        assert pm.total_lines == 0
        assert pm.total_chars == 0
        assert pm.total_tokens == 0
        assert pm.analysis_status == "pending"

    def test_frozen_immutability(self):
        pm = _minimal_project_meta()
        with pytest.raises(ValidationError):
            pm.id = "changed"

    def test_serialization_roundtrip(self):
        pm = _minimal_project_meta(languages=["python", "javascript"], file_count=42)
        data = pm.model_dump()
        restored = ProjectMeta.model_validate(data)
        assert restored == pm
        assert restored.languages == ["python", "javascript"]
        assert restored.file_count == 42

    def test_invalid_analysis_status(self):
        with pytest.raises(ValidationError):
            _minimal_project_meta(analysis_status="done")


class TestDocumentationMeta:
    def test_defaults(self):
        dm = DocumentationMeta()
        assert dm.output_dir == ".codebase-docs/"
        assert dm.index_written is False
        assert dm.overviews_written == 0
        assert dm.details_written == 0
        assert dm.snippets_written == 0
        assert dm.total_planned == 0
        assert dm.source_files_covered == []
        assert dm.source_file_coverage_percent == 0.0
        assert dm.total_tokens_written == 0

    def test_frozen_immutability(self):
        dm = DocumentationMeta()
        with pytest.raises(ValidationError):
            dm.index_written = True


class TestStateFile:
    def test_minimal_construction(self):
        sf = _minimal_state_file()
        assert sf.schema_version == "2.0"
        assert sf.project.id == "proj-1"
        assert sf.analysis_files == {}
        assert sf.tasks == {}
        assert isinstance(sf.documentation, DocumentationMeta)
        assert sf.metadata == {}

    def test_full_construction(self):
        task = TaskRecord(type="batch", status="complete", cone_ids=["c1"])
        sf = _minimal_state_file(
            schema_version="2.1",
            analysis_files={"graph": "graph.json"},
            tasks={"task-1": task},
            metadata={"run_id": "abc"},
        )
        assert sf.schema_version == "2.1"
        assert sf.tasks["task-1"].status == "complete"
        assert sf.analysis_files["graph"] == "graph.json"

    def test_frozen_immutability(self):
        sf = _minimal_state_file()
        with pytest.raises(ValidationError):
            sf.schema_version = "3.0"

    def test_serialization_roundtrip(self):
        task = TaskRecord(type="single", cone_ids=["x"])
        sf = _minimal_state_file(tasks={"t1": task})
        data = sf.model_dump()
        restored = StateFile.model_validate(data)
        assert restored == sf
        assert restored.tasks["t1"].cone_ids == ["x"]

    def test_requires_project(self):
        with pytest.raises(ValidationError):
            StateFile()


