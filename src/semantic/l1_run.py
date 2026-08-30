"""Thin semantic lifecycle client.

Tier assignment and packet presentation remain here for compatibility with the
old command-line UX.  Durable state, recovery, coverage, and completion are
owned by :class:`src.semantic.service.SemanticService` and its public methods.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Final, Iterable, Mapping, Sequence

from src.semantic.gates import assert_prompt_dispatchable
from src.semantic.inventory import enumerate_semantic_inventory
from src.semantic.l1_facts import (
    L1FactError,
    L1SymbolFact,
    failed_checks,
    parse_l1_fact_payload,
    run_l1_checks,
    t0_template_fact,
)
from src.semantic.l1_packet import (
    L1PacketSymbol,
    build_packet_payload,
    kind_from_record,
)
from src.semantic.tiering import (
    EscalationState,
    MANUAL_QUEUE,
    SymbolMetrics,
    TIER_CHAINS,
    assign_tiers,
    measure_repository,
    mess_scores,
    record_attempt,
    self_check,
)


WORKSPACE_ROOT: Final = Path(
    os.environ.get("CBE_ROUTER_WORKSPACE", str(Path.home() / "context-infra"))
)
ROUTER_PYTHON: Final = os.environ.get(
    "PYTHON3_BIN",
    str(WORKSPACE_ROOT / ".venv/bin/python"),
)

RATE_LIMIT_KINDS: Final = frozenset(
    {"provider_rate_limited", "provider_quota_exhausted", "quota_cooling_down"}
)
HX3_BASELINE: Final = {
    "repo": "httpx",
    "symbols_this_slice": 210,
    "calls": 247,
    "tokens": 134596,
    "usd": 0.046,
    "wall_s": 889,
    "http_429": 22,
    "source": "runs/r003_.../evidence/round4/HX3_TIERING.md",
}

#: 本轮实测替补（2026-08-16 03:2x CEST 探针，读数落 `evidence/core/channel_probe.json`）。
#: 冻结架构 §4.3 的处置是「换 fallback，换不动就降解到确定层」——这里是换 fallback 的那一半，
#: 每一条都必须是**同档或更强**，且与被替换者同模型族，否则就是静默降档。
#:   T1 `deepseek-go:flash` / `kimi-ollama:medium` / `composer-cursor:medium` 三条全部本地不可达
#:       → 补 `dsh:pro`（DeepSeek 同族，换 harness；CLAUDE.md 的 `deepseek-pro` 组成员）。
#:   T2 `glm-ollama:high` / `deepseek-go:pro` 同样不可达
#:       → 补 `zcode:high`（GLM 同族，换 harness；CLAUDE.md 的 `glm` 组主选）。
#:   T3 主选 `grok-build:xhigh` 实测可达，不需要替补。
TIER_SUBSTITUTES: Final[Mapping[str, tuple[str, ...]]] = {
    "T0": (),
    "T1": ("dsh:pro",),
    "T2": ("zcode:high",),
    "T3": (),
}

#: 一个链路连续失败几次后本轮不再试它。留 2 次是为了让「它真的一直不可用」有两个独立样本，
#: 而不是一次抖动就把整条链判死。跳过次数照样计数并落盘——跳过不等于没发生。
DEAD_LINK_STRIKES: Final = 2

BATCH_SIZE: Final[Mapping[str, int]] = {"T1": 12, "T2": 6, "T3": 4}

#: T0 的份额（冻结架构 §4.1「符号的 10%」）。取仓内 mess 分数最低的这一档，
#: 且必须一条绝对绊线都没触——绊线优先级高于分位，屎山不因为「相对本仓不难」下沉。
T0_FRACTION: Final = 0.10

_CALL_TIMEOUT_S: Final = 900


# ---------------------------------------------------------------------------
# 三档执行分配
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionAssignment:
    symbol_id: str
    tier: str
    mess_score: float
    absolute_trips: tuple[str, ...]
    top_decile: bool
    bottom_decile: bool


def assign_execution_tiers(metrics: Sequence[SymbolMetrics]) -> tuple[ExecutionAssignment, ...]:
    """把 `assign_tiers` 的两分（T3 / 其余）补成 §4.1 的三分（T0 / T1 / T3）。

    为什么不直接改 `assign_tiers`：它承载的是**屎山判定**这一个职责（双触发，两个触发器
    分别留痕），T0 的份额是**成本分配**，另一个职责。合进去会让「绊线命中率自检」的分母
    变成三分之一个东西。这里按 `rules/FILE_SYSTEM_CORE.md` §1 分开。

    第一轮的 `initial_tier()` 把所有非 T3 符号都从 T0 起跑，而 T0 模板恒过 L1-a..d
    （L1-b 对它豁免、L1-c 因 `unresolved` 非空而过），于是回退链永不触发——85% 的符号
    会拿到一份零调用模板然后被判成完成。那是**判据恒真**，不是省钱。
    """

    if not metrics:
        return ()
    base = {item.symbol_id: item for item in assign_tiers(metrics)}
    scores = mess_scores(metrics)
    ordered = sorted(scores)
    cut = ordered[max(0, min(len(ordered) - 1, int(T0_FRACTION * len(ordered))))]
    assignments: list[ExecutionAssignment] = []
    for item, score in zip(metrics, scores):
        decision = base[item.symbol_id]
        bottom = score <= cut and not decision.absolute_trips
        if decision.tier == "T3":
            tier = "T3"
        elif bottom:
            tier = "T0"
        else:
            tier = "T1"
        assignments.append(
            ExecutionAssignment(
                symbol_id=item.symbol_id,
                tier=tier,
                mess_score=score,
                absolute_trips=decision.absolute_trips,
                top_decile=decision.top_decile,
                bottom_decile=bottom,
            )
        )
    return tuple(assignments)


# ---------------------------------------------------------------------------
# 链路健康：把「触了墙」变成读数
# ---------------------------------------------------------------------------


@dataclass
class LinkHealth:
    """一条链路在本轮的实测台账。每个字段都是**发生过的事**，不是策略声明。"""

    attempted: int = 0
    failed: int = 0
    succeeded: int = 0
    skipped_dead: int = 0
    consecutive_failures: int = 0
    error_kinds: dict[str, int] = field(default_factory=dict)

    @property
    def dead(self) -> bool:
        return self.consecutive_failures >= DEAD_LINK_STRIKES

    def as_dict(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "failed": self.failed,
            "succeeded": self.succeeded,
            "skipped_after_declared_dead": self.skipped_dead,
            "declared_dead": self.dead,
            "error_kinds": dict(sorted(self.error_kinds.items())),
        }


class ChainLedger:
    """回退链的全局读数。线程安全，因为派发是并发的。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self.links: dict[str, LinkHealth] = {}
        self.substitute_used: dict[str, int] = {}
        self.rate_limited: dict[str, int] = {}
        self.http_429_total: int = 0
        self._rr: dict[str, int] = {}

    def _link(self, tier_name: str) -> LinkHealth:
        return self.links.setdefault(tier_name, LinkHealth())

    def live_chain(self, tier: str) -> tuple[str, ...]:
        """本轮仍值得一试的链路。被判死的照样计数，只是不再花 3 分钟去撞它。"""

        chain = tuple(TIER_CHAINS[tier]) + tuple(TIER_SUBSTITUTES[tier])
        with self._lock:
            live: list[str] = []
            for name in chain:
                health = self._link(name)
                if health.dead:
                    health.skipped_dead += 1
                    continue
                live.append(name)
            if len(live) > 1:
                # §4.3 档内轮转：不要把 O(N) 全打进同一个 quota_scope。
                self._rr[tier] = self._rr.get(tier, 0) + 1
                offset = (self._rr[tier] - 1) % len(live)
                live = live[offset:] + live[:offset]
            return tuple(live)

    def record(
        self,
        *,
        tier: str,
        attempts: Sequence[Sequence[object]],
        tier_used: str | None,
        succeeded: bool,
    ) -> None:
        frozen_chain = set(TIER_CHAINS[tier])
        with self._lock:
            for attempt in attempts:
                name = str(attempt[0])
                kind = str(attempt[1]) if len(attempt) > 1 else "unknown"
                health = self._link(name)
                health.attempted += 1
                health.failed += 1
                health.consecutive_failures += 1
                health.error_kinds[kind] = health.error_kinds.get(kind, 0) + 1
                if kind in RATE_LIMIT_KINDS or "429" in kind:
                    self.rate_limited[name] = self.rate_limited.get(name, 0) + 1
                    self.http_429_total += 1
            if tier_used:
                health = self._link(tier_used)
                health.attempted += 1
                health.consecutive_failures = 0
                if succeeded:
                    health.succeeded += 1
                else:
                    health.failed += 1
                if tier_used not in frozen_chain:
                    self.substitute_used[tier_used] = self.substitute_used.get(tier_used, 0) + 1

    def as_dict(self) -> dict[str, object]:
        with self._lock:
            return {
                "links": {name: health.as_dict() for name, health in sorted(self.links.items())},
                "substitute_dispatches": dict(sorted(self.substitute_used.items())),
                "http_429_total": self.http_429_total,
                "rate_limited_by_link": dict(sorted(self.rate_limited.items())),
            }


