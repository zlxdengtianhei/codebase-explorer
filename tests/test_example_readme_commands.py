"""Each published example's README commands still run and print the lines the README quotes."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
ELLIPSIS = "\u2026"


def fenced_block(text: str, language: str) -> list[str] | None:
    match = re.search(rf"^```{language}[ \t]*\n(.*?)^```[ \t]*$", text, re.MULTILINE | re.DOTALL)
    return match.group(1).splitlines() if match else None


def documented(example: Path) -> tuple[list[str], list[str], list[str]]:
    """The README's commands, then the quoted lines of `find` and of `query`."""
    text = (example / "README.md").read_text(encoding="utf-8")
    commands = [line.strip() for line in fenced_block(text, "sh")
                if line.strip() and not line.lstrip().startswith("#")]
    quoted = fenced_block(text, "text")
    blank = quoted.index("") if "" in quoted else len(quoted)
    return commands, quoted[:blank], [line for line in quoted[blank + 1:] if line]


def examples_with_commands() -> list[Path]:
    found = []
    for readme in sorted(EXAMPLES.glob("*/README.md")):
        text = readme.read_text(encoding="utf-8")
        if fenced_block(text, "sh") is not None and fenced_block(text, "text") is not None:
            found.append(readme.parent)
    return found


def run(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), env.get("PATH", "")])
    return subprocess.run(["sh", "-c", command], cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", timeout=120)


def unmatched(quoted: list[str], output: list[str]) -> list[str]:
    missing = []
    for line in quoted:
        if line.endswith(ELLIPSIS):
            prefix = line[:-len(ELLIPSIS)]
            ok = any(out.startswith(prefix) for out in output)
        else:
            ok = line in output
        if not ok:
            missing.append(line)
    return missing


@pytest.mark.parametrize("example", examples_with_commands(), ids=lambda path: path.name)
def test_readme_commands_print_the_quoted_lines(example: Path) -> None:
    commands, find_quote, query_quote = documented(example)
    name = example.name
    assert len(commands) == 2, f"{name}: README sh block has {len(commands)} commands, expected 2: {commands}"
    assert commands[0].startswith("cbe find"), f"{name}: first command is not `cbe find`: {commands[0]}"
    assert commands[1].startswith("cbe query"), f"{name}: second command is not `cbe query`: {commands[1]}"
    assert find_quote and query_quote, f"{name}: text block lacks find lines or query lines"

    for command, quote in zip(commands, (find_quote, query_quote)):
        result = run(command, example)
        assert result.returncode == 0, (
            f"{name}: `{command}` exited {result.returncode}\nstderr:\n{result.stderr}")
        assert result.stdout.strip(), f"{name}: `{command}` printed nothing\nstderr:\n{result.stderr}"
        missing = unmatched(quote, result.stdout.splitlines())
        assert not missing, (
            f"{name}: `{command}` output lacks quoted README lines:\n" + "\n".join(missing)
            + "\n--- first output lines:\n" + "\n".join(result.stdout.splitlines()[:12])
            + f"\nstderr:\n{result.stderr}")
