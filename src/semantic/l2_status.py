"""L2 status labelling: what role each symbol plays, and where each file sits.

Two deliberate separations from clustering:

*Work unit.*  Clustering works on files; status works on symbols.  They are
different questions ("which capability does this belong to" vs "what part does
this play"), so merging them would force one work unit onto both.

*Cost.*  Most of the evidence is already deterministic -- ``is_exported``,
``in_degree`` and ``hops_from_surface`` are AST facts, so ``entry`` and
``public_api`` need no model at all.  Only the ``core`` / ``glue`` / ``adapter``
boundary requires reading a one-liner.  The shape is therefore: deterministic
candidates, cheap tier decides, ambiguity escalates -- not the strong tier over
every symbol.

Status labels attach to symbols, but ``module_id`` attaches to the **file**.
Under the previous design a file carried its module only through its symbols,
so a zero-symbol file had nothing to carry it and silently became
``unclassified``.  Measured: 4 such files in flask, 2 in httpx.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import networkx as nx

from src.graph.feature_cone import PublicSurfaceEntry
from src.graph.file_cards import L1SymbolFact

logger = logging.getLogger(__name__)

STATUS_VALUES = (
    "entry",
    "public_api",
    "core",
    "adapter",
    "data",
    "glue",
    "error_path",
)
"""The status enum from F1 §3.4, unchanged.

Kept as-is deliberately: this run's job is to test the partition, and moving
the label set at the same time would make any change in the readings
un-attributable.
"""

_DETERMINISTIC_STATUSES = frozenset({"entry", "public_api", "error_path"})
_MODEL_STATUSES = tuple(s for s in STATUS_VALUES if s not in _DETERMINISTIC_STATUSES)

_EXCEPTION_NAME = re.compile(r"(Error|Exception|Warning)$")

UNCLASSIFIED_REASONS = {
    "no_cluster_owner": "该文件不在任何簇的成员里（它落在残差清单上）",
    "no_one_liner": "L1 没有给出这个符号的解释，判地位缺输入",
    "model_declined": "分类模型对该符号未给出合法标签，已升档仍未定",
    "not_in_graph": "文件不在运行时依赖图中，度数与跳数无法计算",
}
"""Why a symbol ended up unclassified. Every entry carries one and is rendered.

r003 N-3: the previous pipeline dropped these without a word, so a reader could
not tell an unindexed definition from one that does not exist.
"""


class StatusError(ValueError):
    """Raised when status labelling is given unusable input."""


@dataclass(frozen=True)
class SymbolCard:
    """Evidence for one status decision (F1 §3.4).

    Carries no cluster name or cluster prose: a label that has seen the cluster
    description drifts toward agreeing with it, which would make the label
    confirm the clustering rather than test it.
    """

    symbol_id: str
    path: str
    kind: str
    one_liner: str
    effects: tuple[str, ...]
    in_degree: int
    out_degree: int
    is_exported: bool
    hops_from_surface: int | None
    mess_score: float | None = None


@dataclass(frozen=True)
class StatusLabel:
    """A symbol's assigned role plus the evidence behind it."""

    symbol_id: str
    status: str
    evidence: Mapping[str, object]
    confidence: str
    decided_by: str

    def __post_init__(self) -> None:
        if self.status not in STATUS_VALUES:
            raise StatusError(
                f"status {self.status!r} is outside the enum {STATUS_VALUES}"
            )


@dataclass(frozen=True)
class UnclassifiedSymbol:
    """A symbol with no status, and the reason it has none."""

    symbol_id: str
    path: str
    reason_code: str
    reason: str


@dataclass(frozen=True)
class FileStatusRecord:
    """A file's cluster membership. ``module_id`` lives here, not on symbols."""

    path: str
    module_id: str | None
    symbol_count: int
    reason_code: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class StatusResult:
    """Labels, residuals and per-file module ownership."""

    labels: tuple[StatusLabel, ...]
    unclassified: tuple[UnclassifiedSymbol, ...]
    files: tuple[FileStatusRecord, ...]
    diagnostics: tuple[str, ...] = ()


def compute_hops_from_surface(
    graph: nx.DiGraph,
    seed_paths: Iterable[str],
) -> dict[str, int]:
    """Shortest hop count from any public-surface defining file to each file."""
    seeds = [p for p in seed_paths if p in graph]
    if not seeds:
        return {}
    hops: dict[str, int] = {}
    for seed in seeds:
        for path, distance in nx.single_source_shortest_path_length(graph, seed).items():
            current = hops.get(path)
            if current is None or distance < current:
                hops[path] = distance
    return hops


