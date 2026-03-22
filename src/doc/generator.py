"""Dynamic N-layer document generation.

Orchestrates the full documentation generation pipeline:

1. Build template context from analysis results and module data.
2. Select the appropriate Jinja2 template based on document level.
3. Render the template and prepend the ``doc-meta`` HTML comment.
4. Trim content to fit within the token budget.
5. Write generated documents and produce ``doc-index.json``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.budget.estimator import estimate_tokens_from_chars
from src.doc._context import (
    build_breadcrumbs,
    build_cross_ref,
    build_doc_index,
    deps_to_edges,
    find_plan_node,
    imported_by_list,
    imports_list,
    make_relative_link,
    module_metrics,
    plan_nodes_to_doc_nodes,
    trim_to_budget,
)
from src.doc.depth_planner import DocPlanNode, DocStructurePlan
from src.doc.mermaid import MermaidGenerator
from src.doc.templates import TemplateRenderer
from src.state.models import AnalysisResult, DocNode, ModuleRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TOOL_VERSION = "codebase-explorer v0.1.0"
_DOC_INDEX_FILENAME = "doc-index.json"

# Re-export for backward compatibility
_trim_to_budget = trim_to_budget


def _plan_node_summary(
    nodes: list[DocPlanNode],
    path: str,
) -> dict:
    """Build a placeholder summary dict from a plan node for pre-generation contexts.

    Used when a parent document needs to reference children that
    have not been generated yet.
    """
    pn = find_plan_node(nodes, path)
    target = pn.target if pn else path.replace("/DETAIL.md", "").replace("/OVERVIEW.md", "")
    return {
        "name": target,
        "path": path,
        "level": pn.level if pn else 2,
        "description": target,
        "token_count": 0,
    }


# ---------------------------------------------------------------------------
# Data models (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeneratedDocument:
    """Immutable generated document."""

    path: str
    content: str
    actual_tokens: int
    level: int
    target: str


# ---------------------------------------------------------------------------
# Document Generator
# ---------------------------------------------------------------------------


class DocumentGenerator:
    """Generates documentation based on analysis results and plans."""

    def __init__(
        self,
        template_renderer: TemplateRenderer,
        mermaid_generator: MermaidGenerator,
    ) -> None:
        self._renderer = template_renderer
        self._mermaid = mermaid_generator

    def generate_doc(
        self,
        node: DocNode,
        analysis_result: AnalysisResult | None,
        cross_ref_context: str,
        children_summaries: list[dict],
        source_files: list[str] | None = None,
        documented_modules: frozenset[str] | None = None,
    ) -> GeneratedDocument:
        """Generate a single document for a given doc node.

        Selects the appropriate Jinja2 template based on level:
        - Level 0: ``index.md.j2``
        - Level 1: ``overview.md.j2``
        - Level 2+: ``detail.md.j2``

        Args:
            node: The ``DocNode`` to generate content for.
            analysis_result: Analysis result for the target module.
            cross_ref_context: Pre-built cross-reference context.
            children_summaries: Summaries of child documents.
            source_files: Source file paths covered by this document.
            documented_modules: Set of module names that have documentation.

        Returns:
            ``GeneratedDocument`` with content and token count.
        """
        context = self._build_context(
            node, analysis_result, cross_ref_context, children_summaries,
            source_files=source_files or [],
            documented_modules=documented_modules,
        )

        if node.level == 0:
            raw_content = self._renderer.render_index(context)
        elif node.level == 1:
            raw_content = self._renderer.render_overview(context)
        else:
            raw_content = self._renderer.render_detail(context)

        trimmed = trim_to_budget(raw_content, node.token_budget)
        actual_tokens = estimate_tokens_from_chars(len(trimmed))

        logger.info(
            "Generated %s (level=%d, target=%s, tokens=%d/%d)",
            node.path, node.level, node.target,
            actual_tokens, node.token_budget,
        )

        return GeneratedDocument(
            path=node.path,
            content=trimmed,
            actual_tokens=actual_tokens,
            level=node.level,
            target=node.target,
        )

    def generate_all_docs(
        self,
        plan: DocStructurePlan,
        analysis_results: dict[str, AnalysisResult],
        modules: list[ModuleRecord],
        output_dir: Path,
    ) -> list[GeneratedDocument]:
        """Generate all documents from a structure plan.

        Documents are generated in level order (0, 1, 2, ...) so that
        child summaries are available when parent documents reference
        them.

        Args:
            plan: The ``DocStructurePlan``.
            analysis_results: Module name to ``AnalysisResult``.
            modules: List of ``ModuleRecord`` from the database.
            output_dir: Directory to write generated documents.

        Returns:
            List of ``GeneratedDocument`` objects.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build module_name -> source file list mapping for doc-index.json
        module_files: dict[str, list[str]] = {
            mod.name: list(mod.files) for mod in modules
        }

        # Determine which modules actually have documentation (level 1 nodes)
        # to avoid generating broken cross-reference links.
        documented_modules = frozenset(
            n.target for n in plan.doc_tree if n.level == 1
        )

        # Collect files from merged (undocumented) modules into the "root"
        # entry so that they still appear in doc-index.json for coverage.
        merged_files: list[str] = []
        for mod in modules:
            if mod.name not in documented_modules:
                merged_files.extend(mod.files)
        if merged_files:
            existing_root = module_files.get("root", [])
            module_files["root"] = existing_root + merged_files

        sorted_nodes = sorted(plan.doc_tree, key=lambda n: n.level)
        doc_nodes = plan_nodes_to_doc_nodes(sorted_nodes, project_id="")

        generated: list[GeneratedDocument] = []
        summaries: dict[str, dict] = {}

        for doc_node in doc_nodes:
            pn = find_plan_node(sorted_nodes, doc_node.path)
            children_paths = pn.children_paths if pn else ()
            children_sums = [
                summaries[cp] for cp in children_paths if cp in summaries
            ]

            # For overview/index docs whose children haven't been generated
            # yet, build placeholder summaries from the plan nodes so that
            # the template can render navigation links to child documents.
            if not children_sums and children_paths:
                children_sums = [
                    _plan_node_summary(sorted_nodes, cp)
                    for cp in children_paths
                ]

            result = analysis_results.get(doc_node.target)
            cross_ref = build_cross_ref(doc_node.target, analysis_results)

            # Find the module record for source_files
            source_files = module_files.get(doc_node.target, [])
            if not source_files and "." in doc_node.target:
                parent_target = doc_node.target.rsplit(".", 1)[0]
                source_files = module_files.get(parent_target, [])

            doc = self.generate_doc(
                node=doc_node,
                analysis_result=result,
                cross_ref_context=cross_ref,
                children_summaries=children_sums,
                source_files=source_files,
                documented_modules=documented_modules,
            )
            generated.append(doc)

            summaries[doc_node.path] = {
                "name": doc_node.target,
                "path": doc_node.path,
                "level": doc_node.level,
                "description": (
                    result.description if result else doc_node.target
                ),
                "token_count": doc.actual_tokens,
            }

            file_path = output_dir / doc.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(doc.content, encoding="utf-8")

        index_data = build_doc_index(generated, plan, module_files)
        index_path = output_dir / _DOC_INDEX_FILENAME
        index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Wrote %s with %d entries", index_path, len(generated))

        return generated

    # -- Context building (private) ----------------------------------------

    def _build_context(
        self,
        node: DocNode,
        result: AnalysisResult | None,
        cross_ref: str,
        children: list[dict],
        source_files: list[str] | None = None,
        documented_modules: frozenset[str] | None = None,
    ) -> dict:
        """Build the template variable context for rendering."""
        timestamp = datetime.now(UTC).isoformat()
        base: dict = {
            "token_budget": node.token_budget,
            "generation": {
                "timestamp": timestamp,
                "tool_version": _TOOL_VERSION,
                "model_used": "n/a",
            },
        }

        if node.level == 0:
            return self._index_ctx(base, node, result, children)
        if node.level == 1:
            return self._overview_ctx(
                base, node, result, children,
                documented_modules=documented_modules,
            )
        return self._detail_ctx(
            base, node, result, children,
            source_files=source_files or [],
        )

    def _index_ctx(
        self, base: dict, node: DocNode,
        result: AnalysisResult | None, children: list[dict],
    ) -> dict:
        modules_list = [
            {
                "id": c.get("name", ""),
                "name": c.get("name", ""),
                "description": c.get("description", ""),
                "file_count": 0,
                "complexity_score": 0.5,
                "doc_path": make_relative_link(
                    node.path, c.get("path", ""),
                ),
            }
            for c in children
        ]
        dep_graph = self._mermaid.generate_module_diagram(
            modules=[c.get("name", "") for c in children],
            dependencies=[],
        )
        return {
            **base,
            "project": {
                "name": node.target if node.target != "root" else "Project",
                "description": result.description if result else "",
                "version": "0.1.0",
                "repository_url": None,
            },
            "tech_stack": [],
            "modules": modules_list,
            "entry_points": [],
            "dependency_graph": dep_graph,
            "metrics": {
                "total_files": 0, "total_functions": 0,
                "total_classes": 0, "total_loc": 0,
            },
        }

    def _overview_ctx(
        self, base: dict, node: DocNode,
        result: AnalysisResult | None, children: list[dict],
        documented_modules: frozenset[str] | None = None,
    ) -> dict:
        components = [
            {
                "id": c.get("name", ""),
                "name": c.get("name", ""),
                "description": c.get("description", ""),
                "doc_path": make_relative_link(
                    node.path, c.get("path", ""),
                ),
                "depth": c.get("level", 2),
            }
            for c in children
        ]
        interfaces = [
            {"name": i, "signature": i, "description": "", "type": "function"}
            for i in (result.public_interfaces if result else [])
        ]
        dep_graph = self._mermaid.generate_dependency_mermaid(
            edges=deps_to_edges(result), target=node.target,
        )
        parent_path_rel = make_relative_link(
            node.path, node.parent_path or "INDEX.md",
        )
        return {
            **base,
            "module": {
                "id": node.target,
                "name": node.target,
                "description": result.description if result else "",
                "parent_path": parent_path_rel,
            },
            "files": [],
            "dependencies": {
                "imports": imports_list(
                    result, node.path, documented_modules,
                ),
                "imported_by": imported_by_list(
                    result, node.path, documented_modules,
                ),
            },
            "public_interfaces": interfaces,
            "components": components,
            "dependency_graph": dep_graph,
            "metrics": module_metrics(result),
        }

    def _detail_ctx(
        self, base: dict, node: DocNode,
        result: AnalysisResult | None, children: list[dict],
        source_files: list[str] | None = None,
    ) -> dict:
        children_list = [
            {
                "id": c.get("name", ""),
                "name": c.get("name", ""),
                "description": c.get("description", ""),
                "path": make_relative_link(
                    node.path, c.get("path", ""),
                ),
                "has_children": False,
            }
            for c in children
        ] or None
        structure_graph = self._mermaid.generate_dependency_mermaid(
            edges=deps_to_edges(result), target=node.target,
        )
        parent_path_rel = make_relative_link(
            node.path, node.parent_path or "../OVERVIEW.md",
        )
        return {
            **base,
            "document": {
                "level": node.level,
                "type": "detail",
                "target_id": node.target,
                "target_name": node.target,
                "description": result.description if result else node.target,
            },
            "breadcrumbs": build_breadcrumbs(node),
            "parent": {
                "name": node.parent_path or "Parent",
                "path": parent_path_rel,
            },
            "children": children_list,
            "classes": [],
            "functions": [],
            "structure_graph": structure_graph,
            "data_flow_graph": None,
            "design_decisions": None,
            "source_files": source_files or [],
        }
