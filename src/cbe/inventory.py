"""Freeze the enrolled source tree. File bytes are the content evidence."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from cbe.ir import FileIR, FileRecord, OffsetMap, SourceUnitState, Symbol, TypedFailure, sha256_bytes
from cbe.parser import ENROLLED_SUFFIXES, ParserSet, failure_record

# Named control/cache directories with independent evidence. Folder names such
# as build/dist/vendor and arbitrary dot-directories are *not* treated as
# proven third-party or generated output.
NAMED_EXCLUDE_DIRS: dict[str, tuple[str, str]] = {
    ".git": ("vcs_control", "Git metadata directory is not enrolled own source"),
    ".hg": ("vcs_control", "Mercurial metadata directory is not enrolled own source"),
    ".svn": ("vcs_control", "Subversion metadata directory is not enrolled own source"),
    ".venv": ("dependency_cache", "Python virtualenv directory is not enrolled own source"),
    "venv": ("dependency_cache", "Python virtualenv directory is not enrolled own source"),
    "node_modules": ("dependency_cache", "npm dependency cache is not enrolled own source"),
    "__pycache__": ("bytecode_cache", "Python bytecode cache is not enrolled own source"),
    ".mypy_cache": ("typechecker_cache", "mypy cache is not enrolled own source"),
    ".pytest_cache": ("test_cache", "pytest cache is not enrolled own source"),
    ".tox": ("test_cache", "tox environment cache is not enrolled own source"),
    ".codebase-analysis": ("tool_output", "analysis output directory is not enrolled source"),
}

DEFAULT_EXCLUDE_DIR_NAMES = frozenset(NAMED_EXCLUDE_DIRS)

# ``*.min.js`` / ``*.min.ts`` (and other enrolled-language names) are not
# proof of generated or third-party code. They still enroll as that language
# and count in S_chars. A later semantic pass may treat the name as a hint;
# filename suffix must not shrink the denominator (design §1/3).


@dataclass
class Inventory:
    repo_root: str
    git_head: str | None
    files: dict[str, FileRecord]
    symbols: dict[str, Symbol]
    relations: list[dict]
    file_irs: dict[str, FileIR] = field(default_factory=dict)
    other_language_files: list[dict] = field(default_factory=list)
    excluded_directories: list[dict] = field(default_factory=list)

    @property
    def s_chars(self) -> int:
        return sum(record.char_length for record in self.files.values() if record.enrolled)

    @property
    def source_revision(self) -> str:
        payload = {
            "repo": self.repo_root,
            "git_head": self.git_head,
            "files": {
                path: {"hash": record.content_hash, "bytes": record.byte_length}
                for path, record in sorted(self.files.items())
            },
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "rev_" + sha256_bytes(encoded)

    def to_dict(self) -> dict:
        return {
            "repo_root": self.repo_root,
            "git_head": self.git_head,
            "s_chars": self.s_chars,
            "source_revision": self.source_revision,
            "files": {path: record.to_dict() for path, record in self.files.items()},
            "symbols": {symbol_id: symbol.to_dict() for symbol_id, symbol in self.symbols.items()},
            "relations": list(self.relations),
            "other_language_files": list(self.other_language_files),
            "excluded_directories": list(self.excluded_directories),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> Inventory:
        files = {path: FileRecord.from_dict(value) for path, value in payload.get("files", {}).items()}
        symbols = {key: Symbol.from_dict(value) for key, value in payload.get("symbols", {}).items()}
        return cls(
            repo_root=str(payload["repo_root"]),
            git_head=payload.get("git_head"),
            files=files,
            symbols=symbols,
            relations=list(payload.get("relations") or []),
            other_language_files=list(payload.get("other_language_files") or []),
            excluded_directories=list(payload.get("excluded_directories") or []),
        )


def git_head(repo: Path) -> str | None:
    git_dir = repo / ".git"
    if not git_dir.exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def should_exclude_dir(name: str) -> bool:
    """True only for named control/cache directories with independent evidence."""

    return name in NAMED_EXCLUDE_DIRS


def exclude_rule_for_dir(name: str) -> dict[str, str] | None:
    evidence = NAMED_EXCLUDE_DIRS.get(name)
    if evidence is None:
        return None
    category, reason = evidence
    return {"rule": f"{category}:{name}", "reason": reason, "category": category}


def iter_source_files(
    repo: Path,
) -> tuple[list[tuple[str, Path, str]], list[dict], list[dict]]:
    enrolled: list[tuple[str, Path, str]] = []
    other: list[dict] = []
    excluded_directories: list[dict] = []
    repo = repo.resolve()
    for dirpath, dirnames, filenames in os.walk(repo, topdown=True, followlinks=False):
        dirnames.sort()
        filenames.sort()
        current = Path(dirpath)
        kept: list[str] = []
        for name in dirnames:
            rule = exclude_rule_for_dir(name)
            if rule is None:
                kept.append(name)
                continue
            relative_dir = (current / name).relative_to(repo).as_posix()
            excluded_directories.append({
                "path": relative_dir,
                "rule": rule["rule"],
                "reason": rule["reason"],
                "category": rule["category"],
            })
        dirnames[:] = kept
        for filename in filenames:
            path = current / filename
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(repo).as_posix()
            suffix = path.suffix.lower()
            language = ENROLLED_SUFFIXES.get(suffix)
            if language is None:
                if suffix in {".json", ".md", ".txt", ".toml", ".yml", ".yaml", ".lock", ".cfg", ".ini"}:
                    continue
                other.append(
                    {
                        "path": relative,
                        "reason": "other_language",
                        "language": suffix.lstrip(".") or "unknown",
                    }
                )
                continue
            enrolled.append((relative, path, language))
    return enrolled, other, excluded_directories


def build_inventory(repo: Path) -> Inventory:
    repo = repo.resolve()
    if not repo.is_dir():
        raise ValueError(f"repository root is not a directory: {repo}")
    enrolled, other, excluded_directories = iter_source_files(repo)
    parsers = ParserSet()
    files: dict[str, FileRecord] = {}
    symbols: dict[str, Symbol] = {}
    relations: list[dict] = []
    file_irs: dict[str, FileIR] = {}
    for relative, path, language in enrolled:
        raw = path.read_bytes()
        result = parsers.parse_file(repo, relative, raw)
        if isinstance(result, TypedFailure):
            files[relative] = failure_record(relative, language, raw, result)
            continue
        files[relative] = result.record
        file_irs[relative] = result
        for symbol in result.symbols:
            if symbol.id in symbols:
                raise RuntimeError(f"duplicate symbol id {symbol.id}")
            symbols[symbol.id] = symbol
        for relation in result.relations:
            relations.append(relation.to_dict())
    return Inventory(
        repo_root=repo.as_posix(),
        git_head=git_head(repo),
        files=files,
        symbols=symbols,
        relations=relations,
        file_irs=file_irs,
        other_language_files=other,
        excluded_directories=excluded_directories,
    )


def load_offsets(repo: Path, relative: str) -> OffsetMap:
    raw = (repo / relative).read_bytes()
    return OffsetMap.from_bytes(raw)