def build_symbol_in_degrees(
    ledger_symbols: Mapping[str, Mapping[str, object]],
    ir_relations: Sequence[object],
) -> dict[str, int]:
    """Count resolved in-repository references per ledger symbol.

    Only relations whose target resolves to a symbol in this repository count.
    That is a sparse signal by nature -- measured on flask, 74 of 901 call
    relations resolve -- so it ranks and never gates: a zero here means
    "unresolved", not "unused".
    """
    by_ir_id: dict[str, str] = {}
    for symbol_id, record in ledger_symbols.items():
        ir_id = record.get("ir_symbol_id")
        if isinstance(ir_id, str):
            by_ir_id[ir_id] = symbol_id

    degrees: dict[str, int] = defaultdict(int)
    for relation in ir_relations:
        target = getattr(relation, "target", None)
        target_id = getattr(target, "id", None)
        if not isinstance(target_id, str):
            continue
        symbol_id = by_ir_id.get(target_id)
        if symbol_id is not None:
            degrees[symbol_id] += 1
    return dict(degrees)


def build_symbol_cards(
    facts: Sequence[L1SymbolFact],
    graph: nx.DiGraph,
    surface: Sequence[PublicSurfaceEntry],
    *,
    in_degrees: Mapping[str, int] | None = None,
    hops: Mapping[str, int] | None = None,
) -> tuple[SymbolCard, ...]:
    """Build one card per symbol from deterministic evidence."""
    exported: set[tuple[str, str]] = {
        (entry.defining_path, entry.defining_name) for entry in surface
    }
    degrees = dict(in_degrees or {})
    hop_map = dict(hops or {})

    cards: list[SymbolCard] = []
    for fact in facts:
        short = fact.qualified_name.rsplit(".", 1)[-1]
        cards.append(
            SymbolCard(
                symbol_id=fact.symbol_id,
                path=fact.path,
                kind=fact.kind,
                one_liner=fact.one_liner,
                effects=fact.effects,
                in_degree=degrees.get(fact.symbol_id, 0),
                out_degree=graph.out_degree(fact.path) if fact.path in graph else 0,
                is_exported=(fact.path, short) in exported
                or (fact.path, fact.qualified_name) in exported,
                hops_from_surface=hop_map.get(fact.path),
                mess_score=fact.mess_score,
            )
        )
    return tuple(cards)


def deterministic_status(
    card: SymbolCard,
    *,
    entry_paths: frozenset[str],
    exception_bases: Mapping[str, bool] | None = None,
) -> StatusLabel | None:
    """Assign the statuses that need no model, else ``None``.

    ``entry`` and ``public_api`` follow from AST facts alone.  ``error_path``
    uses the class-name suffix convention plus, when supplied, real inheritance
    from an exception base -- name convention alone would misfire on a class
    merely *about* errors.
    """
    evidence = {
        "is_exported": card.is_exported,
        "in_degree": card.in_degree,
        "hops_from_surface": card.hops_from_surface,
        "kind": card.kind,
    }
    short = card.symbol_id.rsplit("::", 1)[-1].rsplit(".", 1)[-1]

    inherits_exception = (exception_bases or {}).get(card.symbol_id)
    if card.kind == "class" and (
        inherits_exception is True
        or (inherits_exception is None and _EXCEPTION_NAME.search(short))
    ):
        return StatusLabel(
            symbol_id=card.symbol_id,
            status="error_path",
            evidence={**evidence, "exception_name_or_base": True},
            confidence="high",
            decided_by="deterministic",
        )
    if card.path in entry_paths and card.hops_from_surface == 0 and card.is_exported:
        return StatusLabel(
            symbol_id=card.symbol_id,
            status="entry",
            evidence={**evidence, "surface_entry_file": True},
            confidence="high",
            decided_by="deterministic",
        )
    if card.is_exported:
        return StatusLabel(
            symbol_id=card.symbol_id,
            status="public_api",
            evidence=evidence,
            confidence="high",
            decided_by="deterministic",
        )
    return None


def build_status_prompt(cards: Sequence[SymbolCard], *, repo_name: str) -> str:
    """Prompt for the batch that deterministic rules could not decide."""
    payload = [
        {
            "symbol_id": c.symbol_id,
            "path": c.path,
            "kind": c.kind,
            "one_liner": c.one_liner,
            "in_degree": c.in_degree,
            "out_degree": c.out_degree,
            "hops_from_surface": c.hops_from_surface,
        }
        for c in cards
    ]
    return f"""Assign a role to each symbol from `{repo_name}`.

Choose exactly one of: {", ".join(_MODEL_STATUSES)}.

- `core`: implements the substance of a capability; the logic a reader came for.
- `adapter`: translates between this codebase and something outside it
  (a protocol, a third-party library, an I/O boundary, a serialisation format).
- `data`: a value, constant, type, schema or container with little behaviour.
- `glue`: wiring that moves values between other parts without deciding much.

Symbols already known to be entry points, public API or error paths were
removed before this call, so do not use those labels.

Judge only from the evidence given. Where the one-liner does not support a
confident choice, say so with `"confidence": "low"` rather than guessing --
a low-confidence answer is routed to a stronger model, a wrong confident one
is not.

{json.dumps(payload, ensure_ascii=False, indent=1)}

Return JSON only:
{{"labels": [{{"symbol_id": "...", "status": "core", "confidence": "high"}}]}}
"""


