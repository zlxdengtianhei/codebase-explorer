"""Layered content depth: how much of a symbol's ledger prose is shown.

The ledger and the symbol denominator do not change. This module only
decides the *default* projection:

* ``full`` — today's behaviour, every symbol keeps its full explanation
* ``layered`` — ``entry`` / ``public_api`` stay full; ``core`` keeps a
  short extract; everything else is one_liner + a visible ledger pointer
* ``public_only`` — only ``entry`` / ``public_api`` stay full
* ``threshold`` — a symbol gets a block only if a deterministic signal
  fires (``is_exported`` ∨ ``in_degree ≥ 2`` ∨ ``hops_from_surface ≤ 1``
  ∨ ``StatusLabel ∈ {entry, public_api, core}``). Everyone else is one
  compact index row (name + anchor + line range, no explanation).

Folding is progressive disclosure (EV-19), not a coverage cut. A folded
or compact symbol must still appear as ``<!-- symbol:ID -->``. Compact
rows must stay visible on the page; they must not vanish.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping

from src.graph.file_cards import ONE_LINER_MAX_CHARS, derive_one_liner
from src.semantic.l2_status import STATUS_VALUES
from src.synthesis.variant_a.surface import PublicSurface

FULL_STATUSES = frozenset({"entry", "public_api"})
CORE_STATUSES = frozenset({"core"})
FOLD_STATUSES = frozenset({"adapter", "data", "glue", "error_path"})
BLOCK_STATUSES = frozenset({"entry", "public_api", "core"})

LEDGER_POINTER_PREFIX = "完整解释见台账 "
COMPACT_MARK_PREFIX = "<!-- compact:"
_SENTENCE_END = re.compile(r"(?<=[。！？])|(?<=[.!?])(?=\s)")
_FAIL_MARK = re.compile(
    r"失败|异常|抛出|抛 |raise |RuntimeError|TypeError|ValueError|"
    r"NotImplementedError|KeyError|非法|校验"
)
_IO_MARK = re.compile(r"输入|输出|接收|返回|参数|kwargs|returns|return ")


class ContentDepth(StrEnum):
    FULL = "full"
    LAYERED = "layered"
    PUBLIC_ONLY = "public_only"
    THRESHOLD = "threshold"


@dataclass(frozen=True)
class ThresholdSignals:
    """Deterministic per-symbol facts used by the ``threshold`` depth.

    ``hops_from_surface`` is a BFS on the symbol IR from exported seeds.
    File-level hops on same-file probe edges collapse to hop-0 for every
    file that contains an export, which would force 100% blocks.
    """

    exported: frozenset[str]
    in_degree: Mapping[str, int]
    hops_from_surface: Mapping[str, int]


def exported_symbol_ids(surface: PublicSurface) -> frozenset[str]:
    ids: set[str] = set()
    for item in surface.bindings:
        ids.update(item.resolved_symbol_ids)
    return frozenset(ids)


def compute_threshold_signals(
    *,
    exported: Iterable[str] | None = None,
    ir_edges: Iterable[tuple[str, str]] = (),
    symbol_ids: Iterable[str] = (),
    surface: PublicSurface | None = None,
) -> ThresholdSignals:
    seeds = frozenset(exported) if exported is not None else (
        exported_symbol_ids(surface) if surface is not None else frozenset()
    )
    wanted = set(symbol_ids) if symbol_ids else set(seeds)
    for src, dst in ir_edges:
        wanted.add(src)
        wanted.add(dst)
    indeg: dict[str, int] = defaultdict(int)
    adj: dict[str, list[str]] = defaultdict(list)
    for src, dst in ir_edges:
        if dst in wanted:
            indeg[dst] += 1
        if src in wanted and dst in wanted:
            adj[src].append(dst)
    hops: dict[str, int] = {}
    queue: deque[str] = deque()
    for sid in seeds:
        if sid not in wanted:
            continue
        hops[sid] = 0
        queue.append(sid)
    while queue:
        cur = queue.popleft()
        for nxt in adj.get(cur, ()):
            if nxt in hops:
                continue
            hops[nxt] = hops[cur] + 1
            queue.append(nxt)
    return ThresholdSignals(
        exported=seeds,
        in_degree=dict(indeg),
        hops_from_surface=hops,
    )


def qualifies_for_block(
    symbol_id: str,
    status: str | None,
    *,
    exported: Iterable[str] | None = None,
    in_degree: Mapping[str, int] | None = None,
    hops: Mapping[str, int] | None = None,
    signals: ThresholdSignals | None = None,
) -> bool:
    """True when the symbol should get a heading block under ``threshold``."""

    if signals is not None:
        exported = signals.exported
        in_degree = signals.in_degree
        hops = signals.hops_from_surface
    exp = set(exported or ())
    deg = (in_degree or {}).get(symbol_id, 0)
    hop = (hops or {}).get(symbol_id)
    if symbol_id in exp:
        return True
    if deg >= 2:
        return True
    if hop is not None and hop <= 1:
        return True
    if status in BLOCK_STATUSES:
        return True
    return False


class DepthError(ValueError):
    """Raised when a depth render is given unusable status input."""


def parse_depth(value: str) -> ContentDepth:
    try:
        return ContentDepth(value)
    except ValueError as exc:
        raise DepthError(
            f"depth must be one of {[item.value for item in ContentDepth]}, got {value!r}"
        ) from exc


def load_status_map(path: Path) -> dict[str, str]:
    """Accept l2_result JSON (``status_labels``) or a ``{id: status}`` map."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("status_labels"), list):
        rows = payload["status_labels"]
    elif isinstance(payload, dict) and isinstance(payload.get("labels"), list):
        rows = payload["labels"]
    elif isinstance(payload, dict) and all(isinstance(v, str) for v in payload.values()):
        rows = [{"symbol_id": k, "status": v} for k, v in payload.items()]
    else:
        raise DepthError(f"{path} has no status_labels / labels / id→status map")
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = row.get("symbol_id")
        status = str(row.get("status", "")).strip().lower()
        if not isinstance(sid, str) or not sid:
            continue
        if status not in STATUS_VALUES:
            continue
        out[sid] = status
    if not out:
        raise DepthError(f"{path} produced an empty status map")
    return out


