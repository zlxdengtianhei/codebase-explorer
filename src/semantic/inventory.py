"""Probe-exact Python file and lexical symbol inventory.

The ledger never supplies its own denominator.  This module enumerates the
repository again, using the immutable probe's path exclusions, AST traversal,
symbol identity, and span hashing rules.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence

from src.ir import Symbol
from src.semantic.models import (
    PENDING_EXPLANATION_REASON,
    FileStatus,
    SemanticExplanation,
    SemanticFileRecord,
    SemanticLedger,
    SemanticResidual,
    SemanticSymbolKind,
    SemanticSymbolRecord,
    derived_totals,
    revalidate_semantic_ledger,
    semantic_symbol_id,
    hash_json,
)


PROBE_EXCLUDE_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "build",
        "dist",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "site-packages",
        ".eggs",
        ".codebase-analysis",
        ".codebase-docs",
    }
)


OUT_EDGE_SIDECAR = Path(".codebase-analysis/file_out_edges.json")


@dataclass(frozen=True)
class SemanticInventory:
    repo_root: str
    source_revision: str
    files: Mapping[str, SemanticFileRecord]
    symbols: Mapping[str, SemanticSymbolRecord]
    diagnostics: tuple[str, ...] = ()
    #: `path -> sha256:<全文摘要>`。增量的最小单位（F1 §2.3 的 P0）。
    file_revisions: Mapping[str, str] = field(default_factory=dict)
    #: `path -> sha256:<import/call 出边集合>`。图投影是否重算看这个，不看全文。
    file_out_edge_revisions: Mapping[str, str] = field(default_factory=dict)
    #: Typed T2 edge snapshot binding.  Empty legacy fixtures use a deterministic
    #: empty snapshot and are upgraded by the service when relations are present.
    edge_snapshot_sha256: str = "sha256:" + "0" * 64
    edge_relation_count: int = 0


def enumerate_python_files(repo_root: str | Path) -> tuple[Path, ...]:
    """Return the exact Python file denominator used by the acceptance probe."""

    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")
    return tuple(
        path
        for path in sorted(root.rglob("*.py"))
        if not any(part in PROBE_EXCLUDE_DIRS for part in path.relative_to(root).parts)
    )


def _span_hash(source: str, start: int, end: int) -> str:
    lines = source.splitlines()
    body = "\n".join(lines[start - 1 : end])
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def file_out_edge_tokens(source: str) -> tuple[str, ...]:
    """一个文件的 import/call 出边集合。只问「连向谁」，不问函数体怎么写。"""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tokens.add(f"import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            tokens.add(f"from:{node.module or ''}")
            for alias in node.names:
                tokens.add(f"fromname:{alias.name}")
        elif isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                tokens.add(f"call:{function.id}")
            elif isinstance(function, ast.Attribute):
                tokens.add(f"callattr:{function.attr}")
    return tuple(sorted(tokens))


def out_edge_revision(tokens: Sequence[str]) -> str:
    framed = "\n".join(tokens).encode("utf-8")
    return "sha256:" + hashlib.sha256(framed).hexdigest()


def load_file_out_edge_revisions(repo_root: str | Path) -> dict[str, str]:
    path = Path(repo_root) / OUT_EDGE_SIDECAR
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if isinstance(key, str) and isinstance(value, str) and value.startswith("sha256:")
    }


def persist_file_out_edge_revisions(repo_root: str | Path, revisions: Mapping[str, str]) -> Path:
    target = Path(repo_root) / OUT_EDGE_SIDECAR
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(sorted(revisions.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def page_content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PageRewriteDecision:
    path: str
    action: Literal["write", "skip"]
    previous_hash: str | None
    current_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "action": self.action,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
        }


@dataclass(frozen=True)
class PageRewritePlan:
    """渲染层 per-page diff 的可调用接口（F1 §2.3）。

    变体格在写 `.codebase-docs` 之前调 `plan_page_rewrites`。
    `action=skip` 的页不得重写——否则整树 mtime 全变，冒充「产物已更新」。
    本函数不删「只在旧树里出现」的页；删除是调用方的事。
    """

    decisions: tuple[PageRewriteDecision, ...]

    @property
    def write_paths(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.decisions if item.action == "write")

    @property
    def skip_paths(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.decisions if item.action == "skip")

    def as_dict(self) -> dict[str, object]:
        return {
            "write": list(self.write_paths),
            "skip": list(self.skip_paths),
            "decisions": [item.as_dict() for item in self.decisions],
        }


def plan_page_rewrites(
    current_pages: Mapping[str, str],
    previous_hashes: Mapping[str, str] | None = None,
) -> PageRewritePlan:
    """`content_hash` 不变则 skip。契约见 `PageRewritePlan` 文档。"""

    prior = previous_hashes or {}
    decisions: list[PageRewriteDecision] = []
    for path, text in sorted(current_pages.items()):
        digest = page_content_hash(text)
        previous = prior.get(path)
        decisions.append(
            PageRewriteDecision(
                path=path,
                action="skip" if previous == digest else "write",
                previous_hash=previous,
                current_hash=digest,
            )
        )
    return PageRewritePlan(decisions=tuple(decisions))


def _source_revision(rows: list[tuple[str, str]]) -> str:
    """仓库级指纹。**派生的展示字段**，不再是增量判据。

    它作为增量判据时的后果链（F1 §2.3）：改任意一个文件 → 本值变 → `same_revision=False`
    → 全仓每个符号的 `ir_symbol_id / module_id / scc_id / cycle_peer_ids /
    runtime_covered_lines` 被置空 → 需要全图 condensation + 全仓 PageRank + 全仓 AST 重扫。
    判据现在是 `file_revisions` 的逐文件比对，本值只用于展示与整仓相同性的快路判断。
    """

    framed = b"".join(
        path.encode("utf-8") + b"\x00" + digest.encode("ascii")
        for path, digest in sorted(rows)
    )
    return "rev_" + hashlib.sha256(framed).hexdigest()


def _ir_bridge(symbols: Iterable[Symbol]) -> dict[tuple[str, str, int, int], str]:
    bridge: dict[tuple[str, str, int, int], str] = {}
    for symbol in symbols:
        lexical = symbol.language_attributes.get("lexical_qualified_name")
        start = symbol.language_attributes.get("definition_start_line")
        end = symbol.language_attributes.get("definition_end_line")
        if not isinstance(lexical, str) or type(start) is not int or type(end) is not int:
            continue
        bridge[(symbol.path, lexical, start, end)] = symbol.id
    return bridge


def enumerate_semantic_inventory(
    repo_root: str | Path,
    *,
    ir_symbols: Iterable[Symbol] = (),
) -> SemanticInventory:
    """Independently enumerate every probe-visible file and lexical symbol."""

    root = Path(repo_root).resolve()
    files: dict[str, SemanticFileRecord] = {}
    symbols: dict[str, SemanticSymbolRecord] = {}
    diagnostics: list[str] = []
    revision_rows: list[tuple[str, str]] = []
    out_edge_rows: dict[str, str] = {}
    bridge = _ir_bridge(ir_symbols)

    for path in enumerate_python_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            raw = path.read_bytes()
        except OSError as exc:
            reason = f"source read failed: {type(exc).__name__}: {exc}"
            files[relative] = SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason=reason,
            )
            diagnostics.append(f"{relative}: {reason}")
            unreadable_digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()
            revision_rows.append((relative, unreadable_digest))
            continue

        file_digest = hashlib.sha256(raw).hexdigest()
        revision_rows.append((relative, file_digest))
        source = raw.decode("utf-8", errors="replace")
        out_edge_rows[relative] = out_edge_revision(file_out_edge_tokens(source))
        try:
            tree = ast.parse(source, filename=relative)
        except SyntaxError as exc:
            reason = (
                f"Python AST parse failed at line {exc.lineno or 0}, "
                f"column {exc.offset or 0}: {exc.msg}"
            )
            files[relative] = SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason=reason,
            )
            diagnostics.append(f"{relative}: {reason}")
            continue

        stack: list[str] = []
        file_symbol_ids: list[str] = []

        def walk(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name)
                    qualified = ".".join(stack)
                    kind = (
                        SemanticSymbolKind.CLASS
                        if isinstance(child, ast.ClassDef)
                        else SemanticSymbolKind.METHOD
                        if len(stack) > 1
                        else SemanticSymbolKind.FUNCTION
                    )
                    first_line = min(
                        [decorator.lineno for decorator in child.decorator_list]
                        + [child.lineno]
                    )
                    end = getattr(child, "end_lineno", None) or child.lineno
                    symbol_id = semantic_symbol_id(relative, qualified)
                    if symbol_id in symbols:
                        previous = symbols[symbol_id]
                        diagnostics.append(
                            f"{symbol_id}: later definition at line {first_line} replaces "
                            f"probe-colliding definition at line {previous.span[0]}"
                        )
                    record = SemanticSymbolRecord(
                        path=relative,
                        qualified_name=qualified,
                        kind=kind,
                        span=(first_line, end),
                        content_hash=_span_hash(source, first_line, end),
                        explanation=None,
                        ir_symbol_id=bridge.get((relative, qualified, first_line, end)),
                    )
                    symbols[symbol_id] = record
                    if symbol_id not in file_symbol_ids:
                        file_symbol_ids.append(symbol_id)
                    walk(child)
                    stack.pop()
                else:
                    walk(child)

        walk(tree)
        files[relative] = SemanticFileRecord(
            status=FileStatus.RESIDUAL if file_symbol_ids else FileStatus.NO_SYMBOLS,
            reason=PENDING_EXPLANATION_REASON if file_symbol_ids else "",
        )

    return SemanticInventory(
        repo_root=root.as_posix(),
        source_revision=_source_revision(revision_rows),
        files=dict(sorted(files.items())),
        symbols=dict(sorted(symbols.items())),
        diagnostics=tuple(diagnostics),
        file_revisions={path: f"sha256:{digest}" for path, digest in sorted(revision_rows)},
        file_out_edge_revisions=dict(sorted(out_edge_rows.items())),
        edge_snapshot_sha256=hash_json([]),
        edge_relation_count=0,
    )


def _dependency_invalidations(
    current_symbols: Mapping[str, SemanticSymbolRecord],
    prior_symbols: Mapping[str, SemanticSymbolRecord],
    explanation_overrides: Mapping[str, SemanticExplanation | None] | None,
) -> tuple[set[str], dict[str, tuple[str, ...]]]:
    """Find reverse-reachable callers of missing or non-fresh dependencies."""

    current_ids = set(current_symbols)

    def effective_explanation(symbol_id: str) -> SemanticExplanation | None:
        if explanation_overrides is not None and symbol_id in explanation_overrides:
            return explanation_overrides[symbol_id]
        prior = prior_symbols.get(symbol_id)
        return prior.explanation if prior is not None else None

    invalid = set(prior_symbols) - current_ids
    for symbol_id, current in current_symbols.items():
        explanation = effective_explanation(symbol_id)
        if (
            explanation is None
            or explanation.explained_content_hash != current.content_hash
        ):
            invalid.add(symbol_id)

    invalidated_callers: set[str] = set()
    missing_by_caller: dict[str, tuple[str, ...]] = {}
    changed = True
    while changed:
        changed = False
        for symbol_id in current_symbols:
            explanation = effective_explanation(symbol_id)
            citations = explanation.cited_symbol_ids if explanation is not None else ()
            missing = tuple(cited for cited in citations if cited not in current_ids)
            if missing:
                missing_by_caller[symbol_id] = missing
            if symbol_id not in invalid and any(cited in invalid for cited in citations):
                invalid.add(symbol_id)
                invalidated_callers.add(symbol_id)
                changed = True
    return invalidated_callers, missing_by_caller


def reconcile_semantic_ledger(
    inventory: SemanticInventory,
    previous: SemanticLedger | None = None,
    *,
    explanation_overrides: Mapping[str, SemanticExplanation | None] | None = None,
    order_override: tuple[str, ...] | None = None,
    previous_out_edge_revisions: Mapping[str, str] | None = None,
) -> SemanticLedger:
    """Reconcile current truth with an optional prior on-disk ledger.

    Stable identities retain explanations.  A changed body retains the old
    explanation hash, becoming mechanically stale.  Removed identities and
    citations are pruned; no prior denominator is trusted.
    """

    if previous is not None:
        previous = revalidate_semantic_ledger(previous)
        if previous.repo_root != inventory.repo_root:
            raise ValueError("prior ledger belongs to a different repository root")

    current_ids = set(inventory.symbols)
    same_revision = previous is not None and previous.source_revision == inventory.source_revision
    prior_symbols = previous.symbols if previous is not None else {}
    prior_file_revisions = dict(previous.file_revisions) if previous is not None else {}
    prior_out_edges = (
        dict(previous_out_edge_revisions)
        if previous_out_edge_revisions is not None
        else load_file_out_edge_revisions(inventory.repo_root)
        if previous is not None
        else {}
    )
    edge_changed_paths = {
        path
        for path, digest in inventory.file_out_edge_revisions.items()
        if prior_out_edges.get(path) != digest
    } if prior_out_edges else set()
    affected_sccs = {
        prior.scc_id
        for prior in prior_symbols.values()
        if prior.path in edge_changed_paths and prior.scc_id
    }

    def file_projection_survives(path: str) -> bool:
        """图投影保留：文件全文没变，或全文变了但 import/call 出边集合没变。

        旧台账没有 `file_revisions` 时回退到仓库级判据，行为与本改动之前逐字相同——
        增量能力只在两侧都有 per-file 指纹时才打开，不靠猜。
        """

        if not prior_file_revisions:
            return same_revision
        prior_digest = prior_file_revisions.get(path)
        if prior_digest is not None and prior_digest == inventory.file_revisions.get(path):
            return True
        prior_edges = prior_out_edges.get(path)
        current_edges = inventory.file_out_edge_revisions.get(path)
        return (
            prior_edges is not None
            and current_edges is not None
            and prior_edges == current_edges
        )

    invalidated_callers, missing_citations = _dependency_invalidations(
        inventory.symbols,
        prior_symbols,
        explanation_overrides,
    )
    prior_residuals = (
        {item.symbol_id: item.reason for item in previous.residuals}
        if previous is not None
        else {}
    )
    symbols: dict[str, SemanticSymbolRecord] = {}
    for symbol_id, current in inventory.symbols.items():
        prior = prior_symbols.get(symbol_id)
        explanation = (
            explanation_overrides[symbol_id]
            if explanation_overrides is not None and symbol_id in explanation_overrides
            else prior.explanation
            if prior is not None
            else None
        )
        missing = tuple(
            cited
            for cited in (explanation.cited_symbol_ids if explanation is not None else ())
            if cited not in current_ids
        )
        if missing or symbol_id in invalidated_callers:
            explanation = None
        content_changed = prior is not None and prior.content_hash != current.content_hash
        explanation_stale = (
            explanation is not None
            and explanation.explained_content_hash != current.content_hash
        )
        preserve_graph_projection = (
            prior is not None
            and file_projection_survives(current.path)
            and (prior.scc_id is None or prior.scc_id not in affected_sccs)
        )
        invalidation_reason = (
            f"cited symbol removed: {', '.join(missing_citations.get(symbol_id, missing))}"
            if missing_citations.get(symbol_id, missing)
            else "cited symbol is stale or invalid"
            if symbol_id in invalidated_callers
            else "source content hash changed"
            if explanation_stale
            else None
        )
        symbols[symbol_id] = current.model_copy(
            update={
                "explanation": explanation,
                "ir_symbol_id": (
                    current.ir_symbol_id
                    if current.ir_symbol_id is not None
                    else prior.ir_symbol_id
                    if preserve_graph_projection
                    else None
                ),
                "module_id": prior.module_id if preserve_graph_projection else None,
                "scc_id": prior.scc_id if preserve_graph_projection else None,
                "cycle_peer_ids": (
                    tuple(peer for peer in prior.cycle_peer_ids if peer in current_ids)
                    if preserve_graph_projection
                    else ()
                ),
                "invalidation_reason": invalidation_reason,
                "runtime_covered_lines": (
                    prior.runtime_covered_lines if preserve_graph_projection else None
                ),
            }
        )

    residuals: list[SemanticResidual] = []
    for symbol_id, symbol in symbols.items():
        if symbol.is_fresh:
            continue
        if symbol.invalidation_reason is not None:
            reason = f"stale semantic explanation: {symbol.invalidation_reason}"
        elif symbol.is_explained:
            reason = "stale semantic explanation: source content changed"
        else:
            reason = prior_residuals.get(symbol_id, PENDING_EXPLANATION_REASON)
        residuals.append(SemanticResidual(symbol_id=symbol_id, reason=reason))
    residuals.sort(key=lambda item: item.symbol_id)

    by_path: dict[str, list[SemanticSymbolRecord]] = {
        path: [] for path in inventory.files
    }
    for symbol in symbols.values():
        by_path[symbol.path].append(symbol)
    files: dict[str, SemanticFileRecord] = {}
    for path, inventory_record in inventory.files.items():
        path_symbols = by_path[path]
        if not path_symbols:
            files[path] = inventory_record
        elif all(symbol.is_fresh for symbol in path_symbols):
            files[path] = SemanticFileRecord(status=FileStatus.COVERED)
        else:
            stale_count = sum(symbol.is_explained for symbol in path_symbols)
            pending_count = len(path_symbols) - stale_count
            details = []
            if pending_count:
                details.append(f"{pending_count} pending semantic explanation(s)")
            if stale_count:
                details.append(f"{stale_count} stale semantic explanation(s)")
            files[path] = SemanticFileRecord(
                status=FileStatus.RESIDUAL,
                reason="; ".join(details),
            )

    fresh_ids = {symbol_id for symbol_id, symbol in symbols.items() if symbol.is_fresh}
    if order_override is not None:
        order = tuple(symbol_id for symbol_id in order_override if symbol_id in fresh_ids)
    else:
        order = (
            tuple(symbol_id for symbol_id in previous.order if symbol_id in fresh_ids)
            if same_revision and previous is not None
            else ()
        )
    uncovered = tuple(sorted(set(symbols) - fresh_ids))
    totals = derived_totals(symbols, len(residuals))
    coverage = round(100.0 * totals.explained / totals.symbols, 4) if totals.symbols else 0.0
    ledger_kwargs = {
        "repo_root": inventory.repo_root,
        "source_revision": inventory.source_revision,
        "file_revisions": dict(inventory.file_revisions),
        "excluded_globs": previous.excluded_globs if previous is not None else (),
        "files": files,
        "symbols": symbols,
        "order": order,
        "residuals": tuple(residuals),
        "totals": totals,
        "coverage_percent": coverage,
        "uncovered_symbols": uncovered,
    }
    if previous is not None:
        ledger_kwargs["legacy_import"] = previous.legacy_import
    ledger = SemanticLedger(**ledger_kwargs)
    # Bind the current inventory namespace into the canonical v3 ledger.  The
    # relation rows themselves remain owned by T2; only their hash/count binding
    # is carried here, so this module cannot become a second edge ledger.
    bindings = ledger.bindings.model_copy(
        update={
            "edge_snapshot_sha256": inventory.edge_snapshot_sha256,
            "edge_relation_count": inventory.edge_relation_count,
            "symbol_inventory_sha256": hash_json(
                [[symbol_id, symbol.content_hash] for symbol_id, symbol in sorted(inventory.symbols.items())]
            ),
        }
    )
    ledger = ledger.model_copy(update={"bindings": bindings})
    return revalidate_semantic_ledger(ledger)


def build_ledger_skeleton(
    repo_root: str | Path,
    *,
    ir_symbols: Iterable[Symbol] = (),
) -> SemanticLedger:
    """Create an in-memory zero-explanation ledger over current source truth."""

    return reconcile_semantic_ledger(
        enumerate_semantic_inventory(repo_root, ir_symbols=ir_symbols)
    )
