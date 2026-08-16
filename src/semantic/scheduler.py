"""Qualified dependency scheduling with recoverable SCC leases and packets."""

from __future__ import annotations

import ast
import fcntl
import json
import math
import os
import tempfile
import uuid
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
    PENDING_EXPLANATION_REASON,
    SemanticLedger,
    SemanticSymbolRecord,
    revalidate_semantic_ledger,
)
from src.semantic.store import SemanticLedgerStore


SCHEDULER_STATE_RELPATH = Path(".codebase-analysis/semantic_scheduler_state.json")
SCHEDULER_STATE_SCHEMA = "cbe-semantic-scheduler-1"
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
        if (
            relation.kind != "calls"
            or relation.resolution_status is not ResolutionStatus.RESOLVED
            or relation.target is None
        ):
            continue
        caller = ir_to_semantic.get(relation.source.id)
        callee = ir_to_semantic.get(relation.target.id)
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
                self._write_state_unlocked(packets)
                return None

            packet = self._build_packet(
                selected_component,
                available,
                lease_owner=lease_owner.strip(),
                lease_expires_at=timestamp + timedelta(seconds=lease_seconds),
                max_context_tokens=max_context_tokens,
            )
            packets[packet.batch_id] = packet
            self._write_state_unlocked(packets)
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
            self._write_state_unlocked(packets)
            return packets.get(batch_id)

    def release_batch(self, batch_id: str, *, lease_owner: str) -> bool:
        """Release a lease only for its owning actor."""

        with self._state_lock():
            packets = self._live_packets(self._read_state_unlocked(), datetime.now(UTC))
            packet = packets.get(batch_id)
            if packet is None:
                self._write_state_unlocked(packets)
                return False
            if packet.lease_owner != lease_owner:
                raise SemanticSchedulerError("lease owner mismatch")
            del packets[batch_id]
            self._write_state_unlocked(packets)
            return True

    def _build_packet(
        self,
        component: DependencySCC,
        available: tuple[str, ...],
        *,
        lease_owner: str,
        lease_expires_at: datetime,
        max_context_tokens: int,
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
        return SemanticBatchPacket(
            batch_id="semantic_batch_" + uuid.uuid4().hex,
            lease_owner=lease_owner,
            lease_expires_at=lease_expires_at,
            source_revision=self.ledger.source_revision,
            scc_id=component.scc_id,
            cycle_members=component.members if component.is_cycle else (),
            symbols=tuple(selected),
            token_estimate=estimate,
            oversize=estimate.estimated_total_tokens > usable,
        )

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
        if current.source_revision != self.ledger.source_revision:
            raise SemanticSchedulerError("scheduler snapshot is stale; rebuild it from store")

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
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SemanticSchedulerError(f"scheduler packet is corrupt: {exc}") from exc

    def _read_state_unlocked(self) -> dict[str, object]:
        if not self.state_path.exists():
            return {"schema": SCHEDULER_STATE_SCHEMA, "packets": {}}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SemanticSchedulerError(f"scheduler state is unreadable: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema") != SCHEDULER_STATE_SCHEMA:
            raise SemanticSchedulerError("scheduler state schema is invalid")
        return payload

    def _write_state_unlocked(self, packets: Mapping[str, SemanticBatchPacket]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEDULER_STATE_SCHEMA,
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
