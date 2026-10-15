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
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cbe.headless_completion import invoke
from cbe.token_budget import count_text_tokens


SUFFIXES = {".py", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs",
            ".cjs", ".c", ".h", ".cpp", ".cc", ".rs", ".sql"}
_SUFFIX_CACHE: set[str] | None = None


def supported_suffixes() -> set[str]:
    """Source suffixes to scan: the legacy floor plus every grammar the
    installed ``cbe.source_context`` discovers.

    The registry, not a hard-coded list, decides multi-language coverage; an
    extra grammar added to ``source_context`` becomes scannable here with no
    change. If that module is unavailable the legacy set is the honest floor.
    """
    global _SUFFIX_CACHE
    if _SUFFIX_CACHE is None:
        discovered: set[str] = set()
        try:
            from cbe import source_context
            for row in source_context.available_languages().get("languages") or []:
                for suffix in row.get("suffixes") or []:
                    text = str(suffix).lower()
                    discovered.add(text if text.startswith(".") else "." + text)
        except Exception:  # noqa: BLE001 - discovery is optional; the floor stands
            discovered = set()
        _SUFFIX_CACHE = discovered | SUFFIXES
    return _SUFFIX_CACHE
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


class SourceNotEmbedded(GenerateError):
    """A script-driver prompt lacks a source body it must embed before any model call.

    The v2.1.0 failure mode: modules were rebuilt from run state that keeps
    digests, not text, so every prompt named the files but carried empty bodies.
    """


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
    suffixes = supported_suffixes()
    files: list[SourceFile] = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in suffixes:
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
    return bins


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


def system_limit(module_count: int) -> int:
    """Overview and navigation must name every module, so the cap grows with them."""
    return max(2000, min(12000, 250 * module_count))


def _check_system(value: dict[str, Any], limit: int = 2000) -> None:
    for key in ("overview", "maintenance_navigation"):
        if not isinstance(value.get(key), str) or not value[key].strip() or len(value[key]) > limit:
            raise ValueError(f"{key} must be a nonempty concise string of at most {limit} characters")


def _check_review(value: dict[str, Any]) -> None:
    if value.get("decision") not in {"accepted", "needs_repair"}:
        raise ValueError("review decision must be accepted or needs_repair")
    if not isinstance(value.get("issues"), list) or any(not isinstance(x, str) for x in value["issues"]):
        raise ValueError("issues must be a list of strings")


# Repair-first validation. A strict miss is re-asked once with the exact
# error; if the second answer still misses, these normalizers make a usable
# answer compliant and return flags describing every change. They raise only
# when nothing usable is left (for example, no summary at all).


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:max(1, limit - 1)]
    floor = int(limit * 0.7)
    boundary = max((cut.rfind(mark) + len(mark) for mark in (". ", "。", "\n", "; ")
                    if cut.rfind(mark) >= floor), default=-1)
    if boundary < 0:
        boundary = cut.rfind(" ") if cut.rfind(" ") >= floor else len(cut)
    return cut[:boundary].rstrip() + "…"


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _fit(value: dict[str, Any], key: str, limit: int, flags: list[str], *, label: str | None = None) -> None:
    label = label or key
    text = value.get(key)
    if not isinstance(text, str):
        if text is not None:
            flags.append(f"{label} was {type(text).__name__}; converted to text")
        text = _as_text(text)
    if len(text) > limit:
        flags.append(f"{label} truncated from {len(text)} to {limit} characters")
        text = _truncate(text, limit)
    value[key] = text


def fallback_title(module: Module) -> str:
    directory, _ = _primary_directory(module)
    return f"{'Tests' if module.is_test else 'Source'} in {directory or '.'}"[:80]


def normalize_naming(value: Any, modules: list[Module]) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("naming result is not a JSON object")
    rows = value.get("names") if isinstance(value.get("names"), list) else []
    titles: dict[int, str] = {}
    for row in rows:
        if (isinstance(row, dict) and type(row.get("module")) is int and isinstance(row.get("title"), str)
                and row["title"].strip() and row["module"] not in titles
                and 0 <= row["module"] < len(modules)):
            titles[row["module"]] = row["title"]
    if not titles:
        raise ValueError("naming result has no usable titles")
    flags = []
    for module in modules:
        if module.number not in titles:
            titles[module.number] = fallback_title(module)
            flags.append(f"module {module.number + 1} had no title; used {titles[module.number]!r}")
    value["names"] = [{"module": number, "title": titles[number]} for number in sorted(titles)]
    _check_naming(value, modules)
    return flags


