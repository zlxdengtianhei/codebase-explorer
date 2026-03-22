"""Context builders and helper functions for document generation.

Internal module providing pure functions used by ``generator.py`` to
build Jinja2 template contexts and perform post-processing.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import PurePosixPath

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import DocPlanNode, DocStructurePlan
from src.doc.mermaid import MermaidGenerator
from src.state.models import AnalysisResult, DocNode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Relative link helpers
# ---------------------------------------------------------------------------


def make_relative_link(from_doc_path: str, to_doc_path: str) -> str:
    """Compute a relative link from one document to another.

    Both paths must be relative to the docs root (e.g. ``module_0/OVERVIEW.md``,
    ``INDEX.md``).  The returned path is relative to the *directory* containing
    ``from_doc_path``.

    Examples:
        >>> make_relative_link("module_0/OVERVIEW.md", "INDEX.md")
        '../INDEX.md'
        >>> make_relative_link("sansio/group_0/DETAIL.md", "INDEX.md")
        '../../INDEX.md'
        >>> make_relative_link("sansio/group_0/DETAIL.md", "sansio/OVERVIEW.md")
        '../OVERVIEW.md'
        >>> make_relative_link("INDEX.md", "module_0/OVERVIEW.md")
        'module_0/OVERVIEW.md'
    """
    from_dir = str(PurePosixPath(from_doc_path).parent)
    # Use PurePosixPath to compute the relative path from from_dir to to_doc_path
    # We need manual relpath since PurePosixPath doesn't have it
    from_parts = [] if from_dir == "." else from_dir.split("/")
    to_parts = to_doc_path.split("/")

    # Find common prefix length
    common = 0
    for a, b in zip(from_parts, to_parts):
        if a == b:
            common += 1
        else:
            break

    ups = len(from_parts) - common
    remaining = to_parts[common:]

    if ups == 0 and not remaining:
        return to_doc_path

    parts = [".."] * ups + remaining
    return "/".join(parts)


# ---------------------------------------------------------------------------
# Token budget trimming
# ---------------------------------------------------------------------------


def trim_to_budget(content: str, token_budget: int) -> str:
    """Trim rendered content to fit within a token budget.

    Uses a simple character-based heuristic: ~3.5 chars per token
    for Python-centric content.  Lines are removed from the bottom
    (lowest-priority content appears last in templates).
    """
    estimated = estimate_tokens_from_chars(len(content))
    if estimated <= token_budget:
        return content

    target_chars = int(token_budget * 3.5)
    if len(content) <= target_chars:
        return content

    lines = content.split("\n")
    trimmed_lines: list[str] = []
    char_count = 0

    for line in lines:
        line_chars = len(line) + 1
        if char_count + line_chars > target_chars:
            trimmed_lines.append("")
            trimmed_lines.append("<!-- content trimmed to fit token budget -->")
            break
        trimmed_lines.append(line)
        char_count += line_chars

    return "\n".join(trimmed_lines)


# ---------------------------------------------------------------------------
# DocNode conversion
# ---------------------------------------------------------------------------


def plan_nodes_to_doc_nodes(
    plan_nodes: list[DocPlanNode] | tuple[DocPlanNode, ...],
    project_id: str,
) -> list[DocNode]:
    """Convert ``DocPlanNode`` instances to ``DocNode`` model instances."""
    return [
        DocNode(
            id=f"doc-{i}",
            project_id=project_id,
            path=pn.path,
            level=pn.level,
            target=pn.target,
            token_budget=pn.token_budget,
            parent_path=pn.parent_path,
            children_paths=list(pn.children_paths),
            status="planned",
        )
        for i, pn in enumerate(plan_nodes)
    ]


def find_plan_node(
    nodes: list[DocPlanNode] | tuple[DocPlanNode, ...],
    path: str,
) -> DocPlanNode | None:
    """Find a plan node by path."""
    for n in nodes:
        if n.path == path:
            return n
    return None


# ---------------------------------------------------------------------------
# Cross-reference context
# ---------------------------------------------------------------------------


def build_cross_ref(
    target: str,
    results: dict[str, AnalysisResult],
) -> str:
    """Build a cross-reference context string for a target."""
    result = results.get(target)
    if not result:
        return ""

    parts: list[str] = []
    if result.dependencies:
        parts.append(f"Dependencies: {', '.join(result.dependencies)}")
    if result.dependents:
        parts.append(f"Dependents: {', '.join(result.dependents)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Dependency / interface extraction
# ---------------------------------------------------------------------------


def deps_to_edges(result: AnalysisResult | None) -> list[tuple[str, str]]:
    """Convert an AnalysisResult's dependencies to edge tuples."""
    if not result:
        return []
    return [(result.module_name, dep) for dep in result.dependencies]


