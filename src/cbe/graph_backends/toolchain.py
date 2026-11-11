"""Find and install the call-graph analyzer toolchain: Joern and Java.

``cbe graph setup`` downloads a pinned Joern release and a Temurin JRE into
the user cache directory.  Every download is checked against SHA-256 values
pinned below before anything is unpacked.  Nothing here changes an installed
Joern or Java outside the cache directory.

Lookup order used by ``cbe graph build``:

* Joern: ``--joern-home``, ``CBE_JOERN_HOME``, the cache directory, ``joern-parse`` on ``PATH``.
* Java: ``JAVA_HOME``, ``java`` on ``PATH``, the cache directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

JOERN_VERSION = "4.0.654"
JAVA_VERSION = "21.0.13+9"
MIN_JAVA_MAJOR = 21

_JOERN_BASE = f"https://github.com/joernio/joern/releases/download/v{JOERN_VERSION}/"
_JAVA_BASE = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/"


@dataclass(frozen=True)
class Asset:
    """One pinned download.  ``checksums`` maps a hash name to its hex digest."""

    name: str
    url: str
    size: int
    checksums: dict


# Joern: the sha512 values are the upstream ``<asset>.sha512`` files; the sha256
# values are the digests GitHub computed for the release assets.  Java: the
# sha256 values are the ``checksum`` that the Adoptium API reports.  The
# linux-x86_64 Joern zip was also hashed after a real download.
PINNED: dict[str, dict[str, Asset]] = {
    "linux-x86_64": {
        "joern": Asset(
            "joern-cli-linux-x86_64.zip", _JOERN_BASE + "joern-cli-linux-x86_64.zip", 1798080877,
            {"sha256": "830539ea998708362e4c479afea895a7dbfa90ed70537b38c84e53183e6e1fcd",
             "sha512": "706ec7cdc0c6c554b454fc7b83d3ba35ff47b40f9c9b74e041fac61e0b54902e"
                       "8d2a394b71b2a7cb7d1eb5ac9733f5442bd7ba1e6354a8e59f010e01e0377091"}),
        "java": Asset(
            "OpenJDK21U-jre_x64_linux_hotspot_21.0.13_9.tar.gz",
            _JAVA_BASE + "OpenJDK21U-jre_x64_linux_hotspot_21.0.13_9.tar.gz", 52181297,
            {"sha256": "a535a1df9c6284d9618872984e026ae0352d1f7e9e0605425c0e6114f47351dd"}),
    },
    "macos-arm64": {
        "joern": Asset(
            "joern-cli-macos-arm64.zip", _JOERN_BASE + "joern-cli-macos-arm64.zip", 1723620390,
            {"sha256": "4b4634dd1f5ad71eda91a9c4ca8baa18716f4cb03009de24ce1b1bc827401c97",
             "sha512": "779ca311bb0c6cef3130b57862b4f996ce3fabdc1f606a17b42cb1048dc3c1a1"
                       "d8f828d9ca70ba0f6f9bbf5adc79d8f4ac2c9069ad1505ddf42d563d999dc839"}),
        "java": Asset(
            "OpenJDK21U-jre_aarch64_mac_hotspot_21.0.13_9.tar.gz",
            _JAVA_BASE + "OpenJDK21U-jre_aarch64_mac_hotspot_21.0.13_9.tar.gz", 47935740,
            {"sha256": "225bab0a09491ef06835488cd942f5d2befa9a0410a2484f0c8bbcf7506ec09a"}),
    },
    "macos-x86_64": {
        "joern": Asset(
            "joern-cli-macos-x86_64.zip", _JOERN_BASE + "joern-cli-macos-x86_64.zip", 1729326215,
            {"sha256": "de66af2becda50080f35d120d5f723350687608f1f25b6ce73a2016467f53be0",
             "sha512": "7c66ddf9848283631833bc98e8829bd7bb6d48dd1dd1040dc2f1a4279458898d"
                       "858be909c41a09c37c438ed095951e53aa056a7ec7477d1e83c16becca4f9fec"}),
        "java": Asset(
            "OpenJDK21U-jre_x64_mac_hotspot_21.0.13_9.tar.gz",
            _JAVA_BASE + "OpenJDK21U-jre_x64_mac_hotspot_21.0.13_9.tar.gz", 41902098,
            {"sha256": "c909674b1c10c261b9a3fb7e9c0efebd303e33f88a4fe84be7135b5e2d711f89"}),
    },
}

_MANUAL = (f"Install it by hand: download joern-cli-<platform>.zip for Joern {JOERN_VERSION} from "
           f"https://github.com/joernio/joern/releases/tag/v{JOERN_VERSION}, unzip it, and pass the "
           "joern-cli directory as --joern-home (or set CBE_JOERN_HOME). Joern needs Java "
           f"{MIN_JAVA_MAJOR} or newer on PATH or in JAVA_HOME.")


class SetupError(ValueError):
    """A setup step failed; the message says what to do next."""


def platform_key() -> str | None:
    system, machine = platform.system(), platform.machine().lower()
    arch = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    name = {"Linux": "linux", "Darwin": "macos"}.get(system)
    key = f"{name}-{arch}"
    return key if key in PINNED else None


def cache_dir() -> Path:
    """``<user cache>/cbe/tools``: XDG on Linux, ``~/Library/Caches`` on macOS."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Caches" / "cbe" / "tools"
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".cache") / "cbe" / "tools"


