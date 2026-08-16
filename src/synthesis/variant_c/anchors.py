"""Closed citation candidates and deterministic anchor expansion.

This is the structural repair for C's fabricated links.  A producer submits
ids only.  The candidate set is derived from the ledger and planned page
paths; the renderer is the sole component allowed to create Markdown links.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from src.semantic.models import SemanticLedger

from .models import CandidateSet, CandidateTarget, ClusterRecord


_MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\([^)]*\)")
_INTERNAL_HREF = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


class ClosedCitationError(ValueError):
    """The producer attempted to cite outside the deterministic candidate set."""

    def __init__(self, page_id: str, unknown_ids: Iterable[str], reason: str = "") -> None:
        self.page_id = page_id
        self.unknown_ids = tuple(sorted(set(unknown_ids)))
        suffix = f"; {reason}" if reason else ""
        super().__init__(
            f"closed citation gate rejected {page_id}: unknown={self.unknown_ids}{suffix}"
        )


@dataclass(frozen=True, slots=True)
class AnchorReport:
    total_links: int
    resolved_links: int
    dangling_links: tuple[str, ...]
    invalid_ranges: tuple[str, ...] = ()
    false_edges: tuple[tuple[str, str], ...] = ()

    @property
    def anchor_resolved(self) -> float:
        if self.total_links == 0:
            return 1.0
        return self.resolved_links / self.total_links


def symbol_anchor(symbol_id: str) -> str:
    return "symbol-" + hashlib.sha256(symbol_id.encode("utf-8")).hexdigest()[:16]


def page_anchor(page_id: str) -> str:
    return "page-" + hashlib.sha256(page_id.encode("utf-8")).hexdigest()[:16]


def _coerce_ledger(value: SemanticLedger | Mapping[str, object]) -> SemanticLedger:
    if isinstance(value, SemanticLedger):
        return value
    if isinstance(value, Mapping):
        return SemanticLedger.model_validate(value)
    raise TypeError("ledger must be a SemanticLedger or JSON mapping")


def _known_symbol_ids(ledger: SemanticLedger) -> set[str]:
    return set(ledger.symbols)


def build_candidate_set(
    ledger_value: SemanticLedger | Mapping[str, object],
    *,
    page_id: str,
    cluster: ClusterRecord,
    page_path: str,
    page_paths: Mapping[str, str] | None = None,
    symbol_paths: Mapping[str, str] | None = None,
) -> CandidateSet:
    """Build a closed candidate universe from real ledger ids and page paths.

    The cluster's members and its one-hop relation targets are eligible.  A
    page target is added for every planned page path.  No name-only or
    model-provided target is accepted here.
    """

    ledger = _coerce_ledger(ledger_value)
    all_page_paths = dict(page_paths or {})
    all_symbol_paths = dict(symbol_paths or {})
    all_page_paths.setdefault(page_id, page_path)
    targets: dict[str, CandidateTarget] = {
        f"page:{page_id}": CandidateTarget(
            target_id=f"page:{page_id}",
            kind="page",
            label=cluster.name,
            target_path=page_path,
            line_start=1,
            line_end=1,
            anchor=page_anchor(page_id),
        )
    }

    eligible = set(cluster.symbol_ids)
    for source, target in cluster.edges:
        if source in ledger.symbols:
            eligible.add(source)
        if target in ledger.symbols:
            eligible.add(target)
    for symbol_id in cluster.symbol_ids:
        record = ledger.symbols.get(symbol_id)
        if record is None or record.explanation is None:
            continue
        eligible.update(
            cited
            for cited in record.explanation.cited_symbol_ids
            if cited in ledger.symbols
        )

    for symbol_id in sorted(eligible):
        record = ledger.symbols.get(symbol_id)
        if record is None or not record.is_fresh:
            continue
        target_path = all_symbol_paths.get(symbol_id, page_path)
        targets[symbol_id] = CandidateTarget(
            target_id=symbol_id,
            kind="symbol",
            label=record.qualified_name,
            target_path=target_path,
            line_start=record.span[0],
            line_end=record.span[1],
            anchor=symbol_anchor(symbol_id),
            source_symbol_id=symbol_id,
            source_path=record.path,
        )

    for other_page_id, other_path in sorted(all_page_paths.items()):
        target_id = f"page:{other_page_id}"
        targets.setdefault(
            target_id,
            CandidateTarget(
                target_id=target_id,
                kind="page",
                label=other_page_id,
                target_path=other_path,
                line_start=1,
                line_end=1,
                anchor=page_anchor(other_page_id),
            ),
        )
    return CandidateSet(page_id=page_id, targets=tuple(targets[key] for key in sorted(targets)))


def validate_selection(
    selected_target_ids: Iterable[str],
    candidates: CandidateSet,
    *,
    ledger_value: SemanticLedger | Mapping[str, object] | None = None,
    require_non_empty: bool = True,
) -> tuple[str, ...]:
    """S1/S2-style submit gate for a producer's selected ids."""

    selected = tuple(dict.fromkeys(str(item) for item in selected_target_ids))
    if require_non_empty and not selected:
        raise ClosedCitationError(candidates.page_id, (), "selection is empty")
    unknown = [item for item in selected if item not in candidates.ids]
    if unknown:
        raise ClosedCitationError(candidates.page_id, unknown)
    if ledger_value is not None:
        ledger = _coerce_ledger(ledger_value)
        stale = [
            item
            for item in selected
            if (target := candidates.get(item)) is not None
            and target.kind == "symbol"
            and (target.source_symbol_id not in ledger.symbols
                 or not ledger.symbols[target.source_symbol_id].is_fresh)
        ]
        if stale:
            raise ClosedCitationError(candidates.page_id, stale, "symbol is missing or stale")
    return selected


