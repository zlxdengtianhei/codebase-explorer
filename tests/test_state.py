"""Unit tests for the state management layer.

Covers: models (immutability, field validation), database (CRUD, mutual
exclusion, optimistic lock, status aggregation), and checkpoint (round-trip
consistency, latest-checkpoint, metadata serialization).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.state.checkpoint import CheckpointManager
from src.state.database import Database
from src.state.models import (
    AnalysisResult,
    AnalysisTask,
    CheckpointRecord,
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


def _task(
    project_id: str = "proj_1",
    module_name: str = "core",
    task_id: str | None = None,
    batch_index: int = 0,
) -> AnalysisTask:
    return AnalysisTask(
        id=task_id or f"task_{uuid.uuid4().hex[:8]}",
        project_id=project_id,
        module_name=module_name,
        status="pending",
        batch_index=batch_index,
    )


def _result(
    task_id: str,
    project_id: str = "proj_1",
    module_name: str = "core",
) -> AnalysisResult:
    return AnalysisResult(
        id=f"res_{uuid.uuid4().hex[:8]}",
        task_id=task_id,
        project_id=project_id,
        module_name=module_name,
        description="Module analysis result",
        public_interfaces=["func_a", "ClassB"],
        key_data_structures=["dict_x"],
        dependencies=["utils"],
        dependents=["api"],
        patterns_identified=["singleton"],
        detailed_analysis="Detailed text here.",
        mermaid_diagram="graph TD; A-->B;",
        token_count=500,
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


# ===========================================================================
# Database tests (async, in-memory SQLite)
# ===========================================================================


@pytest.mark.asyncio
class TestDatabaseSchema:
    """Verify schema creation."""

    async def test_init_db(self, db: Database):
        """Tables should exist after initialize()."""
        tables_expected = {
            "projects",
            "modules",
            "analysis_tasks",
            "analysis_results",
            "checkpoints",
            "doc_nodes",
            "schema_version",
        }
        async with db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cur:
            rows = await cur.fetchall()
        table_names = {row["name"] for row in rows}
        assert tables_expected.issubset(table_names)


@pytest.mark.asyncio
class TestDatabaseProjects:
    """Insert and retrieve project records."""

    async def test_create_project(self, db: Database):
        proj = _project()
        await db.insert_project(proj)
        loaded = await db.get_project("proj_1")
        assert loaded is not None
        assert loaded.id == "proj_1"
        assert loaded.path == "/fake"
        assert loaded.languages == ["python"]
        assert loaded.file_count == 10


@pytest.mark.asyncio
class TestDatabaseModules:
    """Insert and retrieve module records."""

    async def test_create_module(self, db: Database):
        await db.insert_project(_project())
        mod = _module(module_id="mod_1")
        await db.insert_modules([mod])
        modules = await db.get_modules("proj_1")
        assert len(modules) == 1
        assert modules[0].name == "core"
        assert modules[0].files == ["a.py", "b.py"]


@pytest.mark.asyncio
class TestDatabaseTasks:
    """Task queue: pending fetch, claim, status summary."""

    async def test_get_next_pending_tasks(self, db: Database):
        """get_next_pending_tasks marks them in_progress."""
        await db.insert_project(_project())
        t1 = _task(task_id="t1", module_name="mod_a", batch_index=0)
        t2 = _task(task_id="t2", module_name="mod_b", batch_index=1)
        await db.create_tasks([t1, t2])

        batch = await db.get_next_pending_tasks("proj_1", batch_size=1)
        assert len(batch) == 1
        assert batch[0].status == "in_progress"

        # The claimed task should no longer appear as pending
        batch2 = await db.get_next_pending_tasks("proj_1", batch_size=10)
        assert len(batch2) == 1
        assert batch2[0].id == "t2"

    async def test_claim_task_optimistic_lock(self, db: Database):
        """Second claim on the same task should fail."""
        await db.insert_project(_project())
        t = _task(task_id="t_lock")
        await db.create_tasks([t])

        first = await db.claim_task("t_lock", "agent_1")
        assert first is True

        second = await db.claim_task("t_lock", "agent_2")
        assert second is False

    async def test_submit_result(self, db: Database):
        """Insert and retrieve an analysis result."""
        await db.insert_project(_project())
        t = _task(task_id="t_res")
        await db.create_tasks([t])

        res = _result(task_id="t_res")
        await db.insert_result(res)

        loaded = await db.get_result("proj_1", "core")
        assert loaded is not None
        assert loaded.description == "Module analysis result"
        assert loaded.public_interfaces == ["func_a", "ClassB"]
        assert loaded.token_count == 500

    async def test_get_task_status_summary(self, db: Database):
        """Aggregated status counts."""
        await db.insert_project(_project())
        tasks = [
            _task(task_id="s1", module_name="m1"),
            _task(task_id="s2", module_name="m2"),
            _task(task_id="s3", module_name="m3"),
        ]
        await db.create_tasks(tasks)

        # Complete one, leave others pending
        await db.claim_task("s1", "agent")
        await db.complete_task("s1", "completed")

        summary = await db.get_task_status_summary("proj_1")
        assert summary["total"] == 3
        assert summary["completed"] == 1
        assert summary["pending"] == 2
        assert summary["completed_modules"] == ["m1"]
        assert 0.0 < summary["progress_percent"] <= 100.0


# ===========================================================================
# Checkpoint tests (async)
# ===========================================================================


@pytest.mark.asyncio
class TestCheckpoint:
    """Checkpoint save/load round-trip and latest selection."""

    async def test_save_and_load_checkpoint(self, db: Database):
        """Round-trip: save then load returns identical data."""
        await db.insert_project(_project())
        mgr = CheckpointManager(db)

        cp = await mgr.create_checkpoint(
            project_id="proj_1",
            phase="module_analysis",
            analyzed_modules=["core"],
            pending_modules=["api", "utils"],
            total_tokens_processed=1500,
            metadata={"version": "1.0"},
        )

        result = await mgr.restore_checkpoint("proj_1", cp.id)
        assert result is not None
        loaded, _ = result
        assert loaded.id == cp.id
        assert loaded.phase == "module_analysis"
        assert loaded.analyzed_modules == ["core"]
        assert loaded.pending_modules == ["api", "utils"]
        assert loaded.total_tokens_processed == 1500

    async def test_load_latest_checkpoint(self, db: Database):
        """Multiple checkpoints: restore picks the latest by updated_at."""
        await db.insert_project(_project())
        mgr = CheckpointManager(db)

        await mgr.create_checkpoint(
            project_id="proj_1",
            phase="indexing",
            analyzed_modules=[],
            pending_modules=["a", "b"],
        )
        cp2 = await mgr.create_checkpoint(
            project_id="proj_1",
            phase="module_analysis",
            analyzed_modules=["a"],
            pending_modules=["b"],
        )

        result = await mgr.restore_checkpoint("proj_1")
        assert result is not None
        loaded, _ = result
        assert loaded.id == cp2.id
        assert loaded.phase == "module_analysis"

    async def test_checkpoint_metadata(self, db: Database):
        """JSON metadata survives serialization round-trip."""
        await db.insert_project(_project())
        mgr = CheckpointManager(db)

        metadata = {
            "model": "gpt-4o",
            "config": {"temperature": 0.3, "tags": ["alpha", "beta"]},
        }
        cp = await mgr.create_checkpoint(
            project_id="proj_1",
            phase="indexing",
            analyzed_modules=[],
            pending_modules=["x"],
            metadata=metadata,
        )

        loaded = await db.get_checkpoint(cp.id)
        assert loaded is not None
        assert loaded.metadata["model"] == "gpt-4o"
        assert loaded.metadata["config"]["temperature"] == 0.3
        assert loaded.metadata["config"]["tags"] == ["alpha", "beta"]