def download_size(key: str | None = None, table=PINNED) -> int | None:
    assets = table.get(key or platform_key() or "")
    return sum(asset.size for asset in assets.values()) if assets else None


def setup_hint(key: str | None = None, table=PINNED) -> str:
    size = download_size(key, table)
    gigabytes = f"about {size / 1e9:.1f} GB" if size else "about 2 GB"
    return f"run `cbe graph setup` (downloads {gigabytes})"


def _joern_dir_ok(path: Path) -> bool:
    return (path / "joern").is_file() and (path / "joern-parse").is_file()


def find_joern(joern_home: Path | str | None = None, cache: Path | None = None) -> Path | None:
    """Locate the Joern CLI directory that holds ``joern`` and ``joern-parse``."""
    candidates: list[Path] = []
    for base in (joern_home, os.environ.get("CBE_JOERN_HOME")):
        if base:
            base = Path(base).expanduser()
            candidates += [base, base / "joern-cli", base / "bin"]
    candidates.append((cache or cache_dir()) / f"joern-{JOERN_VERSION}" / "joern-cli")
    which = shutil.which("joern-parse")
    if which:
        candidates.append(Path(which).resolve().parent)
    return next((c for c in candidates if _joern_dir_ok(c)), None)


@dataclass(frozen=True)
class JavaInstall:
    home: Path
    version: str
    major: int
    source: str


def _java_home_in(root: Path) -> Path | None:
    for candidate in (root, root / "Contents" / "Home"):
        if (candidate / "bin" / "java").is_file():
            return candidate
    return None


