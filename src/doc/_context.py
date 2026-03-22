"""Context builders and helper functions for document generation.

Internal module providing pure functions used by ``generator.py`` to
build Jinja2 template contexts and perform post-processing.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import DocPlanNode, DocStructurePlan
from src.doc.mermaid import MermaidGenerator
from src.state.models import AnalysisResult, DocNode

logger = logging.getLogger(__name__)


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


def imports_list(result: AnalysisResult | None) -> list[dict]:
    """Build imports list for overview template."""
    if not result:
        return []
    return [
        {"name": dep, "doc_path": f"../{dep}/OVERVIEW.md", "description": ""}
        for dep in result.dependencies
    ]


def imported_by_list(result: AnalysisResult | None) -> list[dict]:
    """Build imported-by list for overview template."""
    if not result:
        return []
    return [
        {"name": dep, "doc_path": f"../{dep}/OVERVIEW.md", "description": ""}
        for dep in result.dependents
    ]


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
    """Build breadcrumb trail from root to current node."""
    crumbs: list[dict] = [
        {"level": 0, "name": "Project", "path": "INDEX.md"},
    ]

    if node.level >= 1 and node.parent_path:
        crumbs.append({
            "level": 1,
            "name": (
                node.target.split(".")[0]
                if "." in node.target
                else node.target
            ),
            "path": node.parent_path,
        })

    if node.level >= 2:
        crumbs.append({
            "level": node.level,
            "name": node.target,
            "path": node.path,
        })

    return crumbs


# ---------------------------------------------------------------------------
# doc-index.json
# ---------------------------------------------------------------------------


def build_doc_index(
    generated: list,  # list[GeneratedDocument] -- avoid circular import
    plan: DocStructurePlan,
) -> dict:
    """Build the doc-index.json structure."""
    plan_lookup: dict[str, DocPlanNode] = {n.path: n for n in plan.doc_tree}

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
