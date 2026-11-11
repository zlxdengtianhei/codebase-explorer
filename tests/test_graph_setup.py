"""``cbe graph setup``: download, verify, unpack and discovery.  No real downloads."""

from __future__ import annotations

import hashlib
import io
import json
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from cbe import cli
from cbe.graph_backends import toolchain
from cbe.graph_backends.toolchain import Asset, SetupError

JAVA_SCRIPT = """#!/bin/sh
here=$(cd "${0%/*}/.." && pwd)
echo "    java.home = $here" >&2
echo "    java.version = @VERSION@" >&2
"""


def _joern_zip(path: Path, marker: str = "one") -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name in ("joern", "joern-parse"):
            info = zipfile.ZipInfo(f"joern-cli/{name}")
            info.external_attr = (stat.S_IFREG | 0o755) << 16
            zf.writestr(info, f"#!/bin/sh\necho 'Version: 4.0.654 {marker}'\n")
        zf.writestr("joern-cli/lib/readme.txt", marker)


def _jre_tar(path: Path, version: str = "21.0.13") -> None:
    with tarfile.open(path, "w:gz") as tf:
        script = JAVA_SCRIPT.replace("@VERSION@", version).encode()
        info = tarfile.TarInfo("jdk-21.0.13+9-jre/bin/java")
        info.size, info.mode = len(script), 0o755
        tf.addfile(info, io.BytesIO(script))


def _asset(path: Path, **override) -> Asset:
    data = path.read_bytes()
    fields = dict(name=path.name, url=path.as_uri(), size=len(data),
                  checksums={"sha256": hashlib.sha256(data).hexdigest(),
                             "sha512": hashlib.sha512(data).hexdigest()})
    fields.update(override)
    return Asset(**fields)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated cache and a PATH that holds no Java."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    for name in ("JAVA_HOME", "CBE_JOERN_HOME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(toolchain.platform, "system", lambda: "Linux")
    zip_path, tar_path = tmp_path / "joern-cli-fake.zip", tmp_path / "jre-fake.tar.gz"
    _joern_zip(zip_path)
    _jre_tar(tar_path)
    table = {"linux-x86_64": {"joern": _asset(zip_path), "java": _asset(tar_path)}}
    return tmp_path, table, tmp_path / "cache", (zip_path, tar_path)


def _say(lines):
    return lines.append


def test_setup_installs_verifies_and_both_tools_are_found(env):
    tmp_path, table, cache, _ = env
    lines: list[str] = []
    result = toolchain.setup(cache=cache, table=table, key="linux-x86_64", say=_say(lines))
    assert result["missing"] == []
    assert result["steps"] == [{"joern": "installed"}, {"java": "installed"}]
    # Source URL, size and target directory are printed before the transfer.
    assert any(table["linux-x86_64"]["joern"].url in line for line in lines)
    assert any("joern-4.0.654" in line for line in lines if line.startswith("  to "))
    joern = toolchain.find_joern(cache=cache)
    assert joern == cache / "joern-4.0.654" / "joern-cli"
    assert (joern / "joern-parse").stat().st_mode & 0o111  # executable bit survives unzip
    java = toolchain.find_java(cache)
    assert java is not None and java.source == "cache" and java.major == 21
    assert not [p for p in cache.iterdir() if p.name.startswith(".")]  # no temp leftovers


def test_checksum_mismatch_installs_nothing(env):
    _, table, cache, _ = env
    bad = Asset(**{**table["linux-x86_64"]["joern"].__dict__, "checksums": {"sha256": "0" * 64}})
    with pytest.raises(SetupError, match="sha256 mismatch"):
        toolchain.setup(cache=cache, table={"linux-x86_64": {**table["linux-x86_64"], "joern": bad}},
                        key="linux-x86_64", say=lambda _: None)
    assert list(cache.iterdir()) == []


def test_second_run_reports_already_installed_without_downloading(env):
    _, table, cache, (zip_path, _) = env
    toolchain.setup(cache=cache, table=table, key="linux-x86_64", say=lambda _: None)
    zip_path.unlink()  # a second download would now fail
    lines: list[str] = []
    result = toolchain.setup(cache=cache, table=table, key="linux-x86_64", say=_say(lines))
    assert result["steps"][0] == {"joern": "already_installed"}
    assert any("already installed" in line for line in lines)