def parse_status_response(text: str) -> dict[str, tuple[str, str]]:
    """Parse the status model's reply into ``{symbol_id: (status, confidence)}``.

    Entries with a status outside the enum are dropped, so they surface as
    unclassified with a reason instead of entering the ledger as a bad label.
    """
    from src.semantic.l2_cluster import _extract_json_object

    payload = _extract_json_object(text)
    if payload is None:
        raise StatusError("status response contained no JSON object")

    result: dict[str, tuple[str, str]] = {}
    for item in payload.get("labels", []):
        if not isinstance(item, dict):
            continue
        symbol_id = item.get("symbol_id")
        status = str(item.get("status", "")).strip().lower()
        confidence = str(item.get("confidence", "low")).strip().lower()
        if not isinstance(symbol_id, str) or status not in _MODEL_STATUSES:
            continue
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        result[symbol_id] = (status, confidence)
    return result


def assemble_status(
    cards: Sequence[SymbolCard],
    deterministic: Mapping[str, StatusLabel],
    model_labels: Mapping[str, tuple[str, str]],
    path_to_cluster: Mapping[str, str],
    *,
    residual_paths: Mapping[str, str] | None = None,
) -> StatusResult:
    """Combine deterministic and model labels, and record every gap.

    A symbol the model declined is unclassified **with a reason**, never
    silently defaulted to ``core``: a default would make the label set look
    complete while carrying no information.
    """
    residuals = dict(residual_paths or {})
    labels: list[StatusLabel] = []
    unclassified: list[UnclassifiedSymbol] = []
    per_path_counts: dict[str, int] = defaultdict(int)

    for card in cards:
        per_path_counts[card.path] += 1
        existing = deterministic.get(card.symbol_id)
        if existing is not None:
            labels.append(existing)
            continue
        decided = model_labels.get(card.symbol_id)
        if decided is None:
            reason_code = "no_one_liner" if not card.one_liner else "model_declined"
            unclassified.append(
                UnclassifiedSymbol(
                    symbol_id=card.symbol_id,
                    path=card.path,
                    reason_code=reason_code,
                    reason=UNCLASSIFIED_REASONS[reason_code],
                )
            )
            continue
        status, confidence = decided
        labels.append(
            StatusLabel(
                symbol_id=card.symbol_id,
                status=status,
                evidence={
                    "is_exported": card.is_exported,
                    "in_degree": card.in_degree,
                    "hops_from_surface": card.hops_from_surface,
                    "kind": card.kind,
                },
                confidence=confidence,
                decided_by="model",
            )
        )

    files: list[FileStatusRecord] = []
    for path in sorted(set(per_path_counts) | set(path_to_cluster) | set(residuals)):
        module_id = path_to_cluster.get(path)
        if module_id is None:
            reason_code = "no_cluster_owner"
            files.append(
                FileStatusRecord(
                    path=path,
                    module_id=None,
                    symbol_count=per_path_counts.get(path, 0),
                    reason_code=reason_code,
                    reason=residuals.get(path) or UNCLASSIFIED_REASONS[reason_code],
                )
            )
        else:
            files.append(
                FileStatusRecord(
                    path=path,
                    module_id=module_id,
                    symbol_count=per_path_counts.get(path, 0),
                )
            )

    diagnostics: list[str] = []
    if unclassified:
        diagnostics.append(f"unclassified_symbols:{len(unclassified)}")
    zero_symbol_assigned = [f for f in files if f.symbol_count == 0 and f.module_id]
    if zero_symbol_assigned:
        diagnostics.append(
            f"zero_symbol_files_kept:{len(zero_symbol_assigned)} "
            "(module_id on the file, so they are not unclassified)"
        )

    logger.info(
        "Status: %d labelled, %d unclassified, %d files (%d with no cluster)",
        len(labels),
        len(unclassified),
        len(files),
        sum(1 for f in files if f.module_id is None),
    )
    return StatusResult(
        labels=tuple(labels),
        unclassified=tuple(unclassified),
        files=tuple(files),
        diagnostics=tuple(diagnostics),
    )
