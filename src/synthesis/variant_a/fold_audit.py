"""Visible-fold + denominator audit. Coverage must not go green by disappearing."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Mapping, Sequence

from src.synthesis.variant_a.depth import (
    ContentDepth,
    LEDGER_POINTER_PREFIX,
    ThresholdSignals,
    body_mode,
    compute_threshold_signals,
)
from src.synthesis.variant_a.surface import PublicSurface
from src.synthesis.variant_a.verify import load_docs

_SYMBOL_MARK = re.compile(r"<!--\s*symbol:([^\s>]+)\s*-->")


def rendered_symbol_ids(docs: Mapping[str, str]) -> dict[str, list[str]]:
    hosts: dict[str, list[str]] = {}
    for rel, text in docs.items():
        for sid in dict.fromkeys(_SYMBOL_MARK.findall(text)):
            hosts.setdefault(sid, []).append(rel)
    return hosts


def _block_for(docs: Mapping[str, str], symbol_id: str) -> str:
    mark = f"<!-- symbol:{symbol_id} -->"
    end = f"<!-- end:symbol:{symbol_id} -->"
    for text in docs.values():
        if mark not in text:
            continue
        body = text.split(mark, 1)[1]
        return body.split(end, 1)[0] if end in body else body
    return ""


def _resolve_signals(
    depth: ContentDepth,
    *,
    ir_edges: frozenset[tuple[str, str]] | None,
    surface: PublicSurface | None,
    signals: ThresholdSignals | None,
    ledger_ids: Sequence[str],
) -> ThresholdSignals | None:
    if signals is not None:
        return signals
    if depth is not ContentDepth.THRESHOLD:
        return None
    if surface is None:
        return None
    return compute_threshold_signals(
        surface=surface,
        ir_edges=ir_edges or (),
        symbol_ids=ledger_ids,
    )


def _compact_visible(block: str, symbol_id: str) -> bool:
    if f"<!-- compact:{symbol_id} -->" not in block and "<!-- compact:" not in block:
        return False
    if f"<!-- symbol:{symbol_id} -->" not in block and f"symbol:{symbol_id}" not in block:
        # _block_for already starts after the open marker; the marker itself
        # is required on the page (checked via hosts). Here we need name+range.
        pass
    has_name = "`" in block
    has_range = bool(re.search(r"`[^`]+:\d+-\d+`", block))
    has_anchor = "<a id=" in block or "](#" in block or "](" in block
    return has_name and has_range and has_anchor


def audit_fold(
    docs: Mapping[str, str],
    ledger_ids: Sequence[str],
    status_by_symbol: Mapping[str, str],
    depth: ContentDepth,
    *,
    ir_edges: frozenset[tuple[str, str]] | None = None,
    surface: PublicSurface | None = None,
    signals: ThresholdSignals | None = None,
) -> dict[str, object]:
    hosts = rendered_symbol_ids(docs)
    missing = [sid for sid in ledger_ids if sid not in hosts]
    silent: list[str] = []
    folded_ok: list[str] = []
    compact_ok: list[str] = []
    full_ids: list[str] = []
    core_ids: list[str] = []
    resolved = _resolve_signals(
        depth, ir_edges=ir_edges, surface=surface, signals=signals, ledger_ids=ledger_ids
    )
    for sid in ledger_ids:
        mode = body_mode(
            status_by_symbol.get(sid),
            depth,
            symbol_id=sid,
            signals=resolved,
        )
        if mode == "full":
            full_ids.append(sid)
            continue
        block = _block_for(docs, sid)
        if mode == "compact":
            if _compact_visible(block, sid):
                compact_ok.append(sid)
            else:
                silent.append(sid)
            continue
        pointer = f"{LEDGER_POINTER_PREFIX}`{sid}`"
        if pointer not in block:
            silent.append(sid)
        else:
            folded_ok.append(sid)
        if mode == "core":
            core_ids.append(sid)
    n = len(ledger_ids)
    return {
        "n_ledger": n,
        "n_rendered": n - len(missing),
        "missing_markers": missing,
        "silent_folds": silent,
        "n_folded_visible": len(folded_ok),
        "n_compact": len(compact_ok),
        "n_block": len(full_ids),
        "n_full": len(full_ids),
        "n_core": len(core_ids),
        "ok_denominator": not missing and n == len(set(ledger_ids)),
        "ok_visible_folds": not silent,
        "ok": not missing and not silent,
    }


def run_fold_negative_control(
    docs_root: Path,
    scratch: Path,
    ledger_ids: Sequence[str],
    status_by_symbol: Mapping[str, str],
    depth: ContentDepth,
    *,
    ir_edges: frozenset[tuple[str, str]] | None = None,
    surface: PublicSurface | None = None,
    signals: ThresholdSignals | None = None,
) -> dict[str, object]:
    """Strip one visible pointer or compact row; the audit must go red."""

    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(docs_root, scratch, ignore=shutil.ignore_patterns("synthesis_ledger.json"))
    docs = load_docs(scratch)
    extra = {"ir_edges": ir_edges, "surface": surface, "signals": signals}
    baseline = audit_fold(docs, ledger_ids, status_by_symbol, depth, **extra)
    if not baseline["ok"]:
        return {
            "ran": False,
            "ok_flagged_red": False,
            "why": "baseline already red",
            "baseline": baseline,
        }
    resolved = _resolve_signals(
        depth, ir_edges=ir_edges, surface=surface, signals=signals, ledger_ids=ledger_ids
    )
    target = None
    target_mode = None
    for sid in ledger_ids:
        mode = body_mode(
            status_by_symbol.get(sid), depth, symbol_id=sid, signals=resolved
        )
        if mode in {"folded", "compact"}:
            target = sid
            target_mode = mode
            break
    if target is None:
        return {"ran": False, "ok_flagged_red": False, "why": "no folded/compact symbol to mutate"}
    if target_mode == "compact":
        needle = f"<!-- compact:{target} -->"
        replacement = "（已删除紧凑索引行）"
    else:
        needle = f"{LEDGER_POINTER_PREFIX}`{target}`"
        replacement = "（已删除台账指针）"
    mutated_file = None
    for rel, text in list(docs.items()):
        if needle not in text:
            continue
        path = scratch / rel
        path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
        mutated_file = rel
        break
    if mutated_file is None:
        return {"ran": False, "ok_flagged_red": False, "why": "pointer text not found"}
    after = audit_fold(load_docs(scratch), ledger_ids, status_by_symbol, depth, **extra)
    return {
        "ran": True,
        "mutated_symbol": target,
        "mutated_file": mutated_file,
        "ok_flagged_red": (not after["ok"]) and target in after["silent_folds"],
        "after_silent_folds": after["silent_folds"][:5],
    }
