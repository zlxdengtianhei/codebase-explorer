"""Graph construction and analysis layer.

Transforms parsed CodebaseSnapshot data into NetworkX dependency graphs,
performs Louvain community detection for module grouping, and computes
topological analysis ordering with PageRank-based prioritisation.
"""
from __future__ import annotations

from src.graph.dependency import (
    DependencyEdge,
    DependencyGraphResult,
    build_dependency_graph,
    get_module_dependency_subgraph,
    get_dependency_graph_mermaid,
)
from src.graph.grouper import (
    ModuleMetrics,
    GroupingResult,
    group_modules,
    identify_utility_nodes,
)
from src.graph.ordering import (
    AnalysisPlan,
    topological_order,
    compute_pagerank,
    create_analysis_plan,
)
from src.graph.feature_cone import (
    FeatureCone,
    extract_feature_cones,
)
from src.graph.weighted_graph import (
    WeightedGraphResult,
    build_weighted_dependency_graph,
)

__all__ = [
    # dependency
    "DependencyEdge",
    "DependencyGraphResult",
    "build_dependency_graph",
    "get_module_dependency_subgraph",
    "get_dependency_graph_mermaid",
    # grouper
    "ModuleMetrics",
    "GroupingResult",
    "group_modules",
    "identify_utility_nodes",
    # ordering
    "AnalysisPlan",
    "topological_order",
    "compute_pagerank",
    "create_analysis_plan",
    # feature_cone
    "FeatureCone",
    "extract_feature_cones",
    # weighted_graph
    "WeightedGraphResult",
    "build_weighted_dependency_graph",
]
