"""Analysis budget controller for progressive codebase exploration.

Tracks token consumption across modules, enforces stop conditions,
and exposes an MCP-compatible status interface.

Stop rules (ordered by severity):
  1. Total budget exhausted (>= 95% usage).
  2. Single module exceeds max-tokens-per-module limit.
  3. Analysis wall-clock time exceeds the configured limit.
  4. Consecutive analysis failures exceed threshold.
  5. All modules have been analysed (normal completion).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BudgetAllocation:
    """Result of requesting budget for a module analysis."""
    module_name: str
    allocated_tokens: int
    remaining_budget: int
    warning: str | None


@dataclass(frozen=True)
class BudgetStatus:
    """Snapshot of the current budget consumption state."""
    total_budget: int
    used_tokens: int
    remaining_tokens: int
    usage_percent: float
    modules_analyzed: int
    modules_remaining: int
    should_stop: bool
    stop_reason: str | None


@dataclass
class _ModuleRecord:
    """Per-module tracking record (mutable, internal only)."""
    allocated_tokens: int = 0
    actual_tokens: int = 0
    completed: bool = False


class AnalysisBudgetController:
    """Controls token budget allocation and enforces stop conditions.

    Public methods return immutable frozen dataclass instances.
    Internal state is mutated only through ``allocate`` / ``record_usage``.
    """

    def __init__(
        self,
        total_budget: int,
        max_tokens_per_module: int = 10_000,
        *,
        max_elapsed_minutes: float = 15.0,
        max_consecutive_failures: int = 3,
        total_modules: int = 0,
    ) -> None:
        if total_budget <= 0:
            raise ValueError(f"total_budget must be > 0, got {total_budget}")
        if max_tokens_per_module <= 0:
            raise ValueError(f"max_tokens_per_module must be > 0, got {max_tokens_per_module}")

        self._total_budget = total_budget
        self._max_tokens_per_module = max_tokens_per_module
        self._max_elapsed_minutes = max_elapsed_minutes
        self._max_consecutive_failures = max_consecutive_failures
        self._modules: dict[str, _ModuleRecord] = {}
        self._total_used: int = 0
        self._total_modules: int = total_modules
        self._consecutive_failures: int = 0
        self._start_time: float = time.monotonic()

    def set_total_modules(self, count: int) -> None:
        """Update the total expected module count (for progress tracking)."""
        self._total_modules = count

    def allocate(self, module_name: str, estimated_tokens: int) -> BudgetAllocation:
        """Request a budget allocation for analysing *module_name*.

        Caps the allocation at ``max_tokens_per_module`` and at
        remaining budget. Emits a warning when either cap is hit.
        """
        remaining = self._total_budget - self._total_used
        capped = min(estimated_tokens, self._max_tokens_per_module)
        allocated = min(capped, remaining)

        warning: str | None = None
        if estimated_tokens > self._max_tokens_per_module:
            warning = (
                f"Requested {estimated_tokens} tokens exceeds per-module "
                f"limit ({self._max_tokens_per_module}); capped to {allocated}"
            )
            logger.warning("allocate(%s): %s", module_name, warning)
        elif allocated < capped:
            warning = (
                f"Insufficient remaining budget ({remaining} tokens); "
                f"allocated {allocated} instead of {capped}"
            )
            logger.warning("allocate(%s): %s", module_name, warning)

        self._modules[module_name] = _ModuleRecord(allocated_tokens=allocated)
        logger.info(
            "allocate: module=%s requested=%d allocated=%d remaining=%d",
            module_name, estimated_tokens, allocated, remaining - allocated,
        )
        return BudgetAllocation(
            module_name=module_name,
            allocated_tokens=allocated,
            remaining_budget=remaining - allocated,
            warning=warning,
        )

    def record_usage(self, module_name: str, actual_tokens: int) -> None:
        """Record actual token usage after analysing *module_name*."""
        if actual_tokens < 0:
            raise ValueError(f"actual_tokens must be >= 0, got {actual_tokens}")
        record = self._modules.get(module_name)
        if record is None:
            raise KeyError(f"Module '{module_name}' has no allocation. Call allocate() first.")

        record.actual_tokens = actual_tokens
        record.completed = True
        self._total_used += actual_tokens
        self._consecutive_failures = 0
        logger.info(
            "record_usage: module=%s actual=%d total_used=%d/%d (%.1f%%)",
            module_name, actual_tokens, self._total_used,
            self._total_budget, self._usage_percent,
        )

    def record_failure(self, module_name: str) -> None:
        """Record that analysis of *module_name* failed (increments failure counter)."""
        self._consecutive_failures += 1
        logger.warning(
            "record_failure: module=%s consecutive_failures=%d",
            module_name, self._consecutive_failures,
        )

    def should_stop(self) -> tuple[bool, str]:
        """Evaluate five stop rules; return (should_stop, reason)."""
        # Rule 1: total budget exhaustion (>= 95%)
        if self._usage_percent >= 95.0:
            return True, "budget_exhausted"
        # Rule 2: single module over per-module limit
        for name, rec in self._modules.items():
            if rec.actual_tokens > self._max_tokens_per_module:
                return True, f"module_over_limit:{name}"
        # Rule 3: time limit exceeded
        if self._elapsed_minutes > self._max_elapsed_minutes:
            return True, "time_limit_exceeded"
        # Rule 4: consecutive failures
        if self._consecutive_failures >= self._max_consecutive_failures:
            return True, "consecutive_failures"
        # Rule 5: all modules completed
        completed = sum(1 for r in self._modules.values() if r.completed)
        if self._total_modules > 0 and completed >= self._total_modules:
            return True, "all_modules_completed"
        return False, ""

    def get_status(self) -> BudgetStatus:
        """Return an immutable snapshot of the current budget state."""
        completed = sum(1 for r in self._modules.values() if r.completed)
        remaining_modules = max(0, self._total_modules - completed)
        stop, reason = self.should_stop()
        return BudgetStatus(
            total_budget=self._total_budget,
            used_tokens=self._total_used,
            remaining_tokens=self._total_budget - self._total_used,
            usage_percent=round(self._usage_percent, 2),
            modules_analyzed=completed,
            modules_remaining=remaining_modules,
            should_stop=stop,
            stop_reason=reason if stop else None,
        )

    def check_budget_status(self, project_id: str) -> dict:
        """MCP-compatible tool interface returning a plain dict for serialisation."""
        status = self.get_status()
        return {
            "project_id": project_id,
            "status": "ok",
            "summary": (
                f"Budget {status.usage_percent:.1f}% used "
                f"({status.used_tokens}/{status.total_budget} tokens). "
                f"{status.modules_analyzed} modules done, "
                f"{status.modules_remaining} remaining."
            ),
            "data": {
                "total_budget": status.total_budget,
                "used_tokens": status.used_tokens,
                "remaining_tokens": status.remaining_tokens,
                "usage_percent": status.usage_percent,
                "modules_analyzed": status.modules_analyzed,
                "modules_remaining": status.modules_remaining,
                "should_stop": status.should_stop,
                "stop_reason": status.stop_reason,
                "elapsed_minutes": round(self._elapsed_minutes, 2),
            },
        }

    @property
    def _usage_percent(self) -> float:
        if self._total_budget == 0:
            return 100.0
        return (self._total_used / self._total_budget) * 100.0

    @property
    def _elapsed_minutes(self) -> float:
        return (time.monotonic() - self._start_time) / 60.0
