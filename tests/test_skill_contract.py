"""Mechanical contract between the installed skill declaration and FastMCP."""

from __future__ import annotations

import re
from difflib import unified_diff
from pathlib import Path

import pytest

from src.server import mcp


SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "codebase-explorer"
    / "SKILL.md"
)
START_MARKER = "<!-- mcp-tools:start -->"
END_MARKER = "<!-- mcp-tools:end -->"
TOOL_LINE = re.compile(r"- `([a-z][a-z0-9_]*)`")


def declared_skill_tools(path: Path = SKILL_PATH) -> tuple[str, ...]:
    """Read the one machine-owned tool declaration block from the skill."""

    text = path.read_text(encoding="utf-8")
    assert text.count(START_MARKER) == 1
    assert text.count(END_MARKER) == 1
    block = text.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0]
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    names = tuple(
        match.group(1)
        for line in lines
        if (match := TOOL_LINE.fullmatch(line)) is not None
    )
    assert len(names) == len(lines), f"malformed tool declaration in {path}"
    assert len(names) == len(set(names)), f"duplicate tool declaration in {path}"

    count_match = re.search(r"^tools_count:\s*(\d+)\s*$", text, re.MULTILINE)
    assert count_match is not None, f"tools_count missing from {path}"
    assert int(count_match.group(1)) == len(names)
    return names


def _set_diff(expected: set[str], actual: set[str]) -> str:
    return "".join(
        unified_diff(
            [name + "\n" for name in sorted(expected)],
            [name + "\n" for name in sorted(actual)],
            fromfile="server.list_tools",
            tofile="skill.declared_tools",
        )
    )


@pytest.mark.asyncio
async def test_skill_declares_exactly_the_registered_mcp_tools() -> None:
    """Any server/skill name drift must turn this test red."""

    declared = set(declared_skill_tools())
    registered = {tool.name for tool in await mcp.list_tools()}
    assert declared == registered, "\n" + _set_diff(registered, declared)
