"""Stable fragment ids. Line ranges are applied in a second pass."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_LINE_FRAG = re.compile(r"^L(\d+)(?:-L(\d+))?$")
_GENERATED_HEADER = "<!-- generated:codebase-explorer-variant-a -->"


def symbol_anchor(symbol_id: str) -> str:
    digest = hashlib.sha256(symbol_id.encode("utf-8")).hexdigest()[:16]
    return f"symbol-{digest}"


def file_anchor(path: str) -> str:
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
    return f"file-{digest}"


def filebind_anchor(path: str, name: str) -> str:
    """Anchor for a file-level overlay name that is not a ledger symbol."""

    digest = hashlib.sha256(f"{path}\0{name}".encode("utf-8")).hexdigest()[:16]
    return f"filebind-{digest}"


def page_anchor(page_id: str) -> str:
    digest = hashlib.sha256(page_id.encode("utf-8")).hexdigest()[:12]
    return f"page-{digest}"


def line_fragment(start: int, end: int) -> str:
    if end < start:
        end = start
    return f"L{start}-L{end}"


def parse_line_fragment(frag: str) -> tuple[int, int] | None:
    match = _LINE_FRAG.fullmatch(frag)
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    return start, end


def rel_href(src_relpath: str, dst_relpath: str) -> str:
    if src_relpath == dst_relpath:
        return ""
    start = str(Path(src_relpath).parent)
    return Path(os.path.relpath(dst_relpath, start=start)).as_posix()


def md_link(label: str, src: str, dst: str, fragment: str) -> str:
    prefix = rel_href(src, dst)
    target = f"{prefix}#{fragment}" if fragment else prefix or dst
    return f"[{label}]({target})"


def split_target(target: str) -> tuple[str, str]:
    path, _, frag = target.partition("#")
    return path, frag
