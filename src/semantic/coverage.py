"""Independent static coverage projection and optional runtime heat mapping."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from src.semantic.inventory import SemanticInventory
from src.semantic.models import (
    FileStatus,
    SemanticFileRecord,
    SemanticLedger,
    SemanticTotals,
    revalidate_semantic_ledger,
)


@dataclass(frozen=True)
class StaticCoverageProjection:
    """Coverage recomputed from inventory truth instead of ledger membership."""

    files: Mapping[str, SemanticFileRecord]
    symbol_ids: tuple[str, ...]
    fresh_symbol_ids: tuple[str, ...]
    stale_symbol_ids: tuple[str, ...]
    uncovered_symbols: tuple[str, ...]
    totals: SemanticTotals
    coverage_percent: float


@dataclass(frozen=True)
class RuntimeCoverage:
    """Executed source lines keyed by canonical repository-relative path."""

    executed_lines: Mapping[str, frozenset[int]]


def _canonical_coverage_path(raw: str, repo_root: Path) -> str:
    if not isinstance(raw, str) or not raw.strip() or "\\" in raw:
        raise ValueError("coverage file paths must be non-empty POSIX paths")
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"coverage path is outside repository: {raw}") from exc


def load_runtime_coverage(
    coverage_path: str | Path,
    *,
    repo_root: str | Path,
) -> RuntimeCoverage:
    """Load coverage.py-compatible JSON without granting it denominator authority."""

    root = Path(repo_root).resolve()
    try:
        payload = json.loads(Path(coverage_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load runtime coverage: {exc}") from exc
    files = payload.get("files") if isinstance(payload, dict) else None
    if not isinstance(files, dict):
        raise ValueError("coverage JSON must contain an object-valued files field")

    normalized: dict[str, frozenset[int]] = {}
    for raw_path, record in files.items():
        if not isinstance(record, dict):
            raise ValueError(f"coverage record for {raw_path!r} must be an object")
        lines = record.get("executed_lines", [])
        if not isinstance(lines, list) or any(type(line) is not int or line < 1 for line in lines):
            raise ValueError("executed_lines must contain positive integers")
        path = _canonical_coverage_path(raw_path, root)
        normalized[path] = frozenset((*normalized.get(path, frozenset()), *lines))
    return RuntimeCoverage(executed_lines=dict(sorted(normalized.items())))


def derive_static_coverage(
    inventory: SemanticInventory,
    ledger: SemanticLedger,
) -> StaticCoverageProjection:
    """Recompute file/symbol coverage using inventory as the independent truth."""

    if inventory.repo_root != ledger.repo_root:
        raise ValueError("inventory and ledger belong to different repositories")
    if inventory.source_revision != ledger.source_revision:
        raise ValueError("inventory and ledger source revisions differ")
    truth_ids = set(inventory.symbols)
    ledger_ids = set(ledger.symbols)
    if truth_ids != ledger_ids:
        missing = sorted(truth_ids - ledger_ids)
        phantom = sorted(ledger_ids - truth_ids)
        raise ValueError(
            "static symbol denominator mismatch: "
            f"missing={missing[:3]} phantom={phantom[:3]}"
        )
    if set(inventory.files) != set(ledger.files):
        raise ValueError("static file denominator mismatch")

    fresh: set[str] = set()
    stale: set[str] = set()
    for symbol_id, truth in inventory.symbols.items():
        explanation = ledger.symbols[symbol_id].explanation
        if explanation is None or not explanation.text.strip():
            continue
        if explanation.explained_content_hash == truth.content_hash:
            fresh.add(symbol_id)
        else:
            stale.add(symbol_id)
    uncovered = truth_ids - fresh

    symbols_by_path: dict[str, list[str]] = {path: [] for path in inventory.files}
    for symbol_id, symbol in inventory.symbols.items():
        symbols_by_path[symbol.path].append(symbol_id)
    files: dict[str, SemanticFileRecord] = {}
    for path, inventory_record in inventory.files.items():
        path_symbol_ids = symbols_by_path[path]
        if not path_symbol_ids:
            files[path] = inventory_record
        elif all(symbol_id in fresh for symbol_id in path_symbol_ids):
            files[path] = SemanticFileRecord(status=FileStatus.COVERED)
        else:
            pending = sum(symbol_id not in fresh and symbol_id not in stale for symbol_id in path_symbol_ids)
            stale_count = sum(symbol_id in stale for symbol_id in path_symbol_ids)
            details = []
            if pending:
                details.append(f"{pending} pending semantic explanation(s)")
            if stale_count:
                details.append(f"{stale_count} stale semantic explanation(s)")
            files[path] = SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason="; ".join(details),
            )

    totals = SemanticTotals(
        symbols=len(truth_ids),
        explained=len(fresh),
        stale=len(stale),
        uncovered=len(uncovered),
        residual=len(ledger.residuals),
    )
    coverage_percent = (
        round(100.0 * totals.explained / totals.symbols, 4) if totals.symbols else 0.0
    )
    return StaticCoverageProjection(
        files=dict(sorted(files.items())),
        symbol_ids=tuple(sorted(truth_ids)),
        fresh_symbol_ids=tuple(sorted(fresh)),
        stale_symbol_ids=tuple(sorted(stale)),
        uncovered_symbols=tuple(sorted(uncovered)),
        totals=totals,
        coverage_percent=coverage_percent,
    )


def apply_runtime_coverage(
    ledger: SemanticLedger,
    runtime_coverage: RuntimeCoverage,
) -> SemanticLedger:
    """Return a heat-annotated copy while preserving every static projection."""

    symbols = {}
    for symbol_id, symbol in ledger.symbols.items():
        executed = runtime_coverage.executed_lines.get(symbol.path, frozenset())
        start, end = symbol.span
        covered = sum(start <= line <= end for line in executed)
        symbols[symbol_id] = symbol.model_copy(
            update={"runtime_covered_lines": covered}
        )
    projected = ledger.model_copy(update={"symbols": symbols})
    return revalidate_semantic_ledger(projected)