# ---------------------------------------------------------------------------
# 派发
# ---------------------------------------------------------------------------


PRODUCER_PROMPT: Final = (
    "你是函数级语义解释生产者。stdin 是一个 JSON 对象，`symbols` 每项恰好九个字段："
    "symbol_id, path, kind, span, source_body, content_hash, callee_signatures, "
    "language, syntax_diagnostics。"
    "逐符号只依据该符号的 source_body 与 callee_signatures 作答：这段代码做什么、"
    "输入输出与副作用、失败条件、直接用到了哪些标识符。作答范围到此为止。"
    "凡是读完这段源码仍看不出来的，写进 unresolved，不要推测。"
    "\n\n只输出一个 JSON 对象，不要代码块围栏，不要任何解释性文字："
    '{"facts": [...]}。facts 每项恰好九个字段，多一个少一个都会被拒收：\n'
    "- symbol_id：原样抄回\n"
    "- one_liner：不超过 160 字符，说这段代码做的事；不要把符号名换成中文再说一遍\n"
    "- behavior：这段代码的执行过程\n"
    "- effects：从 pure / reads_fs / writes_fs / net_io / mutates_self / mutates_arg / "
    "global_state / raises / spawns / blocking 中选，非空数组，pure 不可与其他并列\n"
    "- inputs_outputs：入参与返回值\n"
    "- failure_modes：字符串数组，可为空数组\n"
    "- identifiers_used：字符串数组，每一项必须逐字出现在该符号的 source_body 或"
    " callee_signatures 里，抄不到就不要写\n"
    "- unresolved：字符串数组，每项形如 CODE 或 CODE:证据，CODE 取自 "
    "LOCAL_SEMANTICS_UNCLEAR / NEEDS_CALLEE_SEMANTICS / DYNAMIC_DISPATCH_UNRESOLVED / "
    "EXTERNAL_CONTRACT_UNKNOWN / SIDE_EFFECT_UNVERIFIABLE\n"
    "- confidence：low / medium / high；取 low 时 unresolved 必须非空\n"
    "不得调用任何工具，不得读取 stdin 之外的任何文件。"
)


