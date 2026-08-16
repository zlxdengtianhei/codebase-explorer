"""Second-pass rewrite: every markdown link becomes ``#Lstart-Lend``.

Line numbers are computed on the first-pass documents. Adding
``<a id="Lstart-Lend"></a>`` happens on the *same line* as the existing
anchor so subsequent line numbers do not shift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.synthesis.variant_a.anchors import (
    _LINK,
    line_fragment,
    parse_line_fragment,
    split_target,
)


_EXPLICIT = re.compile(r'<a\s+(?:id|name)="([^"]+)"')
_SYMBOL_START = re.compile(r"<!--\s*symbol:([^\s>]+)\s*-->")
_SYMBOL_END = re.compile(r"<!--\s*end:symbol:")


@dataclass(frozen=True)
class AnchorSpan:
    ident: str
    start: int  # 1-based inclusive
    end: int  # 1-based inclusive


@dataclass(frozen=True)
class LinkResolution:
    label: str
    raw_target: str
    source_file: str
    target_file: str
    start: int | None
    end: int | None
    ok: bool
    why: str = ""


def _anchors_in(text: str) -> dict[str, AnchorSpan]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        for ident in _EXPLICIT.findall(line):
            starts.append((index, ident))
    spans: dict[str, AnchorSpan] = {}
    for pos, (start, ident) in enumerate(starts):
        end = len(lines)
        if pos + 1 < len(starts):
            end = max(start, starts[pos + 1][0] - 1)
        if ident.startswith("page-"):
            end = len(lines)
        spans[ident] = AnchorSpan(ident=ident, start=start, end=end)
    # Tighten symbol blocks to the explicit end marker when present.
    current_symbol: str | None = None
    symbol_start = 0
    for index, line in enumerate(lines, start=1):
        opened = _SYMBOL_START.search(line)
        if opened:
            current_symbol = None
            for ident, span in spans.items():
                if ident.startswith("symbol-") and span.start <= index <= span.start + 2:
                    current_symbol = ident
                    symbol_start = span.start
                    break
        if current_symbol and _SYMBOL_END.search(line):
            spans[current_symbol] = AnchorSpan(current_symbol, symbol_start, index)
            current_symbol = None
    return spans


def resolve_docs(docs: dict[str, str]) -> tuple[dict[str, dict[str, AnchorSpan]], list[LinkResolution]]:
    by_file = {rel: _anchors_in(text) for rel, text in docs.items()}
    resolved: list[LinkResolution] = []
    for rel, text in sorted(docs.items()):
        for label, target in _LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path_part, frag = split_target(target)
            if path_part.startswith("/"):
                resolved.append(
                    LinkResolution(label, target, rel, path_part, None, None, False, "absolute path")
                )
                continue
            dest = path_part or rel
            if path_part:
                dest = _join(rel, path_part)
            if dest not in docs:
                resolved.append(
                    LinkResolution(label, target, rel, dest, None, None, False, "target file missing")
                )
                continue
            if not frag:
                resolved.append(
                    LinkResolution(label, target, rel, dest, None, None, False, "no fragment")
                )
                continue
            line_span = parse_line_fragment(frag)
            if line_span is not None:
                start, end = line_span
                n_lines = docs[dest].count("\n") + (0 if docs[dest].endswith("\n") else 1)
                ok = 1 <= start <= end <= max(1, n_lines)
                resolved.append(
                    LinkResolution(
                        label,
                        target,
                        rel,
                        dest,
                        start,
                        end,
                        ok,
                        "" if ok else "line range out of file",
                    )
                )
                continue
            span = by_file[dest].get(frag)
            if span is None:
                resolved.append(
                    LinkResolution(label, target, rel, dest, None, None, False, "anchor missing")
                )
                continue
            resolved.append(
                LinkResolution(label, target, rel, dest, span.start, span.end, True, "")
            )
    return by_file, resolved


def _norm_join(src_rel: str, target: str) -> str:
    from pathlib import PurePosixPath

    joined = PurePosixPath(src_rel).parent / target
    parts: list[str] = []
    for part in joined.parts:
        if part == "..":
            if parts:
                parts.pop()
            continue
        if part in (".", ""):
            continue
        parts.append(part)
    return "/".join(parts)


def _join(src_rel: str, target: str) -> str:
    return _norm_join(src_rel, target)


def apply_line_ranges(docs: dict[str, str]) -> dict[str, str]:
    """Rewrite every internal link to ``#Lstart-Lend`` and stamp matching ids."""

    by_file, _ = resolve_docs(docs)
    rewritten: dict[str, str] = {}
    for rel, text in docs.items():
        def repl(match: re.Match[str]) -> str:
            label, target = match.group(1), match.group(2)
            if target.startswith(("http://", "https://", "mailto:")):
                return match.group(0)
            path_part, frag = split_target(target)
            dest = rel if not path_part else _norm_join(rel, path_part)
            if dest not in by_file or not frag:
                return match.group(0)
            if parse_line_fragment(frag) is not None:
                return match.group(0)
            span = by_file[dest].get(frag)
            if span is None:
                return match.group(0)
            frag_l = line_fragment(span.start, span.end)
            new_label = label if re.search(r"L\d+", label) else f"{label} {frag_l}"
            prefix = path_part
            return f"[{new_label}]({prefix}#{frag_l})" if prefix else f"[{new_label}](#{frag_l})"

        new_text = _LINK.sub(repl, text)
        lines = new_text.splitlines()
        spans = by_file[rel]
        # Stamp line-range ids on the start line of each non-L anchor.
        by_start: dict[int, list[AnchorSpan]] = {}
        for span in spans.values():
            if span.ident.startswith("L") and parse_line_fragment(span.ident):
                continue
            by_start.setdefault(span.start, []).append(span)
        for start, group in by_start.items():
            if start < 1 or start > len(lines):
                continue
            extras = []
            for span in group:
                ident = line_fragment(span.start, span.end)
                if f'id="{ident}"' not in lines[start - 1]:
                    extras.append(f'<a id="{ident}"></a>')
            if extras:
                lines[start - 1] = lines[start - 1] + "".join(extras)
        rewritten[rel] = "\n".join(lines) + "\n"
    return rewritten


def audit_tree(docs: dict[str, str]) -> dict[str, object]:
    _, links = resolve_docs(docs)
    total = len(links)
    ok = [item for item in links if item.ok and item.start is not None]
    with_range = [item for item in links if item.start is not None]
    failed = [item for item in links if not item.ok]
    n = max(1, total)
    return {
        "metric": "anchor_with_line_range",
        "links_total": total,
        "with_line_range": len(with_range),
        "resolved": len(ok),
        "failed": len(failed),
        "rate_with_line_range": round(len(with_range) / n, 4),
        "rate_resolved": round(len(ok) / n, 4),
        "failed_sample": [
            {
                "label": item.label[:60],
                "source": item.source_file,
                "target": item.raw_target,
                "why": item.why,
            }
            for item in failed[:20]
        ],
        "links": [
            {
                "label": item.label[:80],
                "source": item.source_file,
                "target_file": item.target_file,
                "start": item.start,
                "end": item.end,
                "ok": item.ok,
                "why": item.why,
            }
            for item in links
        ],
    }
