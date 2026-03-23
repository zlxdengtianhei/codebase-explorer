"""Feature Cone extraction algorithm for codebase module grouping.

Implements the core algorithm for identifying feature-based module groups
by analyzing dependency structure in the codebase DAG.

Algorithm Overview:
1. Find feature roots (entry points with in-degree=0)
2. For each root, trace dependencies via BFS to form a "cone"
3. Identify shared infrastructure nodes (shared by >= threshold cones)
4. Assign SCC groups to dominant cone or infrastructure

This replaces Louvain as the primary grouping strategy in V2.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from src.parser.codebase import CodebaseSnapshot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHARED_THRESHOLD = 2
"""Number of cones that must share a node for it to be classified as infrastructure."""


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureCone:
    """A feature cone representing a cohesive feature or use case.

    A cone is rooted at a feature entry point and contains all files
    that are uniquely used by that feature, plus references to shared
    infrastructure dependencies.
    """

    cone_id: str
    """Unique identifier for this cone (typically the entry point path)."""

    entry_point: str
    """The root file that defines this feature's entry point."""

    exclusive_files: list[str]
    """Files uniquely owned by this cone (not shared with other cones)."""

    shared_deps: list[str]
    """Infrastructure files shared with other cones."""

    layer: int = 0
    """DAG layer depth for this cone (0 = top-level entry)."""

    token_count: int = 0
    """Estimated token count for all files in this cone."""


# ---------------------------------------------------------------------------
# Feature Root Detection
# ---------------------------------------------------------------------------


def find_feature_roots(dag: nx.DiGraph) -> list[str]:
    """Find feature entry points in the DAG.

    Feature roots are nodes with in-degree=0 (no internal code depends on them).
    These represent top-level entry points like CLI commands, API endpoints, etc.

    For library code where all nodes have in-degree>0, falls back to selecting
    nodes with in-degree <= min+1.

    Args:
        dag: The dependency DAG (possibly after SCC condensation).

    Returns:
        List of node IDs that are feature roots.
    """
    in_degrees = dict(dag.in_degree())

    # Ideal case: find nodes with in-degree = 0
    roots = [node for node, deg in in_degrees.items() if deg == 0]

    if roots:
        return sorted(roots)  # Sort for deterministic ordering

    # Library code fallback: no pure entry points
    # Take nodes with minimal in-degree (or min+1)
    min_deg = min(in_degrees.values())
    roots = [node for node, deg in in_degrees.items() if deg <= min_deg + 1]

    return sorted(roots)


# ---------------------------------------------------------------------------
# Feature Cone Extraction
# ---------------------------------------------------------------------------


def extract_feature_cones(
    dag: nx.DiGraph,
    snapshot: CodebaseSnapshot,
    shared_threshold: int = SHARED_THRESHOLD,
) -> tuple[dict[str, FeatureCone], frozenset[str]]:
    """Extract feature cones from the dependency DAG.

    For each feature root, performs BFS to trace all dependencies.
    Nodes shared by >= threshold cones are classified as infrastructure.

    Args:
        dag: The dependency DAG (possibly after SCC condensation).
        snapshot: Codebase snapshot for metadata (currently unused, reserved for future).
        shared_threshold: Minimum number of cones that must share a node
            for it to be classified as infrastructure.

    Returns:
        Tuple of:
        - Dictionary mapping cone_id -> FeatureCone
        - Set of infrastructure node IDs

    Example:
        >>> dag = nx.DiGraph()
        >>> dag.add_edge("cli.py", "app.py")
        >>> dag.add_edge("app.py", "utils.py")
        >>> cones, infra = extract_feature_cones(dag, snapshot)
        >>> "cli.py" in cones
        True
    """
    # Find all feature roots
    roots = find_feature_roots(dag)

    # Track which cones each node belongs to
    node_cones: dict[str, set[str]] = defaultdict(set)

    # BFS from each root to trace dependencies
    for root in roots:
        cone_name = root
        visited: set[str] = set()
        queue = [root]

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)

            # Mark node as belonging to this cone
            node_cones[node].add(cone_name)

            # Trace all dependencies (successors = nodes this node depends on)
            for successor in dag.successors(node):
                if successor not in visited:
                    queue.append(successor)

    # Classify nodes: exclusive vs shared infrastructure
    infrastructure_nodes: set[str] = set()
    for node, belonging_cones in node_cones.items():
        if len(belonging_cones) >= shared_threshold:
            infrastructure_nodes.add(node)

    # Build FeatureCone objects
    cones: dict[str, FeatureCone] = {}

    for root in roots:
        exclusive: list[str] = []
        shared_refs: list[str] = []

        # Collect nodes for this cone
        for node, belonging_cones in node_cones.items():
            if root in belonging_cones:
                if node in infrastructure_nodes:
                    shared_refs.append(node)
                else:
                    exclusive.append(node)

        cones[root] = FeatureCone(
            cone_id=root,
            entry_point=root,
            exclusive_files=sorted(exclusive),  # Sort for determinism
            shared_deps=sorted(shared_refs),
        )

    return cones, frozenset(infrastructure_nodes)


# ---------------------------------------------------------------------------
# SCC Assignment
# ---------------------------------------------------------------------------


def assign_scc_to_cone(
    scc_members: list[str],
    cone_assignments: dict[str, str],
) -> str:
    """Determine which cone an SCC (strongly connected component) belongs to.

    Strategy: Assign SCC to the cone that contains the most SCC members.
    In case of a tie, classify as infrastructure.

    Args:
        scc_members: List of file paths in the SCC.
        cone_assignments: Dictionary mapping file path -> cone_id for non-SCC nodes.

    Returns:
        Cone ID that owns this SCC, or "infrastructure" if tied or unassigned.

    Example:
        >>> members = ["app.py", "ctx.py", "globals.py"]
        >>> assignments = {"app.py": "cone1", "ctx.py": "cone1", "globals.py": "cone2"}
        >>> assign_scc_to_cone(members, assignments)
        'cone1'
    """
    # Count how many SCC members belong to each cone
    cone_member_count: dict[str, int] = defaultdict(int)

    for member in scc_members:
        if member in cone_assignments:
            cone_id = cone_assignments[member]
            cone_member_count[cone_id] += 1

    # No members assigned to any cone
    if not cone_member_count:
        return "infrastructure"

    # Find cone(s) with maximum membership
    max_count = max(cone_member_count.values())
    winners = [cone_id for cone_id, count in cone_member_count.items() if count == max_count]

    # Tie goes to infrastructure
    if len(winners) == 1:
        return winners[0]
    else:
        return "infrastructure"