@dataclass(frozen=True)
class PreparedSymbol:
    packet: L1PacketSymbol
    qualified_name: str


@dataclass(frozen=True)
class DispatchOutcome:
    tier: str
    tier_used: str | None
    attempts: tuple[tuple[str, str], ...]
    duration_s: float
    is_substitute: bool
    facts_by_id: Mapping[str, Mapping[str, Any]]
    error: str
    prompt_chars: int
    reply_chars: int
    cost_usd: float = 0.0
    estimated_tokens: int = 0
    http_429: int = 0
    rate_limit_kinds: tuple[str, ...] = ()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[: -3]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def dispatch_batch(
    symbols: Sequence[PreparedSymbol],
    *,
    tier: str,
    ledger: ChainLedger,
    task_name: str,
) -> DispatchOutcome:
    """一个批次一次派发。闸 1 在 `build_packet_payload`，闸 2 在 `assert_prompt_dispatchable`。"""

    rows = build_packet_payload([item.packet for item in symbols])  # 闸 1
    assert_prompt_dispatchable(PRODUCER_PROMPT, subject=f"L1 {tier} producer prompt")  # 闸 2
    stdin_text = (
        PRODUCER_PROMPT
        + "\n\nstdin:\n"
        + json.dumps({"symbols": rows}, ensure_ascii=False)
        + "\n"
    )
    chain = ledger.live_chain(tier)
    if not chain:
        return DispatchOutcome(
            tier=tier,
            tier_used=None,
            attempts=(),
            duration_s=0.0,
            is_substitute=False,
            facts_by_id={},
            error="all links in this tier chain were declared dead earlier in the run",
            prompt_chars=len(stdin_text),
            reply_chars=0,
            cost_usd=0.0,
            estimated_tokens=0,
            http_429=0,
        )
    primary, *fallback = chain
    argv = [
        ROUTER_PYTHON,
        "-m",
        "tools.cli_agent.router",
        "--primary",
        primary,
    ]
    if fallback:
        argv.append("--fallback")
        argv.extend(fallback)
    argv.extend(
        ["--task-name", task_name, "--workdir", str(WORKSPACE_ROOT), "--timeout", "600"]
    )
    started = time.time()
    try:
        completed = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT),
            timeout=_CALL_TIMEOUT_S,
            env={**os.environ, "PYTHONPATH": str(WORKSPACE_ROOT)},
        )
    except subprocess.TimeoutExpired:
        ledger.record(tier=tier, attempts=[(primary, "hard_timeout")], tier_used=None, succeeded=False)
        return DispatchOutcome(
            tier=tier,
            tier_used=None,
            attempts=((primary, "hard_timeout"),),
            duration_s=time.time() - started,
            is_substitute=False,
            facts_by_id={},
            error=f"router wall-clock timeout after {_CALL_TIMEOUT_S}s",
            prompt_chars=len(stdin_text),
            reply_chars=0,
            cost_usd=0.0,
            estimated_tokens=0,
            http_429=0,
        )
    duration = time.time() - started
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        ledger.record(tier=tier, attempts=[(primary, "router_no_json")], tier_used=None, succeeded=False)
        return DispatchOutcome(
            tier=tier,
            tier_used=None,
            attempts=((primary, "router_no_json"),),
            duration_s=duration,
            is_substitute=False,
            facts_by_id={},
            error=f"router stdout was not JSON: {completed.stdout[:200]!r} / {completed.stderr[-300:]!r}",
            prompt_chars=len(stdin_text),
            reply_chars=0,
            cost_usd=0.0,
            estimated_tokens=0,
            http_429=0,
        )
    attempts = tuple(
        (str(item[0]), str(item[1]) if len(item) > 1 else "unknown")
        for item in result.get("attempts", [])
    )
    rate_kinds = tuple(
        kind for _name, kind in attempts if kind in RATE_LIMIT_KINDS or "429" in kind
    )
    tier_used = result.get("tier_used")
    reply = str(result.get("result_text") or "")
    payload = _extract_json_object(reply) if reply else None
    facts_by_id: dict[str, Mapping[str, Any]] = {}
    error = str(result.get("error") or "")
    if payload is not None:
        raw_facts = payload.get("facts")
        if isinstance(raw_facts, list):
            for entry in raw_facts:
                if isinstance(entry, dict) and isinstance(entry.get("symbol_id"), str):
                    facts_by_id[entry["symbol_id"]] = entry
        elif not error:
            error = "reply JSON has no `facts` array"
    elif not error:
        error = f"reply was not parseable JSON: {reply[:160]!r}"
    ledger.record(
        tier=tier,
        attempts=attempts,
        tier_used=tier_used,
        succeeded=bool(facts_by_id),
    )
    cost_usd = float(result.get("cost_usd") or 0.0)
    estimated_tokens = int(result.get("estimated_tokens") or 0)
    if estimated_tokens <= 0 and (reply or facts_by_id):
        # Router left tokens at 0 (opencode/ollama/cursor often do). Chars/4 is
        # the documented fallback, not a billing number — marked in the call record.
        estimated_tokens = max(1, (len(stdin_text) + len(reply)) // 4)
    return DispatchOutcome(
        tier=tier,
        tier_used=tier_used,
        attempts=attempts,
        duration_s=duration,
        is_substitute=bool(result.get("is_substitute")),
        facts_by_id=facts_by_id,
        error=error,
        prompt_chars=len(stdin_text),
        reply_chars=len(reply),
        cost_usd=cost_usd,
        estimated_tokens=estimated_tokens,
        http_429=len(rate_kinds),
        rate_limit_kinds=rate_kinds,
    )


# ---------------------------------------------------------------------------
# 单符号判定
# ---------------------------------------------------------------------------


@dataclass
class SymbolRun:
    symbol_id: str
    qualified_name: str
    path: str
    assigned_tier: str
    state: EscalationState
    fact: L1SymbolFact | None = None
    accepted_tier: str = ""
    check_details: list[dict[str, object]] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.fact is not None

    def as_dict(self) -> dict[str, object]:
        return {
            "symbol_id": self.symbol_id,
            "qualified_name": self.qualified_name,
            "path": self.path,
            "assigned_tier": self.assigned_tier,
            "accepted_tier": self.accepted_tier,
            "resolved": self.resolved,
            "escalation": self.state.as_dict(),
            "checks": self.check_details,
            "parse_errors": self.parse_errors,
            "fact": self.fact.to_payload() if self.fact is not None else None,
        }


def judge_symbol(
    run: SymbolRun,
    prepared: PreparedSymbol,
    payload: Mapping[str, Any] | None,
    *,
    tier: str,
    error: str,
) -> None:
    """把一次产出判成「收下」或「拒收 + 升档」。四条检查一起跑，不短路。"""

    if payload is None:
        run.parse_errors.append(f"{tier}: {error or 'no fact returned for this symbol'}")
        run.state = record_attempt(
            run.state,
            failed_checks=("L1-d",),
            confidence="low",
            unresolved=("LOCAL_SEMANTICS_UNCLEAR",),
            payload=None,
        )
        run.check_details.append(
            {
                "tier": tier,
                "outcome": "no_payload",
                "detail": (error or "producer returned nothing for this symbol")[:400],
            }
        )
        return
    try:
        fact = parse_l1_fact_payload(payload)
    except (L1FactError, ValueError, KeyError, TypeError) as exc:
        run.parse_errors.append(f"{tier}: {type(exc).__name__}: {exc}")
        run.state = record_attempt(
            run.state,
            failed_checks=("L1-d",),
            confidence="low",
            unresolved=("LOCAL_SEMANTICS_UNCLEAR",),
            payload=dict(payload),
        )
        run.check_details.append(
            {"tier": tier, "outcome": "schema_rejected", "detail": f"{type(exc).__name__}: {exc}"[:400]}
        )
        return
    results = run_l1_checks(
        fact,
        source_body=prepared.packet.source_body,
        qualified_name=prepared.qualified_name,
        callee_signatures=prepared.packet.callee_signatures,
        tier=tier,
    )
    failures = failed_checks(results)
    run.check_details.append(
        {
            "tier": tier,
            "outcome": "accepted" if not failures else "rejected",
            "results": [item.as_dict() for item in results],
        }
    )
    if not failures:
        run.fact = fact
        run.accepted_tier = tier
    run.state = record_attempt(
        run.state,
        failed_checks=failures,
        confidence=fact.confidence,
        unresolved=fact.unresolved,
        payload=fact.to_payload(),
    )


# ---------------------------------------------------------------------------
# 全量跑
# ---------------------------------------------------------------------------


def _source_body(repo_root: Path, path: str, span: tuple[int, int]) -> str:
    text = (repo_root / path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    body = "\n".join(lines[span[0] - 1 : span[1]])
    return body if body.strip() else "# empty"


def prepare_symbols(repo_root: Path) -> tuple[dict[str, PreparedSymbol], dict[str, str], list[str]]:
    inventory = enumerate_semantic_inventory(repo_root)
    prepared: dict[str, PreparedSymbol] = {}
    paths: dict[str, str] = {}
    for symbol_id, record in inventory.symbols.items():
        diagnostics = tuple(item for item in inventory.diagnostics if record.path in item)
        prepared[symbol_id] = PreparedSymbol(
            packet=L1PacketSymbol(
                symbol_id=symbol_id,
                path=record.path,
                kind=kind_from_record(record.kind),
                span=tuple(record.span),  # type: ignore[arg-type]
                source_body=_source_body(repo_root, record.path, tuple(record.span)),  # type: ignore[arg-type]
                content_hash=record.content_hash,
                callee_signatures=(),
                language="python",
                syntax_diagnostics=diagnostics,
            ),
            qualified_name=record.qualified_name,
        )
        paths[symbol_id] = record.path
    return prepared, paths, list(inventory.diagnostics)


def _batches(symbol_ids: Sequence[str], size: int, paths: Mapping[str, str]) -> list[list[str]]:
    """同文件的符号尽量同批：同一份源码的上下文对读者和模型是同一件事。"""

    ordered = sorted(symbol_ids, key=lambda item: (paths.get(item, ""), item))
    return [list(ordered[index : index + size]) for index in range(0, len(ordered), size)]


def run_repository(
    repo_root: str | Path,
    *,
    name: str = "semantic",
    out_dir: Path | None = None,
    workers: int = 8,
    limit: int = 0,
    symbol_prefix: str = "",
    transport: str = "local",
    legacy_dir: str | Path | None = None,
    max_context_tokens: int = 16_000,
    lease_seconds: int = 900,
    resume_batch: str | None = None,
    stop_after_claim: bool = False,
) -> dict[str, Any]:
    """Run the public semantic lifecycle adapter and return a non-authoritative view.

    The legacy tiering helpers above are intentionally retained as presentation
    utilities.  This entry point never opens, resumes, checkpoints, or writes a
    parallel ledger.  ``out_dir`` remains an API-compatible argument for older
    callers, but canonical state is always resolved by ``SemanticService``.
    """

    if transport not in {"local", "mcp-stdio"}:
        raise ValueError("transport must be local or mcp-stdio")
    if max_context_tokens < 1 or lease_seconds < 1:
        raise ValueError("context and lease budgets must be positive")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")

    # Keep the adapter import local: tiering and packet presentation remain
    # usable in isolation, while lifecycle state is owned by the service.
    from src.semantic.service import SemanticService

    started_at = time.time()
    service = SemanticService(root)
    ledger = service.bootstrap_semantic()

    packet = None
    if resume_batch:
        packet = service.recover_semantic_batch(resume_batch)
    elif stop_after_claim:
        packet = service.claim_semantic_batch(
            actor=f"cli:{name}",
            max_context_tokens=max_context_tokens,
            lease_seconds=lease_seconds,
        )

    progress = service.get_semantic_progress()
    packet_payload = None
    if packet is not None:
        packet_payload = {
            "batch_id": packet.batch_id,
            "source_revision": packet.source_revision,
            "source_revision_id": packet.source_revision_id,
            "ledger_revision": packet.ledger_revision,
            "semantic_schema": packet.semantic_schema,
            "edge_snapshot_sha256": packet.edge_snapshot_sha256,
            "claim_generation": packet.claim_generation,
            "claim_generation_id": packet.claim_generation_id,
            "packet_sha256": packet.packet_sha256,
            "lease_owner": packet.lease_owner,
            "lease_expires_at": packet.lease_expires_at.isoformat(),
            "symbol_ids": [item.symbol_id for item in packet.symbols],
        }

    # ``legacy_dir`` is deliberately reported as an input hint only.  The
    # service/store owns the one-shot import gate and its canonical path; this
    # client must never read import artifacts itself.
    return {
        "schema": "cbe-semantic-run-summary/1",
        "repo": name,
        "repo_root": str(root),
        "transport": transport,
        "authoritative": False,
        "canonical": {
            "ledger_path": str(service.store.path),
            "ledger_revision": progress["ledger_revision"],
            "ledger_sha256": progress["ledger_sha256"],
            "source_revision_id": progress["source_revision_id"],
            "semantic_schema": ledger.schema,
            "edge_snapshot_sha256": ledger.bindings.edge_snapshot_sha256,
        },
        "completion": {
            "product_complete": progress["product_complete"],
            "coverage_percent": progress["coverage_percent"],
            "totals": progress["totals"],
            "render_pending": progress["render_pending"],
            "legacy_import_status": progress["legacy_import_status"],
        },
        "packet": packet_payload,
        "resume_batch": resume_batch,
        "stop_after_claim": stop_after_claim,
        "legacy_dir": str(Path(legacy_dir).resolve()) if legacy_dir is not None else None,
        "presentation": {
            "workers": workers,
            "limit": limit,
            "symbol_prefix": symbol_prefix,
        },
        "calls": {"total": 0},
        "wall_clock_s": round(time.time() - started_at, 3),
    }


def _count(values: Iterable[object]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for value in values:
        key = str(value) or "(none)"
        counter[key] = counter.get(key, 0) + 1
    return dict(sorted(counter.items()))


def _rejection_histogram(runs: Iterable[SymbolRun]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for run in runs:
        for attempt in run.state.attempts:
            for check in attempt.failed_checks:
                key = f"{attempt.tier}:{check}"
                counter[key] = counter.get(key, 0) + 1
    return dict(sorted(counter.items()))


def _unresolved_causes(runs: Sequence[SymbolRun]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for run in runs:
        if run.state.manual_queue_reason:
            key = run.state.manual_queue_reason.split(";")[0][:80]
        elif run.parse_errors:
            key = run.parse_errors[-1].split(":", 2)[-1][:80]
        else:
            key = "still pending when the run ended"
        counter[key] = counter.get(key, 0) + 1
    return dict(sorted(counter.items(), key=lambda item: -item[1]))


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run the canonical semantic lifecycle adapter")
    run.add_argument("repo_root")
    run.add_argument("--name", default="semantic")
    run.add_argument("--output-dir", "--out", dest="output_dir", default=None)
    run.add_argument("--transport", choices=("local", "mcp-stdio"), default="local")
    run.add_argument("--legacy-dir", default=None)
    run.add_argument("--max-context-tokens", type=int, default=16_000)
    run.add_argument("--lease-seconds", type=int, default=900)
    run.add_argument("--resume-batch", default=None)
    run.add_argument("--stop-after-claim", action="store_true")
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--limit", type=int, default=0, help="cap symbols (smoke runs only)")
    run.add_argument("--symbol-prefix", default="", help="only symbols whose id starts with this")
    args = parser.parse_args(argv)
    summary = run_repository(
        args.repo_root,
        name=args.name,
        out_dir=Path(args.output_dir) if args.output_dir else None,
        workers=args.workers,
        limit=args.limit,
        symbol_prefix=args.symbol_prefix,
        transport=args.transport,
        legacy_dir=args.legacy_dir,
        max_context_tokens=args.max_context_tokens,
        lease_seconds=args.lease_seconds,
        resume_batch=args.resume_batch,
        stop_after_claim=args.stop_after_claim,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
