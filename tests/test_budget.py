"""Tests for src/budget/estimator.py -- token estimation functions.

Covers:
- estimate_tokens_from_chars with different languages and edge cases
- estimate_tokens_from_lines with different languages and edge cases
- estimate_module_tokens with various file compositions
- Boundary cases: 0 chars/lines, very large inputs, negative inputs
- Language-specific ratio correctness
"""
from __future__ import annotations

import pytest

from src.budget.estimator import (
    CHARS_PER_TOKEN,
    TOKENS_PER_LINE,
    FileInfo,
    ModuleTokenEstimate,
    estimate_module_tokens,
    estimate_tokens_from_chars,
    estimate_tokens_from_lines,
)


# ---------------------------------------------------------------------------
# estimate_tokens_from_chars
# ---------------------------------------------------------------------------


class TestEstimateTokensFromChars:
    """Tests for estimate_tokens_from_chars."""

    def test_python_ratio(self) -> None:
        """Python uses chars/3.5 ratio."""
        result = estimate_tokens_from_chars(350, "python")
        assert result == int(350 / 3.5)
        assert result == 100

    def test_typescript_ratio(self) -> None:
        """TypeScript uses chars/4.0 ratio."""
        result = estimate_tokens_from_chars(400, "typescript")
        assert result == int(400 / 4.0)
        assert result == 100

    def test_javascript_ratio(self) -> None:
        """JavaScript uses chars/3.8 ratio."""
        result = estimate_tokens_from_chars(380, "javascript")
        assert result == int(380 / 3.8)
        assert result == 100

    def test_default_ratio_for_unknown_language(self) -> None:
        """Unknown languages fall back to default ratio (3.8)."""
        result = estimate_tokens_from_chars(380, "rust")
        expected = int(380 / CHARS_PER_TOKEN["default"])
        assert result == expected

    def test_zero_chars(self) -> None:
        """Zero characters yields zero tokens."""
        assert estimate_tokens_from_chars(0, "python") == 0

    def test_negative_chars_raises(self) -> None:
        """Negative char_count raises ValueError."""
        with pytest.raises(ValueError, match="char_count must be >= 0"):
            estimate_tokens_from_chars(-1, "python")

    def test_very_large_input(self) -> None:
        """Very large character counts produce proportional token counts."""
        large_count = 10_000_000
        result = estimate_tokens_from_chars(large_count, "python")
        expected = int(large_count / 3.5)
        assert result == expected

    def test_small_input_rounds_down(self) -> None:
        """Small inputs that don't divide evenly are truncated via int()."""
        # 1 char / 3.5 = 0.2857... -> int() = 0
        assert estimate_tokens_from_chars(1, "python") == 0

    def test_case_insensitive_language(self) -> None:
        """Language lookup is case-insensitive."""
        upper = estimate_tokens_from_chars(350, "PYTHON")
        lower = estimate_tokens_from_chars(350, "python")
        assert upper == lower

    def test_returns_int(self) -> None:
        """Return type is always int."""
        result = estimate_tokens_from_chars(100, "python")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# estimate_tokens_from_lines
# ---------------------------------------------------------------------------


class TestEstimateTokensFromLines:
    """Tests for estimate_tokens_from_lines."""

    def test_python_ratio(self) -> None:
        """Python uses 12 tokens per line."""
        result = estimate_tokens_from_lines(10, "python")
        assert result == 10 * TOKENS_PER_LINE["python"]
        assert result == 120

    def test_typescript_ratio(self) -> None:
        """TypeScript uses 15 tokens per line."""
        result = estimate_tokens_from_lines(10, "typescript")
        assert result == 10 * TOKENS_PER_LINE["typescript"]
        assert result == 150

    def test_default_ratio_for_unknown_language(self) -> None:
        """Unknown languages fall back to default (15 tokens/line)."""
        result = estimate_tokens_from_lines(10, "go")
        assert result == 10 * TOKENS_PER_LINE["default"]

    def test_zero_lines(self) -> None:
        """Zero lines yields zero tokens."""
        assert estimate_tokens_from_lines(0, "python") == 0

    def test_negative_lines_raises(self) -> None:
        """Negative line_count raises ValueError."""
        with pytest.raises(ValueError, match="line_count must be >= 0"):
            estimate_tokens_from_lines(-5, "python")

    def test_very_large_line_count(self) -> None:
        """Very large line counts produce proportional results."""
        result = estimate_tokens_from_lines(1_000_000, "python")
        assert result == 1_000_000 * 12


# ---------------------------------------------------------------------------
# estimate_module_tokens
# ---------------------------------------------------------------------------


class TestEstimateModuleTokens:
    """Tests for estimate_module_tokens."""

    def test_empty_file_list(self) -> None:
        """Empty file list returns zeroed ModuleTokenEstimate."""
        result = estimate_module_tokens([], "empty_module")
        assert result == ModuleTokenEstimate(
            module_name="empty_module",
            total_chars=0,
            total_lines=0,
            estimated_tokens=0,
            language="unknown",
            file_count=0,
        )

    def test_single_file(self) -> None:
        """Single file produces correct aggregate."""
        files = [FileInfo(filepath="a.py", language="python", line_count=50, char_count=350)]
        result = estimate_module_tokens(files, "single")
        assert result.module_name == "single"
        assert result.total_chars == 350
        assert result.total_lines == 50
        assert result.estimated_tokens == int(350 / 3.5)
        assert result.language == "python"
        assert result.file_count == 1

    def test_multiple_files_same_language(self) -> None:
        """Multiple files in the same language are summed correctly."""
        files = [
            FileInfo(filepath="a.py", language="python", line_count=100, char_count=700),
            FileInfo(filepath="b.py", language="python", line_count=200, char_count=1400),
        ]
        result = estimate_module_tokens(files, "py_mod")
        assert result.total_chars == 2100
        assert result.total_lines == 300
        assert result.estimated_tokens == int(700 / 3.5) + int(1400 / 3.5)
        assert result.language == "python"
        assert result.file_count == 2

    def test_mixed_languages_primary_by_count(self) -> None:
        """Primary language is the one with the most files."""
        files = [
            FileInfo(filepath="a.py", language="python", line_count=10, char_count=100),
            FileInfo(filepath="b.ts", language="typescript", line_count=20, char_count=200),
            FileInfo(filepath="c.ts", language="typescript", line_count=30, char_count=300),
        ]
        result = estimate_module_tokens(files, "mixed")
        # TypeScript has 2 files vs Python's 1
        assert result.language == "typescript"

    def test_module_tokens_accumulation(self) -> None:
        """Token estimation accumulates per-file char-based estimates."""
        files = [
            FileInfo(filepath="a.py", language="python", line_count=10, char_count=70),
            FileInfo(filepath="b.js", language="javascript", line_count=20, char_count=76),
        ]
        result = estimate_module_tokens(files, "acc_mod")
        expected = int(70 / 3.5) + int(76 / 3.8)
        assert result.estimated_tokens == expected

    def test_result_is_frozen(self) -> None:
        """ModuleTokenEstimate is immutable (frozen dataclass)."""
        files = [FileInfo(filepath="a.py", language="python", line_count=10, char_count=100)]
        result = estimate_module_tokens(files, "frozen_test")
        with pytest.raises(AttributeError):
            result.total_chars = 999  # type: ignore[misc]

    def test_default_module_name(self) -> None:
        """Default module_name is empty string when not provided."""
        files = [FileInfo(filepath="x.py", language="python", line_count=1, char_count=10)]
        result = estimate_module_tokens(files)
        assert result.module_name == ""
