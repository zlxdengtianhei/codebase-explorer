#!/usr/bin/env python3
"""Check documentation coverage against source code.

CLI:
    python check_coverage.py <docs_dir> <source_dir> [--format json|text]

Exit codes:
    0 - All checks passed
    1 - Coverage below thresholds
    2 - Usage / IO error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Source file extensions considered "documentable"
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".swift",
        ".kt",
        ".scala",
        ".php",
        ".lua",
        ".ex",
        ".exs",
        ".erl",
        ".hs",
        ".ml",
        ".mli",
    }
)

# Files / dirs to skip when scanning source
SKIP_PATTERNS: frozenset[str] = frozenset(
    {
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "egg-info",
    }
)

# Minimum pass thresholds
MIN_FILE_DISCOVERY_RATE = 0.80
MIN_MODULE_COVERAGE = 0.80
MIN_TOKEN_COMPLIANCE_RATE = 0.80


# ---------------------------------------------------------------------------
# doc-meta parsing (stdlib-only, same as validate_doc_links.py)
# ---------------------------------------------------------------------------

_DOC_META_BLOCK_RE = re.compile(
    r"<!--\s*doc-meta\s*\n(.*?)\n-->", re.DOTALL
)

_YAML_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+)$")


def _parse_yaml_value(raw: str) -> str | int | float | None:
    """Parse a simple YAML scalar value."""
    stripped = raw.strip()
    if stripped.lower() in ("null", "~", ""):
        return None
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1]
    return stripped


def parse_doc_meta(content: str) -> dict[str, Any] | None:
    """Extract doc-meta HTML comment block and return as dict."""
    match = _DOC_META_BLOCK_RE.search(content)
    if match is None:
        return None

    raw_yaml = match.group(1)
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if current_key is not None and current_list is not None:
                result[current_key] = list(current_list)
                current_key = None
                current_list = None
            continue

        list_match = _YAML_LIST_ITEM_RE.match(line)
        if list_match and current_key is not None:
            if current_list is None:
                current_list = []
            current_list.append(list_match.group(1).strip())
            continue

        if current_key is not None and current_list is not None:
            result[current_key] = list(current_list)
            current_key = None
            current_list = None

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = _parse_yaml_value(value)
                current_key = None
                current_list = None
            else:
                current_key = key
                current_list = None

    if current_key is not None and current_list is not None:
        result[current_key] = list(current_list)
    elif current_key is not None:
        result[current_key] = None

    return result


# ---------------------------------------------------------------------------
# Source file discovery
# ---------------------------------------------------------------------------


def _should_skip(path: Path) -> bool:
    """Return True if *path* or any ancestor matches skip patterns."""
    for part in path.parts:
        if part in SKIP_PATTERNS:
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def discover_source_files(source_dir: Path) -> list[Path]:
    """Return sorted list of source files under *source_dir*."""
    files: list[Path] = []
    for p in sorted(source_dir.rglob("*")):
        if not p.is_file():
            continue
        if _should_skip(p):
            continue
        if p.suffix in SOURCE_EXTENSIONS:
            files.append(p)
    return files


def discover_modules(source_dir: Path) -> set[str]:
    """Discover top-level modules (immediate subdirectories with source files)."""
    modules: set[str] = set()
    for child in sorted(source_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            if _should_skip(child):
                continue
            # Has at least one source file?
            has_source = any(
                f.suffix in SOURCE_EXTENSIONS
                for f in child.rglob("*")
                if f.is_file() and not _should_skip(f)
            )
            if has_source:
                modules.add(child.name)
    # Also consider standalone files at source root as a pseudo-module
    root_sources = [
        f
        for f in source_dir.iterdir()
        if f.is_file() and f.suffix in SOURCE_EXTENSIONS
    ]
    if root_sources:
        modules.add("__root__")
    return modules


# ---------------------------------------------------------------------------
# doc-index.json loading
# ---------------------------------------------------------------------------


def load_doc_index(docs_dir: Path) -> dict[str, Any] | None:
    """Load doc-index.json from *docs_dir*. Returns None if missing."""
    index_path = docs_dir / "doc-index.json"
    if not index_path.is_file():
        return None
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English/code."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def check_coverage(docs_dir: Path, source_dir: Path) -> dict[str, Any]:
    """Run coverage analysis and return result dict."""
    docs_dir = docs_dir.resolve()
    source_dir = source_dir.resolve()

    # -- Source analysis --
    source_files = discover_source_files(source_dir)
    source_modules = discover_modules(source_dir)

    source_file_relpaths: set[str] = {
        str(f.relative_to(source_dir)) for f in source_files
    }

    # -- Load doc-index.json --
    doc_index = load_doc_index(docs_dir)

    documented_files: set[str] = set()
    documented_modules: set[str] = set()
    doc_entries: list[dict[str, Any]] = []
    max_depth = 0

    if doc_index is not None:
        doc_entries = doc_index.get("docs", [])
        max_depth = doc_index.get("max_depth", 0)

        for entry in doc_entries:
            # Collect documented source files
            for sf in entry.get("source_files", []):
                documented_files.add(sf)

            # Infer modules from targets (first segment of dotted target)
            target = entry.get("target", "")
            if target:
                top_module = target.split(".")[0]
                if top_module:
                    documented_modules.add(top_module)
                    # Treat "root" as equivalent to "__root__" for coverage
                    # matching, since generators may use either convention.
                    if top_module == "root":
                        documented_modules.add("__root__")

    # -- File discovery rate --
    file_discovery_rate = (
        len(documented_files & source_file_relpaths) / len(source_file_relpaths)
        if source_file_relpaths
        else 1.0
    )

    # -- Module coverage --
    module_coverage = (
        len(documented_modules & source_modules) / len(source_modules)
        if source_modules
        else 1.0
    )

    # -- Token budget compliance --
    token_compliance = _check_token_budget_compliance(docs_dir, doc_entries)

    # -- Depth analysis --
    depth_analysis = _analyse_depth(doc_entries, max_depth)

    # -- Status --
    status = "PASS" if (
        file_discovery_rate >= MIN_FILE_DISCOVERY_RATE
        and module_coverage >= MIN_MODULE_COVERAGE
        and token_compliance["rate"] >= MIN_TOKEN_COMPLIANCE_RATE
        and depth_analysis["dynamic_depth_working"]
    ) else "FAIL"

    return {
        "source_files": len(source_files),
        "documented_files": len(documented_files & source_file_relpaths),
        "file_discovery_rate": round(file_discovery_rate, 3),
        "total_modules": len(source_modules),
        "documented_modules": len(documented_modules & source_modules),
        "module_coverage": round(module_coverage, 3),
        "token_budget_compliance": token_compliance,
        "depth_analysis": depth_analysis,
        "status": status,
    }


def _check_token_budget_compliance(
    docs_dir: Path,
    doc_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify token_budget vs actual_tokens for every document.

    A document is *compliant* when its actual token count does not exceed
    its declared token budget by more than 20 %.
    """
    total_docs = 0
    compliant = 0

    for entry in doc_entries:
        doc_path = docs_dir / entry.get("path", "")
        if not doc_path.is_file():
            continue

        total_docs += 1

        # Budget from doc-index entry
        budget = entry.get("token_budget")
        # Also check budget from doc-meta in the file itself
        content = doc_path.read_text(encoding="utf-8", errors="replace")
        meta = parse_doc_meta(content)
        if meta and budget is None:
            budget = meta.get("token_budget")

        if budget is None:
            # No budget declared -- count as compliant (no constraint)
            compliant += 1
            continue

        actual = entry.get("token_count")
        if actual is None:
            actual = estimate_tokens(content)

        # Allow 20 % overrun
        if actual <= budget * 1.2:
            compliant += 1

    rate = compliant / total_docs if total_docs > 0 else 1.0

    return {
        "total_docs": total_docs,
        "compliant": compliant,
        "rate": round(rate, 3),
    }


