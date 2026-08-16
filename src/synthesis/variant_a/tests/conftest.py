from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from src.semantic.models import (
    FileStatus,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticSymbolKind,
    SemanticSymbolRecord,
    SemanticTotals,
)
from src.synthesis.variant_a.surface import PublicSurface, SurfaceBinding


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_symbol(
    path: str,
    qualified: str,
    *,
    kind: SemanticSymbolKind = SemanticSymbolKind.FUNCTION,
    span: tuple[int, int] = (1, 4),
    module_id: str | None = "core",
    cited: tuple[str, ...] = (),
    text: str = "Explains responsibility, inputs, outputs, and the important failure boundary.",
) -> SemanticSymbolRecord:
    digest = _hash(f"{path}:{qualified}")
    return SemanticSymbolRecord(
        path=path,
        qualified_name=qualified,
        kind=kind,
        span=span,
        content_hash=digest,
        module_id=module_id,
        explanation=SemanticExplanation(
            text=text,
            explained_content_hash=digest,
            cited_symbol_ids=cited,
            producer="test",
            created_at=datetime(2026, 8, 16, tzinfo=UTC),
        ),
    )


def make_ledger(tmp_path: Path, symbols: list[SemanticSymbolRecord], extra_files: list[str] | None = None) -> SemanticLedger:
    files = {item.path: SemanticFileRecord(status=FileStatus.COVERED) for item in symbols}
    for path in extra_files or ():
        files.setdefault(path, SemanticFileRecord(status=FileStatus.NO_SYMBOLS))
    ids = [item.symbol_id for item in symbols]
    return SemanticLedger(
        repo_root=tmp_path.as_posix(),
        source_revision=_hash("rev"),
        files=files,
        symbols={item.symbol_id: item for item in symbols},
        order=tuple(ids),
        totals=SemanticTotals(
            symbols=len(symbols),
            explained=len(symbols),
            stale=0,
            uncovered=0,
            residual=0,
        ),
        coverage_percent=100.0 if symbols else 0.0,
    )


def make_surface(ledger: SemanticLedger, names: list[tuple[str, str, tuple[str, ...]]]) -> PublicSurface:
    bindings = [
        SurfaceBinding(surface_id=f"surface:{path}:{name}", name=name, path=path, resolved_symbol_ids=resolved)
        for path, name, resolved in names
    ]
    return PublicSurface(
        schema="cbe-public-surface-1",
        repo_root=ledger.repo_root,
        source_revision=ledger.source_revision,
        bindings=tuple(bindings),
        overlay_file_hashes={path: _hash(path) for path, _, _ in names},
    )