def imports_list(
    result: AnalysisResult | None,
    from_doc_path: str = "",
    documented_modules: frozenset[str] | None = None,
) -> list[dict]:
    """Build imports list for overview template.

    If ``from_doc_path`` is provided, links are relative to that document.
    If ``documented_modules`` is provided, only include dependencies that
    have generated documentation (prevents broken links).
    """
    if not result:
        return []
    entries: list[dict] = []
    for dep in result.dependencies:
        if documented_modules is not None and dep not in documented_modules:
            continue
        target_path = f"{dep}/OVERVIEW.md"
        link = (
            make_relative_link(from_doc_path, target_path)
            if from_doc_path
            else f"../{dep}/OVERVIEW.md"
        )
        entries.append({"name": dep, "doc_path": link, "description": ""})
    return entries


def imported_by_list(
    result: AnalysisResult | None,
    from_doc_path: str = "",
    documented_modules: frozenset[str] | None = None,
) -> list[dict]:
    """Build imported-by list for overview template.

    If ``from_doc_path`` is provided, links are relative to that document.
    If ``documented_modules`` is provided, only include dependents that
    have generated documentation (prevents broken links).
    """
    if not result:
        return []
    entries: list[dict] = []
    for dep in result.dependents:
        if documented_modules is not None and dep not in documented_modules:
            continue
        target_path = f"{dep}/OVERVIEW.md"
        link = (
            make_relative_link(from_doc_path, target_path)
            if from_doc_path
            else f"../{dep}/OVERVIEW.md"
        )
        entries.append({"name": dep, "doc_path": link, "description": ""})
    return entries


def module_metrics(result: AnalysisResult | None) -> dict:
    """Build metrics dict for overview template."""
    return {
        "file_count": 0,
        "function_count": len(result.public_interfaces) if result else 0,
        "class_count": 0,
        "avg_complexity": 0.0,
    }


# ---------------------------------------------------------------------------
# Breadcrumbs
# ---------------------------------------------------------------------------


def build_breadcrumbs(node: DocNode) -> list[dict]:
    """Build breadcrumb trail from root to current node.

    All paths are computed relative to the current document's location.
    """
    current_path = node.path

    crumbs: list[dict] = [
        {
            "level": 0,
            "name": "Project",
            "path": make_relative_link(current_path, "INDEX.md"),
        },
    ]

    if node.level >= 1 and node.parent_path:
        crumbs.append({
            "level": 1,
            "name": (
                node.target.split(".")[0]
                if "." in node.target
                else node.target
            ),
            "path": make_relative_link(current_path, node.parent_path),
        })

    if node.level >= 2:
        crumbs.append({
            "level": node.level,
            "name": node.target,
            "path": make_relative_link(current_path, node.path),
        })

    return crumbs


# ---------------------------------------------------------------------------
# doc-index.json
# ---------------------------------------------------------------------------


def build_doc_index(
    generated: list,  # list[GeneratedDocument] -- avoid circular import
    plan: DocStructurePlan,
    module_files: dict[str, list[str]] | None = None,
) -> dict:
    """Build the doc-index.json structure.

    Args:
        generated: List of generated documents.
        plan: The documentation structure plan.
        module_files: Mapping of module target name to source file paths.
            Used to populate the ``source_files`` field in each entry.
    """
    plan_lookup: dict[str, DocPlanNode] = {n.path: n for n in plan.doc_tree}
    file_lookup = module_files or {}

    docs: list[dict] = []
    for doc in generated:
        plan_node = plan_lookup.get(doc.path)
        entry: dict = {
            "level": doc.level,
            "target": doc.target,
            "path": doc.path,
            "type": _level_to_type(doc.level),
            "token_count": doc.actual_tokens,
            "token_budget": plan_node.token_budget if plan_node else 0,
        }
        if plan_node:
            if plan_node.parent_path:
                entry["parent"] = plan_node.parent_path
            if plan_node.children_paths:
                entry["children"] = list(plan_node.children_paths)

        # Populate source_files from the module's file list.
        # For detail docs (target like "module.sub"), look up the parent module.
        source_files = file_lookup.get(doc.target, [])
        if not source_files and "." in doc.target:
            parent_target = doc.target.rsplit(".", 1)[0]
            source_files = file_lookup.get(parent_target, [])
        entry["source_files"] = sorted(source_files)

        docs.append(entry)

    total_tokens = sum(d.actual_tokens for d in generated)
    return {
        "version": "1.0",
        "project_name": "",
        "generated_at": datetime.now(UTC).isoformat(),
        "max_depth": plan.max_depth,
        "total_tokens": total_tokens,
        "total_coverage": 0.0,
        "docs": docs,
    }


def _level_to_type(level: int) -> str:
    """Map a document level to its type string."""
    if level == 0:
        return "index"
    if level == 1:
        return "overview"
    return "detail"