def assert_model_body_has_no_links(body: str) -> None:
    """The producer may write prose, but not a link target or anchor."""

    match = _MARKDOWN_LINK.search(body)
    if match:
        raise ClosedCitationError("body", (), "model supplied Markdown link; renderer owns links")


def _relative_href(current_path: str, target: CandidateTarget) -> str:
    current_dir = posixpath.dirname(current_path) or "."
    if target.target_path == current_path:
        path_part = ""
    else:
        path_part = posixpath.relpath(target.target_path, current_dir)
    return f"{path_part}#{target.anchor}" if path_part else f"#{target.anchor}"


def render_selected_citations(
    selected_target_ids: Iterable[str],
    candidates: CandidateSet,
    *,
    current_path: str,
) -> list[str]:
    """Expand ids to links after the submit gate, using only deterministic data."""

    selected = validate_selection(selected_target_ids, candidates, require_non_empty=False)
    lines = ["## 引用锚点", ""]
    for target_id in selected:
        target = candidates.get(target_id)
        if target is None:  # defensive; validate_selection already checks this
            continue
        range_text = f"{target.source_path}:{target.line_start}-{target.line_end}"
        lines.append(f"- [{target.label}]({_relative_href(current_path, target)})（{range_text}）")
    if not selected:
        lines.append("- 本页没有额外引用；正文只使用本批次事实卡。")
    lines.append("")
    return lines


def _resolve_href(source_path: str, href: str) -> tuple[str, str | None]:
    path_part, separator, anchor = href.partition("#")
    target_path = source_path if not path_part else posixpath.normpath(
        posixpath.join(posixpath.dirname(source_path) or ".", path_part)
    )
    return target_path, anchor if separator else None


def verify_rendered_links(documents: Mapping[str, str]) -> AnchorReport:
    """Check every internal Markdown link against emitted pages and anchors."""

    anchors: dict[str, set[str]] = {
        path: set(re.findall(r'<a\s+id="([^"]+)"', content))
        for path, content in documents.items()
    }
    total = 0
    resolved = 0
    dangling: list[str] = []
    invalid_ranges: list[str] = []
    for source_path, content in documents.items():
        for match in _INTERNAL_HREF.finditer(content):
            href = match.group(2)
            if "://" in href or href.startswith("mailto:"):
                continue
            total += 1
            target_path, anchor = _resolve_href(source_path, href)
            if target_path not in documents or (anchor and anchor not in anchors[target_path]):
                dangling.append(f"{source_path} -> {href}")
                continue
            resolved += 1
    return AnchorReport(
        total_links=total,
        resolved_links=resolved,
        dangling_links=tuple(sorted(dangling)),
        invalid_ranges=tuple(sorted(invalid_ranges)),
    )


def validate_edges(
    edges: Iterable[tuple[str, str]],
    known_symbol_ids: Iterable[str],
) -> tuple[tuple[str, str], ...]:
    """Return only real IR edges; callers can record the rejected remainder."""

    known = set(known_symbol_ids)
    return tuple(sorted({(source, target) for source, target in edges if source in known and target in known}))
