"""Canonical repo-relative path handling shared by the graph layer.

``lstrip("./")`` is wrong: it turns ``../foo`` into ``foo`` and ``.hidden``
into ``hidden``.  A query or manifest path must be a normalized POSIX path
inside the repository, or be rejected.
"""

from __future__ import annotations

import re

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def canonical_repo_path(raw: object) -> str | None:
    """Return a canonical repo-relative POSIX path, or ``None`` if unsafe.

    ``./a/b`` -> ``a/b``; ``a/../b`` -> ``b``; ``../a`` -> ``None`` (escapes
    the root); absolute paths and Windows drive paths -> ``None``.  Dot-files
    such as ``.gitignore`` are preserved.
    """

    if raw is None:
        return None
    text = str(raw).replace("\\", "/").strip()
    if not text:
        return None
    if text.startswith("/") or _WINDOWS_DRIVE.match(text):
        return None
    parts: list[str] = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        return None
    return "/".join(parts)
