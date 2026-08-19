"""Qualified dependency scheduling with recoverable SCC leases and packets."""

from __future__ import annotations

import ast
import fcntl
import json
import math
import os
import tempfile
import uuid
import hashlib
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Self

import networkx as nx

from src.budget.estimator import estimate_tokens_from_chars
from src.graph.ordering import (
    DependencyFirstSCCPlan,
    DependencySCC,
    compute_pagerank,
    dependency_first_scc_layers,
)
from src.ir import Relation, ResolutionStatus
from src.semantic.inventory import (
    SemanticInventory,
    enumerate_semantic_inventory,
    load_file_out_edge_revisions,
    reconcile_semantic_ledger,
)
from src.semantic.models import (
    LEDGER_SCHEMA,
    PENDING_EXPLANATION_REASON,
    SemanticLedger,
    SemanticSymbolRecord,
    revalidate_semantic_ledger,
    canonical_json_bytes,
    hash_bytes,
)
from src.semantic.store import SemanticLedgerStore


SCHEDULER_STATE_RELPATH = Path(".codebase-analysis/semantic_scheduler_state.json")
SCHEDULER_STATE_SCHEMA = "cbe-semantic-scheduler-state/2"
DEFAULT_RESPONSE_RESERVE_TOKENS = 512


class SemanticSchedulerError(RuntimeError):
    """Raised when persistent scheduler state cannot be trusted."""


@dataclass(frozen=True)
class ReadySemanticSCC:
    scc_id: str
    members: tuple[str, ...]
    cycle_members: tuple[str, ...]
    stale_present: bool
    runtime_covered_lines: int
    pagerank: float


@dataclass(frozen=True)
class SemanticPacketSymbol:
    symbol_id: str
    path: str
    kind: str
    span: tuple[int, int]
    source_body: str
    content_hash: str
    callee_ids: tuple[str, ...]
    callee_explanations: tuple[tuple[str, str], ...]
    cycle_peer_ids: tuple[str, ...]
    dynamic_call_diagnostics: tuple[str, ...]
    module_id: str | None
    source_tokens: int
    dependency_tokens: int


@dataclass(frozen=True)
class PacketTokenEstimate:
    usable_tokens: int
    source_tokens: int
    dependency_tokens: int
    response_reserve_tokens: int
    estimated_total_tokens: int


@dataclass(frozen=True)
class SemanticBatchPacket:
    batch_id: str
    lease_owner: str
    lease_expires_at: datetime
    source_revision: str
    scc_id: str
    cycle_members: tuple[str, ...]
    symbols: tuple[SemanticPacketSymbol, ...]
    token_estimate: PacketTokenEstimate
    oversize: bool
    ledger_revision: int = 0
    semantic_schema: str = LEDGER_SCHEMA
    edge_snapshot_sha256: str = "sha256:" + "0" * 64
    claim_generation: int = 1
    claim_generation_id: str = "claimgen_" + "0" * 64
    packet_sha256: str = "sha256:" + "0" * 64

    @property
    def source_revision_id(self) -> str:
        """V3 name for the retained compatibility ``source_revision`` field."""

        return self.source_revision

    @property
    def claim_revision(self) -> int:
        """Ledger revision against which this packet was claimed."""

        return self.ledger_revision

    @property
    def symbol_bindings(self) -> tuple[dict[str, str], ...]:
        """Canonical packet bindings used by the generation identity."""

        return tuple(
            {
                "symbol_id": symbol.symbol_id,
                "content_hash": symbol.content_hash,
                "dependency_context_sha256": hash_bytes(
                    canonical_json_bytes(symbol.callee_explanations)
                ),
            }
            for symbol in sorted(self.symbols, key=lambda item: item.symbol_id)
        )

    @property
    def schema(self) -> str:
        return "cbe-semantic-batch/3"


def _qualified_parent(symbol_id: str) -> str | None:
    path, separator, qualified = symbol_id.partition("::")
    if not separator or "." not in qualified:
        return None
    return f"{path}::{qualified.rsplit('.', 1)[0]}"


