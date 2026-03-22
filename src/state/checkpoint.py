"""Checkpoint management for analysis session resume.

Provides save/load/update operations for analysis checkpoints,
enabling agents to resume from where a previous session left off.
Round-trip consistency is guaranteed: save then load returns identical data.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from .database import Database
from .models import AnalysisResult, CheckpointRecord

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages analysis checkpoints for session resume.

    Wraps Database checkpoint operations with higher-level logic
    for creating, restoring, and updating checkpoints.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # -----------------------------------------------------------------------
    # Create
    # -----------------------------------------------------------------------

    async def create_checkpoint(
        self,
        project_id: str,
        phase: str,
        analyzed_modules: list[str],
        pending_modules: list[str],
        *,
        status: str = "in_progress",
        total_tokens_processed: int = 0,
        metadata: dict | None = None,
        errors: list[dict] | None = None,
    ) -> CheckpointRecord:
        """Create a new checkpoint capturing current analysis progress.

        Args:
            project_id: The project being analyzed.
            phase: Current analysis phase (indexing, module_analysis,
                   cross_reference, doc_generation).
            analyzed_modules: Modules already analyzed.
            pending_modules: Modules remaining to be analyzed.
            status: Checkpoint status (default: in_progress).
            total_tokens_processed: Cumulative tokens processed.
            metadata: Arbitrary JSON-serializable metadata.
            errors: List of error dicts encountered during analysis.

        Returns:
            The created CheckpointRecord.
        """
        now = datetime.now(UTC)
        total_modules = len(analyzed_modules) + len(pending_modules)

        checkpoint = CheckpointRecord(
            id=f"ckpt_{uuid.uuid4().hex[:8]}",
            project_id=project_id,
            status=status,  # type: ignore[arg-type]
            phase=phase,  # type: ignore[arg-type]
            analyzed_modules=list(analyzed_modules),
            pending_modules=list(pending_modules),
            total_modules=total_modules,
            total_tokens_processed=total_tokens_processed,
            errors=list(errors) if errors else [],
            metadata=dict(metadata) if metadata else {},
            created_at=now,
            updated_at=now,
        )

        await self._db.save_checkpoint(checkpoint)
        logger.info(
            "Checkpoint created: %s (project=%s, phase=%s, "
            "analyzed=%d, pending=%d)",
            checkpoint.id,
            project_id,
            phase,
            len(analyzed_modules),
            len(pending_modules),
        )
        return checkpoint

    # -----------------------------------------------------------------------
    # Restore
    # -----------------------------------------------------------------------

    async def restore_checkpoint(
        self, project_id: str, checkpoint_id: str | None = None
    ) -> tuple[CheckpointRecord, list[AnalysisResult]] | None:
        """Load a checkpoint and its associated analysis results.

        If checkpoint_id is provided, loads that specific checkpoint.
        Otherwise, loads the latest checkpoint for the project.

        Args:
            project_id: The project to restore.
            checkpoint_id: Optional specific checkpoint to restore.

        Returns:
            Tuple of (checkpoint, list of analysis results) or None
            if no checkpoint exists.
        """
        if checkpoint_id is not None:
            checkpoint = await self._db.get_checkpoint(checkpoint_id)
        else:
            checkpoint = await self._db.get_latest_checkpoint(project_id)

        if checkpoint is None:
            logger.info(
                "No checkpoint found for project=%s", project_id
            )
            return None

        # Load analysis results for all analyzed modules
        results = await self._db.get_all_results(project_id)

        # Filter to only results for modules listed in the checkpoint
        analyzed_set = frozenset(checkpoint.analyzed_modules)
        relevant_results = [
            r for r in results if r.module_name in analyzed_set
        ]

        logger.info(
            "Checkpoint restored: %s (phase=%s, analyzed=%d, "
            "pending=%d, results=%d)",
            checkpoint.id,
            checkpoint.phase,
            len(checkpoint.analyzed_modules),
            len(checkpoint.pending_modules),
            len(relevant_results),
        )
        return checkpoint, relevant_results

    # -----------------------------------------------------------------------
    # Update
    # -----------------------------------------------------------------------

    async def update_checkpoint(
        self,
        checkpoint_id: str,
        analyzed_modules: list[str],
        pending_modules: list[str],
        status: str,
        tokens_processed: int,
        *,
        phase: str | None = None,
        metadata: dict | None = None,
        errors: list[dict] | None = None,
    ) -> CheckpointRecord | None:
        """Update an existing checkpoint with new progress.

        Loads the existing checkpoint, applies updates, and saves.
        Returns the updated checkpoint or None if not found.

        Args:
            checkpoint_id: ID of the checkpoint to update.
            analyzed_modules: Updated list of analyzed modules.
            pending_modules: Updated list of pending modules.
            status: New status.
            tokens_processed: Cumulative tokens processed.
            phase: Optional new phase (keeps existing if None).
            metadata: Optional metadata update (merged with existing).
            errors: Optional errors update (replaces existing).

        Returns:
            Updated CheckpointRecord or None if checkpoint not found.
        """
        existing = await self._db.get_checkpoint(checkpoint_id)
        if existing is None:
            logger.warning(
                "Cannot update checkpoint: %s not found", checkpoint_id
            )
            return None

        # Merge metadata if provided
        merged_metadata = dict(existing.metadata)
        if metadata is not None:
            merged_metadata.update(metadata)

        total_modules = len(analyzed_modules) + len(pending_modules)

        updated = CheckpointRecord(
            id=existing.id,
            project_id=existing.project_id,
            status=status,  # type: ignore[arg-type]
            phase=phase if phase is not None else existing.phase,  # type: ignore[arg-type]
            analyzed_modules=list(analyzed_modules),
            pending_modules=list(pending_modules),
            total_modules=total_modules,
            total_tokens_processed=tokens_processed,
            errors=list(errors) if errors is not None else list(existing.errors),
            metadata=merged_metadata,
            created_at=existing.created_at,
            updated_at=datetime.now(UTC),
        )

        await self._db.save_checkpoint(updated)
        logger.info(
            "Checkpoint updated: %s (status=%s, analyzed=%d, pending=%d)",
            checkpoint_id,
            status,
            len(analyzed_modules),
            len(pending_modules),
        )
        return updated

    # -----------------------------------------------------------------------
    # Convenience: progress summary
    # -----------------------------------------------------------------------

    async def get_progress_summary(
        self, project_id: str
    ) -> dict | None:
        """Get a human-readable progress summary from the latest checkpoint.

        Returns:
            Dict with progress info or None if no checkpoint exists.
        """
        checkpoint = await self._db.get_latest_checkpoint(project_id)
        if checkpoint is None:
            return None

        progress_percent = (
            len(checkpoint.analyzed_modules) / checkpoint.total_modules * 100
            if checkpoint.total_modules > 0
            else 0.0
        )

        return {
            "checkpoint_id": checkpoint.id,
            "phase": checkpoint.phase,
            "status": checkpoint.status,
            "analyzed_count": len(checkpoint.analyzed_modules),
            "pending_count": len(checkpoint.pending_modules),
            "total_modules": checkpoint.total_modules,
            "progress_percent": round(progress_percent, 1),
            "tokens_processed": checkpoint.total_tokens_processed,
            "error_count": len(checkpoint.errors),
            "updated_at": checkpoint.updated_at.isoformat(),
        }