def normalize_system(value: Any, limit: int) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("overview result is not a JSON object")
    flags: list[str] = []
    for key in ("overview", "maintenance_navigation"):
        _fit(value, key, limit, flags)
    if not value["overview"].strip():
        raise ValueError("overview result has no overview")
    if not value["maintenance_navigation"].strip():
        value["maintenance_navigation"] = "See the subsystem list below."
        flags.append("maintenance_navigation was empty")
    _check_system(value, limit)
    return flags


def normalize_review(value: Any) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("review result is not a JSON object")
    flags: list[str] = []
    issues = value.get("issues")
    if not isinstance(issues, list):
        issues = [] if issues in (None, "") else [_as_text(issues)]
        flags.append("issues was not a list")
    value["issues"] = [_as_text(item) for item in issues]
    if value.get("decision") not in {"accepted", "needs_repair"}:
        value["decision"] = "needs_repair" if value["issues"] else "accepted"
        flags.append(f"decision was invalid; treated as {value['decision']}")
    _check_review(value)
    return flags


def _mark_result(csv_path: Path, task: str, attempt: int, result: str) -> None:
    # This runs after invoke has appended its row. Other workers may append
    # rows meanwhile, so rewrite under the same lock invoke uses.
    from cbe.headless_completion import CSV_LOCK, FIELDS
    with CSV_LOCK:
        with csv_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            if row["task"] == task and row["attempt"] == str(attempt):
                row["result"] = result
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


def _primary_directory(module: Module) -> tuple[str, float]:
    counts: dict[str, int] = {}
    for item in module.files:
        directory = Path(item.path).parent.as_posix()
        counts[directory] = counts.get(directory, 0) + 1
    directory = min(counts, key=lambda path: (-counts[path], path))
    return directory, counts[directory] / len(module.files)


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


# A script completion has no file tools, so the model must have been sent the source text. If the
# model reports far fewer input tokens than the source it was sent, it never saw the code.
DELIVERY_FLOOR = 0.5


def _delivery_problem(run_dir: Path, csv_path: Path) -> tuple[str | None, str]:
    """Return ("source_not_delivered", detail) when reported input is under half the source sent."""
    if not csv_path.is_file():
        return None, ""
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    from cbe import host_run
    sent = host_run.source_sent_tokens(state)
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    # Cached input still reached the model, so count it; calls without usage add nothing.
    reported = sum(int(row[field]) for row in rows for field in ("input_tokens", "cache_tokens") if row[field])
    if sent <= 0 or not any(row["input_tokens"] for row in rows) or reported >= DELIVERY_FLOOR * sent:
        return None, ""
    return "source_not_delivered", (f"model-reported input {reported} tokens is under "
                                    f"{int(DELIVERY_FLOOR * 100)}% of the {sent} source tokens sent")


# Tasks whose prompt embeds source bodies; names and system prompts embed none.
SOURCE_TASK_KINDS = ("module", "repair", "review")


def _embedded_paths(state: dict[str, Any], task_id: str) -> list[str]:
    """Module file paths a task's prompt must embed; empty when it embeds none."""
    task = state["tasks"][task_id]
    if task["kind"] not in SOURCE_TASK_KINDS:
        return []
    return list(state["modules"][task["module"]]["files"])


def _verify_embedded_source(run_dir: Path, task_id: str, prompt: str) -> None:
    """Pre-flight before each script-driver model call: every file the task's
    prompt must embed is present in the prompt with its full body, read back
    from disk and checked against the plan digest.

    Under the semantic mainline the prompt embeds the frozen context chunks
    rather than whole files, so the check is that each of the task's chunks is
    present verbatim in the prompt. Raises :class:`SourceNotEmbedded` naming the
    file, so the run stops before the call is spent."""
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    paths = _embedded_paths(state, task_id)
    if not paths:
        return
    planned = {row["path"]: row for row in state["files"]}
    repo = Path(state["repo"])
    for path in paths:
        row = planned[path]
        try:
            raw = (repo / path).read_bytes()
        except OSError as exc:
            raise SourceNotEmbedded(f"{path}: cannot be read ({exc.strerror or exc})") from exc
        if hashlib.sha256(raw).hexdigest() != row["digest"]:
            raise SourceNotEmbedded(f"{path}: changed since the plan (digest mismatch)")
        body = raw.decode("utf-8")
        if not body and not row["tokens"]:
            continue  # an empty file embeds nothing by design
        if body not in prompt:
            raise SourceNotEmbedded(
                f"{path}: not embedded in the prompt ({row['tokens']} planned tokens); the model was not called")