def _probe_compatible_call_edges(inventory: SemanticInventory) -> set[tuple[str, str]]:
    """Reproduce the immutable probe's conservative same-file call edges."""

    root = Path(inventory.repo_root)
    edges: set[tuple[str, str]] = set()
    for relative in inventory.files:
        path = root / relative
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        local_to_id: dict[str, str] = {}
        stack: list[str] = []

        def index(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name)
                    local_to_id.setdefault(child.name, f"{relative}::{'.'.join(stack)}")
                    index(child)
                    stack.pop()
                else:
                    index(child)

        index(tree)

        def collect(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name)
                    caller = f"{relative}::{'.'.join(stack)}"
                    for descendant in ast.walk(child):
                        if not isinstance(descendant, ast.Call):
                            continue
                        function = descendant.func
                        name = getattr(function, "id", None) or getattr(function, "attr", None)
                        callee = local_to_id.get(name) if name else None
                        if callee and callee != caller:
                            edges.add((caller, callee))
                    collect(child)
                    stack.pop()
                else:
                    collect(child)

        collect(tree)
    return edges


def build_semantic_graph(
    inventory: SemanticInventory,
    *,
    relations: Iterable[Relation] = (),
) -> nx.DiGraph:
    """Build a fully qualified ``caller -> callee`` symbol graph."""

    graph = nx.DiGraph()
    graph.add_nodes_from(inventory.symbols)

    ir_to_semantic = {
        symbol.ir_symbol_id: symbol_id
        for symbol_id, symbol in inventory.symbols.items()
        if symbol.ir_symbol_id is not None
    }
    for relation in relations:
        typed_resolution = relation.call_resolution
        if typed_resolution is not None:
            # Python v3 call Relations deliberately leave the legacy target
            # field empty.  A semantic graph is a transient consumer, so it
            # follows only the proven repository ref and never promotes the
            # lexical/override evidence into an exact dependency.
            if (
                typed_resolution.outcome.value != "runtime_exact"
                or typed_resolution.runtime_exact_target is None
            ):
                continue
            target_id = typed_resolution.runtime_exact_target.target.ref.id
        else:
            # Keep the pre-v3 lane for legacy non-Python callers and existing
            # semantic fixtures.  The typed branch above is intentionally
            # exclusive, so a virtual/external/unresolved Python outcome can
            # never fall back to Relation.target.
            if (
                relation.kind not in {"calls", "call"}
                or relation.resolution_status is not ResolutionStatus.RESOLVED
                or relation.target is None
            ):
                continue
            target_id = relation.target.id
        caller = ir_to_semantic.get(relation.source.id)
        callee = ir_to_semantic.get(target_id)
        if caller is not None and callee is not None and caller != callee:
            graph.add_edge(caller, callee, sources=("ir_relation",))

    for caller, callee in sorted(_probe_compatible_call_edges(inventory)):
        if caller in graph and callee in graph:
            prior = tuple(graph.edges[caller, callee].get("sources", ())) if graph.has_edge(caller, callee) else ()
            graph.add_edge(caller, callee, sources=tuple(dict.fromkeys((*prior, "probe_ast"))))

    for symbol_id in inventory.symbols:
        parent = _qualified_parent(symbol_id)
        if parent in graph:
            prior = tuple(graph.edges[parent, symbol_id].get("sources", ())) if graph.has_edge(parent, symbol_id) else ()
            graph.add_edge(parent, symbol_id, sources=tuple(dict.fromkeys((*prior, "containment"))))
    return graph


