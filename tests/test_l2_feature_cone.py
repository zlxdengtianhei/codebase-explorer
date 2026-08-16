"""Acceptance tests for the deterministic public-surface overlay."""
from __future__ import annotations

from pathlib import Path

from src.graph.feature_cone import (
    build_runtime_import_graph,
    compute_surface_reachability,
    extract_public_surface,
)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_surface_resolves_reexports_and_skips_type_checking_edges(tmp_path: Path):
    """The seed starts at the definition, not at the package facade."""
    root = tmp_path / "pkg"
    root.mkdir()
    _write(
        root,
        "__init__.py",
        "from .api import public\nfrom . import sub\n__all__ = ['public', 'sub']\n",
    )
    _write(
        root,
        "api.py",
        "from .core import core\n"
        "if TYPE_CHECKING:\n    from .types import TypeOnly\n"
        "def public():\n    return core()\n",
    )
    _write(root, "core.py", "def core():\n    return 1\n")
    _write(root, "types.py", "class TypeOnly: pass\n")
    _write(root, "sub/__init__.py", "from .impl import sub_public\n")
    _write(root, "sub/impl.py", "def sub_public():\n    return 2\n")

    universe = (
        "__init__.py",
        "api.py",
        "core.py",
        "types.py",
        "sub/__init__.py",
        "sub/impl.py",
    )
    surface, diagnostics = extract_public_surface(str(root), universe, package_name="pkg")
    assert not diagnostics
    public = next(entry for entry in surface if entry.name == "public")
    assert (public.declared_in, public.defining_path, public.defining_name) == (
        "__init__.py",
        "api.py",
        "public",
    )
    assert any(entry.name == "sub.sub_public" and entry.defining_path == "sub/impl.py" for entry in surface)

    graph = build_runtime_import_graph(str(root), universe, package_name="pkg")
    assert graph.has_edge("__init__.py", "api.py")
    assert graph.has_edge("api.py", "core.py")
    assert not graph.has_edge("api.py", "types.py")
    assert not graph.has_edge("api.py", "__init__.py")

    reachability = compute_surface_reachability(graph, surface, universe)
    assert reachability.signature_of("core.py") == frozenset({"api.py"})
    assert reachability.signature_of("types.py") == frozenset()
    assert "types.py" in reachability.unreached


def test_surface_reachability_is_deterministic():
    """Inverting closures twice gives byte-stable signatures and residuals."""
    import networkx as nx

    graph = nx.DiGraph((source, target) for source, target in (("a", "shared"), ("b", "shared")))
    surface = (
        # The object only needs the fields consumed by the reachability layer.
        type("Entry", (), {"defining_path": "a"})(),
        type("Entry", (), {"defining_path": "b"})(),
    )
    first = compute_surface_reachability(graph, surface, ("a", "b", "shared", "orphan"))
    second = compute_surface_reachability(graph, surface, ("a", "b", "shared", "orphan"))
    assert first == second
    assert first.signature_of("shared") == frozenset({"a", "b"})
    assert first.unreached == ("orphan",)
