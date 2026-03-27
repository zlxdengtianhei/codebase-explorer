"""Document generation layer for codebase-explorer.

V5 Architecture:
- **depth_planner**: DAG-based depth calculation and FFD bin-packing
  for agent task assignment.
"""

from src.doc.depth_planner import (
    build_task_manifest,
    calculate_feature_cone_depth,
)

__all__ = [
    "build_task_manifest",
    "calculate_feature_cone_depth",
]
