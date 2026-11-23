"""Release notes and both READMEs quote measured numbers with their basis and their limit."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def bullets(text: str) -> list[str]:
    """The newest section that has entries ("Unreleased" while it has any, else the latest release),
    one whitespace-collapsed string per top-level bullet."""
    for section in text.split("\n## ")[1:]:
        body = section.split("\n", 1)[1] if "\n" in section else ""
        entries = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n(?=- )", body) if part.strip().startswith("- ")]
        if entries:
            return entries
    return []


def test_a_score_quoted_in_a_release_note_states_the_rubric_limit():
    scored = [entry for entry in bullets(_read("CHANGELOG.md")) if "CodeWikiBench" in entry]
    assert scored, "no release note quotes a CodeWikiBench score"
    for entry in scored:
        assert "rubric" in entry and "not that the page is better written" in entry, entry


def test_the_read_numbers_agree_between_the_release_note_and_the_readmes():
    chart = [entry for entry in bullets(_read("CHANGELOG.md")) if "Chart.js" in entry]
    assert chart, "no release note quotes the Chart.js readings"
    for entry in chart:
        assert "13 files" in entry and "23,967" in entry and "24,591" in entry, entry
    for name in ("README.md", "README.zh-CN.md"):
        page = _read(name)
        assert "23,967" in page and "24,591" in page and "325,137" in page, name
        assert "24,000" in page, name


def test_the_unchanged_run_note_says_what_was_compared():
    unchanged = [entry for entry in bullets(_read("CHANGELOG.md")) if "byte for byte" in entry]
    assert unchanged, "no release note claims an unchanged run"
    for entry in unchanged:
        assert "summary.json" in entry and "wall-clock" in entry and "calls.csv" in entry, entry
