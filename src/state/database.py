"""Async SQLite database for state persistence.

Uses WAL mode for concurrent read support. All writes are serialized
through aiosqlite. Schema is defined in _schema.py.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from ._schema import SCHEMA_SQL
from .models import (
    AnalysisResult, AnalysisTask, CheckpointRecord,
    DocNode, ModuleRecord, ProjectRecord,
)

logger = logging.getLogger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO-format datetime string from SQLite."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _json_loads(value: str | None, default: list | dict | None = None):
    """Safely load JSON from a SQLite TEXT column."""
    if value is None:
        return default if default is not None else []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


class Database:
    """Async SQLite database with WAL mode for state persistence."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create tables and enable WAL mode. Idempotent."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()
        logger.info("Database initialized at %s", self._db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Return the active database connection."""
        if self._conn is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._conn

    # -- Projects ------------------------------------------------------------

    async def insert_project(self, project: ProjectRecord) -> None:
        """Insert a new project record."""
        await self.connection.execute(
            """INSERT INTO projects (id, path, created_at, status, languages,
               file_count, function_count, class_count, total_lines)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project.id, project.path, project.created_at.isoformat(),
             project.status, json.dumps(project.languages), project.file_count,
             project.function_count, project.class_count, project.total_lines))
        await self.connection.commit()

    async def get_project(self, project_id: str) -> ProjectRecord | None:
        """Get a project by ID."""
        async with self.connection.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_project(row) if row else None

    async def get_latest_project(self) -> ProjectRecord | None:
        """Get the most recently created project."""
        async with self.connection.execute(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_project(row) if row else None

    async def update_project_status(self, project_id: str, status: str) -> None:
        """Update a project's status field."""
        await self.connection.execute(
            "UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
        await self.connection.commit()

    @staticmethod
    def _row_to_project(row: aiosqlite.Row) -> ProjectRecord:
        return ProjectRecord(
            id=row["id"], path=row["path"],
            created_at=_parse_dt(row["created_at"]),  # type: ignore[arg-type]
            status=row["status"], languages=_json_loads(row["languages"]),
            file_count=row["file_count"], function_count=row["function_count"],
            class_count=row["class_count"], total_lines=row["total_lines"])

    # -- Modules -------------------------------------------------------------

    async def insert_modules(self, modules: list[ModuleRecord]) -> None:
        """Bulk insert module records."""
        await self.connection.executemany(
            """INSERT OR REPLACE INTO modules (id, project_id, name, files,
               file_count, line_count, function_count, class_count,
               is_utility, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(m.id, m.project_id, m.name, json.dumps(m.files), m.file_count,
              m.line_count, m.function_count, m.class_count,
              int(m.is_utility), m.description) for m in modules])
        await self.connection.commit()

    async def get_modules(self, project_id: str) -> list[ModuleRecord]:
        """Get all modules for a project."""
        async with self.connection.execute(
            "SELECT * FROM modules WHERE project_id = ? ORDER BY name",
            (project_id,),
        ) as cur:
            return [self._row_to_module(r) for r in await cur.fetchall()]

    async def get_module(self, project_id: str, name: str) -> ModuleRecord | None:
        """Get a single module by project ID and name."""
        async with self.connection.execute(
            "SELECT * FROM modules WHERE project_id = ? AND name = ?",
            (project_id, name),
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_module(row) if row else None

    @staticmethod
    def _row_to_module(row: aiosqlite.Row) -> ModuleRecord:
        return ModuleRecord(
            id=row["id"], project_id=row["project_id"], name=row["name"],
            files=_json_loads(row["files"]), file_count=row["file_count"],
            line_count=row["line_count"], function_count=row["function_count"],
            class_count=row["class_count"], is_utility=bool(row["is_utility"]),
            description=row["description"])

    # -- Analysis Tasks ------------------------------------------------------

    async def create_tasks(self, tasks: list[AnalysisTask]) -> None:
        """Bulk insert analysis tasks."""
        await self.connection.executemany(
            """INSERT OR REPLACE INTO analysis_tasks (id, project_id,
               module_name, status, assigned_agent, batch_index,
               created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(t.id, t.project_id, t.module_name, t.status, t.assigned_agent,
              t.batch_index, t.created_at.isoformat(),
              t.completed_at.isoformat() if t.completed_at else None)
             for t in tasks])
        await self.connection.commit()

    async def get_next_pending_tasks(
        self, project_id: str, batch_size: int = 3,
    ) -> list[AnalysisTask]:
        """Atomically fetch and mark the next batch of pending tasks.

        Selects pending tasks in batch order and marks them as in_progress
        to prevent double-processing by concurrent agents.
        """
        async with self.connection.execute(
            """SELECT id FROM analysis_tasks
               WHERE project_id = ? AND status = 'pending'
               ORDER BY batch_index, created_at LIMIT ?""",
            (project_id, batch_size),
        ) as cur:
            rows = await cur.fetchall()
        if not rows:
            return []
        task_ids = [row["id"] for row in rows]
        ph = ",".join("?" for _ in task_ids)
        await self.connection.execute(
            f"UPDATE analysis_tasks SET status = 'in_progress' "
            f"WHERE id IN ({ph})", task_ids)
        await self.connection.commit()
        async with self.connection.execute(
            f"SELECT * FROM analysis_tasks WHERE id IN ({ph})", task_ids,
        ) as cur:
            return [self._row_to_task(r) for r in await cur.fetchall()]

    async def claim_task(self, task_id: str, agent_id: str) -> bool:
        """Attempt to claim a task. Only succeeds if status is 'pending'."""
        cur = await self.connection.execute(
            """UPDATE analysis_tasks SET status = 'in_progress', assigned_agent = ?
               WHERE id = ? AND status = 'pending'""", (agent_id, task_id))
        await self.connection.commit()
        return cur.rowcount > 0

    async def complete_task(self, task_id: str, status: str) -> None:
        """Mark a task as completed/failed/skipped."""
        await self.connection.execute(
            "UPDATE analysis_tasks SET status = ?, completed_at = ? WHERE id = ?",
            (status, datetime.now(UTC).isoformat(), task_id))
        await self.connection.commit()

    async def get_task_status_summary(self, project_id: str) -> dict:
        """Get aggregated task status counts for a project."""
        counts: dict[str, int] = {
            "pending": 0, "in_progress": 0, "completed": 0,
            "failed": 0, "skipped": 0}
        async with self.connection.execute(
            "SELECT status, COUNT(*) as cnt FROM analysis_tasks "
            "WHERE project_id = ? GROUP BY status", (project_id,),
        ) as cur:
            async for row in cur:
                counts[row["status"]] = row["cnt"]
        total = sum(counts.values())
        async with self.connection.execute(
            "SELECT module_name FROM analysis_tasks "
            "WHERE project_id = ? AND status = 'completed' ORDER BY batch_index",
            (project_id,),
        ) as cur:
            completed_modules = [row["module_name"] async for row in cur]
        progress = (counts["completed"] / total * 100) if total > 0 else 0.0
        return {"total": total, **counts, "completed_modules": completed_modules,
                "progress_percent": round(progress, 1)}

    @staticmethod
    def _row_to_task(row: aiosqlite.Row) -> AnalysisTask:
        return AnalysisTask(
            id=row["id"], project_id=row["project_id"],
            module_name=row["module_name"], status=row["status"],
            assigned_agent=row["assigned_agent"], batch_index=row["batch_index"],
            created_at=_parse_dt(row["created_at"]),  # type: ignore[arg-type]
            completed_at=_parse_dt(row["completed_at"]))

    # -- Analysis Results ----------------------------------------------------

    async def insert_result(self, result: AnalysisResult) -> None:
        """Insert an analysis result, replacing any existing one."""
        await self.connection.execute(
            """INSERT OR REPLACE INTO analysis_results
               (id, task_id, project_id, module_name, description,
                public_interfaces, key_data_structures, dependencies,
                dependents, patterns_identified, detailed_analysis,
                mermaid_diagram, token_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.id, result.task_id, result.project_id, result.module_name,
             result.description, json.dumps(result.public_interfaces),
             json.dumps(result.key_data_structures), json.dumps(result.dependencies),
             json.dumps(result.dependents), json.dumps(result.patterns_identified),
             result.detailed_analysis, result.mermaid_diagram,
             result.token_count, result.created_at.isoformat()))
        await self.connection.commit()

    async def get_result(self, project_id: str, module_name: str) -> AnalysisResult | None:
        """Get the analysis result for a specific module."""
        async with self.connection.execute(
            "SELECT * FROM analysis_results WHERE project_id = ? AND module_name = ?",
            (project_id, module_name),
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_result(row) if row else None

    async def get_all_results(self, project_id: str) -> list[AnalysisResult]:
        """Get all analysis results for a project."""
        async with self.connection.execute(
            "SELECT * FROM analysis_results WHERE project_id = ? ORDER BY module_name",
            (project_id,),
        ) as cur:
            return [self._row_to_result(r) for r in await cur.fetchall()]

    @staticmethod
    def _row_to_result(row: aiosqlite.Row) -> AnalysisResult:
        return AnalysisResult(
            id=row["id"], task_id=row["task_id"], project_id=row["project_id"],
            module_name=row["module_name"], description=row["description"],
            public_interfaces=_json_loads(row["public_interfaces"]),
            key_data_structures=_json_loads(row["key_data_structures"]),
            dependencies=_json_loads(row["dependencies"]),
            dependents=_json_loads(row["dependents"]),
            patterns_identified=_json_loads(row["patterns_identified"]),
            detailed_analysis=row["detailed_analysis"],
            mermaid_diagram=row["mermaid_diagram"], token_count=row["token_count"],
            created_at=_parse_dt(row["created_at"]))  # type: ignore[arg-type]

    # -- Checkpoints ---------------------------------------------------------

    async def save_checkpoint(self, checkpoint: CheckpointRecord) -> None:
        """Insert or replace a checkpoint record."""
        await self.connection.execute(
            """INSERT OR REPLACE INTO checkpoints
               (id, project_id, status, phase, analyzed_modules, pending_modules,
                total_modules, total_tokens_processed, errors, metadata,
                created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (checkpoint.id, checkpoint.project_id, checkpoint.status,
             checkpoint.phase, json.dumps(checkpoint.analyzed_modules),
             json.dumps(checkpoint.pending_modules), checkpoint.total_modules,
             checkpoint.total_tokens_processed, json.dumps(checkpoint.errors),
             json.dumps(checkpoint.metadata), checkpoint.created_at.isoformat(),
             checkpoint.updated_at.isoformat()))
        await self.connection.commit()

    async def get_latest_checkpoint(self, project_id: str) -> CheckpointRecord | None:
        """Get the most recent checkpoint for a project."""
        async with self.connection.execute(
            "SELECT * FROM checkpoints WHERE project_id = ? "
            "ORDER BY updated_at DESC LIMIT 1", (project_id,),
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_checkpoint(row) if row else None

    async def get_checkpoint(self, checkpoint_id: str) -> CheckpointRecord | None:
        """Get a checkpoint by its ID."""
        async with self.connection.execute(
            "SELECT * FROM checkpoints WHERE id = ?", (checkpoint_id,),
        ) as cur:
            row = await cur.fetchone()
            return self._row_to_checkpoint(row) if row else None

    @staticmethod
    def _row_to_checkpoint(row: aiosqlite.Row) -> CheckpointRecord:
        return CheckpointRecord(
            id=row["id"], project_id=row["project_id"],
            status=row["status"], phase=row["phase"],
            analyzed_modules=_json_loads(row["analyzed_modules"]),
            pending_modules=_json_loads(row["pending_modules"]),
            total_modules=row["total_modules"],
            total_tokens_processed=row["total_tokens_processed"],
            errors=_json_loads(row["errors"]),
            metadata=_json_loads(row["metadata"], default={}),
            created_at=_parse_dt(row["created_at"]),  # type: ignore[arg-type]
            updated_at=_parse_dt(row["updated_at"]))  # type: ignore[arg-type]

    # -- Doc Nodes -----------------------------------------------------------

    async def insert_doc_nodes(self, nodes: list[DocNode]) -> None:
        """Bulk insert documentation tree nodes."""
        await self.connection.executemany(
            """INSERT OR REPLACE INTO doc_nodes (id, project_id, path, level,
               target, token_budget, parent_path, children_paths, content,
               actual_tokens, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(n.id, n.project_id, n.path, n.level, n.target, n.token_budget,
              n.parent_path, json.dumps(n.children_paths), n.content,
              n.actual_tokens, n.status) for n in nodes])
        await self.connection.commit()

    async def get_doc_tree(self, project_id: str) -> list[DocNode]:
        """Get all doc nodes for a project, ordered by level and path."""
        async with self.connection.execute(
            "SELECT * FROM doc_nodes WHERE project_id = ? ORDER BY level, path",
            (project_id,),
        ) as cur:
            return [self._row_to_doc_node(r) for r in await cur.fetchall()]

    async def update_doc_node_content(
        self, node_id: str, content: str, actual_tokens: int,
    ) -> None:
        """Update a doc node with generated content."""
        await self.connection.execute(
            "UPDATE doc_nodes SET content = ?, actual_tokens = ?, "
            "status = 'generated' WHERE id = ?", (content, actual_tokens, node_id))
        await self.connection.commit()

    @staticmethod
    def _row_to_doc_node(row: aiosqlite.Row) -> DocNode:
        return DocNode(
            id=row["id"], project_id=row["project_id"], path=row["path"],
            level=row["level"], target=row["target"],
            token_budget=row["token_budget"], parent_path=row["parent_path"],
            children_paths=_json_loads(row["children_paths"]),
            content=row["content"], actual_tokens=row["actual_tokens"],
            status=row["status"])
