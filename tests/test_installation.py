"""Installation ownership and host path behavior, using the installed wheel."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from cbe_install import cli


def test_custom_path_repeat_and_user_change(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "skills with spaces"
    assert cli.main(["install", "--dir", str(root)]) == 0
    skill = root / cli.SKILLS[0]
    source = cli._resource_files(cli.SKILLS[0])
    assert (skill / "SKILL.md").read_bytes() == source["SKILL.md"]
    assert cli.main(["install", "--dir", str(root)]) == 0
    assert "unchanged" in capsys.readouterr().out

    (skill / "SKILL.md").write_text("user edit\n", encoding="utf-8")
    assert cli.main(["upgrade", "--dir", str(root)]) == 2
    assert cli.main(["uninstall", "--dir", str(root)]) == 2
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == "user edit\n"
    assert "user-modified" in capsys.readouterr().err


def test_upgrade_and_uninstall_preserve_unowned_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "skills"
    assert cli.main(["install", "--dir", str(root)]) == 0
    skill = root / cli.SKILLS[0]
    (skill / "my-notes.md").write_text("keep me\n", encoding="utf-8")
    original = cli._resource_files

    def updated(name: str) -> dict[str, bytes]:
        payload = original(name).copy()
        if name == cli.SKILLS[0]:
            payload["new-reference.md"] = b"release update\n"
        return payload

    monkeypatch.setattr(cli, "_resource_files", updated)
    assert cli.main(["upgrade", "--dir", str(root)]) == 0
    assert (skill / "new-reference.md").read_bytes() == b"release update\n"
    assert (skill / "my-notes.md").read_text(encoding="utf-8") == "keep me\n"
    assert cli.main(["uninstall", "--dir", str(root)]) == 0
    assert (skill / "my-notes.md").read_text(encoding="utf-8") == "keep me\n"
    assert not (skill / "SKILL.md").exists()
    assert not (skill / "new-reference.md").exists()
    assert not (skill / cli.MANIFEST).exists()


def test_interactive_custom_and_project_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "chosen skills"
    monkeypatch.setattr("sys.stdin", io.StringIO(f"custom\n{custom}\n"))
    assert cli.main(["install", "--interactive"]) == 0
    for name in cli.SKILLS:
        assert (custom / name / "SKILL.md").is_file()

    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["install", "--host", "all", "--project", str(project)]) == 0
    for host, parts in cli.PROJECT_DIRS.items():
        for name in cli.SKILLS:
            assert (project.joinpath(*parts) / name / "SKILL.md").is_file(), host


def test_unowned_conflict_and_missing_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "skills"
    existing = root / cli.SKILLS[0]
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("another owner\n", encoding="utf-8")
    assert cli.main(["install", "--dir", str(root)]) == 2
    assert (existing / "SKILL.md").read_text(encoding="utf-8") == "another owner\n"
    assert "ownership manifest" in capsys.readouterr().err

    def missing(_: str) -> None:
        raise ModuleNotFoundError("No module named 'required-package'", name="required-package")

    monkeypatch.setattr(cli.importlib, "import_module", missing)
    assert cli.main(["doctor"]) == 2
    assert "uv tool install --reinstall" in capsys.readouterr().err


def test_manifest_tracks_only_shipped_files(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    assert cli.main(["install", "--dir", str(root)]) == 0
    for name in cli.SKILLS:
        manifest = json.loads((root / name / cli.MANIFEST).read_text(encoding="utf-8"))
        assert manifest["product"] == cli.PRODUCT
        assert set(manifest["files"]) == set(cli._resource_files(name))
        if name in cli.RUNTIME_SKILLS:
            runtime = manifest["runtime_python"]
            installed = (root / name / "SKILL.md").read_text(encoding="utf-8")
            assert "Installed runtime" in installed and runtime in installed
            for module in cli.RUNTIME_MODULES:
                assert f"-m {module}" in installed
                no_bin = os.environ.copy()
                no_bin["PATH"] = ""
                result = subprocess.run([runtime, "-m", module, "--help"], cwd=tmp_path,
                                        env=no_bin, capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
        assert cli.main(["doctor", "--dir", str(root)]) == 0


def test_bundled_markdown_links_resolve_without_author_checkout(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    assert cli.main(["install", "--dir", str(root)]) == 0
    for name in cli.SKILLS:
        for document in (root / name).rglob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                target = link.split("#", 1)[0]
                if not target or target.startswith(("https://", "http://", "mailto:")):
                    continue
                assert not Path(target).is_absolute(), (document, link)
                assert (document.parent / target).is_file(), (document, link)


def test_user_scope_honors_host_config_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh-home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    args = cli._parser().parse_args(["install", "--scope", "user", "--host", "dsh", "--host", "opencode"])
    assert cli._targets(args) == [tmp_path / "dsh-home/skills", tmp_path / "xdg-config/opencode/skills"]


def test_runtime_note_command_runs_pasted_into_a_shell_and_warns_against_variables(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "tool env" / "bin"
    bin_dir.mkdir(parents=True)
    launcher = bin_dir / "python"
    launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.setattr(cli, "_runtime_python", lambda: launcher)

    note = cli._with_runtime(b"---\nname: x\n---\nbody\n").decode("utf-8")
    entry = next(line for line in note.splitlines() if line.startswith("- `cbe`: `"))
    command = entry.split(": ", 1)[1].strip("`")
    result = subprocess.run(f"{command} --version", shell=True, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "cbe" in result.stdout
    assert "shell variable" in note and "shell function" in note


SHIPPED_AGENT = Path(__file__).resolve().parents[1] / ".dsh/agents/cbe-writer.md"


def test_shipped_writer_agent_has_only_the_read_and_write_tools() -> None:
    frontmatter = SHIPPED_AGENT.read_text(encoding="utf-8").split("---\n")[1]
    fields = dict(line.split(": ", 1) for line in frontmatter.splitlines())
    assert fields["name"] == "cbe-writer"
    assert [tool.strip() for tool in fields["tools"].split(",")] == ["Read", "Write"]


def test_claude_code_install_adds_the_writer_agent_and_uninstall_removes_it(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["install", "--host", "claude-code", "--project", str(project)]) == 0
    agent = project / ".claude" / "agents" / "cbe-writer.md"
    assert agent.read_bytes() == SHIPPED_AGENT.read_bytes()
    manifest = json.loads((project / ".claude/skills" / cli.SKILLS[0] / cli.MANIFEST).read_text(encoding="utf-8"))
    assert manifest["agents"] == {"cbe-writer.md": hashlib.sha256(SHIPPED_AGENT.read_bytes()).hexdigest()}
    assert str(agent) in capsys.readouterr().out

    assert cli.main(["install", "--host", "claude-code", "--project", str(project)]) == 0
    assert "unchanged" in capsys.readouterr().out
    assert cli.main(["doctor", "--host", "claude-code", "--project", str(project)]) == 0
    assert str(agent) in capsys.readouterr().out

    (project / ".claude" / "agents" / "mine.md").write_text("another agent\n", encoding="utf-8")
    assert cli.main(["uninstall", "--host", "claude-code", "--project", str(project)]) == 0
    assert not agent.exists()
    assert not (project / ".claude/skills" / cli.SKILLS[0]).exists()
    assert (project / ".claude" / "agents" / "mine.md").read_text(encoding="utf-8") == "another agent\n"


def test_only_the_claude_code_host_gets_an_agent_and_user_scope_uses_home(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["install", "--host", "all", "--project", str(project)]) == 0
    assert sorted(path.relative_to(project).as_posix() for path in project.rglob("cbe-writer.md")) == [
        ".claude/agents/cbe-writer.md"]
    assert cli.main(["install", "--dir", str(tmp_path / "skills with spaces")]) == 0
    assert not (tmp_path / "agents").exists()

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    assert cli.main(["install", "--scope", "user", "--host", "claude-code"]) == 0
    assert (home / ".claude" / "agents" / "cbe-writer.md").read_bytes() == SHIPPED_AGENT.read_bytes()
    assert cli.main(["uninstall", "--scope", "user", "--host", "claude-code"]) == 0
    assert not (home / ".claude" / "agents" / "cbe-writer.md").exists()


def test_install_does_not_overwrite_another_owners_agent_file(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    agents = project / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "cbe-writer.md").write_text("another owner\n", encoding="utf-8")
    assert cli.main(["install", "--host", "claude-code", "--project", str(project)]) == 2
    assert (agents / "cbe-writer.md").read_text(encoding="utf-8") == "another owner\n"
    assert not (project / ".claude" / "skills" / cli.SKILLS[0]).exists()
    assert "unowned file conflicts" in capsys.readouterr().err


def test_edited_agent_file_blocks_upgrade_and_uninstall(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["install", "--host", "claude-code", "--project", str(project)]) == 0
    agent = project / ".claude" / "agents" / "cbe-writer.md"
    agent.write_text("user edit\n", encoding="utf-8")
    for command in ("upgrade", "uninstall", "doctor"):
        assert cli.main([command, "--host", "claude-code", "--project", str(project)]) == 2
    assert agent.read_text(encoding="utf-8") == "user edit\n"
    assert (project / ".claude/skills" / cli.SKILLS[0] / "SKILL.md").is_file()
    assert "user-modified" in capsys.readouterr().err


def test_upgrade_adds_the_agent_to_a_skill_installed_without_one(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    assert cli.main(["install", "--host", "claude-code", "--project", str(project)]) == 0
    agent = project / ".claude" / "agents" / "cbe-writer.md"
    manifest_path = project / ".claude/skills" / cli.SKILLS[0] / cli.MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["agents"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    agent.unlink()

    assert cli.main(["doctor", "--host", "claude-code", "--project", str(project)]) == 2
    assert cli.main(["upgrade", "--host", "claude-code", "--project", str(project)]) == 0
    assert agent.read_bytes() == SHIPPED_AGENT.read_bytes()
    assert cli.main(["doctor", "--host", "claude-code", "--project", str(project)]) == 0

    agent.unlink()
    assert cli.main(["doctor", "--host", "claude-code", "--project", str(project)]) == 2
    assert cli.main(["install", "--host", "claude-code", "--project", str(project)]) == 0
    assert agent.read_bytes() == SHIPPED_AGENT.read_bytes()