def body_mode(
    status: str | None,
    depth: ContentDepth,
    *,
    symbol_id: str | None = None,
    signals: ThresholdSignals | None = None,
) -> str:
    """Return ``full``, ``core``, ``folded``, or ``compact``."""

    if depth is ContentDepth.THRESHOLD:
        if symbol_id and signals is not None and qualifies_for_block(
            symbol_id, status, signals=signals
        ):
            return "full"
        return "compact"
    if depth is ContentDepth.FULL:
        return "full"
    if status in FULL_STATUSES:
        return "full"
    if depth is ContentDepth.PUBLIC_ONLY:
        return "folded"
    if status in CORE_STATUSES or status is None:
        # Unlabelled: keep the richer core extract rather than vanish.
        return "core"
    return "folded"


def split_sentences(text: str) -> list[str]:
    stripped = " ".join(text.split())
    if not stripped:
        return []
    parts = [part.strip() for part in _SENTENCE_END.split(stripped) if part and part.strip()]
    return parts or [stripped]


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def extract_core_fields(text: str) -> tuple[str, str, str]:
    """Deterministic (one_liner, failure, io) cut from the ledger behaviour."""

    one = derive_one_liner(text, max_chars=ONE_LINER_MAX_CHARS)
    sentences = split_sentences(text)
    fail_bits = [s for s in sentences if _FAIL_MARK.search(s) and s != one]
    io_bits = [s for s in sentences if _IO_MARK.search(s) and s not in fail_bits]
    preferred_io = [s for s in io_bits if s != one] or io_bits
    fail = _clip(" ".join(fail_bits[:2]), 220)
    io = _clip(" ".join(preferred_io[:2]), 220)
    return one, fail, io


def ledger_pointer(symbol_id: str) -> str:
    return f"{LEDGER_POINTER_PREFIX}`{symbol_id}`"


def render_symbol_prose(
    *,
    symbol_id: str,
    text: str,
    mode: str,
    status: str | None,
) -> list[str]:
    """Body lines under the symbol heading. Never drops the symbol itself."""

    label = status if status in STATUS_VALUES else None
    status_bit = f"`{label}`" if label else "地位未标注"
    if mode == "full":
        lines = [f"- 地位：{status_bit} · 展开：`{mode}`"]
        if text:
            lines.extend(["", text])
        return lines
    one, fail, io = extract_core_fields(text)
    lines = [f"- 地位：{status_bit} · 展开：`{mode}`"]
    if one:
        lines.append(one)
    if mode == "core":
        lines.append(f"- 关键失败条件：{fail or '（台账未单独列出）'}")
        lines.append(f"- 输入输出：{io or '（台账未单独列出）'}")
    lines.append(f"<!-- folded:{symbol_id} -->")
    lines.append(ledger_pointer(symbol_id))
    return lines


def count_modes(
    symbol_ids: list[str],
    status_by_symbol: Mapping[str, str],
    depth: ContentDepth,
    *,
    signals: ThresholdSignals | None = None,
) -> dict[str, int]:
    counts = {"full": 0, "core": 0, "folded": 0, "compact": 0, "unlabelled": 0}
    for sid in symbol_ids:
        status = status_by_symbol.get(sid)
        if status is None:
            counts["unlabelled"] += 1
        counts[body_mode(status, depth, symbol_id=sid, signals=signals)] += 1
    return counts
