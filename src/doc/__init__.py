"""Document generation layer for codebase-explorer.

This package implements dynamic N-layer documentation planning:

- **depth_planner**: Three-dimensional depth decision algorithm and
  token budget allocation (see design/depth_strategy.md).
- **mermaid**: Mermaid diagram generation for dependency, class, and
  flow diagrams.
"""

from src.doc.depth_planner import (
    DocPlanNode,
    DocStructurePlan,
    DocumentPlan,
    SplitStrategy,
    plan_doc_structure,
    plan_documentation,
)
from src.doc.mermaid import MermaidGenerator

__all__ = [
    "DocPlanNode",
    "DocStructurePlan",
    "DocumentPlan",
    "MermaidGenerator",
    "SplitStrategy",
    "plan_doc_structure",
    "plan_documentation",
]
