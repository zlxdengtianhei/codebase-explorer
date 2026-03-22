"""Budget control layer for codebase analysis.

Provides token estimation and budget management utilities:

- ``estimate_tokens_from_chars`` -- character-based token estimation
- ``estimate_tokens_from_lines`` -- line-based token estimation
- ``estimate_file_tokens``       -- file-level token estimation
- ``estimate_module_tokens``     -- module-level aggregate estimation
- ``AnalysisBudgetController``   -- budget tracking and stop-condition enforcement

Data models (all frozen dataclasses):

- ``TokenEstimate``        -- per-file estimation result
- ``ModuleTokenEstimate``  -- per-module aggregate result
- ``BudgetAllocation``     -- allocation response from the controller
- ``BudgetStatus``         -- budget consumption snapshot
- ``FileInfo``             -- minimal file metadata (estimator-local)
"""

from src.budget.controller import (
    AnalysisBudgetController,
    BudgetAllocation,
    BudgetStatus,
)
from src.budget.estimator import (
    CHARS_PER_TOKEN,
    TOKENS_PER_LINE,
    FileInfo,
    ModuleTokenEstimate,
    TokenEstimate,
    estimate_file_tokens,
    estimate_module_tokens,
    estimate_tokens_from_chars,
    estimate_tokens_from_lines,
)

__all__ = [
    # Estimator functions
    "estimate_tokens_from_chars",
    "estimate_tokens_from_lines",
    "estimate_file_tokens",
    "estimate_module_tokens",
    # Controller
    "AnalysisBudgetController",
    # Data models
    "TokenEstimate",
    "ModuleTokenEstimate",
    "BudgetAllocation",
    "BudgetStatus",
    "FileInfo",
    # Constants
    "CHARS_PER_TOKEN",
    "TOKENS_PER_LINE",
]
