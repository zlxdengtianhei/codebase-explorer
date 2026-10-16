"""Source scan and reading batches: which files are read together by one detail author.

A batch (``Module``) is a reading unit, not a semantic module. Batches keep a
subsystem and its tests apart, keep fitting directory subtrees whole, and join
files linked by imports first, within a token target per batch.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from cbe import source_context
from cbe.token_budget import count_text_tokens


class BatchingError(ValueError):
    """The repository cannot be split into reading batches."""


TARGET_TOKENS = 20_000
MAX_TOKENS = 25_000
MAX_SINGLE_FILE_TOKENS = 60_000


@dataclass
class SourceFile:
    path: str
    source: str
    tokens: int
    digest: str
    signatures: list[str]
    imports: set[str] = field(default_factory=set)

    @property
    def is_test(self) -> bool:
        return self.path.startswith(("tests/", "test/", "t/")) or "/test_" in self.path


@dataclass
class Module:
    number: int
    files: list[SourceFile]
    bucket: str
    title: str = ""

    @property
    def tokens(self) -> int:
        return sum(item.tokens for item in self.files)

    @property
    def is_test(self) -> bool:
        return all(item.is_test for item in self.files)


def _signatures(path: str, source: str) -> list[str]:
    if not path.endswith(".py"):
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    rows: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            rows.append(node.name)
            rows.extend(f"{node.name}.{child.name}" for child in node.body
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows.append(node.name)
    return rows


def _imports(path: str, source: str) -> set[str]:
    names: set[str] = set()
    if path.endswith(".py"):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return names
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
                names.update(node.module + "." + alias.name for alias in node.names)
    else:
        names.update(re.findall(r"#include\s*[\"<]([^\">]+)[\">]", source))
        names.update(re.findall(r"\bfrom\s*[\"']([^\"']+)[\"']", source))
        names.update(re.findall(r"\brequire\s*\(\s*[\"']([^\"']+)[\"']", source))
    return names


def scan(repo: Path) -> list[SourceFile]:
    """Every regular source file outside the excluded directories; symlinks are never followed."""
    suffixes = source_context.registered_suffixes() | source_context.FALLBACK_SUFFIXES
    files: list[SourceFile] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in suffixes:
            continue
        if any(part in source_context.DEFAULT_EXCLUDE_DIR_NAMES for part in path.relative_to(repo).parts):
            continue
        raw = path.read_bytes()
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BatchingError(f"source is not UTF-8: {path.relative_to(repo)}") from exc
        rel = path.relative_to(repo).as_posix()
        files.append(SourceFile(rel, source, count_text_tokens(source), hashlib.sha256(raw).hexdigest(),
                                _signatures(rel, source), _imports(rel, source)))
    if not files:
        raise BatchingError("no supported source files")
    return files


def _subsystem(item: SourceFile, production_areas: set[str],
               production_files: list[SourceFile], primary_root: str) -> str:
    parts = Path(item.path).parts
    if not item.is_test:
        if parts[0] != primary_root:
            return parts[0]
        return parts[1] if len(parts) > 2 else "core"

    # A test's physical directory remains its packing boundary. The matching
    # source subsystem only decides where its page appears in the index.
    ignored = {"t", "test", "tests", "unit", "integration", "smoke", "benchmarks"}
    for part in parts[1:-1]:
        if part in ignored:
            continue
        if part in production_areas:
            return part
        for area in sorted(production_areas):
            if part.rstrip("s") == area.rstrip("s"):
                return area
    local_area = next((part for part in parts[1:-1] if part not in ignored), "core")
    stem = Path(item.path).stem.removeprefix("test_").removesuffix("_test")
    if stem in {"__init__", "conftest"}:
        return local_area
    words = set(stem.split("_"))
    for area in sorted(production_areas):
        if area.rstrip("s") in {word.rstrip("s") for word in words}:
            return area
    matches = [(len(Path(source.path).parts),
                _subsystem(source, production_areas, [], primary_root))
               for source in production_files
               if Path(source.path).stem == stem or
               Path(source.path).stem.rstrip("s") == stem.rstrip("s")]
    if matches:
        # A top-level implementation is a better default than an equally
        # named CLI adapter or example nested several directories below it.
        return min(matches)[1]
    return local_area


def _pack_directory(files: list[SourceFile], *, strict: bool = False) -> list[list[SourceFile]]:
    """Join imports first, then fill only within a specific source directory."""
    groups = {i: [item] for i, item in enumerate(sorted(files, key=lambda item: item.path))}
    tokens = {i: group[0].tokens for i, group in groups.items()}
    candidates: dict[str, set[int]] = {}
    for i, group in groups.items():
        path = Path(group[0].path)
        for name in {group[0].path, path.name, path.stem, ".".join(path.with_suffix("").parts),
                     ".".join(path.with_suffix("").parts[1:])}:
            candidates.setdefault(name, set()).add(i)
    links: dict[int, dict[int, int]] = {i: {} for i in groups}
    for i, group in groups.items():
        targets: set[int] = set()
        for ref in group[0].imports:
            # Exact names and nonempty dotted suffixes implement the original
            # candidate match; a set counts each directed file pair just once.
            keys = {ref} | {ref[pos + 1:] for pos, char in enumerate(ref)
                            if char == "." and ref[pos + 1:]}
            for key in keys:
                targets.update(candidates.get(key, ()))
        for j in targets - {i}:
            links[i][j] = links[i].get(j, 0) + 1
            links[j][i] = links[j].get(i, 0) + 1
    while True:
        pairs = []
        ids = list(groups)
        for offset, left in enumerate(ids):
            for right in ids[offset + 1:]:
                combined_tokens = tokens[left] + tokens[right]
                if combined_tokens > MAX_TOKENS:
                    continue
                weight = links[left].get(right, 0)
                if weight:
                    # Stable ids retain group order after removals, hence the
                    # same left/right tie break as the original list indices.
                    pairs.append((weight, -abs(TARGET_TOKENS - combined_tokens),
                                  -left, -right, left, right))
        if not pairs:
            break
        *_, left, right = max(pairs)
        groups[left].extend(groups.pop(right))
        tokens[left] += tokens.pop(right)
        for other in groups:
            if other == left:
                continue
            weight = links[left].get(other, 0) + links[right].get(other, 0)
            if weight:
                links[left][other] = links[other][left] = weight
            links[other].pop(right, None)
        links[left].pop(right, None)
        links.pop(right)
    if strict:
        return list(groups.values())
    packed: list[list[SourceFile]] = []
    for group in sorted(groups.values(), key=lambda group: (-sum(item.tokens for item in group), group[0].path)):
        candidates = [existing for existing in packed
                      if sum(item.tokens for item in existing + group) <= MAX_TOKENS]
        if candidates:
            chosen = max(candidates, key=lambda existing: (
                min(sum(item.tokens for item in existing + group), TARGET_TOKENS),
                -packed.index(existing)))
            chosen.extend(group)
        else:
            packed.append(group)
    return packed


def _directory_groups(files: list[SourceFile], *, strict_root: Path | None = None) -> list[list[SourceFile]]:
    """Keep fitting subtrees whole; recurse only when a subtree is oversized."""
    if sum(item.tokens for item in files) <= MAX_TOKENS:
        return [files]
    parents = {Path(item.path).parent for item in files}
    common = Path(os.path.commonpath([str(parent) for parent in parents]))
    direct = [item for item in files if Path(item.path).parent == common]
    children: dict[str, list[SourceFile]] = {}
    for item in files:
        if item in direct:
            continue
        relative = Path(item.path).relative_to(common)
        children.setdefault(relative.parts[0], []).append(item)
    groups = _pack_directory(direct, strict=common == strict_root)
    child_groups = [_directory_groups(children[name], strict_root=strict_root) for name in sorted(children)]
    # Small sibling directories may share one module, but never cross an area
    # or a test/production boundary (the caller already partitioned both).
    small = [group for sibling in child_groups for group in sibling
             if sum(item.tokens for item in group) < 4_000]
    groups.extend(group for sibling in child_groups for group in sibling
                  if sum(item.tokens for item in group) >= 4_000)
    if small:
        groups.extend(_pack_directory([item for group in small for item in group]))
    return groups


def plan(files: list[SourceFile]) -> list[Module]:
    for item in files:
        if item.tokens > MAX_SINGLE_FILE_TOKENS:
            raise BatchingError(f"one whole source file exceeds {MAX_SINGLE_FILE_TOKENS} tokens: {item.path}")
    production = [item for item in files if not item.is_test]
    root_tokens: dict[str, int] = {}
    for item in production:
        root = Path(item.path).parts[0]
        root_tokens[root] = root_tokens.get(root, 0) + item.tokens
    primary_root = max(root_tokens, key=root_tokens.get) if root_tokens else ""
    production_areas = {(_subsystem(item, set(), [], primary_root)) for item in production}
    partitions: dict[tuple[str, bool], list[SourceFile]] = {}
    for item in files:
        area = _subsystem(item, production_areas, production, primary_root)
        partitions.setdefault((area, item.is_test), []).append(item)
    bins: list[Module] = []
    for (area, is_test), members in sorted(partitions.items()):
        strict_root = Path(primary_root) if area == "core" and not is_test else None
        for group in _directory_groups(members, strict_root=strict_root):
            bins.append(Module(len(bins), sorted(group, key=lambda item: item.path), area))
    return bins


def fallback_title(module: Module) -> str:
    directory, _ = primary_directory(module)
    return f"{'Tests' if module.is_test else 'Source'} in {directory or '.'}"[:80]


def primary_directory(module: Module) -> tuple[str, float]:
    counts: dict[str, int] = {}
    for item in module.files:
        directory = Path(item.path).parent.as_posix()
        counts[directory] = counts.get(directory, 0) + 1
    directory = min(counts, key=lambda path: (-counts[path], path))
    return directory, counts[directory] / len(module.files)
