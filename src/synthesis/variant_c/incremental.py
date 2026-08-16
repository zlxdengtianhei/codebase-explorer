"""Per-file revisions and page-level cited-symbol incremental closure."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from collections.abc import Mapping

from src.semantic.models import SemanticLedger

from .models import PageArtifact, PageState, stable_digest


def file_revisions_from_repo(
    repo_root: str | Path,
    paths: Mapping[str, object] | list[str] | tuple[str, ...],
) -> dict[str, str]:
    """Compute independent file digests; a changed sibling does not alter other pages."""

    root = Path(repo_root).resolve()
    path_names = paths.keys() if isinstance(paths, Mapping) else paths
    revisions: dict[str, str] = {}
    for relative in sorted(str(path) for path in path_names):
        path = root / relative
        try:
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            revisions[relative] = f"sha256:{digest}"
        except OSError as exc:
            marker = f"{type(exc).__name__}:{relative}:{exc}".encode("utf-8")
            revisions[relative] = "sha256:" + hashlib.sha256(marker).hexdigest()
    return revisions


def _coerce_revisions(
    revisions: Mapping[str, str] | object,
    paths: set[str],
) -> dict[str, str]:
    if isinstance(revisions, Mapping):
        return {path: str(revisions[path]) for path in sorted(paths) if path in revisions}
    revision_for = getattr(revisions, "revision_for", None)
    if callable(revision_for):
        return {path: str(revision_for(path)) for path in sorted(paths)}
    by_path = getattr(revisions, "by_path", None)
    if isinstance(by_path, Mapping):
        return {path: str(by_path[path]) for path in sorted(paths) if path in by_path}
    raise TypeError("file revisions must be a mapping or expose revision_for()/by_path")


def _coerce_ledger(value: SemanticLedger | Mapping[str, object]) -> SemanticLedger:
    if isinstance(value, SemanticLedger):
        return value
    if isinstance(value, Mapping):
        return SemanticLedger.model_validate(value)
    raise TypeError("ledger must be a SemanticLedger or JSON mapping")


def _page_hash(
    *,
    page_id: str,
    output_path: str,
    body: str,
    cited_target_ids: tuple[str, ...],
    symbol_hashes: tuple[tuple[str, str], ...],
    file_revisions: tuple[tuple[str, str], ...],
) -> str:
    parts = [page_id, output_path, body, "TARGETS"]
    parts.extend(cited_target_ids)
    parts.append("SYMBOLS")
    parts.extend(f"{symbol_id}\t{digest}" for symbol_id, digest in symbol_hashes)
    parts.append("FILES")
    parts.extend(f"{path}\t{digest}" for path, digest in file_revisions)
    return stable_digest(parts)


def build_page_state(
    artifact: PageArtifact,
    *,
    ledger_value: SemanticLedger | Mapping[str, object],
    file_revisions: Mapping[str, str] | object,
    dependency_file_paths: tuple[str, ...] = (),
    rendered_body: str | None = None,
) -> PageState:
    """Record the closure a page actually depends on, not the global revision."""

    ledger = _coerce_ledger(ledger_value)
    selected = tuple(artifact.draft.selected_target_ids)
    # ``covered_symbol_ids`` is a display roster, not a semantic dependency
    # claim. Only selected targets enter the rewrite closure; this is the
    # decisive difference from C's old parent-chain invalidation.
    cited: set[str] = set()
    for target_id in selected:
        target = artifact.candidates.get(target_id)
        if target is not None and target.source_symbol_id:
            cited.add(target.source_symbol_id)
    cited = {symbol_id for symbol_id in cited if symbol_id in ledger.symbols}
    paths = set(dependency_file_paths)
    paths.update(ledger.symbols[symbol_id].path for symbol_id in cited)
    revision_map = _coerce_revisions(file_revisions, paths)
    symbol_hashes = tuple(
        sorted((symbol_id, ledger.symbols[symbol_id].content_hash) for symbol_id in cited)
    )
    body = rendered_body if rendered_body is not None else artifact.draft.body
    page_hash = _page_hash(
        page_id=artifact.page_id,
        output_path=artifact.output_path,
        body=body,
        cited_target_ids=selected,
        symbol_hashes=symbol_hashes,
        file_revisions=tuple(sorted(revision_map.items())),
    )
    return PageState(
        page_id=artifact.page_id,
        output_path=artifact.output_path,
        cited_symbol_ids=tuple(sorted(cited)),
        cited_target_ids=selected,
        symbol_hashes=symbol_hashes,
        file_revisions=tuple(sorted(revision_map.items())),
        page_hash=page_hash,
    )


@dataclass(frozen=True, slots=True)
class IncrementalPlan:
    rewrite_page_ids: tuple[str, ...]
    reused_page_ids: tuple[str, ...]
    reasons: tuple[tuple[str, str], ...]

    @property
    def total_pages(self) -> int:
        return len(self.rewrite_page_ids) + len(self.reused_page_ids)

    @property
    def rewrite_ratio(self) -> float:
        return compute_rewrite_ratio(len(self.rewrite_page_ids), self.total_pages)


def plan_incremental_rewrite(
    previous_pages: Mapping[str, PageState],
    *,
    ledger_value: SemanticLedger | Mapping[str, object],
    file_revisions: Mapping[str, str] | object,
) -> IncrementalPlan:
    """Mark only pages whose cited symbols/files changed or became unavailable."""

    ledger = _coerce_ledger(ledger_value)
    all_paths = {
        path
        for page in previous_pages.values()
        for path, _digest in page.file_revisions
    }
    current_revisions = _coerce_revisions(file_revisions, all_paths)
    rewritten: list[str] = []
    reused: list[str] = []
    reasons: list[tuple[str, str]] = []
    for page_id, page in sorted(previous_pages.items()):
        reason: str | None = None
        for symbol_id, old_hash in page.symbol_hashes:
            record = ledger.symbols.get(symbol_id)
            if record is None:
                reason = f"cited_symbol_removed:{symbol_id}"
                break
            if not record.is_fresh:
                reason = f"cited_symbol_stale:{symbol_id}"
                break
            if record.content_hash != old_hash:
                reason = f"cited_symbol_changed:{symbol_id}"
                break
        if reason is None:
            for path, old_revision in page.file_revisions:
                current = current_revisions.get(path)
                if current != old_revision:
                    reason = f"cited_file_changed:{path}"
                    break
        if reason is None:
            reused.append(page_id)
        else:
            rewritten.append(page_id)
            reasons.append((page_id, reason))
    return IncrementalPlan(
        rewrite_page_ids=tuple(rewritten),
        reused_page_ids=tuple(reused),
        reasons=tuple(reasons),
    )


def compute_rewrite_ratio(rewritten_pages: int, total_pages: int) -> float:
    if total_pages < 0 or rewritten_pages < 0 or rewritten_pages > total_pages:
        raise ValueError("rewrite counts must satisfy 0 <= rewritten <= total")
    return rewritten_pages / total_pages if total_pages else 0.0


def mark_page_states_stale(
    pages: Mapping[str, PageState],
    plan: IncrementalPlan,
) -> dict[str, PageState]:
    """Return a new state mapping; the persisted prior mapping is never mutated."""

    reasons = dict(plan.reasons)
    return {
        page_id: replace(
            page,
            status="stale" if page_id in reasons else page.status,
            stale_reason=reasons.get(page_id),
        )
        for page_id, page in pages.items()
    }
