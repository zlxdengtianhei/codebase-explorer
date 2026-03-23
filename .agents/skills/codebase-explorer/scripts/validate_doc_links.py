#!/usr/bin/env python3
"""Validate all Markdown links and doc-meta parent/children consistency.

CLI:
    python validate_doc_links.py <docs_dir> [--format json|text]

Exit codes:
    0 - All checks passed
    1 - Validation failures detected
    2 - Usage / IO error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# doc-meta parsing (stdlib only, YAML subset via regex)
# ---------------------------------------------------------------------------

_DOC_META_BLOCK_RE = re.compile(
    r"<!--\s*doc-meta\s*\n(.*?)\n-->", re.DOTALL
)

_YAML_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+)$")


def _parse_yaml_value(raw: str) -> str | int | float | None:
    """Parse a simple YAML scalar value (no pydantic / no PyYAML)."""
    stripped = raw.strip()
    if stripped.lower() in ("null", "~", ""):
        return None
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    # Integer
    try:
        return int(stripped)
    except ValueError:
        pass
    # Float
    try:
        return float(stripped)
    except ValueError:
        pass
    # String (strip surrounding quotes if present)
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1]
    return stripped


def parse_doc_meta(content: str) -> dict[str, Any] | None:
    """Extract doc-meta HTML comment and return as dict.

    Supports the YAML subset used in doc-meta blocks:
    - ``key: value`` scalars
    - ``key:`` followed by ``- item`` list entries
    - Nested mapping keys prefixed by indent (``metrics:\\n  file_count: 12``)

    Returns *None* when no doc-meta block is found.
    """
    match = _DOC_META_BLOCK_RE.search(content)
    if match is None:
        return None

    raw_yaml = match.group(1)
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw_yaml.splitlines():
        # Skip blank lines and comment lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            # Flush pending list
            if current_key is not None and current_list is not None:
                result[current_key] = list(current_list)
                current_key = None
                current_list = None
            continue

        # List item continuation
        list_match = _YAML_LIST_ITEM_RE.match(line)
        if list_match and current_key is not None:
            if current_list is None:
                current_list = []
            current_list.append(list_match.group(1).strip())
            continue

        # Flush previous list
        if current_key is not None and current_list is not None:
            result[current_key] = list(current_list)
            current_key = None
            current_list = None

        # key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = _parse_yaml_value(value)
                current_key = None
                current_list = None
            else:
                # Potential list or nested mapping -- start collecting
                current_key = key
                current_list = None  # will be populated on first ``- item``

    # Flush tail
    if current_key is not None and current_list is not None:
        result[current_key] = list(current_list)
    elif current_key is not None:
        # Key with no value and no list items following it
        result[current_key] = None

    return result


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def extract_md_links(content: str) -> list[tuple[str, str]]:
    """Return ``[(text, href), ...]`` for every Markdown link.

    Skips URLs (http/https), anchors (``#...``), and ``mailto:`` links.
    """
    links: list[tuple[str, str]] = []
    for text, href in _MD_LINK_RE.findall(content):
        href_stripped = href.strip()
        if href_stripped.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # Strip anchor from local paths (e.g. "OVERVIEW.md#section")
        path_part = href_stripped.split("#")[0]
        if path_part:
            links.append((text, path_part))
    return links


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------


def _resolve_link(source_file: Path, href: str, docs_dir: Path) -> Path:
    """Resolve a relative link target to an absolute path."""
    return (source_file.parent / href).resolve()


def validate(docs_dir: Path) -> dict[str, Any]:
    """Run all validations and return a result dict."""
    docs_dir = docs_dir.resolve()
    md_files = sorted(docs_dir.rglob("*.md"))

    # Collect per-file data
    file_metas: dict[Path, dict[str, Any] | None] = {}
    file_links: dict[Path, list[tuple[str, str]]] = {}

    for md in md_files:
        content = md.read_text(encoding="utf-8", errors="replace")
        file_metas[md] = parse_doc_meta(content)
        file_links[md] = extract_md_links(content)

    # ---- 1. Check link targets exist ----
    total_links = 0
    valid_links = 0
    broken_links: list[dict[str, str]] = []

    for md, links in file_links.items():
        for text, href in links:
            total_links += 1
            target = _resolve_link(md, href, docs_dir)
            if target.exists():
                valid_links += 1
            else:
                broken_links.append(
                    {
                        "source": str(md.relative_to(docs_dir)),
                        "text": text,
                        "href": href,
                        "expected": str(target.relative_to(docs_dir))
                        if target.is_relative_to(docs_dir)
                        else str(target),
                    }
                )

    # ---- 2. Find orphaned docs (never referenced by any other doc) ----
    referenced_paths: set[Path] = set()
    for md, links in file_links.items():
        for _, href in links:
            target = _resolve_link(md, href, docs_dir)
            referenced_paths.add(target)

    # Also add paths referenced via doc-meta children / parent
    for md, meta in file_metas.items():
        if meta is None:
            continue
        children = meta.get("children")
        if isinstance(children, list):
            for child in children:
                referenced_paths.add((md.parent / child).resolve())
        parent = meta.get("parent")
        if parent and isinstance(parent, str):
            referenced_paths.add((md.parent / parent).resolve())

    orphaned_docs: list[str] = []
    for md in md_files:
        if md not in referenced_paths:
            rel = str(md.relative_to(docs_dir))
            # INDEX.md (level 0) is the root -- never orphaned by definition
            meta = file_metas.get(md)
            if meta and meta.get("level") == 0:
                continue
            # If it is the only doc, skip orphan check
            if len(md_files) <= 1:
                continue
            orphaned_docs.append(rel)

    # ---- 3. Parent-children bidirectional consistency ----
    parent_child_errors: list[dict[str, str]] = []

    for md, meta in file_metas.items():
        if meta is None:
            continue

        md_rel = str(md.relative_to(docs_dir))

        # Check: if A lists parent B, then B.children should contain A
        parent = meta.get("parent")
        if parent and isinstance(parent, str):
            parent_abs = (md.parent / parent).resolve()
            parent_meta = file_metas.get(parent_abs)
            if parent_meta is not None:
                parent_children = parent_meta.get("children")
                if isinstance(parent_children, list):
                    # Compute the relative path from parent to this doc
                    try:
                        child_rel = str(md.relative_to(parent_abs.parent))
                    except ValueError:
                        child_rel = str(
                            Path(
                                _relpath(md, parent_abs.parent)
                            )
                        )

                    # Resolve all children of parent to absolute paths for robust comparison
                    parent_children_abs = {
                        (parent_abs.parent / c).resolve()
                        for c in parent_children
                    }
                    if md not in parent_children_abs:
                        parent_child_errors.append(
                            {
                                "type": "parent_missing_child",
                                "doc": md_rel,
                                "parent": str(parent_abs.relative_to(docs_dir))
                                if parent_abs.is_relative_to(docs_dir)
                                else parent,
                                "detail": (
                                    f"{md_rel} declares parent={parent}, "
                                    f"but parent does not list it as a child"
                                ),
                            }
                        )

        # Check: if A lists child C, then C.parent should point to A
        children = meta.get("children")
        if isinstance(children, list):
            for child in children:
                child_abs = (md.parent / child).resolve()
                child_meta = file_metas.get(child_abs)
                if child_meta is not None:
                    child_parent = child_meta.get("parent")
                    if child_parent and isinstance(child_parent, str):
                        declared_parent_abs = (
                            child_abs.parent / child_parent
                        ).resolve()
                        if declared_parent_abs != md:
                            parent_child_errors.append(
                                {
                                    "type": "child_wrong_parent",
                                    "doc": md_rel,
                                    "child": child,
                                    "detail": (
                                        f"{md_rel} lists child {child}, "
                                        f"but child declares parent={child_parent} "
                                        f"(resolves to {declared_parent_abs})"
                                    ),
                                }
                            )
                    elif child_parent is None:
                        parent_child_errors.append(
                            {
                                "type": "child_no_parent",
                                "doc": md_rel,
                                "child": child,
                                "detail": (
                                    f"{md_rel} lists child {child}, "
                                    f"but child has no parent field in doc-meta"
                                ),
                            }
                        )

    parent_child_consistent = len(parent_child_errors) == 0

    # ---- Build result ----
    status = "PASS" if (
        not broken_links
        and not orphaned_docs
        and parent_child_consistent
    ) else "FAIL"

    report: dict[str, Any] = {
        "total_docs": len(md_files),
        "total_links": total_links,
        "valid_links": valid_links,
        "broken_links": broken_links,
        "orphaned_docs": orphaned_docs,
        "parent_child_consistency": parent_child_consistent,
        "parent_child_errors": parent_child_errors,
        "status": status,
    }
    return report


def _relpath(target: Path, base: Path) -> str:
    """Pure-Python relative path (works even when on different drives)."""
    try:
        return str(target.relative_to(base))
    except ValueError:
        # Fallback to os.path.relpath-style
        import os
        return os.path.relpath(str(target), str(base))


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _format_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"Document Link Validation Report")
    lines.append(f"{'=' * 40}")
    lines.append(f"Total documents : {report['total_docs']}")
    lines.append(f"Total links     : {report['total_links']}")
    lines.append(f"Valid links     : {report['valid_links']}")
    lines.append(f"Broken links    : {len(report['broken_links'])}")
    lines.append(f"Orphaned docs   : {len(report['orphaned_docs'])}")
    lines.append(
        f"Parent-child OK : {report['parent_child_consistency']}"
    )
    lines.append(f"Status          : {report['status']}")
    lines.append("")

    if report["broken_links"]:
        lines.append("Broken Links:")
        for bl in report["broken_links"]:
            lines.append(
                f"  - [{bl['text']}]({bl['href']}) in {bl['source']}"
            )
        lines.append("")

    if report["orphaned_docs"]:
        lines.append("Orphaned Documents (not referenced by any other doc):")
        for od in report["orphaned_docs"]:
            lines.append(f"  - {od}")
        lines.append("")

    if report["parent_child_errors"]:
        lines.append("Parent-Child Consistency Errors:")
        for err in report["parent_child_errors"]:
            lines.append(f"  - [{err['type']}] {err['detail']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Markdown links and doc-meta parent/children "
            "consistency in a documentation directory."
        ),
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="Path to the documentation directory to validate.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    docs_dir: Path = args.docs_dir.resolve()
    if not docs_dir.is_dir():
        print(f"Error: {docs_dir} is not a directory.", file=sys.stderr)
        return 2

    report = validate(docs_dir)

    if args.output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_text(report))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