def _call_delivery_problem(run_dir: Path, task_id: str,
                           usage: dict[str, int | None] | None) -> str | None:
    """Per-call delivery check: reject an answer unless the model reported at
    least the delivery floor of the source tokens embedded in its own prompt.

    Returns None when the call is fine or nothing was reported (the caller
    records ``usage_unknown`` for silent hosts instead of failing)."""
    if not usage:
        return None
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    paths = _embedded_paths(state, task_id)
    if not paths:
        return None
    planned = {row["path"]: row["tokens"] for row in state["files"]}
    sent = sum(planned[path] for path in paths)
    reported = (usage.get("input") or 0) + (usage.get("cache") or 0)
    if sent <= 0 or reported >= DELIVERY_FLOOR * sent:
        return None
    return (f"source_not_delivered: reported {reported} input tokens (input + cache-read) "
            f"against the {sent} source tokens embedded in this prompt")


def _csv_task(task_id: str, review: str) -> str:
    """Keep calls.csv task names comparable with earlier script runs."""
    if task_id == "names":
        return "module_names"
    if task_id == "system":
        return "system_overview"
    if review == "sample" and task_id.startswith(("review_", "repair_")):
        return "sample_review" if task_id.startswith("review_") else "sample_repair"
    return task_id


def generate(repo: Path, run_dir: Path, *, model: str, config: Path | None = None,
             jobs: int = 4, review: str | None = None, timeout: int = 360,
             host: str = "opencode", resume: bool = False,
             graph_path: Path | None = None, api_base_url: str | None = None,
             api_key_env: str | None = None) -> dict[str, Any]:
    """Script driver: the shared run state, with each task as one tool-free completion.

    A task failure never voids the run. Finished modules render; failed parts
    stay pending in the run state, and ``resume=True`` continues the same run.

    Two hard delivery checks guard every call: a pre-flight that each prompt
    really embeds its module's source (``SourceNotEmbedded`` stops the run
    before the call is spent), and a per-call token check that rejects answers
    whose reported input is under half the embedded source.
    """
    from cbe import host_run

    review = review or host_run.DEFAULT_REVIEW
    repo, run_dir = repo.resolve(), run_dir.resolve()
    if not repo.is_dir():
        raise GenerateError("repository root is not a directory")
    if jobs < 1 or review not in host_run.REVIEW_MODES or timeout < 1:
        raise GenerateError("jobs and timeout must be positive; review must be none, sample, or all")
    if host not in {"opencode", "devin", "api"}:
        raise GenerateError("host must be opencode, devin or api")
    if host == "opencode" and ("/" not in model or model.startswith("/") or model.endswith("/")):
        raise GenerateError("OpenCode model must be a provider/model name")
    if host == "devin" and (not model or "/" in model):
        raise GenerateError("Devin model must be one exact catalog model ID")
    if host == "api" and not model:
        raise GenerateError("API host requires a model name (--model)")
    has_state = (run_dir / "host" / "state.json").is_file()
    if resume and not has_state:
        raise GenerateError("nothing to resume: the run directory has no run state")
    if not resume and ((run_dir / "calls.csv").exists() or has_state):
        raise GenerateError("run directory already contains a run; pass --resume or choose a fresh run directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    if config is None:
        config = run_dir / f"{host}-completion.json"
        if not config.is_file():
            if host == "devin":
                from cbe.devin_completion import DEFAULT_DEVIN_CONFIG
                default_config = DEFAULT_DEVIN_CONFIG
            elif host == "api":
                from cbe.api_completion import DEFAULT_API_CONFIG
                default_config = DEFAULT_API_CONFIG
            else:
                default_config = DEFAULT_HOST_CONFIG
            config.write_text(json.dumps(default_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        config = config.resolve()
        if not config.is_file():
            raise GenerateError(f"{host} config file does not exist")
    api_overrides: dict[str, Any] = {}
    if host == "api":
        # Apply the CLI overrides in memory only: never copy a user config that
        # may carry an auth header into the run directory.
        if api_base_url:
            api_overrides["base_url"] = api_base_url
        if api_key_env:
            api_overrides["api_key_env"] = api_key_env
    started = time.monotonic()
    if resume:
        host_run.resume(run_dir, owner=host, graph_path=graph_path)
    else:
        host_run.plan(repo, run_dir, review=review, jobs=jobs, host=host, driver="script",
                      graph_path=graph_path)
    review = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))["review"]
    csv_path = run_dir / "calls.csv"
    stopped: str | None = None
    active: dict[Any, tuple[dict[str, Any], str]] = {}
    preflight: SourceNotEmbedded | None = None
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        while True:
            if stopped is None and preflight is None and len(active) < jobs:
                try:
                    batch = host_run.next_tasks(run_dir, limit=jobs - len(active), owner=host)["tasks"]
                except host_run.HostRunError as exc:
                    # Dispatch itself refused the task (a listed source is
                    # missing, unreadable, or drifted); stop the same way.
                    preflight = SourceNotEmbedded(str(exc))
                    host_run.mark_partial(run_dir, "source_not_embedded", str(preflight))
                    batch = []
                for item in batch:
                    csv_task = _csv_task(item["task"], review)
                    try:
                        prompt = host_run.completion_prompt(run_dir, item["task"])
                        _verify_embedded_source(run_dir, item["task"], prompt)
                    except (SourceNotEmbedded, host_run.HostRunError, OSError) as exc:
                        # The prompt cannot carry this module's source (unreadable,
                        # drifted, or bodies missing), so the model must not be
                        # called; stop the run instead of paying for documentation
                        # written from file names.
                        preflight = exc if isinstance(exc, SourceNotEmbedded) else SourceNotEmbedded(str(exc))
                        host_run.mark_partial(run_dir, "source_not_embedded", str(preflight))
                        break
                    future = pool.submit(invoke, task=csv_task, attempt=item["attempt"],
                                         prompt=prompt,
                                         repo=repo, run_dir=run_dir, model=model, config=config,
                                         timeout=timeout, csv_path=csv_path, host=host,
                                         api_overrides=api_overrides or None)
                    active[future] = (item, csv_task)
            if not active:
                break
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                item, csv_task = active.pop(future)
                try:
                    completion = future.result()
                except Exception as exc:  # noqa: BLE001 - one broken call must not void the run
                    outcome = host_run.submit(run_dir, item["task"], error=f"driver_error:{exc}")
                    continue
                if completion.error:
                    outcome = host_run.submit(run_dir, item["task"], error=completion.error,
                                              raw_text=completion.raw_text or None)
                    if completion.error in {"provider_limit", "provider_auth"}:
                        stopped = completion.error
                    continue
                delivery = _call_delivery_problem(run_dir, item["task"], completion.usage)
                if delivery is not None:
                    # The model never saw this prompt's source, so its answer
                    # is not accepted; the retry/partial logic takes over.
                    outcome = host_run.submit(run_dir, item["task"], error=delivery,
                                              raw_text=completion.raw_text or None)
                    _mark_result(csv_path, csv_task, item["attempt"], "source_not_delivered")
                    continue
                if completion.usage is None:
                    host_run.note_usage_unknown(run_dir, item["task"], item["attempt"])
                Path(item["output_file"]).write_text(completion.raw_text, encoding="utf-8")
                outcome = host_run.submit(run_dir, item["task"])
                if not outcome["accepted"] and outcome["error"].startswith("schema_error"):
                    # The host call completed; its CSV row must still show the check failure.
                    _mark_result(csv_path, csv_task, item["attempt"], "schema_error")
                elif outcome.get("normalized"):
                    _mark_result(csv_path, csv_task, item["attempt"], "normalized")
    if stopped or preflight is not None:
        host_run.release(run_dir)
    cost = _cost(run_dir, host=host) if csv_path.is_file() else {"calls": 0}
    if preflight is None:
        host_run.mark_partial(run_dir, *_delivery_problem(run_dir, csv_path))
    result = host_run.finish(run_dir)
    summary = {**result, "status": result.get("status", "partial"),
               "stopped": stopped, "wall_seconds": round(time.monotonic() - started, 3),
               "run_dir": str(run_dir), "index": str(run_dir / "docs" / "INDEX.md"),
               "progress_log": str(run_dir / "progress.log"), "host": host, "model": model,
               "input_token_basis": ("Devin CLI reported input_tokens; cache inclusion is unverified"
                                     if host == "devin" else "OpenCode noncached input tokens"),
               **cost}
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if preflight is not None:
        raise preflight
    return summary


def _query_catalog(run_dir: Path) -> dict[str, Any]:
    from cbe.semantic import catalog_symbols

    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    catalog["symbols"] = catalog_symbols(catalog)
    return catalog


def find(run_dir: Path, term: str, limit: int = 25) -> list[dict[str, Any]]:
    catalog = _query_catalog(run_dir)
    needle = term.casefold()
    results = [{"id": sid, **record} for sid, record in catalog["symbols"].items()
               if needle in sid.casefold() or needle in json.dumps(record, ensure_ascii=False).casefold()]
    # Module-level facts (constants, option tables, templates) live on file
    # entries; their text is searched like symbol notes.
    results += [{"id": path, **record} for path, record in catalog["files"].items()
                if record.get("facts")
                and needle in json.dumps(record["facts"], ensure_ascii=False).casefold()]
    return results[:limit]


def query(run_dir: Path, symbol_id: str) -> dict[str, Any]:
    catalog = _query_catalog(run_dir)
    if symbol_id in catalog["symbols"]:
        return {"id": symbol_id, **catalog["symbols"][symbol_id]}
    if symbol_id in catalog["files"]:
        return {"id": symbol_id, **catalog["files"][symbol_id]}
    raise GenerateError(f"unknown symbol or file: {symbol_id}")
