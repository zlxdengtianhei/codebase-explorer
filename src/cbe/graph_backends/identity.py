"""Repository file membership and canonical graph identities.

All backends and the merge boundary use the same excluded-directory policy.
A file identity can only be constructed for an inventoried repository file.
"""
from __future__ import annotations

import os
from pathlib import Path

from cbe.source_context import DEFAULT_EXCLUDE_DIR_NAMES
from ._paths import canonical_repo_path


def repository_files(repo: Path) -> frozenset[str]:
    repo = repo.resolve()
    files = set()
    for directory, dirs, names in os.walk(repo, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in DEFAULT_EXCLUDE_DIR_NAMES
                         and not (Path(directory) / d).is_symlink())
        for name in names:
            full = Path(directory) / name
            if full.is_file() and not full.is_symlink():
                files.add(full.relative_to(repo).as_posix())
    return frozenset(files)


def file_id(path: str | None, files) -> str | None:
    return "file:" + path if path and path in files and canonical_repo_path(path) == path else None


def external_id(name: str) -> str:
    return "ext:" + name


def validate_identities(nodes, edges, files):
    """Validate backend identities; import resolution belongs to the resolver."""
    aliases, invalid, diagnostics, result = {}, set(), [], []
    for node in nodes:
        native = node["id"]
        if native.startswith("file:"):
            canonical = file_id(node.get("path"), files)
            if canonical is None:
                invalid.add(native)
                diagnostics.append(dict(path=node.get("path"), code="invalid_file_identity",
                                        message=f"discarded non-repository file identity {native}"))
                continue
            aliases[native] = canonical
            node = {**node, "id": canonical}
        result.append(node)
    unique = {n["id"]: n for n in result}
    repaired = []
    for edge in edges:
        edge = dict(edge)
        degraded = False
        for endpoint in ("source", "target"):
            value = edge.get(endpoint)
            if value in invalid:
                edge[endpoint] = None
                degraded = True
            elif value in aliases:
                edge[endpoint] = aliases[value]
                if endpoint == "target" and edge.get("kind") == "import":
                    edge["status"] = "resolved"
        if degraded:
            edge["status"] = "unresolved"
        repaired.append(edge)
    return list(unique.values()), repaired, diagnostics