def test_force_installs_again(env):
    _, table, cache, (zip_path, _) = env
    toolchain.setup(cache=cache, table=table, key="linux-x86_64", say=lambda _: None)
    marker = cache / "joern-4.0.654" / "joern-cli" / "lib" / "readme.txt"
    assert marker.read_text() == "one"
    _joern_zip(zip_path, marker="two")
    table["linux-x86_64"]["joern"] = _asset(zip_path)
    result = toolchain.setup(force=True, cache=cache, table=table, key="linux-x86_64", say=lambda _: None)
    assert result["steps"][0] == {"joern": "installed"}
    assert marker.read_text() == "two"


def test_usable_java_skips_the_jre_download_and_with_java_forces_it(env, monkeypatch):
    _, table, cache, (_, tar_path) = env
    system_java = toolchain.JavaInstall(Path("/somewhere/jdk"), "21.0.1", 21, "PATH")
    monkeypatch.setattr(toolchain, "find_java", lambda cache=None, rejected=None: system_java)
    tar_path.unlink()  # a JRE download would fail
    result = toolchain.setup(cache=cache, table=table, key="linux-x86_64", say=lambda _: None)
    assert result["steps"][1] == {"java": "skipped, using PATH"}
    with pytest.raises(SetupError, match="download failed"):
        toolchain.setup(with_java=True, cache=cache, table=table, key="linux-x86_64", say=lambda _: None)


def test_unsupported_platform_names_supported_ones_and_manual_install(env, monkeypatch, capsys):
    tmp_path, table, _, _ = env
    monkeypatch.setattr(toolchain.platform, "system", lambda: "Windows")
    monkeypatch.setattr(toolchain.platform, "machine", lambda: "AMD64")
    assert toolchain.platform_key() is None
    assert cli.main(["graph", "setup"]) == 2
    message = capsys.readouterr().err
    assert "no download for Windows AMD64" in message
    assert "linux-x86_64" in message and "--joern-home" in message and "CBE_JOERN_HOME" in message


def test_platform_keys():
    assert set(toolchain.PINNED) == {"linux-x86_64", "macos-arm64", "macos-x86_64"}
    # The pinned release matches the pinned Joern version in every URL.
    for assets in toolchain.PINNED.values():
        assert f"v{toolchain.JOERN_VERSION}/" in assets["joern"].url
        assert assets["joern"].checksums["sha256"] and assets["java"].checksums["sha256"]


def test_joern_lookup_order(tmp_path, monkeypatch):
    def fake(base: Path) -> Path:
        base.mkdir(parents=True)
        for name in ("joern", "joern-parse"):
            (base / name).touch()
            (base / name).chmod(0o755)
        return base

    cache = tmp_path / "cache"
    cached = fake(cache / f"joern-{toolchain.JOERN_VERSION}" / "joern-cli")
    on_path = fake(tmp_path / "path-bin")
    from_env = fake(tmp_path / "env-home")
    explicit = fake(tmp_path / "explicit-home")
    monkeypatch.setenv("PATH", str(on_path))
    monkeypatch.delenv("CBE_JOERN_HOME", raising=False)
    assert toolchain.find_joern(cache=tmp_path / "none") == on_path
    assert toolchain.find_joern(cache=cache) == cached
    monkeypatch.setenv("CBE_JOERN_HOME", str(from_env))
    assert toolchain.find_joern(cache=cache) == from_env
    assert toolchain.find_joern(explicit, cache=cache) == explicit


