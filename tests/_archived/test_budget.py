"""Unit tests for the budget management layer.

Covers: estimator (char/line/module token estimation, zero-input edge case).
"""
from __future__ import annotations

import pytest

from src.budget.estimator import (
    CHARS_PER_TOKEN,
    TOKENS_PER_LINE,
    FileInfo,
    estimate_module_tokens,
    estimate_tokens_from_chars,
    estimate_tokens_from_lines,
)


# ===========================================================================
# Estimator tests
# ===========================================================================


class TestEstimateTokensFromChars:
    """Character-based token estimation."""

    def test_estimate_tokens_from_chars_python(self):
        chars = 3500
        tokens = estimate_tokens_from_chars(chars, "python")
        expected = int(chars / CHARS_PER_TOKEN["python"])
        assert tokens == expected

    def test_estimate_tokens_from_chars_typescript(self):
        chars = 4000
        tokens = estimate_tokens_from_chars(chars, "typescript")
        expected = int(chars / CHARS_PER_TOKEN["typescript"])
        assert tokens == expected

    def test_zero_input_chars(self):
        assert estimate_tokens_from_chars(0, "python") == 0


class TestEstimateTokensFromLines:
    """Line-based token estimation."""

    def test_estimate_tokens_from_lines(self):
        lines = 100
        tokens = estimate_tokens_from_lines(lines, "python")
        expected = lines * TOKENS_PER_LINE["python"]
        assert tokens == expected

    def test_zero_input_lines(self):
        assert estimate_tokens_from_lines(0, "python") == 0


class TestEstimateModuleTokens:
    """Module-level token aggregation."""

    def test_estimate_module_tokens(self):
        files = [
            FileInfo(filepath="a.py", language="python", line_count=50, char_count=1750),
            FileInfo(filepath="b.py", language="python", line_count=80, char_count=2800),
        ]
        result = estimate_module_tokens(files, module_name="core")
        assert result.module_name == "core"
        assert result.file_count == 2
        assert result.total_chars == 1750 + 2800
        assert result.total_lines == 50 + 80
        assert result.estimated_tokens > 0
        assert result.language == "python"

    def test_estimate_module_tokens_empty(self):
        result = estimate_module_tokens([], module_name="empty")
        assert result.estimated_tokens == 0
        assert result.file_count == 0
        assert result.language == "unknown"