def _analyse_depth(
    doc_entries: list[dict[str, Any]],
    max_depth: int,
) -> dict[str, Any]:
    """Analyse documentation depth distribution.

    *Dynamic depth is working* if at least one module uses depth >= 2 and
    not all modules have the same depth -- i.e. depth adapts to complexity
    rather than being hardcoded.
    """
    # Collect max depth per top-level module (first segment of target)
    module_depths: dict[str, int] = {}
    for entry in doc_entries:
        target = entry.get("target", "")
        level = entry.get("level", 0)
        top_module = target.split(".")[0] if target else ""
        if top_module:
            module_depths[top_module] = max(
                module_depths.get(top_module, 0), level
            )

    modules_with_depth_gte_2 = sum(
        1 for d in module_depths.values() if d >= 2
    )
    modules_with_depth_eq_1 = sum(
        1 for d in module_depths.values() if d == 1
    )

    # Dynamic depth is working if:
    #   1. There is at least one module with depth >= 2
    #   2. AND not every module has the exact same depth (unless there
    #      is only one module).
    distinct_depths = set(module_depths.values())
    dynamic_depth_working = (
        modules_with_depth_gte_2 > 0
        and (len(distinct_depths) > 1 or len(module_depths) <= 1)
    )

    return {
        "max_depth": max_depth if max_depth else max(module_depths.values(), default=0),
        "modules_with_depth_gte_2": modules_with_depth_gte_2,
        "modules_with_depth_eq_1": modules_with_depth_eq_1,
        "dynamic_depth_working": dynamic_depth_working,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _format_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("Documentation Coverage Report")
    lines.append("=" * 40)
    lines.append(f"Source files        : {report['source_files']}")
    lines.append(f"Documented files    : {report['documented_files']}")
    lines.append(f"File discovery rate : {report['file_discovery_rate']:.1%}")
    lines.append(f"Total modules       : {report['total_modules']}")
    lines.append(f"Documented modules  : {report['documented_modules']}")
    lines.append(f"Module coverage     : {report['module_coverage']:.1%}")
    lines.append("")

    tc = report["token_budget_compliance"]
    lines.append("Token Budget Compliance:")
    lines.append(f"  Total docs   : {tc['total_docs']}")
    lines.append(f"  Compliant    : {tc['compliant']}")
    lines.append(f"  Rate         : {tc['rate']:.1%}")
    lines.append("")

    da = report["depth_analysis"]
    lines.append("Depth Analysis:")
    lines.append(f"  Max depth            : {da['max_depth']}")
    lines.append(f"  Modules depth >= 2   : {da['modules_with_depth_gte_2']}")
    lines.append(f"  Modules depth == 1   : {da['modules_with_depth_eq_1']}")
    lines.append(f"  Dynamic depth OK     : {da['dynamic_depth_working']}")
    lines.append("")

    lines.append(f"Status : {report['status']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check documentation coverage by comparing source files "
            "against doc-index.json and doc-meta metadata."
        ),
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="Path to the documentation directory (must contain doc-index.json).",
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Path to the source code directory.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    docs_dir: Path = args.docs_dir.resolve()
    source_dir: Path = args.source_dir.resolve()

    if not docs_dir.is_dir():
        print(f"Error: {docs_dir} is not a directory.", file=sys.stderr)
        return 2
    if not source_dir.is_dir():
        print(f"Error: {source_dir} is not a directory.", file=sys.stderr)
        return 2

    report = check_coverage(docs_dir, source_dir)

    if args.output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_text(report))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
