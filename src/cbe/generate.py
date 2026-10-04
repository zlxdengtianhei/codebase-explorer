"""Script-driven, single-turn codebase documentation generation.

The controller is ordinary Python: there is no model parent session and no
per-task native handoff. Every host completion is a fresh, tool-free session.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cbe.headless_completion import invoke
from cbe.inventory import build_inventory
from cbe.syntax_facts import atoms_for
from cbe.token_budget import count_text_tokens


SUFFIXES = {".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs",
            ".cjs", ".c", ".h", ".cpp", ".cc", ".rs", ".sql"}
TARGET_TOKENS = 20_000
MAX_TOKENS = 25_000
MAX_SINGLE_FILE_TOKENS = 60_000
FIXED = """You document source code in one response. Use only supplied source and signatures. Never use tools or ask to read files. Return exactly one JSON object, no Markdown fences. Separate observed syntax from inferred behavior; state uncertainty instead of inventing runtime facts. Be concise. Test functions and trivial accessors need no individual prose. Paths identify files; do not repeat large source passages."""
DEFAULT_HOST_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "agent": {"cbe-completion": {
        "mode": "primary",
        "description": "One-shot source documentation with no tools",
        "prompt": "You are a documentation completion engine. Follow the user-provided JSON schema and source evidence. Do not use tools, request files, or infer runtime behavior absent from the supplied source. Return only one JSON object.",
        "permission": {"*": "deny"},
    }},
    # The run isolates XDG_CONFIG_HOME so unrelated global instructions do
    # not enter every call. Include the default model definition in that
    # isolated config; OpenCode still reads its normal auth store for the key.
    "provider": {"zai-coding-plan": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Z.AI Coding Plan",
        "options": {"baseURL": "https://api.z.ai/api/coding/paas/v4"},
        "models": {"glm-5.3-flash": {"name": "GLM-5.3-Flash",
                                     "limit": {"context": 200000, "output": 32768}}},
    }},
}


class GenerateError(ValueError):
    pass


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
    depends_on: set[int] = field(default_factory=set)
    output: dict[str, Any] | None = None

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
    files: list[SourceFile] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in SUFFIXES:
            continue
        if any(part in {".git", ".venv", "venv", "node_modules", "__pycache__", ".codebase-analysis"}
               for part in path.relative_to(repo).parts):
            continue
        raw = path.read_bytes()
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GenerateError(f"source is not UTF-8: {path.relative_to(repo)}") from exc
        rel = path.relative_to(repo).as_posix()
        files.append(SourceFile(rel, source, count_text_tokens(source), hashlib.sha256(raw).hexdigest(),
                                _signatures(rel, source), _imports(rel, source)))
    if not files:
        raise GenerateError("no supported source files")
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


def _linked(left: SourceFile, right: SourceFile) -> bool:
    candidates = {right.path, Path(right.path).name, Path(right.path).stem,
                  ".".join(Path(right.path).with_suffix("").parts),
                  ".".join(Path(right.path).with_suffix("").parts[1:])}
    return any(ref in candidates or any(ref.endswith("." + candidate) for candidate in candidates if candidate)
               for ref in left.imports)


def _pack_directory(files: list[SourceFile], *, strict: bool = False) -> list[list[SourceFile]]:
    """Join imports first, then fill only within a specific source directory."""
    groups = [[item] for item in sorted(files, key=lambda item: item.path)]
    while True:
        pairs = []
        for left in range(len(groups)):
            for right in range(left + 1, len(groups)):
                combined = groups[left] + groups[right]
                if sum(item.tokens for item in combined) > MAX_TOKENS:
                    continue
                links = sum(_linked(a, b) + _linked(b, a)
                            for a in groups[left] for b in groups[right])
                if links:
                    pairs.append((links, -abs(TARGET_TOKENS - sum(item.tokens for item in combined)),
                                  -left, -right, left, right))
        if not pairs:
            break
        *_, left, right = max(pairs)
        groups[left].extend(groups.pop(right))
    if strict:
        return groups
    packed: list[list[SourceFile]] = []
    for group in sorted(groups, key=lambda group: (-sum(item.tokens for item in group), group[0].path)):
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
            raise GenerateError(f"one whole source file exceeds {MAX_SINGLE_FILE_TOKENS} tokens: {item.path}")
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
    for module in bins:
        for other in bins:
            if module.number != other.number and any(_linked(file, dependency)
                    for file in module.files for dependency in other.files):
                module.depends_on.add(other.number)
    return bins


def _dependency_components(modules: list[Module]) -> dict[int, set[int]]:
    """Treat import cycles as concurrent units; wait only for outside dependencies."""
    order = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    index: dict[int, int] = {}
    low: dict[int, int] = {}
    membership: dict[int, set[int]] = {}

    def visit(node: int) -> None:
        nonlocal order
        index[node] = low[node] = order
        order += 1
        stack.append(node)
        on_stack.add(node)
        for dep in modules[node].depends_on:
            if dep not in index:
                visit(dep)
                low[node] = min(low[node], low[dep])
            elif dep in on_stack:
                low[node] = min(low[node], index[dep])
        if low[node] == index[node]:
            group: set[int] = set()
            while True:
                member = stack.pop()
                on_stack.remove(member)
                group.add(member)
                if member == node:
                    break
            for member in group:
                membership[member] = group

    for module in modules:
        if module.number not in index:
            visit(module.number)
    return membership


def _check_naming(value: dict[str, Any], modules: list[Module]) -> None:
    rows = value.get("names")
    if not isinstance(rows, list) or len(rows) != len(modules):
        raise ValueError("names must contain one entry per module")
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("module")) is not int or not isinstance(row.get("title"), str):
            raise ValueError("each name needs integer module and string title")
        if row["module"] in seen or not row["title"].strip():
            raise ValueError("duplicate or empty module title")
        title = row["title"].strip()
        if len(title) > 80:
            title = title[:80].rsplit(" ", 1)[0] or title[:80]
        row["title"] = title
        seen.add(row["module"])
    if seen != {module.number for module in modules}:
        raise ValueError("module title IDs do not match planned modules")


def _check_module(value: dict[str, Any], module: Module) -> None:
    for key, limit in (("summary", 1500), ("flow", 2000)):
        if not isinstance(value.get(key), str) or not value[key].strip() or len(value[key]) > limit:
            raise ValueError(f"{key} must be a nonempty concise string")
    coverage = value.get("test_coverage")
    if isinstance(coverage, (list, dict)):
        # Providers sometimes structure a long test summary as JSON instead of
        # one string. Preserve that content as readable text for rendering.
        coverage = json.dumps(coverage, ensure_ascii=False, indent=2)
    if not isinstance(coverage, str):
        raise ValueError("test_coverage must be text or a JSON list/object")
    coverage_limit = max(1500, min(12000, module.tokens // 2))
    if len(coverage) > coverage_limit:
        raise ValueError(f"test_coverage exceeds module-sized limit of {coverage_limit} characters")
    value["test_coverage"] = coverage
    if module.is_test and not value["test_coverage"].strip():
        raise ValueError("test modules require a test_coverage summary")
    highlights = value.get("key_behaviors")
    if not isinstance(highlights, list):
        raise ValueError("key_behaviors must be a list")
    if len(highlights) > 16:
        highlights = value["key_behaviors"] = highlights[:16]
    if module.is_test or not any(file.signatures for file in module.files):
        # Test and unsupported-language symbol prose is not published; their
        # file/signature catalogue and module coverage summary remain.
        highlights = value["key_behaviors"] = []
    alias_ids: dict[str, set[str]] = {}
    for file in module.files:
        stem = Path(file.path).stem
        dotted = ".".join(Path(file.path).with_suffix("").parts)
        if dotted.startswith("src."):
            dotted = dotted[4:]
        for name in file.signatures:
            source_id = f"{file.path}::{name}"
            for alias in (name, f"{stem}.{name}", f"{dotted}.{name}", source_id):
                alias_ids.setdefault(alias, set()).add(source_id)
    valid_highlights: list[dict[str, Any]] = []
    for row in highlights:
        if not isinstance(row, dict) or not isinstance(row.get("symbol"), str):
            raise ValueError(f"unknown key behavior symbol: {row.get('symbol') if isinstance(row, dict) else row}")
        matches = alias_ids.get(row["symbol"], set())
        if len(matches) != 1:
            # A short alias can name several files in an examples tree. Do
            # not publish prose against an arbitrary source symbol.
            continue
        row["source_id"] = next(iter(matches))
        for key in ("behavior", "conditions", "failures"):
            if not isinstance(row.get(key), str) or len(row[key]) > 750:
                raise ValueError(f"key_behaviors.{key} must be a concise string")
        valid_highlights.append(row)
    value["key_behaviors"] = valid_highlights
    uncertainties = value.get("uncertainties")
    if not isinstance(uncertainties, list) or len(uncertainties) > 8 or any(
            not isinstance(item, str) or len(item) > 400 for item in uncertainties):
        raise ValueError("uncertainties must be a list of short strings")


def _check_system(value: dict[str, Any]) -> None:
    for key in ("overview", "maintenance_navigation"):
        if not isinstance(value.get(key), str) or not value[key].strip() or len(value[key]) > 2000:
            raise ValueError(f"{key} must be a nonempty concise string")


def _check_review(value: dict[str, Any]) -> None:
    if value.get("decision") not in {"accepted", "needs_repair"}:
        raise ValueError("review decision must be accepted or needs_repair")
    if not isinstance(value.get("issues"), list) or any(not isinstance(x, str) for x in value["issues"]):
        raise ValueError("issues must be a list of strings")


def _call(*, task: str, prompt: str, check: Any, repo: Path, run_dir: Path,
          model: str, config: Path, timeout: int, host: str = "opencode") -> dict[str, Any]:
    previous_error = ""
    for attempt in (1, 2):
        full_prompt = FIXED + "\n\n" + prompt
        if previous_error:
            full_prompt += "\n\nPrevious completion failed. Correct it now. Original error: " + previous_error
        completion = invoke(task=task, attempt=attempt, prompt=full_prompt,
                            repo=repo, run_dir=run_dir, model=model, config=config,
                            timeout=timeout, csv_path=run_dir / "calls.csv", host=host)
        if completion.error:
            previous_error = completion.error
            if completion.error in {"provider_limit", "provider_auth"}:
                break
            continue
        try:
            check(completion.value)
        except (ValueError, TypeError) as exc:
            previous_error = f"schema_error:{exc}; original_output:{completion.raw_text}"
            # The host call itself completed, but its CSV result must show the
            # schema failure. Do not erase its observed usage.
            _mark_schema_failure(run_dir / "calls.csv", task, attempt)
            continue
        return completion.value or {}
    raise GenerateError(f"{task} failed after two physical calls: {previous_error[:250]}")


def _mark_schema_failure(csv_path: Path, task: str, attempt: int) -> None:
    # This runs after invoke has appended its row. No other writer can modify
    # that row while _call is inside one worker, but other workers may append.
    from cbe.headless_completion import CSV_LOCK, FIELDS
    with CSV_LOCK:
        with csv_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            if row["task"] == task and row["attempt"] == str(attempt):
                row["result"] = "schema_error"
                break
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def _name_prompt(modules: list[Module]) -> str:
    rows = [{"module": module.number, "subsystem": module.bucket,
             "kind": "tests" if module.is_test else "source",
             "files": [f.path for f in module.files],
             "signatures": [name for f in module.files for name in f.signatures[:30]]}
            for module in modules]
    return ("TASK: Give each source module a short functional title, not a numbered part or path hash. "
            "Return JSON: {\"names\":[{\"module\":0,\"title\":\"...\"}, ...]}. "
            "Respect each module's subsystem and test/source kind. Name the common role, not a list of unrelated files. "
            "Keep mixed-language scope honest. Modules:\n" + json.dumps(rows, ensure_ascii=False))


def _module_prompt(module: Module, modules: list[Module], issues: list[str] | None = None) -> str:
    dependencies = [other for other in modules if other.number in module.depends_on]
    dep_lines = [f"{other.title}: " + ", ".join(
        f"{file.path}: {', '.join(file.signatures[:30])}" for file in other.files)
        for other in dependencies]
    aliases = [(f"{Path(file.path).stem}.{name}", f"{file.path}::{name}")
               for file in module.files for name in file.signatures]
    counts = Counter(alias for alias, _ in aliases)
    symbols = ([] if module.is_test else
               [alias if counts[alias] == 1 else source_id for alias, source_id in aliases])
    header = (f"TASK: Document the module titled {module.title}. Return JSON with string fields "
              "summary, flow, test_coverage; key_behaviors is a list of at most 16 objects with "
              "symbol, behavior, conditions, failures strings; uncertainties is a list of short strings. "
              "Choose only meaningful symbols from the given signature list and copy their names exactly. "
              "If this module consists of tests, "
              "summarize tested behavior once and leave key_behaviors empty. Do not claim test execution. "
              "Keep each field compact; use empty strings for conditions or failures when not established. "
              "If Available symbols is empty, key_behaviors MUST be an empty list even when the source contains "
              "commands or functions; describe them in summary or flow instead.\n"
              f"Available symbols: {json.dumps(symbols, ensure_ascii=False)}\n"
              f"Dependency signatures: {json.dumps(dep_lines, ensure_ascii=False)}\n")
    if issues:
        header += "Correct these review findings without broadening claims: " + json.dumps(issues, ensure_ascii=False) + "\n"
    for file in sorted(module.files, key=lambda item: item.path):
        header += f"\nSOURCE FILE {file.path}\n```\n{file.source}\n```\n"
    return header


def _verify_source(repo: Path, files: list[SourceFile]) -> None:
    for file in files:
        if hashlib.sha256((repo / file.path).read_bytes()).hexdigest() != file.digest:
            raise GenerateError(f"source changed during generation: {file.path}")


def _slug(title: str, number: int) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:65]
    return text or f"module-{number + 1}"


def _primary_directory(module: Module) -> tuple[str, float]:
    counts: dict[str, int] = {}
    for item in module.files:
        directory = Path(item.path).parent.as_posix()
        counts[directory] = counts.get(directory, 0) + 1
    directory = min(counts, key=lambda path: (-counts[path], path))
    return directory, counts[directory] / len(module.files)


def _guard_rows(repo: Path, files: list[SourceFile]) -> dict[str, list[dict[str, Any]]]:
    if not any(item.path.endswith(".py") for item in files):
        return {}
    inventory = build_inventory(repo)
    ledger = {"repo_root": str(repo), "inventory": inventory.to_dict()}
    rows: dict[str, list[dict[str, Any]]] = {}
    for sid, symbol in ledger["inventory"]["symbols"].items():
        if symbol.get("kind") not in {"function", "method"}:
            continue
        # The general fact API keeps a short first-page default. A published
        # module page needs later guarded outcomes too: an early sequence of
        # checks must not hide the final no-work/status branch.
        facts = atoms_for(ledger, sid, max_atoms=32)
        interesting = [atom for atom in facts["atoms"] if atom["guards"] or atom["kind"] in {
            "raise_expression", "reraise", "return_none"}]
        if interesting:
            rows.setdefault(symbol["path"], []).extend({"symbol": symbol["name"], **atom}
                                                        for atom in interesting)
    return rows


def _render(repo: Path, run_dir: Path, files: list[SourceFile], modules: list[Module],
            system: dict[str, Any]) -> dict[str, Any]:
    _verify_source(repo, files)
    output = run_dir / "docs"
    pages = output / "modules"
    pages.mkdir(parents=True, exist_ok=True)
    guards = _guard_rows(repo, files)
    catalog: dict[str, Any] = {"modules": [], "symbols": {}, "files": {}}
    index = ["# Codebase Explorer", "", system["overview"], "", "## Maintenance navigation", "",
             system["maintenance_navigation"], "", "## Subsystems", ""]
    used_slugs: set[str] = set()
    current_subsystem = None
    for module in modules:
        if module.bucket != current_subsystem:
            current_subsystem = module.bucket
            index += [f"### {current_subsystem.replace('_', ' ').title()}", ""]
        slug = _slug(module.title, module.number)
        if slug in used_slugs:
            slug += f"-{module.number + 1}"
        used_slugs.add(slug)
        page = f"modules/{slug}.md"
        result = module.output or {}
        lines = [f"# {module.title}", "", result.get("summary", ""), "", "## Flow", "",
                 result.get("flow", ""), "", "## Key behaviors", ""]
        highlights = result.get("key_behaviors") or []
        if highlights:
            for item in highlights:
                lines += [f"- **{item['symbol']}** — {item['behavior']}"]
                if item["conditions"]:
                    lines += [f"  - Conditions: {item['conditions']}"]
                if item["failures"]:
                    lines += [f"  - Failures: {item['failures']}"]
        else:
            lines.append("No individual behavior prose; see the source catalogue below.")
        lines += ["", "## Test coverage", "", result.get("test_coverage") or "No test coverage established for this module.", "",
                  "## Source catalogue", ""]
        for file in sorted(module.files, key=lambda item: item.path):
            lines += [f"### `{file.path}`", ""]
            if file.signatures:
                lines += ["; ".join(f"`{name}`" for name in file.signatures), ""]
            else:
                lines += ["Mechanically indexed file; no supported symbol parser in this baseline.", ""]
            catalog["files"][file.path] = {"module": module.title, "page": page,
                                            "tokens": file.tokens, "language": Path(file.path).suffix}
            for name in file.signatures:
                sid = f"{file.path}::{name}"
                catalog["symbols"][sid] = {"file": file.path, "name": name, "module": module.title,
                                            "page": page, "notes": [x for x in highlights if x.get("source_id") == sid]}
            if guards.get(file.path):
                lines += ["## Conditions and failure paths (mechanical syntax)", "",
                          "Lexical guards and statements only; reachability and runtime effects are unverified.", "",
                          "| Symbol | Guard | Statement |", "|---|---|---|"]
                for atom in guards[file.path]:
                    guard = " / ".join(atom["guards"]).replace("|", "\\|") or "—"
                    syntax = atom["syntax"].replace("|", "\\|")
                    lines.append(f"| `{atom['symbol']}` | `{guard}` | `{syntax}` |")
                lines.append("")
        if result.get("uncertainties"):
            lines += ["## Uncertainties", ""] + [f"- {item}" for item in result["uncertainties"]]
        (output / page).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        directory, share = _primary_directory(module)
        kind = "tests" if module.is_test else "source"
        index.append(f"- [{module.title}]({page}) — {kind}; primary directory "
                     f"`{directory}` {share:.0%} ({len(module.files)} files): "
                     f"{', '.join(f.path for f in module.files)}")
        catalog["modules"].append({"title": module.title, "page": page,
                                   "files": [f.path for f in module.files], "source_tokens": module.tokens})
    (output / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    (run_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def _cost(run_dir: Path, *, host: str = "opencode") -> dict[str, Any]:
    with (run_dir / "calls.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    fields = ("input_tokens", "output_tokens", "cache_tokens")
    complete = {field: all(row[field] != "" for row in rows) for field in fields}
    totals = {field: sum(int(row[field]) for row in rows if row[field]) for field in fields}
    known = all(complete.values())
    input_tokens, output_tokens, cache_tokens = (totals[field] for field in fields)
    return {"calls": len(rows),
            **{field: totals[field] if complete[field] else None for field in fields},
            "observed_cache_tokens": cache_tokens,
            "calls_with_unknown_cache": sum(row["cache_tokens"] == "" for row in rows),
            "priced_usd": round((input_tokens * 5 + output_tokens * 25 + cache_tokens * .5) / 1_000_000, 6)
            if known and host == "opencode" else None,
            "usage_complete": known, "seconds": round(sum(float(row["seconds"]) for row in rows), 3)}


def generate(repo: Path, run_dir: Path, *, model: str, config: Path | None = None,
             jobs: int = 4, review: str = "sample", timeout: int = 360,
             host: str = "opencode") -> dict[str, Any]:
    repo, run_dir = repo.resolve(), run_dir.resolve()
    if not repo.is_dir():
        raise GenerateError("repository root is not a directory")
    if jobs < 1 or review not in {"none", "sample"} or timeout < 1:
        raise GenerateError("jobs and timeout must be positive; review must be none or sample")
    if host not in {"opencode", "devin"}:
        raise GenerateError("host must be opencode or devin")
    if host == "opencode" and ("/" not in model or model.startswith("/") or model.endswith("/")):
        raise GenerateError("OpenCode model must be a provider/model name")
    if host == "devin" and (not model or "/" in model):
        raise GenerateError("Devin model must be one exact catalog model ID")
    if (run_dir / "calls.csv").exists():
        raise GenerateError("run directory already contains calls; choose a fresh run directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    if config is None:
        config = run_dir / f"{host}-completion.json"
        if host == "devin":
            from cbe.devin_completion import DEFAULT_DEVIN_CONFIG
            default_config = DEFAULT_DEVIN_CONFIG
        else:
            default_config = DEFAULT_HOST_CONFIG
        config.write_text(json.dumps(default_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        config = config.resolve()
        if not config.is_file():
            raise GenerateError(f"{host} config file does not exist")
    started = time.monotonic()
    files = scan(repo)
    modules = plan(files)
    names = _call(task="module_names", prompt=_name_prompt(modules),
                  check=lambda value: _check_naming(value, modules), repo=repo, run_dir=run_dir,
                  model=model, config=config, timeout=timeout, host=host)
    for row in names["names"]:
        modules[row["module"]].title = row["title"].strip()

    pending = {module.number for module in modules}
    completed: set[int] = set()
    active: dict[Any, int] = {}
    components = _dependency_components(modules)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        while pending or active:
            ready = [mid for mid in sorted(pending)
                     if (modules[mid].depends_on - components[mid]) <= completed]
            for mid in ready[:max(0, jobs - len(active))]:
                module = modules[mid]
                future = pool.submit(_call, task=f"module_{mid + 1}",
                    prompt=_module_prompt(module, modules),
                    check=lambda value, chosen=module: _check_module(value, chosen),
                    repo=repo, run_dir=run_dir, model=model, config=config, timeout=timeout,
                    host=host)
                active[future] = mid
                pending.remove(mid)
            if not active:
                raise GenerateError("module dependency scheduling deadlock")
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                mid = active.pop(future)
                modules[mid].output = future.result()
                completed.add(mid)

    if review == "sample":
        chosen = max(modules, key=lambda module: (module.tokens, -module.number))
        question = ("TASK: Check this module documentation against the source. Return JSON "
                    "{\"decision\":\"accepted\" or \"needs_repair\",\"issues\":[...]} . "
                    "Only report material unsupported or missing behavior.\n"
                    "DOCUMENTATION: " + json.dumps(chosen.output, ensure_ascii=False) + "\n"
                    + _module_prompt(chosen, modules))
        verdict = _call(task="sample_review", prompt=question, check=_check_review,
                        repo=repo, run_dir=run_dir, model=model, config=config, timeout=timeout,
                        host=host)
        if verdict["decision"] == "needs_repair" and verdict["issues"]:
            chosen.output = _call(task="sample_repair", prompt=_module_prompt(chosen, modules, verdict["issues"]),
                                  check=lambda value: _check_module(value, chosen), repo=repo, run_dir=run_dir,
                                  model=model, config=config, timeout=timeout, host=host)

    summaries = [{"title": module.title, "summary": module.output["summary"],
                  "flow": module.output["flow"], "files": [file.path for file in module.files]}
                 for module in modules]
    system = _call(task="system_overview", prompt=("TASK: Synthesize only these module summaries. "
        "Return JSON with nonempty strings overview and maintenance_navigation. "
        "Explain which module to open for a maintenance question; do not invent unseen details.\n"
        + json.dumps(summaries, ensure_ascii=False)), check=_check_system,
        repo=repo, run_dir=run_dir, model=model, config=config, timeout=timeout, host=host)
    catalog = _render(repo, run_dir, files, modules, system)
    cost = _cost(run_dir, host=host)
    summary = {"status": "complete", "source_files": len(files),
               "source_tokens": sum(file.tokens for file in files), "modules": len(modules),
               "published_pages": len(catalog["modules"]) + 1,
               "wall_seconds": round(time.monotonic() - started, 3),
               "run_dir": str(run_dir), "index": str(run_dir / "docs" / "INDEX.md"),
               "host": host, "model": model,
               "input_token_basis": ("Devin CLI reported input_tokens; cache inclusion is unverified"
                                     if host == "devin" else "OpenCode noncached input tokens"),
               **cost}
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def find(run_dir: Path, term: str, limit: int = 25) -> list[dict[str, Any]]:
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    needle = term.casefold()
    results = [{"id": sid, **record} for sid, record in catalog["symbols"].items()
               if needle in sid.casefold() or needle in json.dumps(record, ensure_ascii=False).casefold()]
    return results[:limit]


def query(run_dir: Path, symbol_id: str) -> dict[str, Any]:
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    if symbol_id in catalog["symbols"]:
        return {"id": symbol_id, **catalog["symbols"][symbol_id]}
    if symbol_id in catalog["files"]:
        return {"id": symbol_id, **catalog["files"][symbol_id]}
    raise GenerateError(f"unknown symbol or file: {symbol_id}")
