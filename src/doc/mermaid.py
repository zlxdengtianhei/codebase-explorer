"""Mermaid diagram generation for documentation.

Generates valid Mermaid syntax for:
- Module dependency graphs (``flowchart``).
- Class hierarchy diagrams (``classDiagram``).
- Data flow / step diagrams (``flowchart``).

All public functions return plain strings containing Mermaid definitions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MAX_NODES = 30
_DEFAULT_MAX_EDGES = 50
_DEFAULT_MAX_CLASSES = 20

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_]")


# ---------------------------------------------------------------------------
# Data models (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassDiagramInfo:
    """Data required to render a class in a Mermaid classDiagram."""

    name: str
    base_classes: tuple[str, ...]
    methods: tuple[str, ...]


@dataclass(frozen=True)
class FlowStep:
    """A single step in a flow diagram."""

    id: str
    label: str
    next_ids: tuple[str, ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_id(name: str) -> str:
    """Convert an arbitrary string to a valid Mermaid node id."""
    return _SAFE_ID_RE.sub("_", name)


def _truncate_label(label: str, max_len: int = 40) -> str:
    """Truncate a label for Mermaid readability."""
    if len(label) <= max_len:
        return label
    return label[: max_len - 3] + "..."


def _escape_label(label: str) -> str:
    """Escape characters that break Mermaid syntax."""
    return label.replace('"', "'").replace("[", "(").replace("]", ")")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class MermaidGenerator:
    """Stateless generator for Mermaid diagram strings."""

    def generate_module_diagram(
        self,
        modules: list[str],
        dependencies: list[tuple[str, str]],
        *,
        max_nodes: int = _DEFAULT_MAX_NODES,
    ) -> str:
        """Generate a Mermaid flowchart showing inter-module dependencies.

        Args:
            modules: List of module names.
            dependencies: List of ``(source, target)`` dependency edges.
            max_nodes: Maximum nodes to render.

        Returns:
            Mermaid flowchart definition string.
        """
        if not modules:
            return "graph TB\n    empty[No modules detected]"

        lines: list[str] = ["graph TB"]
        visible = set(modules[:max_nodes])
        overflow = len(modules) - max_nodes

        for mod in modules[:max_nodes]:
            sid = _safe_id(mod)
            label = _escape_label(mod)
            lines.append(f"    {sid}[{label}]")

        for src, tgt in dependencies:
            if src in visible and tgt in visible:
                lines.append(f"    {_safe_id(src)} --> {_safe_id(tgt)}")

        if overflow > 0:
            lines.append(f'    more["... and {overflow} more"]')

        return "\n".join(lines)

    def generate_class_diagram(
        self,
        classes: list[ClassDiagramInfo],
        *,
        max_classes: int = _DEFAULT_MAX_CLASSES,
    ) -> str:
        """Generate a Mermaid classDiagram from class hierarchy data.

        Args:
            classes: List of ``ClassDiagramInfo``.
            max_classes: Maximum classes to render.

        Returns:
            Mermaid classDiagram definition string.
        """
        if not classes:
            return "classDiagram\n    class Empty"

        lines: list[str] = ["classDiagram"]
        rendered_names: set[str] = set()

        for cls in classes[:max_classes]:
            name = _safe_id(cls.name)
            rendered_names.add(name)
            lines.append(f"    class {name} {{")
            for method in cls.methods:
                lines.append(f"        +{_escape_label(method)}")
            lines.append("    }")

        # Inheritance arrows
        for cls in classes[:max_classes]:
            child = _safe_id(cls.name)
            for base in cls.base_classes:
                parent = _safe_id(base)
                if parent not in rendered_names:
                    lines.append(f"    class {parent}")
                    rendered_names.add(parent)
                lines.append(f"    {parent} <|-- {child}")

        overflow = len(classes) - max_classes
        if overflow > 0:
            lines.append(f"    class More [\"... and {overflow} more\"]")

        return "\n".join(lines)

    def generate_flow_diagram(
        self,
        steps: list[FlowStep],
        *,
        max_edges: int = _DEFAULT_MAX_EDGES,
    ) -> str:
        """Generate a Mermaid flowchart from sequential steps.

        Args:
            steps: List of ``FlowStep`` objects.
            max_edges: Maximum edges to render.

        Returns:
            Mermaid flowchart definition string.
        """
        if not steps:
            return "graph LR\n    empty[No steps]"

        lines: list[str] = ["graph LR"]
        edge_count = 0

        for step in steps:
            sid = _safe_id(step.id)
            label = _escape_label(_truncate_label(step.label))
            lines.append(f"    {sid}[{label}]")

        for step in steps:
            src = _safe_id(step.id)
            for nxt in step.next_ids:
                if edge_count >= max_edges:
                    break
                lines.append(f"    {src} --> {_safe_id(nxt)}")
                edge_count += 1

        return "\n".join(lines)

    def generate_dependency_mermaid(
        self,
        edges: list[tuple[str, str]],
        *,
        scope: str = "project",
        target: str | None = None,
        max_nodes: int = _DEFAULT_MAX_NODES,
    ) -> str:
        """Generate a Mermaid flowchart from raw dependency edges.

        When *target* is given, only edges involving the target are
        included.

        Args:
            edges: List of ``(source, target)`` dependency tuples.
            scope: ``"project"``, ``"module"``, or ``"component"``.
            target: Optional node name to center the view on.
            max_nodes: Maximum nodes to render.

        Returns:
            Mermaid flowchart definition string.
        """
        if not edges:
            return "graph TB\n    empty[No dependencies]"

        # Collect unique nodes
        nodes: set[str] = set()
        filtered_edges: list[tuple[str, str]] = []
        for src, tgt in edges:
            if target and target != src and target != tgt:
                continue
            nodes.add(src)
            nodes.add(tgt)
            filtered_edges.append((src, tgt))

        sorted_nodes = sorted(nodes)[:max_nodes]
        visible = set(sorted_nodes)

        lines: list[str] = ["graph TB"]
        for node in sorted_nodes:
            sid = _safe_id(node)
            label = _escape_label(node)
            lines.append(f"    {sid}[{label}]")

        for src, tgt in filtered_edges:
            if src in visible and tgt in visible:
                lines.append(f"    {_safe_id(src)} --> {_safe_id(tgt)}")

        overflow = len(nodes) - max_nodes
        if overflow > 0:
            lines.append(f'    more["... and {overflow} more"]')

        return "\n".join(lines)

    def generate_call_graph_mermaid(
        self,
        calls: list[tuple[str, str]],
        *,
        max_edges: int = _DEFAULT_MAX_EDGES,
    ) -> str:
        """Generate a Mermaid flowchart from call relationships.

        Args:
            calls: List of ``(caller, callee)`` tuples.
            max_edges: Maximum edges to render.

        Returns:
            Mermaid diagram string.
        """
        if not calls:
            return "graph LR\n    empty[No call relationships]"

        nodes: set[str] = set()
        lines: list[str] = ["graph LR"]

        edge_count = 0
        for caller, callee in calls:
            if edge_count >= max_edges:
                break
            nodes.add(caller)
            nodes.add(callee)
            edge_count += 1

        for node in sorted(nodes):
            sid = _safe_id(node)
            label = _escape_label(node)
            lines.append(f"    {sid}[{label}]")

        for caller, callee in calls[:max_edges]:
            lines.append(f"    {_safe_id(caller)} --> {_safe_id(callee)}")

        return "\n".join(lines)

    def generate_class_hierarchy_mermaid(
        self,
        classes: list[ClassDiagramInfo],
        *,
        max_classes: int = _DEFAULT_MAX_CLASSES,
    ) -> str:
        """Alias for ``generate_class_diagram`` matching architecture spec."""
        return self.generate_class_diagram(classes, max_classes=max_classes)
