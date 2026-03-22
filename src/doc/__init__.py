"""Document generation layer for codebase-explorer.

This package implements dynamic N-layer documentation planning and
generation, including:

- **depth_planner**: Three-dimensional depth decision algorithm and
  token budget allocation (see design/depth_strategy.md).
- **generator**: Jinja2-based document rendering with priority-based
  content trimming.
- **mermaid**: Mermaid diagram generation for dependency, class, and
  flow diagrams.
- **templates**: Jinja2 template loading and rendering engine.
"""

from src.doc.depth_planner import (
    DocPlanNode,
    DocStructurePlan,
    DocumentPlan,
    SplitStrategy,
    plan_doc_structure,
    plan_documentation,
)
from src.doc.generator import DocumentGenerator, GeneratedDocument
from src.doc.mermaid import MermaidGenerator
from src.doc.templates import TemplateRenderer

__all__ = [
    "DocPlanNode",
    "DocStructurePlan",
    "DocumentGenerator",
    "DocumentPlan",
    "GeneratedDocument",
    "MermaidGenerator",
    "SplitStrategy",
    "TemplateRenderer",
    "plan_doc_structure",
    "plan_documentation",
]
