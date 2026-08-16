"""File cards: the only evidence the L2 clustering layer is allowed to see.

The layered architecture (F1 §3.2) whitelists what reaches L2 clustering:
file cards, file-level import/call edges, and the public-surface overlay.  It
forbids source code (not one line), the L1 ``behavior`` long text, and any L1
execution trace, model identity or retry count.  The last group is forbidden
for a specific reason: if L2 could see that a card came from the strong tier it
would weight it higher, and the layer boundary would leak back upward.

That whitelist is enforced here by construction rather than by prompt wording.
:class:`FileCard` has no field that can carry source, and
:func:`clustering_payload` serialises only the card's own fields, so a caller
cannot smuggle extra context through without editing this module.

Card contents are cheap on purpose: flask's 24 cards are roughly 6k tokens, so
the strong model sees the whole repository in one call.  Symbol cards would
not scale the same way -- flask's 415 are ~25k and sqlalchemy's 7717 are
~460k, which overflows the window outright.  Choosing the file as L2's work
unit is what makes the layer affordable, not a stylistic preference.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from src.graph.feature_cone import PublicSurfaceEntry

logger = logging.getLogger(__name__)

TOP_SYMBOL_LIMIT = 7
"""Cap on ``top_symbols`` per card (F1 §3.4)."""

ONE_LINER_MAX_CHARS = 160
"""Hard cap on a derived one-liner, so a card cannot smuggle in long behaviour text."""

_SENTENCE_END = re.compile(r"(?<=[。！？])|(?<=[.!?])(?=\s)")


class FileCardError(ValueError):
    """Raised when file-card construction is given unusable input."""


@dataclass(frozen=True)
class L1SymbolFact:
    """One symbol's L1 output, in the shape L2 is allowed to consume.

    This mirrors ``L1SymbolFact`` in F1 §2.1: it deliberately carries no
    ``role`` or ``importance`` field, because status is L2's job to assign and
    a status claim arriving from below would pre-empt it.
    """

    symbol_id: str
    path: str
    qualified_name: str
    kind: str
    one_liner: str
    effects: tuple[str, ...] = ()
    mess_score: float | None = None

    def __post_init__(self) -> None:
        if not self.symbol_id:
            raise FileCardError("L1 fact requires a symbol id")
        if not self.path:
            raise FileCardError(f"L1 fact {self.symbol_id!r} requires a path")


@dataclass(frozen=True)
class TopSymbol:
    """A symbol surfaced on a file card."""

    symbol_id: str
    one_liner: str


@dataclass(frozen=True)
class FileCard:
    """Structured, source-free evidence about one file (F1 §3.4)."""

    path: str
    language: str
    exported_names: tuple[str, ...]
    symbol_count: int
    symbol_kinds: Mapping[str, int]
    top_symbols: tuple[TopSymbol, ...]
    effects_histogram: Mapping[str, int]
    out_files: tuple[str, ...]
    in_files: tuple[str, ...]
    mess_p50: float | None = None


def derive_one_liner(text: str, *, max_chars: int = ONE_LINER_MAX_CHARS) -> str:
    """Reduce an L1 explanation to its first sentence.

    Deterministic and language-agnostic (the corpus mixes Chinese and English).
    This exists because the current ledger stores only the long ``behavior``
    text; once L1 emits a real ``one_liner`` this becomes a no-op adapter and
    callers do not change.
    """
    stripped = text.strip()
    if not stripped:
        return ""
    parts = [part for part in _SENTENCE_END.split(stripped, maxsplit=1) if part]
    first = parts[0].strip() if parts else stripped
    if len(first) > max_chars:
        suffix = "…"
        first = first[: max(0, max_chars - len(suffix))].rstrip() + suffix
    return first


def load_l1_facts(ledger_path: str | Path) -> tuple[tuple[L1SymbolFact, ...], tuple[str, ...]]:
    """Load L1 facts from a semantic ledger.

    Returns ``(facts, diagnostics)``.  A symbol with no explanation yields a
    fact with an empty ``one_liner`` plus a diagnostic, rather than being
    dropped: silently shrinking the symbol universe is exactly how a coverage
    denominator drifts.

    Raises:
        FileCardError: If the ledger is missing or unreadable.
    """
    path = Path(ledger_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FileCardError(f"cannot read semantic ledger {path}: {exc}") from exc

    symbols = payload.get("symbols")
    if not isinstance(symbols, dict):
        raise FileCardError(f"semantic ledger {path} has no symbol table")

    facts: list[L1SymbolFact] = []
    diagnostics: list[str] = []
    for symbol_id, record in sorted(symbols.items()):
        explanation = record.get("explanation") or {}
        text = explanation.get("text", "") if isinstance(explanation, dict) else ""
        one_liner = derive_one_liner(text)
        if not one_liner:
            diagnostics.append(f"missing_one_liner:{symbol_id}")
        facts.append(
            L1SymbolFact(
                symbol_id=symbol_id,
                path=record["path"],
                qualified_name=record["qualified_name"],
                kind=record.get("kind", "unknown"),
                one_liner=one_liner,
            )
        )
    logger.info(
        "Loaded %d L1 facts from %s (%d without a one-liner)",
        len(facts),
        path,
        len(diagnostics),
    )
    return tuple(facts), tuple(diagnostics)


def build_file_cards(
    facts: Sequence[L1SymbolFact],
    graph: nx.DiGraph,
    surface: Sequence[PublicSurfaceEntry],
    universe: Iterable[str],
    *,
    language: str = "python",
    symbol_in_degree: Mapping[str, int] | None = None,
) -> tuple[tuple[FileCard, ...], tuple[str, ...]]:
    """Build one card per file in *universe*.

    Args:
        facts: L1 facts for every symbol (the symbol universe; its size is the
            coverage denominator and is never reduced here).
        graph: Runtime file-import graph; ``A -> B`` means A imports B.
        surface: Public-surface entries, used for ``exported_names`` and to
            rank ``top_symbols``.
        universe: Files to card.  A file with zero symbols still gets a card --
            dropping it is how zero-symbol files fall into ``unclassified``.
        symbol_in_degree: Optional per-symbol in-degree for ranking.
        language: Language tag recorded on every card.

    Returns:
        ``(cards, diagnostics)`` where diagnostics name every input gap that
        left a card field empty, so a missing upstream layer stays visible.

    Raises:
        FileCardError: If *universe* is empty.
    """
    paths = sorted(set(universe))
    if not paths:
        raise FileCardError("file-card construction needs a non-empty universe")

    in_degree = dict(symbol_in_degree or {})
    facts_by_path: dict[str, list[L1SymbolFact]] = defaultdict(list)
    for fact in facts:
        facts_by_path[fact.path].append(fact)

    exported_by_path: dict[str, set[str]] = defaultdict(set)
    exported_symbol_names: dict[str, set[str]] = defaultdict(set)
    for entry in surface:
        exported_by_path[entry.defining_path].add(entry.name)
        exported_symbol_names[entry.defining_path].add(entry.defining_name)

    diagnostics: list[str] = []
    if not in_degree:
        diagnostics.append("absent_input:symbol_in_degree (top_symbols ranked by export flag and name)")

    cards: list[FileCard] = []
    for path in paths:
        path_facts = facts_by_path.get(path, [])
        if not path_facts:
            diagnostics.append(f"zero_symbol_file:{path}")

        effects: Counter[str] = Counter()
        mess_scores: list[float] = []
        for fact in path_facts:
            effects.update(fact.effects)
            if fact.mess_score is not None:
                mess_scores.append(fact.mess_score)

        exported_names = exported_by_path.get(path, set())
        local_exports = exported_symbol_names.get(path, set())
        ranked = sorted(
            path_facts,
            key=lambda f: (
                0 if _short_name(f.qualified_name) in local_exports else 1,
                -in_degree.get(f.symbol_id, 0),
                f.qualified_name,
            ),
        )
        top = tuple(
            TopSymbol(symbol_id=f.symbol_id, one_liner=f.one_liner)
            for f in ranked[:TOP_SYMBOL_LIMIT]
        )

        cards.append(
            FileCard(
                path=path,
                language=language,
                exported_names=tuple(sorted(exported_names)),
                symbol_count=len(path_facts),
                symbol_kinds=dict(sorted(Counter(f.kind for f in path_facts).items())),
                top_symbols=top,
                effects_histogram=dict(sorted(effects.items())),
                out_files=tuple(sorted(graph.successors(path))) if path in graph else (),
                in_files=tuple(sorted(graph.predecessors(path))) if path in graph else (),
                mess_p50=_median(mess_scores),
            )
        )

    if not any(card.effects_histogram for card in cards):
        diagnostics.append("absent_input:l1_effects (effects_histogram empty on every card)")
    if all(card.mess_p50 is None for card in cards):
        diagnostics.append("absent_input:l1_mess_score (mess_p50 null on every card)")

    logger.info("Built %d file cards (%d diagnostics)", len(cards), len(diagnostics))
    return tuple(cards), tuple(diagnostics)


def _short_name(qualified_name: str) -> str:
    """Last dotted component of a qualified name."""
    return qualified_name.rsplit(".", 1)[-1]


def _median(values: Sequence[float]) -> float | None:
    """Median of *values*, or ``None`` when empty."""
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def clustering_payload(cards: Sequence[FileCard]) -> list[dict[str, object]]:
    """Serialise cards for the L2 naming call.

    The whitelist is this function body.  Nothing reaches the model that is not
    a :class:`FileCard` field, so "no source code" holds structurally rather
    than by asking the caller to remember.
    """
    return [
        {
            "path": card.path,
            "language": card.language,
            "exported_names": list(card.exported_names),
            "symbol_count": card.symbol_count,
            "symbol_kinds": dict(card.symbol_kinds),
            "top_symbols": [
                {"symbol_id": s.symbol_id, "one_liner": s.one_liner}
                for s in card.top_symbols
            ],
            "effects_histogram": dict(card.effects_histogram),
            "out_files": list(card.out_files),
            "in_files": list(card.in_files),
            "mess_p50": card.mess_p50,
        }
        for card in cards
    ]