def out_edges_changed(
    inventory: SemanticInventory,
    previous_out_edge_revisions: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """出边集合变了的文件。空元组 = 图投影不必为这次改动重算。"""

    prior = (
        dict(previous_out_edge_revisions)
        if previous_out_edge_revisions is not None
        else load_file_out_edge_revisions(inventory.repo_root)
    )
    if not prior:
        return tuple(sorted(inventory.file_out_edge_revisions))
    changed = [
        path
        for path, digest in sorted(inventory.file_out_edge_revisions.items())
        if prior.get(path) != digest
    ]
    return tuple(changed)


def build_semantic_graph_if_needed(
    inventory: SemanticInventory,
    *,
    relations: Iterable[Relation] = (),
    previous_graph: nx.DiGraph | None = None,
    previous_out_edge_revisions: Mapping[str, str] | None = None,
) -> tuple[nx.DiGraph, tuple[str, ...]]:
    """出边没变就复用旧图；变了才重建。返回 (图, 出边变化的 path 列表)。"""

    changed = out_edges_changed(inventory, previous_out_edge_revisions)
    if previous_graph is not None and not changed:
        return previous_graph, ()
    return build_semantic_graph(inventory, relations=relations), changed


def _is_explicit_terminal_residual(reason: str | None) -> bool:
    if reason is None:
        return False
    normalized = reason.strip().lower()
    return bool(normalized) and normalized != PENDING_EXPLANATION_REASON and not normalized.startswith(
        "stale semantic explanation"
    )


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("scheduler timestamps must be timezone-aware")
    return current.astimezone(UTC)


class SemanticScheduler:
    """Rebuild graph/frontier from source+ledger and persist only active leases."""

    def __init__(
        self,
        inventory: SemanticInventory,
        ledger: SemanticLedger,
        *,
        relations: Iterable[Relation] = (),
        store: SemanticLedgerStore | None = None,
    ) -> None:
        if inventory.repo_root != ledger.repo_root:
            raise ValueError("inventory and ledger belong to different repositories")
        if inventory.source_revision != ledger.source_revision:
            raise ValueError("inventory and ledger source revisions differ")
        if inventory.edge_snapshot_sha256 != ledger.bindings.edge_snapshot_sha256:
            raise ValueError("inventory and ledger edge snapshots differ")
        if set(inventory.symbols) != set(ledger.symbols):
            raise ValueError("inventory and ledger symbol denominators differ")
        self.inventory = inventory
        self.graph = build_semantic_graph(inventory, relations=relations)
        self.scc_plan = dependency_first_scc_layers(self.graph)
        self._component_by_id = {item.scc_id: item for item in self.scc_plan.components}
        self._pagerank = compute_pagerank(self.graph)
        self._store = store
        self.repo_root = Path(inventory.repo_root)
        self.state_path = self.repo_root / SCHEDULER_STATE_RELPATH
        self.state_lock_path = self.state_path.with_name(f"{self.state_path.name}.lock")
        self.ledger = self._with_graph_projection(ledger)

    @classmethod
    def from_inventory(
        cls,
        inventory: SemanticInventory,
        *,
        ledger: SemanticLedger | None = None,
        relations: Iterable[Relation] = (),
    ) -> Self:
        return cls(
            inventory,
            ledger or reconcile_semantic_ledger(inventory),
            relations=relations,
        )

    @classmethod
    def from_store(
        cls,
        store: SemanticLedgerStore,
        *,
        relations: Iterable[Relation] = (),
    ) -> Self:
        ledger = store.reopen()
        inventory = enumerate_semantic_inventory(store.repo_root)
        if inventory.source_revision != ledger.source_revision:
            raise SemanticSchedulerError("semantic ledger is stale; reconcile store before scheduling")
        return cls(inventory, ledger, relations=relations, store=store)

    def _with_graph_projection(self, ledger: SemanticLedger) -> SemanticLedger:
        symbols: dict[str, SemanticSymbolRecord] = {}
        for symbol_id, symbol in ledger.symbols.items():
            scc_id = self.scc_plan.component_by_node[symbol_id]
            peers = tuple(
                sorted(
                    target
                    for target in self.graph.successors(symbol_id)
                    if target != symbol_id
                    and self.scc_plan.component_by_node[target] == scc_id
                )
            )
            symbols[symbol_id] = symbol.model_copy(
                update={"scc_id": scc_id, "cycle_peer_ids": peers}
            )
        return revalidate_semantic_ledger(ledger.model_copy(update={"symbols": symbols}))

    def _terminal_scc_ids(self) -> set[str]:
        residual_by_symbol = {item.symbol_id: item.reason for item in self.ledger.residuals}
        terminal: set[str] = set()
        for component in self.scc_plan.components:
            if all(
                self.ledger.symbols[symbol_id].is_fresh
                or _is_explicit_terminal_residual(residual_by_symbol.get(symbol_id))
                for symbol_id in component.members
            ):
                terminal.add(component.scc_id)
        return terminal

    def _priority(self, component: DependencySCC) -> tuple[int, int, float, str]:
        symbols = tuple(self.ledger.symbols[symbol_id] for symbol_id in component.members)
        stale_present = any(symbol.is_explained and not symbol.is_fresh for symbol in symbols)
        runtime_heat = sum(symbol.runtime_covered_lines or 0 for symbol in symbols)
        pagerank = sum(self._pagerank.get(symbol_id, 0.0) for symbol_id in component.members)
        return (0 if stale_present else 1, -runtime_heat, -pagerank, component.scc_id)

    def ready_frontier(self) -> tuple[ReadySemanticSCC, ...]:
        """Return nonterminal SCCs whose cross-SCC callees are terminal."""

        terminal = self._terminal_scc_ids()
        ready = [
            component
            for component in self.scc_plan.components
            if component.scc_id not in terminal
            and set(component.callee_scc_ids) <= terminal
        ]
        ready.sort(key=self._priority)
        return tuple(self._frontier_item(component) for component in ready)

    def _frontier_item(self, component: DependencySCC) -> ReadySemanticSCC:
        symbols = tuple(self.ledger.symbols[symbol_id] for symbol_id in component.members)
        return ReadySemanticSCC(
            scc_id=component.scc_id,
            members=component.members,
            cycle_members=component.members if component.is_cycle else (),
            stale_present=any(symbol.is_explained and not symbol.is_fresh for symbol in symbols),
            runtime_covered_lines=sum(symbol.runtime_covered_lines or 0 for symbol in symbols),
            pagerank=sum(self._pagerank.get(symbol_id, 0.0) for symbol_id in component.members),
        )

    def full_order(self) -> tuple[str, ...]:
        """Return a deterministic all-symbol order across callee-first SCC layers."""

        ordered: list[str] = []
        for layer in self.scc_plan.layers:
            for component in sorted(layer, key=self._priority):
                ordered.extend(component.members)
        if len(ordered) != len(self.inventory.symbols) or set(ordered) != set(self.inventory.symbols):
            raise SemanticSchedulerError("SCC order does not cover the static symbol denominator")
        return tuple(ordered)

    def claim_semantic_batch(
        self,
        *,
        lease_owner: str,
        max_context_tokens: int,
        lease_seconds: int = 900,
        now: datetime | None = None,
    ) -> SemanticBatchPacket | None:
        """Lease one contiguous page from the highest-priority ready SCC."""

        if not isinstance(lease_owner, str) or not lease_owner.strip():
            raise ValueError("lease_owner must be non-empty")
        if type(max_context_tokens) is not int or max_context_tokens < 1:
            raise ValueError("max_context_tokens must be a positive integer")
        if type(lease_seconds) is not int or lease_seconds < 1:
            raise ValueError("lease_seconds must be a positive integer")
        timestamp = _utc(now)
        self._assert_store_revision_current()

        with self._state_lock():
            state = self._read_state_unlocked()
            packets = self._live_packets(state, timestamp)
            next_generation = self._next_generation(state)
            leased_symbols = {
                symbol.symbol_id
                for packet in packets.values()
                for symbol in packet.symbols
            }
            selected_component: DependencySCC | None = None
            available: tuple[str, ...] = ()
            for frontier in self.ready_frontier():
                candidates = tuple(
                    symbol_id
                    for symbol_id in frontier.members
                    if symbol_id not in leased_symbols
                    and not self.ledger.symbols[symbol_id].is_fresh
                )
                if candidates:
                    selected_component = self._component_by_id[frontier.scc_id]
                    available = candidates
                    break
            if selected_component is None:
                self._write_state_unlocked(packets, next_generation=next_generation)
                return None

            packet = self._build_packet(
                selected_component,
                available,
                lease_owner=lease_owner.strip(),
                lease_expires_at=timestamp + timedelta(seconds=lease_seconds),
                max_context_tokens=max_context_tokens,
                claim_generation=next_generation,
            )
            packets[packet.batch_id] = packet
            self._write_state_unlocked(
                packets,
                next_generation=next_generation + 1,
            )
            return packet

    def recover_batch(
        self,
        batch_id: str,
        *,
        now: datetime | None = None,
    ) -> SemanticBatchPacket | None:
        """Recover an exact unexpired packet snapshot after process reset."""

        timestamp = _utc(now)
        with self._state_lock():
            state = self._read_state_unlocked()
            packets = self._live_packets(state, timestamp)
            self._write_state_unlocked(
                packets,
                next_generation=self._next_generation(state),
            )
            return packets.get(batch_id)

    def release_batch(
        self,
        batch_id: str,
        *,
        lease_owner: str,
        claim_generation: int | None = None,
    ) -> bool:
        """Release a lease only for its owning actor."""

        with self._state_lock():
            state = self._read_state_unlocked()
            packets = self._live_packets(state, datetime.now(UTC))
            packet = packets.get(batch_id)
            if packet is None:
                self._write_state_unlocked(
                    packets,
                    next_generation=self._next_generation(state),
                )
                return False
            if packet.lease_owner != lease_owner:
                raise SemanticSchedulerError("lease owner mismatch")
            if claim_generation is not None and packet.claim_generation != claim_generation:
                raise SemanticSchedulerError("claim generation mismatch")
            del packets[batch_id]
            self._write_state_unlocked(
                packets,
                next_generation=self._next_generation(state),
            )
            return True

    def _build_packet(
        self,
        component: DependencySCC,
        available: tuple[str, ...],
        *,
        lease_owner: str,
        lease_expires_at: datetime,
        max_context_tokens: int,
        claim_generation: int,
    ) -> SemanticBatchPacket:
        usable = max(1, math.floor(max_context_tokens * 0.80) - 2_000)
        selected: list[SemanticPacketSymbol] = []
        estimated_total = 0
        for symbol_id in available:
            packet_symbol = self._packet_symbol(symbol_id, component)
            if not selected:
                dependency_budget = max(
                    0,
                    usable
                    - packet_symbol.source_tokens
                    - DEFAULT_RESPONSE_RESERVE_TOKENS,
                )
                packet_symbol = self._compress_dependency_context(
                    packet_symbol,
                    max_tokens=dependency_budget,
                )
            cost = (
                packet_symbol.source_tokens
                + packet_symbol.dependency_tokens
                + DEFAULT_RESPONSE_RESERVE_TOKENS
            )
            if selected and estimated_total + cost > usable:
                break
            selected.append(packet_symbol)
            estimated_total += cost
            if estimated_total > usable:
                break

        source_tokens = sum(symbol.source_tokens for symbol in selected)
        dependency_tokens = sum(symbol.dependency_tokens for symbol in selected)
        response_tokens = DEFAULT_RESPONSE_RESERVE_TOKENS * len(selected)
        estimate = PacketTokenEstimate(
            usable_tokens=usable,
            source_tokens=source_tokens,
            dependency_tokens=dependency_tokens,
            response_reserve_tokens=response_tokens,
            estimated_total_tokens=source_tokens + dependency_tokens + response_tokens,
        )
        edge_snapshot = self.ledger.bindings.edge_snapshot_sha256
        claim_revision = self.ledger.ledger_revision
        bindings = tuple(
            {
                "symbol_id": symbol.symbol_id,
                "content_hash": symbol.content_hash,
                "dependency_context_sha256": hash_bytes(
                    canonical_json_bytes(symbol.callee_explanations)
                ),
            }
            for symbol in sorted(selected, key=lambda item: item.symbol_id)
        )
        claim_generation_id = self._claim_generation_id(
            source_revision_id=self.ledger.source_revision,
            edge_snapshot_sha256=edge_snapshot,
            claim_revision=claim_revision,
            claim_generation=claim_generation,
            lease_owner=lease_owner,
            symbol_bindings=bindings,
        )
        batch_id = self._batch_id(
            source_revision_id=self.ledger.source_revision,
            edge_snapshot_sha256=edge_snapshot,
            claim_revision=claim_revision,
            claim_generation_id=claim_generation_id,
            lease_owner=lease_owner,
            symbol_bindings=bindings,
        )
        packet = SemanticBatchPacket(
            batch_id=batch_id,
            lease_owner=lease_owner,
            lease_expires_at=lease_expires_at,
            source_revision=self.ledger.source_revision,
            scc_id=component.scc_id,
            cycle_members=component.members if component.is_cycle else (),
            symbols=tuple(selected),
            token_estimate=estimate,
            oversize=estimate.estimated_total_tokens > usable,
            ledger_revision=claim_revision,
            semantic_schema=LEDGER_SCHEMA,
            edge_snapshot_sha256=edge_snapshot,
            claim_generation=claim_generation,
            claim_generation_id=claim_generation_id,
        )
        packet_payload = self._packet_to_json(packet)
        packet_payload["packet_sha256"] = None
        return replace(packet, packet_sha256=hash_bytes(canonical_json_bytes(packet_payload)))

    @staticmethod
    def _claim_generation_id(
        *,
        source_revision_id: str,
        edge_snapshot_sha256: str,
        claim_revision: int,
        claim_generation: int,
        lease_owner: str,
        symbol_bindings: tuple[dict[str, str], ...],
    ) -> str:
        frame = (
            "cbe-claim-generation/1\0"
            + source_revision_id
            + "\0"
            + edge_snapshot_sha256
            + "\0"
            + str(claim_revision)
            + "\0"
            + str(claim_generation)
            + "\0"
            + lease_owner
            + "\0"
        ).encode("utf-8") + canonical_json_bytes(list(symbol_bindings))
        return "claimgen_" + __import__("hashlib").sha256(frame).hexdigest()

    @staticmethod
    def _batch_id(
        *,
        source_revision_id: str,
        edge_snapshot_sha256: str,
        claim_revision: int,
        claim_generation_id: str,
        lease_owner: str,
        symbol_bindings: tuple[dict[str, str], ...],
    ) -> str:
        frame = (
            "cbe-semantic-batch/3\0"
            + source_revision_id
            + "\0"
            + edge_snapshot_sha256
            + "\0"
            + str(claim_revision)
            + "\0"
            + claim_generation_id
            + "\0"
            + lease_owner
            + "\0"
        ).encode("utf-8") + canonical_json_bytes(list(symbol_bindings))
        return "semantic_batch_" + __import__("hashlib").sha256(frame).hexdigest()

    def _packet_symbol(
        self,
        symbol_id: str,
        component: DependencySCC,
    ) -> SemanticPacketSymbol:
        symbol = self.ledger.symbols[symbol_id]
        source_body = self._source_body(symbol)
        callee_ids = tuple(
            sorted(
                target
                for target in self.graph.successors(symbol_id)
                if self.scc_plan.component_by_node[target] != component.scc_id
            )
        )
        callee_explanations = tuple(
            (callee, explanation.text)
            for callee in callee_ids
            if (explanation := self.ledger.symbols[callee].explanation) is not None
            and self.ledger.symbols[callee].is_fresh
        )
        dependency_text = "\n".join(text for _, text in callee_explanations)
        return SemanticPacketSymbol(
            symbol_id=symbol_id,
            path=symbol.path,
            kind=symbol.kind.value,
            span=symbol.span,
            source_body=source_body,
            content_hash=symbol.content_hash,
            callee_ids=callee_ids,
            callee_explanations=callee_explanations,
            cycle_peer_ids=symbol.cycle_peer_ids,
            dynamic_call_diagnostics=(),
            module_id=symbol.module_id,
            source_tokens=estimate_tokens_from_chars(len(source_body), "python"),
            dependency_tokens=estimate_tokens_from_chars(len(dependency_text), "python"),
        )

    @staticmethod
    def _compress_dependency_context(
        symbol: SemanticPacketSymbol,
        *,
        max_tokens: int,
    ) -> SemanticPacketSymbol:
        """Bound cited explanations while preserving the current source body."""

        if symbol.dependency_tokens <= max_tokens:
            return symbol
        if max_tokens <= 0 or not symbol.callee_explanations:
            return replace(symbol, callee_explanations=(), dependency_tokens=0)

        max_chars = math.floor(max_tokens * 3.5)
        per_callee = max_chars // len(symbol.callee_explanations)
        compressed = tuple(
            (callee, text[:per_callee].rstrip())
            for callee, text in symbol.callee_explanations
            if per_callee > 0
        )
        dependency_text = "\n".join(text for _, text in compressed)
        return replace(
            symbol,
            callee_explanations=compressed,
            dependency_tokens=estimate_tokens_from_chars(len(dependency_text), "python"),
        )

    def _source_body(self, symbol: SemanticSymbolRecord) -> str:
        try:
            lines = (self.repo_root / symbol.path).read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError as exc:
            raise SemanticSchedulerError(f"cannot read symbol source {symbol.path}: {exc}") from exc
        start, end = symbol.span
        if not (1 <= start <= end <= len(lines)):
            raise SemanticSchedulerError(f"symbol span is outside source file: {symbol.symbol_id}")
        return "\n".join(lines[start - 1 : end])

    def _assert_store_revision_current(self) -> None:
        if self._store is None:
            return
        current = self._store.reopen()
        if (
            current.source_revision != self.ledger.source_revision
            or current.ledger_revision != self.ledger.ledger_revision
            or current.bindings.edge_snapshot_sha256
            != self.ledger.bindings.edge_snapshot_sha256
        ):
            raise SemanticSchedulerError("scheduler snapshot is stale; rebuild it from store")

    @staticmethod
    def _next_generation(state: Mapping[str, object]) -> int:
        value = state.get("next_generation", 1)
        if type(value) is not int or value < 1:
            raise SemanticSchedulerError("scheduler next_generation must be an integer >= 1")
        return value

    def assert_packet_current(
        self,
        packet: SemanticBatchPacket,
        *,
        now: datetime | None = None,
    ) -> None:
        """Fail closed unless an exact generation-bound packet is still leased."""

        with self._state_lock():
            state = self._read_state_unlocked()
            current = self._live_packets(state, _utc(now)).get(packet.batch_id)
            if current is None:
                raise SemanticSchedulerError("claim generation mismatch")
            if (
                current.claim_generation != packet.claim_generation
                or current.claim_generation_id != packet.claim_generation_id
                or current.packet_sha256 != packet.packet_sha256
                or current.source_revision_id != packet.source_revision_id
                or current.edge_snapshot_sha256 != packet.edge_snapshot_sha256
            ):
                raise SemanticSchedulerError("claim generation mismatch")

    def _live_packets(
        self,
        state: Mapping[str, object],
        now: datetime,
    ) -> dict[str, SemanticBatchPacket]:
        raw_packets = state.get("packets", {})
        if not isinstance(raw_packets, dict):
            raise SemanticSchedulerError("scheduler state packets must be an object")
        packets: dict[str, SemanticBatchPacket] = {}
        for batch_id, raw in raw_packets.items():
            packet = self._packet_from_json(raw)
            if (
                packet.batch_id == batch_id
                and packet.source_revision == self.ledger.source_revision
                and packet.ledger_revision == self.ledger.ledger_revision
                and packet.semantic_schema == LEDGER_SCHEMA
                and packet.edge_snapshot_sha256
                == self.ledger.bindings.edge_snapshot_sha256
                and packet.lease_expires_at > now
            ):
                packets[batch_id] = packet
        return packets

    @staticmethod
    def _packet_to_json(packet: SemanticBatchPacket) -> dict[str, object]:
        payload = asdict(packet)
        payload["lease_expires_at"] = packet.lease_expires_at.isoformat()
        return payload

    @staticmethod
    def _packet_from_json(raw: object) -> SemanticBatchPacket:
        if not isinstance(raw, dict):
            raise SemanticSchedulerError("scheduler packet must be an object")
        try:
            symbols = tuple(
                SemanticPacketSymbol(
                    **{
                        **item,
                        "span": tuple(item["span"]),
                        "callee_ids": tuple(item["callee_ids"]),
                        "callee_explanations": tuple(
                            tuple(pair) for pair in item["callee_explanations"]
                        ),
                        "cycle_peer_ids": tuple(item["cycle_peer_ids"]),
                        "dynamic_call_diagnostics": tuple(item["dynamic_call_diagnostics"]),
                    }
                )
                for item in raw["symbols"]
            )
            estimate = PacketTokenEstimate(**raw["token_estimate"])
            return SemanticBatchPacket(
                batch_id=raw["batch_id"],
                lease_owner=raw["lease_owner"],
                lease_expires_at=datetime.fromisoformat(raw["lease_expires_at"]).astimezone(UTC),
                source_revision=raw["source_revision"],
                scc_id=raw["scc_id"],
                cycle_members=tuple(raw["cycle_members"]),
                symbols=symbols,
                token_estimate=estimate,
                oversize=raw["oversize"],
                ledger_revision=raw.get("ledger_revision", 0),
                semantic_schema=raw.get("semantic_schema", LEDGER_SCHEMA),
                edge_snapshot_sha256=raw.get(
                    "edge_snapshot_sha256", "sha256:" + "0" * 64
                ),
                claim_generation=raw.get("claim_generation", 1),
                claim_generation_id=raw.get(
                    "claim_generation_id", "claimgen_" + "0" * 64
                ),
                packet_sha256=raw.get("packet_sha256", "sha256:" + "0" * 64),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SemanticSchedulerError(f"scheduler packet is corrupt: {exc}") from exc

    def _read_state_unlocked(self) -> dict[str, object]:
        if not self.state_path.exists():
            return {
                "schema": SCHEDULER_STATE_SCHEMA,
                "source_revision_id": self.ledger.source_revision,
                "edge_snapshot_sha256": self.ledger.bindings.edge_snapshot_sha256,
                "ledger_revision": self.ledger.ledger_revision,
                "next_generation": 1,
                "packets": {},
            }
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SemanticSchedulerError(f"scheduler state is unreadable: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema") != SCHEDULER_STATE_SCHEMA:
            raise SemanticSchedulerError("scheduler state schema is invalid")
        source_revision_id = payload.get("source_revision_id", self.ledger.source_revision)
        edge_snapshot_sha256 = payload.get(
            "edge_snapshot_sha256", self.ledger.bindings.edge_snapshot_sha256
        )
        ledger_revision = payload.get("ledger_revision", self.ledger.ledger_revision)
        if (
            source_revision_id != self.ledger.source_revision
            or edge_snapshot_sha256 != self.ledger.bindings.edge_snapshot_sha256
            or ledger_revision != self.ledger.ledger_revision
        ):
            # A semantic commit/reconcile invalidates every prior lease.  Keep
            # the durable monotonic generation counter, but never carry old
            # packets into the new ledger binding.
            next_generation = payload.get("next_generation", 1)
            if type(next_generation) is not int or next_generation < 1:
                raise SemanticSchedulerError("scheduler next_generation must be an integer >= 1")
            return {
                "schema": SCHEDULER_STATE_SCHEMA,
                "source_revision_id": self.ledger.source_revision,
                "edge_snapshot_sha256": self.ledger.bindings.edge_snapshot_sha256,
                "ledger_revision": self.ledger.ledger_revision,
                "next_generation": next_generation,
                "packets": {},
            }
        payload.setdefault("source_revision_id", self.ledger.source_revision)
        payload.setdefault("edge_snapshot_sha256", self.ledger.bindings.edge_snapshot_sha256)
        payload.setdefault("ledger_revision", self.ledger.ledger_revision)
        payload.setdefault("next_generation", 1)
        self._next_generation(payload)
        return payload

    def _write_state_unlocked(
        self,
        packets: Mapping[str, SemanticBatchPacket],
        *,
        next_generation: int,
    ) -> None:
        if type(next_generation) is not int or next_generation < 1:
            raise SemanticSchedulerError("scheduler next_generation must be an integer >= 1")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEDULER_STATE_SCHEMA,
            "source_revision_id": self.ledger.source_revision,
            "edge_snapshot_sha256": self.ledger.bindings.edge_snapshot_sha256,
            "ledger_revision": self.ledger.ledger_revision,
            "next_generation": next_generation,
            "packets": {
                batch_id: self._packet_to_json(packet)
                for batch_id, packet in sorted(packets.items())
            },
        }
        encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(
            dir=self.state_path.parent,
            prefix=f".{self.state_path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.state_path)
            directory = os.open(self.state_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    @contextmanager
    def _state_lock(self) -> Iterator[None]:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.state_lock_path, flags, 0o600)
        except OSError as exc:
            raise SemanticSchedulerError(f"cannot open scheduler lock: {exc}") from exc
        with os.fdopen(descriptor, "a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
