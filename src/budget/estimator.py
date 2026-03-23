"""Token estimation for source code files and modules.

Provides language-aware heuristic estimation of token counts
from character counts and line counts. Uses empirical
chars-per-token and tokens-per-line ratios for supported languages.

No external dependencies -- pure Python stdlib.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language-specific estimation ratios
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN: dict[str, float] = {
    "python": 3.5,
    "typescript": 4.0,
    "javascript": 3.8,
    "default": 3.8,
}

TOKENS_PER_LINE: dict[str, int] = {
    "python": 12,
    "typescript": 15,
    "javascript": 15,
    "default": 15,
}

# ---------------------------------------------------------------------------
# Data models (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenEstimate:
    """Immutable token estimate for a single code unit."""
    source_tokens: int
    char_count: int
    line_count: int
    language: str
    method: str  # "chars" | "lines" | "tiktoken"


@dataclass(frozen=True)
class ModuleTokenEstimate:
    """Immutable aggregate token estimate for a module."""
    module_name: str
    total_chars: int
    total_lines: int
    estimated_tokens: int
    language: str
    file_count: int


@dataclass(frozen=True)
class FileInfo:
    """Minimal file metadata required by the estimator.

    Local definition so ``budget/`` stays decoupled from ``parser/``.
    Callers may pass any object with matching attributes.
    """
    filepath: str
    language: str
    line_count: int
    char_count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _chars_ratio(language: str) -> float:
    return CHARS_PER_TOKEN.get(language.lower(), CHARS_PER_TOKEN["default"])


def _line_ratio(language: str) -> int:
    return TOKENS_PER_LINE.get(language.lower(), TOKENS_PER_LINE["default"])


# ---------------------------------------------------------------------------
# Public estimation functions
# ---------------------------------------------------------------------------

def estimate_tokens_from_chars(char_count: int, language: str = "python") -> int:
    """Estimate token count from character count.  Accuracy: +/- 15%.

    This is the V2 primary estimation method.

    Args:
        char_count: Number of characters in the source code (>= 0).
        language: Programming language for ratio lookup.

    Returns:
        Estimated token count (always >= 0).
    """
    if char_count < 0:
        raise ValueError(f"char_count must be >= 0, got {char_count}")
    ratio = _chars_ratio(language)
    estimated = int(char_count / ratio)
    logger.info(
        "[estimator] estimate_tokens_from_chars: %d chars / %.1f = %d tokens (%s)",
        char_count, ratio, estimated, language,
    )
    return estimated


def estimate_tokens_from_lines(line_count: int, language: str = "python") -> int:
    """Estimate token count from line count.  Accuracy: +/- 20%.

    .. deprecated:: V2
        Use :func:`estimate_tokens_from_chars` instead for better accuracy.

    Args:
        line_count: Number of source code lines (>= 0).
        language: Programming language for ratio lookup.

    Returns:
        Estimated token count (always >= 0).
    """
    logger.warning(
        "[estimator] estimate_tokens_from_lines deprecated, use estimate_tokens_from_chars"
    )
    if line_count < 0:
        raise ValueError(f"line_count must be >= 0, got {line_count}")
    tpl = _line_ratio(language)
    estimated = line_count * tpl
    logger.debug(
        "estimate_tokens_from_lines: lines=%d lang=%s tpl=%d -> tokens=%d",
        line_count, language, tpl, estimated,
    )
    return estimated


def estimate_file_tokens(filepath: str, language: str = "python") -> TokenEstimate:
    """Estimate tokens for a single source file by reading it from disk.

    Raises:
        FileNotFoundError: If *filepath* does not exist.
    """
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    char_count = len(content)
    line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    tokens = estimate_tokens_from_chars(char_count, language)
    return TokenEstimate(
        source_tokens=tokens,
        char_count=char_count,
        line_count=line_count,
        language=language,
        method="chars",
    )


def estimate_module_tokens(
    files: list[FileInfo],
    module_name: str = "",
) -> ModuleTokenEstimate:
    """Estimate tokens for all files in a module.

    Iterates over *files*, accumulating per-file character-based
    estimates.  Primary language is determined by file count majority.

    Args:
        files: List of ``FileInfo`` (or duck-typed compatible) objects.
        module_name: Human-readable module name for the result.

    Returns:
        ModuleTokenEstimate summarising the module.
    """
    if not files:
        return ModuleTokenEstimate(
            module_name=module_name, total_chars=0, total_lines=0,
            estimated_tokens=0, language="unknown", file_count=0,
        )

    total_chars = 0
    total_lines = 0
    total_tokens = 0
    language_counts: dict[str, int] = {}

    for f in files:
        total_chars += f.char_count
        total_lines += f.line_count
        total_tokens += estimate_tokens_from_chars(f.char_count, f.language)
        language_counts[f.language] = language_counts.get(f.language, 0) + 1

    primary_language = max(language_counts, key=lambda lang: language_counts[lang])
    result = ModuleTokenEstimate(
        module_name=module_name,
        total_chars=total_chars,
        total_lines=total_lines,
        estimated_tokens=total_tokens,
        language=primary_language,
        file_count=len(files),
    )
    logger.info(
        "estimate_module_tokens: module=%s files=%d chars=%d lines=%d tokens=%d lang=%s",
        module_name, len(files), total_chars, total_lines, total_tokens, primary_language,
    )
    return result
