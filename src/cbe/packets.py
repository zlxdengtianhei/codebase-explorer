"""First-round non-overlapping source packets.

Each enrolled character belongs to exactly one first-round packet. Nested
class/method structural spans are allowed; exclusive text is not repeated.

Packing finishes first. Fragment identity is then assigned per symbol per
packet from exclusive spans intersected with the packed intervals.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from cbe.ir import CharSpan, OffsetMap, Symbol, sha256_bytes, sha256_text
from cbe.inventory import Inventory, load_offsets

DEFAULT_PACKET_WINDOW_CHARS = 24_000


class PacketSourceError(RuntimeError):
    """Frozen source is unreadable, undecodable, or no longer matches the inventory hash."""


class DuplicateIdentityError(RuntimeError):
    """Packet, task, or fragment identity collided before list→dict."""


def unique_by_id(items: Iterable[Any], *, id_of: Callable[[Any], str], kind: str) -> dict[str, Any]:
    """Index items by identity. Duplicate or empty IDs fail closed before dict overwrite."""

    result: dict[str, Any] = {}
    for item in items:
        key = id_of(item)
        if not key:
            raise DuplicateIdentityError(f"empty {kind} id")
        if key in result:
            raise DuplicateIdentityError(f"duplicate {kind} id: {key}")
        result[key] = item
    return result


def merge_char_spans(spans: Sequence[CharSpan]) -> tuple[CharSpan, ...]:
    ordered = sorted((span for span in spans if span.length > 0), key=lambda item: (item.start, item.end))
    merged: list[CharSpan] = []
    for span in ordered:
        if merged and span.start <= merged[-1].end:
            merged[-1] = CharSpan(merged[-1].start, max(merged[-1].end, span.end))
        else:
            merged.append(span)
    return tuple(merged)


def intersect_span_sets(left: Sequence[CharSpan], right: Sequence[CharSpan]) -> tuple[CharSpan, ...]:
    pieces: list[CharSpan] = []
    for first in left:
        for second in right:
            start = max(first.start, second.start)
            end = min(first.end, second.end)
            if end > start:
                pieces.append(CharSpan(start, end))
    return merge_char_spans(pieces)


def packet_identity_id(
    path: str,
    spans: Sequence[CharSpan],
    content_hash: str,
    *,
    raw: bool = False,
) -> str:
    payload = {
        "path": path,
        "spans": [[span.start, span.end] for span in spans],
        "content_hash": content_hash,
    }
    digest = sha256_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    kind = "raw" if raw else "pkt"
    return f"{path}::{kind}::{digest}"


def fragment_identity_hash(symbol_id: str, packet_id: str, owned: Sequence[CharSpan]) -> str:
    payload = {
        "symbol_id": symbol_id,
        "packet_id": packet_id,
        "owned_spans": [[span.start, span.end] for span in owned],
    }
    return sha256_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


@dataclass(frozen=True)
class FragmentRef:
    """Per-symbol identity inside one packed packet. Does not copy source text."""

    fragment_id: str
    symbol_id: str
    packet_id: str
    owned_spans: tuple[CharSpan, ...]
    fragment_index: int
    fragment_count: int
    identity_hash: str

    @property
    def writes_canonical(self) -> bool:
        return self.fragment_count == 1

    @property
    def output_id(self) -> str:
        return self.symbol_id if self.writes_canonical else self.fragment_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "symbol_id": self.symbol_id,
            "packet_id": self.packet_id,
            "owned_spans": [span.to_dict() for span in self.owned_spans],
            "fragment_index": self.fragment_index,
            "fragment_count": self.fragment_count,
            "identity_hash": self.identity_hash,
            "writes_canonical": self.writes_canonical,
            "output_id": self.output_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FragmentRef:
        owned = tuple(CharSpan.from_dict(item) for item in payload.get("owned_spans") or [])
        fragment_count = int(payload.get("fragment_count") or 1)
        packet_id = str(payload.get("packet_id") or "")
        symbol_id = str(payload.get("symbol_id") or "")
        identity = str(payload.get("identity_hash") or "")
        if not identity:
            identity = fragment_identity_hash(symbol_id, packet_id, owned)
        fragment_id = str(payload.get("fragment_id") or "")
        if not fragment_id:
            fragment_id = symbol_id if fragment_count == 1 else f"{symbol_id}::frag::{identity}"
        return cls(
            fragment_id=fragment_id,
            symbol_id=symbol_id,
            packet_id=packet_id,
            owned_spans=owned,
            fragment_index=int(payload.get("fragment_index") or 0),
            fragment_count=fragment_count,
            identity_hash=identity,
        )


def retarget_fragment(fragment: FragmentRef, packet_id: str) -> FragmentRef:
    """Rebind a rebuilt fragment onto a persisted packet identity."""

    identity = fragment_identity_hash(fragment.symbol_id, packet_id, fragment.owned_spans)
    fragment_id = (
        fragment.symbol_id
        if fragment.fragment_count == 1
        else f"{fragment.symbol_id}::frag::{identity}"
    )
    return FragmentRef(
        fragment_id=fragment_id,
        symbol_id=fragment.symbol_id,
        packet_id=packet_id,
        owned_spans=fragment.owned_spans,
        fragment_index=fragment.fragment_index,
        fragment_count=fragment.fragment_count,
        identity_hash=identity,
    )


def is_fragment_output_id(ident: str) -> bool:
    return "::frag::" in ident or "::slice::" in ident


@dataclass
class Packet:
    packet_id: str
    path: str
    language: str
    spans: tuple[CharSpan, ...]
    symbol_ids: tuple[str, ...]
    parent_symbol_id: str | None
    slice_index: int
    slice_count: int
    content_hash: str
    source_chars: int
    first_round: bool = True
    fragments: tuple[FragmentRef, ...] = ()

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "path": self.path,
            "language": self.language,
            "spans": [span.to_dict() for span in self.spans],
            "symbol_ids": list(self.symbol_ids),
            "parent_symbol_id": self.parent_symbol_id,
            "slice_index": self.slice_index,
            "slice_count": self.slice_count,
            "content_hash": self.content_hash,
            "source_chars": self.source_chars,
            "first_round": self.first_round,
            "fragments": [item.to_dict() for item in self.fragments],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> Packet:
        fragments = tuple(FragmentRef.from_dict(item) for item in payload.get("fragments") or ())
        return cls(
            packet_id=str(payload["packet_id"]),
            path=str(payload["path"]),
            language=str(payload["language"]),
            spans=tuple(CharSpan.from_dict(item) for item in payload["spans"]),
            symbol_ids=tuple(payload.get("symbol_ids") or ()),
            parent_symbol_id=payload.get("parent_symbol_id"),
            slice_index=int(payload.get("slice_index", 0)),
            slice_count=int(payload.get("slice_count", 1)),
            content_hash=str(payload["content_hash"]),
            source_chars=int(payload["source_chars"]),
            first_round=bool(payload.get("first_round", True)),
            fragments=fragments,
        )


@dataclass
class PacketIndex:
    window_chars: int
    packets: list[Packet] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "window_chars": self.window_chars,
            "packets": [packet.to_dict() for packet in self.packets],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> PacketIndex:
        return cls(
            window_chars=int(payload.get("window_chars", DEFAULT_PACKET_WINDOW_CHARS)),
            packets=[Packet.from_dict(item) for item in payload.get("packets", [])],
        )


def load_frozen_offsets(repo: Path, path: str, record) -> OffsetMap:
    """Read enrolled bytes and refuse empty-source masquerade on failure or hash drift."""

    expected_hash = getattr(record, "content_hash", None)
    if expected_hash is None and isinstance(record, dict):
        expected_hash = record.get("content_hash")
    expected_chars = getattr(record, "char_length", None)
    if expected_chars is None and isinstance(record, dict):
        expected_chars = record.get("char_length")
    try:
        offsets = load_offsets(repo, path)
    except OSError as exc:
        raise PacketSourceError(f"source unreadable {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise PacketSourceError(f"source decode conflict {path}: {exc}") from exc
    digest = sha256_bytes(offsets.raw)
    if expected_hash and digest != expected_hash:
        raise PacketSourceError(
            f"source hash conflict {path}: frozen={expected_hash} current={digest}"
        )
    if expected_chars is not None and len(offsets.text) != int(expected_chars):
        raise PacketSourceError(
            f"source length conflict {path}: frozen_chars={expected_chars} current={len(offsets.text)}"
        )
    return offsets


def _interval_units(symbols: list[Symbol], text_len: int) -> list[tuple[CharSpan, tuple[str, ...], str | None]]:
    """File-order exclusive intervals tagged with the symbols they belong to."""

    units: list[tuple[CharSpan, tuple[str, ...], str | None]] = []
    for symbol in sorted(symbols, key=lambda item: (item.span.start, -item.span.end, item.id)):
        parent = symbol.id if symbol.kind in {"function", "method", "class", "lambda"} else symbol.parent_id
        for span in symbol.exclusive_spans:
            if span.length <= 0:
                continue
            units.append((span, (symbol.id,), parent if symbol.kind != "module_residual" else None))
    units.sort(key=lambda item: (item[0].start, item[0].end))
    return units


def _split_oversize(span: CharSpan, window: int) -> list[CharSpan]:
    if span.length <= window:
        return [span]
    parts: list[CharSpan] = []
    cursor = span.start
    while cursor < span.end:
        nxt = min(span.end, cursor + window)
        parts.append(CharSpan(cursor, nxt))
        cursor = nxt
    return parts


def _unique_parent(parents: set[str]) -> str | None:
    """Only a single parent is recorded. Mixed packets must not fake one parent."""

    parents = {item for item in parents if item}
    if len(parents) == 1:
        return next(iter(parents))
    return None


def _number_file_packets(packets: list[Packet], path: str) -> None:
    file_packets = [packet for packet in packets if packet.path == path]
    count = len(file_packets)
    for index, packet in enumerate(file_packets):
        packet.slice_index = index
        packet.slice_count = count


def attach_fragments(packets: list[Packet], symbols: Sequence[Symbol]) -> None:
    """Second pass: unique fragment identity from packed intervals ∩ exclusive spans."""

    by_path: dict[str, list[Packet]] = defaultdict(list)
    for packet in packets:
        by_path[packet.path].append(packet)
    symbols_by_path: dict[str, list[Symbol]] = defaultdict(list)
    for symbol in symbols:
        symbols_by_path[symbol.path].append(symbol)
    fragment_ids: list[str] = []
    for path, file_packets in by_path.items():
        planned: dict[str, list[tuple[Packet, tuple[CharSpan, ...]]]] = {}
        for symbol in symbols_by_path.get(path, []):
            hits: list[tuple[Packet, tuple[CharSpan, ...]]] = []
            for packet in file_packets:
                owned = intersect_span_sets(symbol.exclusive_spans, packet.spans)
                if owned:
                    hits.append((packet, owned))
            if not hits:
                continue
            hits.sort(
                key=lambda item: (
                    item[1][0].start,
                    item[1][0].end,
                    item[0].packet_id,
                )
            )
            planned[symbol.id] = hits
        assigned: dict[str, list[FragmentRef]] = {packet.packet_id: [] for packet in file_packets}
        for symbol_id, hits in planned.items():
            count = len(hits)
            for index, (packet, owned) in enumerate(hits):
                identity = fragment_identity_hash(symbol_id, packet.packet_id, owned)
                fragment_id = symbol_id if count == 1 else f"{symbol_id}::frag::{identity}"
                assigned[packet.packet_id].append(
                    FragmentRef(
                        fragment_id=fragment_id,
                        symbol_id=symbol_id,
                        packet_id=packet.packet_id,
                        owned_spans=owned,
                        fragment_index=index,
                        fragment_count=count,
                        identity_hash=identity,
                    )
                )
        for packet in file_packets:
            items = assigned[packet.packet_id]
            items.sort(
                key=lambda fragment: (
                    fragment.owned_spans[0].start if fragment.owned_spans else 0,
                    fragment.symbol_id,
                )
            )
            packet.fragments = tuple(items)
            fragment_ids.extend(item.fragment_id for item in items)
    unique_by_id(fragment_ids, id_of=lambda item: item, kind="fragment")


def pack_inventory(
    inventory: Inventory,
    *,
    repo: Path,
    window_chars: int = DEFAULT_PACKET_WINDOW_CHARS,
    window_chars_by_path: dict[str, int] | None = None,
) -> PacketIndex:
    packets: list[Packet] = []
    symbols_by_path: dict[str, list[Symbol]] = defaultdict(list)
    for symbol in inventory.symbols.values():
        symbols_by_path[symbol.path].append(symbol)
    for path, record in sorted(inventory.files.items()):
        if not record.enrolled:
            continue
        file_window = (window_chars_by_path or {}).get(path, window_chars)
        if file_window <= 0:
            raise ValueError(f"packet window must be positive: {path}")
        packet_start = len(packets)
        offsets = load_frozen_offsets(repo, path, record)
        file_symbols = symbols_by_path.get(path, [])
        if record.parse_failure is not None:
            span = CharSpan(0, record.char_length)
            slices = _split_oversize(span, file_window)
            text = offsets.text
            for piece in slices:
                body = text[piece.start:piece.end]
                if piece.length and not body:
                    raise PacketSourceError(
                        f"empty source slice for parse-failure file {path} at {piece.start}:{piece.end}"
                    )
                content_hash = sha256_bytes(body.encode("utf-8"))
                packets.append(
                    Packet(
                        packet_id=packet_identity_id(path, (piece,), content_hash, raw=True),
                        path=path,
                        language=record.language,
                        spans=(piece,),
                        symbol_ids=(),
                        parent_symbol_id=None,
                        slice_index=0,
                        slice_count=1,
                        content_hash=content_hash,
                        source_chars=piece.length,
                    )
                )
            _number_file_packets(packets[packet_start:], path)
            _assert_partition(path, packets[packet_start:], offsets)
            continue
        units = _interval_units(file_symbols, record.char_length)
        covered = 0
        current_spans: list[CharSpan] = []
        current_symbols: list[str] = []
        current_parents: set[str] = set()
        current_chars = 0

        def flush() -> None:
            nonlocal current_spans, current_symbols, current_parents, current_chars
            if not current_spans:
                return
            text = "".join(offsets.text[span.start:span.end] for span in current_spans)
            content_hash = sha256_bytes(text.encode("utf-8"))
            span_tuple = tuple(current_spans)
            packets.append(
                Packet(
                    packet_id=packet_identity_id(path, span_tuple, content_hash),
                    path=path,
                    language=record.language,
                    spans=span_tuple,
                    symbol_ids=tuple(dict.fromkeys(current_symbols)),
                    parent_symbol_id=_unique_parent(current_parents),
                    slice_index=0,
                    slice_count=1,
                    content_hash=content_hash,
                    source_chars=sum(span.length for span in current_spans),
                )
            )
            current_spans = []
            current_symbols = []
            current_parents = set()
            current_chars = 0

        for span, symbol_ids, parent in units:
            pieces = _split_oversize(span, file_window)
            if len(pieces) > 1:
                flush()
                text = offsets.text
                parent_id = symbol_ids[0] if symbol_ids else parent
                for piece in pieces:
                    body = text[piece.start:piece.end]
                    if piece.length and not body:
                        raise PacketSourceError(
                            f"empty source slice for {path} at {piece.start}:{piece.end}"
                        )
                    content_hash = sha256_bytes(body.encode("utf-8"))
                    packets.append(
                        Packet(
                            packet_id=packet_identity_id(path, (piece,), content_hash),
                            path=path,
                            language=record.language,
                            spans=(piece,),
                            symbol_ids=symbol_ids,
                            parent_symbol_id=parent_id,
                            slice_index=0,
                            slice_count=1,
                            content_hash=content_hash,
                            source_chars=piece.length,
                        )
                    )
                covered += span.length
                continue
            if current_spans and current_chars + span.length > file_window:
                flush()
            if not current_spans:
                current_parents = set()
            if parent:
                current_parents.add(parent)
            current_spans.append(span)
            current_symbols.extend(symbol_ids)
            current_chars += span.length
            covered += span.length
        flush()
        _number_file_packets(packets[packet_start:], path)
        _assert_partition(path, packets[packet_start:], offsets)
    attach_fragments(packets, list(inventory.symbols.values()))
    unique_by_id(packets, id_of=lambda packet: packet.packet_id, kind="packet")
    validate_packed_fragments(packets, inventory)
    return PacketIndex(window_chars=window_chars, packets=packets)


def validate_packed_fragments(packets: Sequence[Packet], inventory: Inventory) -> None:
    """Structural fragment checks on a packed plan (not persisted consumption)."""

    unique_by_id(packets, id_of=lambda packet: packet.packet_id, kind="packet")
    fragment_ids: list[str] = []
    owned_by_symbol: dict[str, list[CharSpan]] = defaultdict(list)
    counts: dict[str, int] = {}
    actual_counts: dict[str, int] = defaultdict(int)
    for packet in packets:
        seen_symbols: set[str] = set()
        for fragment in packet.fragments:
            if fragment.packet_id != packet.packet_id:
                raise DuplicateIdentityError(
                    f"fragment {fragment.fragment_id} packet_id {fragment.packet_id} "
                    f"!= packet {packet.packet_id}"
                )
            if fragment.symbol_id in seen_symbols:
                raise DuplicateIdentityError(
                    f"duplicate symbol {fragment.symbol_id} fragments in packet {packet.packet_id}"
                )
            seen_symbols.add(fragment.symbol_id)
            fragment_ids.append(fragment.fragment_id)
            owned_by_symbol[fragment.symbol_id].extend(fragment.owned_spans)
            actual_counts[fragment.symbol_id] += 1
            previous = counts.get(fragment.symbol_id)
            if previous is None:
                counts[fragment.symbol_id] = fragment.fragment_count
            elif previous != fragment.fragment_count:
                raise DuplicateIdentityError(
                    f"inconsistent fragment_count for {fragment.symbol_id}"
                )
            for owned in fragment.owned_spans:
                if not any(
                    packet_span.start <= owned.start and owned.end <= packet_span.end
                    for packet_span in packet.spans
                ):
                    raise RuntimeError(
                        f"fragment {fragment.fragment_id} owned span "
                        f"{owned.start}:{owned.end} outside packet {packet.packet_id}"
                    )
    unique_by_id(fragment_ids, id_of=lambda item: item, kind="fragment")
    for symbol_id, owned in owned_by_symbol.items():
        symbol = inventory.symbols.get(symbol_id)
        if symbol is None:
            continue
        if merge_char_spans(owned) != merge_char_spans(symbol.exclusive_spans):
            raise RuntimeError(
                f"fragment owned union != exclusive spans for {symbol_id}"
            )
        expected = counts.get(symbol_id) or 0
        actual = actual_counts[symbol_id]
        if expected and actual != expected:
            raise DuplicateIdentityError(
                f"symbol {symbol_id} expected {expected} fragments, packed {actual}"
            )


def _assert_partition(path: str, packets: list[Packet], offsets: OffsetMap) -> None:
    owned = [0] * len(offsets.text)
    for packet in packets:
        if packet.path != path or not packet.first_round:
            continue
        for span in packet.spans:
            for index in range(span.start, span.end):
                if owned[index]:
                    raise RuntimeError(f"overlapping first-round packet at {path}:{index}")
                owned[index] = 1
    missing = [index for index, flag in enumerate(owned) if flag == 0]
    if missing:
        raise RuntimeError(f"first-round packets miss {len(missing)} chars in {path}")


def packet_source(offsets: OffsetMap, packet: Packet) -> str:
    body = "".join(offsets.text[span.start:span.end] for span in packet.spans)
    if packet.source_chars and not body:
        raise PacketSourceError(
            f"packet {packet.packet_id} has source_chars={packet.source_chars} but loaded empty text"
        )
    return body


def source_for_fragment_ids(
    offsets: OffsetMap,
    packet: Packet,
    fragment_ids: Sequence[str],
) -> tuple[str, list[dict[str, Any]], str]:
    """Owned spans of the missing fragments on this packet only. Never the full parent."""

    wanted = [item for item in fragment_ids if item]
    if not wanted:
        return "", [], "no missing fragments on this packet"
    found: set[str] = set()
    spans: list[CharSpan] = []
    for fragment in packet.fragments:
        keys = {fragment.output_id, fragment.fragment_id, fragment.identity_hash}
        if fragment.writes_canonical:
            keys.add(fragment.symbol_id)
        if any(item in keys for item in wanted):
            spans.extend(fragment.owned_spans)
            found.update(keys)
    missing = [item for item in wanted if item not in found]
    if missing:
        raise PacketSourceError(
            f"repair fragment ids not owned by packet {packet.packet_id}: {missing}"
        )
    merged = merge_char_spans(spans)
    body = "".join(offsets.text[span.start:span.end] for span in merged)
    out_spans = [{"path": packet.path, "start": span.start, "end": span.end} for span in merged]
    basis = "owned spans of missing fragments on the current packet only"
    return body, out_spans, basis


def source_for_symbol_ids(
    offsets: OffsetMap,
    symbols: dict[str, dict[str, Any]],
    symbol_ids: list[str],
    packet: Packet | None = None,
) -> tuple[str, list[dict[str, Any]], str]:
    """Exclusive spans for the remaining symbols only. Does not re-pack the whole packet."""
    spans: list[tuple[int, int]] = []
    missing: list[str] = []
    for symbol_id in symbol_ids:
        record = symbols.get(symbol_id) or {}
        exclusive = record.get("exclusive_spans") or []
        used = []
        for item in exclusive:
            if isinstance(item, dict) and "start" in item and "end" in item:
                used.append((int(item["start"]), int(item["end"])))
        if not used:
            span = record.get("span") or {}
            if isinstance(span, dict) and "start" in span and "end" in span:
                used.append((int(span["start"]), int(span["end"])))
        if not used:
            missing.append(symbol_id)
            continue
        spans.extend(used)
    if missing and packet is not None:
        body = packet_source(offsets, packet)
        basis = (
            "exclusive spans missing for "
            + ",".join(missing)
            + "; used packet interval because remaining symbols cannot be isolated"
        )
        packet_spans = [{"path": packet.path, **span.to_dict()} for span in packet.spans]
        return body, packet_spans, basis
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    body = "".join(offsets.text[start:end] for start, end in merged)
    path = packet.path if packet is not None else ""
    out_spans = [{"path": path, "start": start, "end": end} for start, end in merged]
    kinds = [str((symbols.get(sid) or {}).get("kind") or "") for sid in symbol_ids]
    basis = "exclusive spans of remaining symbols only"
    if any(kind == "module_residual" for kind in kinds):
        basis += "; module_residual exclusive span included because that symbol is still remaining"
    return body, out_spans, basis


def write_packet_file(run_dir: Path, packet: Packet, source: str, extra: dict | None = None) -> Path:
    payload = packet.to_dict()
    payload["source"] = source
    if extra:
        payload["extra"] = extra
    encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    digest = sha256_bytes(encoded)
    target = run_dir / "packets" / f"{digest}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(encoded)
    return target


def span_key(packet: Packet) -> tuple[str, tuple[tuple[int, int], ...]]:
    return (packet.path, tuple((span.start, span.end) for span in packet.spans))