def probe_java(java_exe: Path) -> tuple[Path, str, int] | None:
    """Ask a ``java`` executable for its home and version; None if it cannot run."""
    try:
        done = subprocess.run([str(java_exe), "-XshowSettings:properties", "-version"],
                              capture_output=True, text=True, timeout=60, check=False,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (done.stderr or "") + (done.stdout or "")
    home = re.search(r"^\s*java\.home = (.+)$", text, re.M)
    version = re.search(r"^\s*java\.version = (\S+)$", text, re.M)
    if done.returncode != 0 or not home or not version:
        return None
    major = re.match(r"(\d+)", version.group(1))
    return Path(home.group(1).strip()), version.group(1), int(major.group(1)) if major else 0


def java_candidates(cache: Path | None = None) -> list[tuple[str, Path]]:
    """Java executables in lookup order, as (source, path)."""
    found: list[tuple[str, Path]] = []
    if os.environ.get("JAVA_HOME"):
        found.append(("JAVA_HOME", Path(os.environ["JAVA_HOME"]).expanduser() / "bin" / "java"))
    if shutil.which("java"):
        found.append(("PATH", Path(shutil.which("java"))))
    home = _java_home_in((cache or cache_dir()) / f"jre-{JAVA_VERSION}")
    if home:
        found.append(("cache", home / "bin" / "java"))
    return found


def find_java(cache: Path | None = None, *, rejected: list | None = None) -> JavaInstall | None:
    """First Java of at least ``MIN_JAVA_MAJOR`` in lookup order; others go to ``rejected``."""
    for source, exe in java_candidates(cache):
        if not exe.is_file():
            if rejected is not None:
                rejected.append((source, str(exe), "not an executable file"))
            continue
        probed = probe_java(exe)
        if probed is None:
            if rejected is not None:
                rejected.append((source, str(exe), "does not run"))
            continue
        home, version, major = probed
        if major >= MIN_JAVA_MAJOR:
            return JavaInstall(home, version, major, source)
        if rejected is not None:
            rejected.append((source, str(exe), f"Java {version} is older than {MIN_JAVA_MAJOR}"))
    return None


def java_environment(java: JavaInstall | None, base: dict | None = None) -> dict | None:
    """Environment that makes Joern's launcher use ``java``; None when nothing needs changing."""
    if java is None:
        return base
    env = dict(os.environ if base is None else base)
    env["JAVA_HOME"] = str(java.home)
    env["PATH"] = str(java.home / "bin") + os.pathsep + env.get("PATH", "")
    return env


def check(cache: Path | None = None) -> dict:
    """What is installed and what is missing; downloads nothing."""
    from .joern import joern_version  # noqa: PLC0415

    key = platform_key()
    joern_dir = find_joern(cache=cache)
    rejected: list = []
    java = find_java(cache, rejected=rejected)
    joern = None
    if joern_dir:
        joern = {"path": str(joern_dir), "version": joern_version(joern_dir / "joern", 120, java=java)}
    missing = []
    if joern is None:
        missing.append("joern")
    if java is None:
        missing.append("java")
    report = {
        "platform": key or f"{platform.system().lower()}-{platform.machine().lower()}",
        "joern": joern,
        "java": ({"path": str(java.home), "version": java.version, "source": java.source}
                 if java else None),
        "java_rejected": [{"source": s, "path": p, "reason": r} for s, p, r in rejected],
        "missing": missing,
        "cache_dir": str(cache or cache_dir()),
        "pinned_joern": JOERN_VERSION,
    }
    if missing:
        report["next"] = setup_hint(key)
    return report


def _human(size: float) -> str:
    return f"{size / 1e9:.2f} GB" if size >= 1e8 else f"{size / 1e6:.1f} MB"


def _download(asset: Asset, target: Path, say) -> None:
    """Stream ``asset`` to ``target`` and verify its pinned checksums before returning."""
    digests = {name: hashlib.new(name) for name in asset.checksums}
    started, shown = time.monotonic(), -1
    try:
        with urllib.request.urlopen(asset.url, timeout=60) as response, target.open("wb") as out:
            total = int(response.headers.get("Content-Length") or asset.size)
            done = 0
            while chunk := response.read(1 << 20):
                out.write(chunk)
                for digest in digests.values():
                    digest.update(chunk)
                done += len(chunk)
                step = done * 10 // max(total, 1)
                if step != shown and total >= 1e8:
                    shown = step
                    say(f"  {step * 10}% ({_human(done)} of {_human(total)}, {time.monotonic() - started:.0f}s)")
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise SetupError(f"download failed for {asset.url}: {exc}. Check the network and run the command again. "
                         + _MANUAL) from exc
    for name, expected in asset.checksums.items():
        actual = digests[name].hexdigest()
        if actual != expected:
            target.unlink(missing_ok=True)
            raise SetupError(f"{name} mismatch for {asset.name}: expected {expected}, got {actual}. "
                             "The file was deleted and nothing was installed.")


def _extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    root = destination.resolve()
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                target = (root / info.filename).resolve()
                if target != root and root not in target.parents:
                    raise SetupError(f"archive entry escapes the target directory: {info.filename}")
                mode = info.external_attr >> 16
                if (mode & 0o170000) == 0o120000:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.unlink(missing_ok=True)
                    target.symlink_to(zf.read(info).decode())
                    continue
                zf.extract(info, root)
                if mode & 0o111 and not info.is_dir():
                    target.chmod(target.stat().st_mode | 0o111)  # zipfile drops the executable bit
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(root, filter="data")


def _install_asset(kind: str, asset: Asset, final: Path, cache: Path, say, *, strip_top: bool) -> None:
    say(f"Downloading {asset.name} ({_human(asset.size)}) from {asset.url}")
    say(f"  to {final}")
    cache.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{kind}-", dir=cache))
    try:
        archive = work / asset.name
        _download(asset, archive, say)
        say(f"  checksums match: {', '.join(sorted(asset.checksums))}")
        _extract(archive, work / "unpacked")
        archive.unlink()
        unpacked = work / "unpacked"
        entries = [p for p in unpacked.iterdir()]
        top = entries[0] if strip_top and len(entries) == 1 and entries[0].is_dir() else unpacked
        if final.exists():
            shutil.rmtree(final)
        shutil.move(str(top), str(final))
    except zipfile.BadZipFile as exc:
        raise SetupError(f"{asset.name} is not a valid zip file: {exc}") from exc
    except tarfile.TarError as exc:
        raise SetupError(f"{asset.name} is not a valid tar file: {exc}") from exc
    finally:
        shutil.rmtree(work, ignore_errors=True)


def setup(*, force: bool = False, with_java: bool = False, cache: Path | None = None,
          table: dict | None = None, key: str | None = None, say=None) -> dict:
    """Install pinned Joern and, when no Java 21+ is usable, a JRE into the cache directory."""
    say = say or (lambda text: print(text, file=sys.stderr, flush=True))
    table = PINNED if table is None else table
    key = key or platform_key()
    if key is None or key not in table:
        raise SetupError(f"`cbe graph setup` has no download for {platform.system()} {platform.machine()}. "
                         f"Supported: {', '.join(sorted(table))}. " + _MANUAL)
    cache = cache or cache_dir()
    assets = table[key]
    joern_final = cache / f"joern-{JOERN_VERSION}"
    jre_final = cache / f"jre-{JAVA_VERSION}"
    result: dict = {"platform": key, "cache_dir": str(cache), "steps": []}

    if _joern_dir_ok(joern_final / "joern-cli") and not force:
        say(f"Joern {JOERN_VERSION} is already installed in {joern_final}; use --force to reinstall.")
        result["steps"].append({"joern": "already_installed"})
    else:
        _install_asset("joern", assets["joern"], joern_final, cache, say, strip_top=False)
        if not _joern_dir_ok(joern_final / "joern-cli"):
            raise SetupError(f"{assets['joern'].name} unpacked without joern-cli/joern and joern-parse")
        result["steps"].append({"joern": "installed"})

    have_java = None if with_java else find_java(cache)
    if force and _java_home_in(jre_final):
        have_java = None  # --force also reinstalls a JRE this command put in the cache
    if have_java is not None:
        say(f"Java {have_java.version} from {have_java.source} is usable ({have_java.home}); "
            "not downloading a JRE. Use --with-java to download one anyway.")
        result["steps"].append({"java": f"skipped, using {have_java.source}"})
    else:
        _install_asset("jre", assets["java"], jre_final, cache, say, strip_top=True)
        if _java_home_in(jre_final) is None:
            raise SetupError(f"{assets['java'].name} unpacked without bin/java")
        result["steps"].append({"java": "installed"})
    final = check(cache)
    result.update(joern=final["joern"], java=final["java"], missing=final["missing"])
    return result