def test_java_lookup_order_and_old_java_is_rejected(tmp_path, monkeypatch):
    def fake_java(home: Path, version: str) -> Path:
        (home / "bin").mkdir(parents=True)
        exe = home / "bin" / "java"
        exe.write_text(JAVA_SCRIPT.replace("@VERSION@", version))
        exe.chmod(0o755)
        return home

    cache = tmp_path / "cache"
    fake_java(cache / f"jre-{toolchain.JAVA_VERSION}", "21.0.13")
    on_path = fake_java(tmp_path / "path-jdk", "22.0.1")
    old = fake_java(tmp_path / "old-jdk", "17.0.9")
    monkeypatch.setenv("PATH", str(on_path / "bin"))
    monkeypatch.delenv("JAVA_HOME", raising=False)
    assert toolchain.find_java(cache).source == "PATH"
    monkeypatch.setenv("PATH", str(tmp_path / "nowhere"))
    assert toolchain.find_java(cache).source == "cache"
    monkeypatch.setenv("JAVA_HOME", str(old))
    rejected: list = []
    found = toolchain.find_java(cache, rejected=rejected)
    assert found.source == "cache"  # Java 17 in JAVA_HOME is skipped, with a reason
    assert rejected and "older than 21" in rejected[0][2]
    fake_java(tmp_path / "good-jdk", "21.0.2")
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "good-jdk"))
    assert toolchain.find_java(cache).source == "JAVA_HOME"


def test_cli_check_reports_found_and_missing(env, monkeypatch, capsys):
    tmp_path, table, cache, _ = env
    monkeypatch.setattr(toolchain, "PINNED", table)
    monkeypatch.setattr(toolchain, "platform_key", lambda: "linux-x86_64")
    assert cli.main(["graph", "setup", "--check"]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["missing"] == ["joern", "java"] and "cbe graph setup" in missing["next"]
    assert cli.main(["graph", "setup"]) == 0
    capsys.readouterr()
    assert cli.main(["graph", "setup", "--check"]) == 0
    found = json.loads(capsys.readouterr().out)
    assert found["missing"] == [] and found["joern"]["version"].startswith("4.0.654")
    assert found["java"]["source"] == "cache"


def test_missing_joern_message_points_at_setup(tmp_path, monkeypatch):
    from cbe.graph import GraphError, analyze_graph

    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("CBE_JOERN_HOME", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    with pytest.raises(GraphError) as raised:
        analyze_graph(repo, tmp_path / "g.json", backend="joern")
    message = next(d["message"] for d in raised.value.graph["diagnostics"] if d["code"] == "backend_unavailable")
    assert "run `cbe graph setup` (downloads about" in message


def test_languages_report_call_graph_status():
    from cbe.source_context import available_languages

    rows = {row["name"]: row["call_graph"] for row in available_languages()["languages"]}
    for name in ("c", "cpp", "python", "javascript", "typescript", "java", "go", "ruby"):
        assert rows[name] == {"status": "works"}
    assert rows["c_sharp"]["status"] == "known_failure" and "4.0.654" in rows["c_sharp"]["note"]
    assert rows["kotlin"]["status"] == "known_failure" and "MethodRef" in rows["kotlin"]["note"]
    assert rows["php"]["status"] == "needs_tool" and "php" in rows["php"]["note"]
    assert rows["rust"]["status"] == "needs_tool" and "cargo" in rows["rust"]["note"]
    assert rows["swift"] == {"status": "untested"}
    # Every language keeps its parsing support; only the note about graphs changes.
    assert all("call_graph" in row and "suffixes" in row for row in available_languages()["languages"])


def test_build_runs_joern_with_the_found_java_and_hints_when_none(tmp_path, monkeypatch):
    import subprocess

    import cbe.graph_backends.joern as joern

    home = tmp_path / "joern"
    home.mkdir()
    for name in ("joern", "joern-parse"):
        (home / name).touch()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("x = 1\n")
    seen = []

    def run(argv, timeout, cwd, *, env=None):
        seen.append(env)
        if "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, "Version: 1", "")
        return subprocess.CompletedProcess(argv, 1, "", "java: not found")  # joern-parse fails

    monkeypatch.setattr(joern, "_run", run)
    java = toolchain.JavaInstall(tmp_path / "jdk", "21.0.1", 21, "cache")
    fragment = joern.build_with_joern(repo, tmp_path / "r1", ["python"], home, 5, java=java)
    assert all(env["JAVA_HOME"] == str(java.home) and env["PATH"].startswith(str(java.home / "bin"))
               for env in seen)
    assert "no Java" not in fragment["diagnostics"][0]["message"]
    fragment = joern.build_with_joern(repo, tmp_path / "r2", ["python"], home, 5)
    assert "no Java 21+ was found, run `cbe graph setup`" in fragment["diagnostics"][0]["message"]
