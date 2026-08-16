"""Two-pass line-range anchors.

Pass 1 emits `@@REF:kind:key@@` and `<!-- tgt:kind:key -->` markers.
Pass 2 rewrites every markdown link to `path#Lstart-Lend` and plants
`<a id="Lstart-Lend"></a>` on the start line so N7 can resolve the fragment.

Document line numbers (not source spans) are what a no-search reader can
`sed -n 'start,endp'` — see r003 NAV3_T2_codex.md.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from src.synthesis.variant_b.types import TargetRef, href_token

_LINK = re.compile(r"\[([^\]]*)\]\((@@REF:([^:]+):([^@]+)@@)\)")
_OPEN = re.compile(r"^<!-- tgt:([^:]+):(.*) -->$")
_CLOSE = re.compile(r"^<!-- /tgt:([^:]+):(.*) -->$")
_RANGE = re.compile(r"^L(\d+)-L(\d+)$")
_SYMBOL_LABEL = re.compile(r"^`([^`]+)`(?: L\d+-L\d+)?$")
_BARE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def _symbol_promise_label(label: str, start: int, end: int) -> str:
    """Symbol-level links advertise the document span they actually cover."""

    text = label.strip()
    if "→" in text:
        return label
    matched = _SYMBOL_LABEL.match(text)
    if matched:
        return f"`{matched.group(1)}` L{start}-L{end}"
    if _BARE_NAME.match(text):
        return f"`{text}` L{start}-L{end}"
    if text.startswith("`") and text.endswith("`") and " L" not in text:
        return f"{text} L{start}-L{end}"
    return label


def _rel_href(from_page: str, to_page: str, start: int, end: int) -> str:
    frag = f"L{start}-L{end}"
    if from_page == to_page:
        return f"#{frag}"
    src = Path(from_page).parent
    rel = Path(os.path.relpath(to_page, src)).as_posix()
    return f"{rel}#{frag}"


def collect_targets(pages: dict[str, list[str]]) -> dict[tuple[str, str], TargetRef]:
    found: dict[tuple[str, str], TargetRef] = {}
    for page, lines in pages.items():
        stack: list[tuple[str, str, int]] = []
        for index, line in enumerate(lines, start=1):
            opened = _OPEN.match(line.strip())
            if opened:
                stack.append((opened.group(1), opened.group(2), index))
                continue
            closed = _CLOSE.match(line.strip())
            if not closed:
                continue
            kind, key = closed.group(1), closed.group(2)
            start = index
            for item_kind, item_key, item_start in reversed(stack):
                if item_kind == kind and item_key == key:
                    start = item_start
                    break
            found[(kind, key)] = TargetRef(kind=kind, key=key, page=page, start=start, end=index)
    for page, lines in pages.items():
        found.setdefault(("page", page), TargetRef("page", page, page, 1, max(1, len(lines))))
    return found


def apply_line_ranges(pages: dict[str, list[str]]) -> dict[str, list[str]]:
    targets = collect_targets(pages)
    rewritten: dict[str, list[str]] = {}
    used_ids: dict[str, set[str]] = {page: set() for page in pages}

    def replace(match: re.Match[str], page: str) -> str:
        label = match.group(1)
        kind, key = match.group(3), match.group(4)
        target = targets.get((kind, key))
        if target is None and kind == "page":
            target = targets.get(("page", key))
        if target is None:
            target = targets.get(("page", "INDEX.md"))
        if target is None:
            return match.group(0)
        href = _rel_href(page, target.page, target.start, target.end)
        used_ids.setdefault(target.page, set()).add(f"L{target.start}-L{target.end}")
        shown = label
        if kind == "symbol":
            shown = _symbol_promise_label(label, target.start, target.end)
        return f"[{shown}]({href})"

    for page, lines in pages.items():
        rewritten[page] = [_LINK.sub(lambda match, p=page: replace(match, p), line) for line in lines]

    for page, ids in used_ids.items():
        lines = rewritten[page]
        by_start: dict[int, list[str]] = {}
        for frag in sorted(ids):
            matched = _RANGE.match(frag)
            if not matched:
                continue
            by_start.setdefault(int(matched.group(1)), []).append(frag)
        for start, frags in by_start.items():
            if start < 1 or start > len(lines):
                continue
            extra = "".join(f'<a id="{frag}"></a>' for frag in frags if f'id="{frag}"' not in lines[start - 1])
            if extra:
                lines[start - 1] = lines[start - 1] + extra
        rewritten[page] = lines
    return rewritten


def unresolved_placeholders(pages: dict[str, list[str]]) -> list[str]:
    leftover: list[str] = []
    token = href_token("x", "y").split("x")[0]
    for page, lines in pages.items():
        for line in lines:
            if "@@REF:" in line:
                leftover.append(f"{page}: {line.strip()[:160]}")
    return leftover
