"""One-call-per-cluster production with closed-citation escalation."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping
from typing import Any, Protocol

from src.semantic.models import SemanticLedger

from .anchors import (
    ClosedCitationError,
    assert_model_body_has_no_links,
    validate_selection,
)
from .models import (
    SECTION_TITLES,
    BatchPlan,
    BatchReceipt,
    CandidateSet,
    ClusterRecord,
    PageDraft,
)


DEFAULT_PRIMARY = "grok-build:xhigh"
DEFAULT_FALLBACKS = ("gpt:luna-max", "claude-zai:high")


@dataclass(frozen=True, slots=True)
class Invocation:
    text: str
    provider: str
    fallback_used: bool = False
    is_substitute: bool = False
    requested_primary: str | None = None
    resolved_tier: str | None = None
    fallback_chain_requested: tuple[str, ...] = ()
    route_attempts: tuple[tuple[str, str, str], ...] = ()
    source_receipt_id: str | None = None


class BatchInvoker(Protocol):
    def invoke(self, prompt: str, *, task_name: str) -> Invocation:
        """Run one batch request. The implementation may use an explicit router chain."""


class RouterDispatchError(RuntimeError):
    """A router dispatch failed after producing a machine-readable route result."""

    def __init__(
        self,
        message: str,
        *,
        requested_primary: str | None = None,
        resolved_tier: str | None = None,
        fallback_chain_requested: tuple[str, ...] = (),
        route_attempts: tuple[tuple[str, str, str], ...] = (),
        is_substitute: bool = False,
        source_receipt_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.requested_primary = requested_primary
        self.resolved_tier = resolved_tier
        self.fallback_chain_requested = tuple(fallback_chain_requested)
        self.route_attempts = tuple(route_attempts)
        self.is_substitute = is_substitute
        self.source_receipt_id = source_receipt_id


def _normalize_route_attempts(value: object) -> tuple[tuple[str, str, str], ...]:
    """Normalize router's JSON attempt projection to an immutable receipt shape."""

    if not isinstance(value, (list, tuple)):
        return ()
    normalized: list[tuple[str, str, str]] = []
    for item in value:
        if isinstance(item, Mapping):
            normalized.append(
                (
                    str(item.get("tier") or ""),
                    str(item.get("error_kind") or item.get("kind") or ""),
                    str(item.get("detail") or ""),
                )
            )
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            normalized.append((str(item[0]), str(item[1]), str(item[2])))
    return tuple(normalized)


def _find_workspace_root() -> Path:
    """Find the repository root that owns the router module."""

    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "cli_agent" / "router.py").is_file():
            return parent
    raise RuntimeError("context-infra router root is not discoverable")


@dataclass(frozen=True, slots=True)
class ProducedBatch:
    plan: BatchPlan
    draft: PageDraft
    candidates: CandidateSet
    receipt: BatchReceipt


class StaticInvoker:
    """Test/evidence invoker; it still goes through the same submit gate."""

    def __init__(self, payloads: dict[str, str | dict[str, Any]], provider: str = "test-provider") -> None:
        self._payloads = dict(payloads)
        self._provider = provider
        self.calls: list[str] = []

    def invoke(self, prompt: str, *, task_name: str) -> Invocation:
        self.calls.append(task_name)
        payload = self._payloads.get(task_name)
        if payload is None:
            raise RuntimeError(f"no static payload for {task_name}")
        text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else payload
        return Invocation(text=text, provider=self._provider)


class RouterInvoker:
    """Invoke the repository router with a visible same-or-stronger fallback chain."""

    def __init__(
        self,
        *,
        workdir: str | Path,
        python_executable: str | None = None,
        primary: str = DEFAULT_PRIMARY,
        fallbacks: tuple[str, ...] = DEFAULT_FALLBACKS,
        timeout_seconds: float = 240.0,
        router_workdir: str | Path | None = None,
        router_timeout_seconds: int = 240,
    ) -> None:
        self.workdir = str(Path(workdir).resolve())
        self.router_workdir = str(
            Path(router_workdir or _find_workspace_root()).resolve()
        )
        self.python_executable = python_executable or sys.executable
        self.primary = primary
        self.fallbacks = tuple(fallbacks)
        self.timeout_seconds = float(timeout_seconds)
        self.router_timeout_seconds = int(router_timeout_seconds)

    @property
    def command_prefix(self) -> tuple[str, ...]:
        return (
            self.python_executable,
            "-m",
            "tools.cli_agent.router",
            "--primary",
            self.primary,
            "--fallback",
            *self.fallbacks,
            "--timeout",
            str(self.router_timeout_seconds),
        )

    def invoke(self, prompt: str, *, task_name: str) -> Invocation:
        command = (
            *self.command_prefix,
            "--task-name",
            task_name,
            "--workdir",
            self.router_workdir,
        )
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=self.router_workdir,
            timeout=self.timeout_seconds,
            check=False,
        )
        raw_stdout = completed.stdout.strip()
        routed_text = raw_stdout
        provider = self.primary
        fallback_used = False
        is_substitute = False
        requested_primary: str | None = self.primary
        resolved_tier: str | None = None
        fallback_chain_requested = self.fallbacks
        route_attempts: tuple[tuple[str, str, str], ...] = ()
        source_receipt_id: str | None = None
        try:
            envelope = json.loads(raw_stdout)
            if isinstance(envelope, dict):
                if "result_text" in envelope:
                    routed_text = str(envelope.get("result_text") or "")
                elif "result" in envelope:
                    routed_text = str(envelope.get("result") or "")
                requested_primary = str(
                    envelope.get("requested_primary") or self.primary
                )
                resolved_tier = (
                    str(envelope.get("resolved_tier"))
                    if envelope.get("resolved_tier")
                    else None
                )
                provider = str(
                    envelope.get("tier_used")
                    or resolved_tier
                    or envelope.get("model_id_observed")
                    or envelope.get("model_id_configured")
                    or self.primary
                )
                is_substitute = bool(envelope.get("is_substitute", False))
                fallback_used = is_substitute
                raw_fallbacks = envelope.get("fallback_chain_requested")
                if isinstance(raw_fallbacks, (list, tuple)):
                    fallback_chain_requested = tuple(str(item) for item in raw_fallbacks)
                route_attempts = _normalize_route_attempts(envelope.get("attempts"))
                if not route_attempts and not bool(envelope.get("is_error", False)):
                    route_attempts = ((provider, "success", ""),)
                source_receipt_id = (
                    str(envelope.get("source_receipt_id"))
                    if envelope.get("source_receipt_id")
                    else None
                )
        except json.JSONDecodeError:
            pass
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "router failed").strip()[-1000:]
            if route_attempts:
                raise RouterDispatchError(
                    f"router exit {completed.returncode}: {detail}",
                    requested_primary=requested_primary,
                    resolved_tier=resolved_tier,
                    fallback_chain_requested=fallback_chain_requested,
                    route_attempts=route_attempts,
                    is_substitute=is_substitute,
                    source_receipt_id=source_receipt_id,
                )
            raise RuntimeError(f"router exit {completed.returncode}: {detail}")
        return Invocation(
            text=routed_text.strip(),
            provider=provider,
            fallback_used=fallback_used,
            is_substitute=is_substitute,
            requested_primary=requested_primary,
            resolved_tier=resolved_tier,
            fallback_chain_requested=fallback_chain_requested,
            route_attempts=route_attempts,
            source_receipt_id=source_receipt_id,
        )


def build_batch_prompt(plan: BatchPlan, cluster: ClusterRecord, candidates: CandidateSet) -> str:
    """Build the L2-fact-only prompt; source bytes never cross this boundary."""

    file_lines = "\n".join(
        f"- {card.path}: {card.purpose}; revision={card.revision}; symbols={len(card.symbol_ids)}"
        for card in cluster.files
        if card.path in plan.file_paths
    ) or "- (no file cards)"
    symbol_lookup = {symbol.symbol_id: symbol for symbol in cluster.symbols}
    symbol_lines = "\n".join(
        f"- {symbol_id}: {symbol_lookup[symbol_id].qualified_name} "
        f"({symbol_lookup[symbol_id].path}:{symbol_lookup[symbol_id].span[0]}-{symbol_lookup[symbol_id].span[1]}): "
        f"{symbol_lookup[symbol_id].one_liner}"
        for symbol_id in plan.symbol_ids
        if symbol_id in symbol_lookup
    ) or "- (no symbols; explain the file-level functional boundary)"
    edge_lines = "\n".join(f"- {source} -> {target}" for source, target in cluster.edges) or "- (none)"
    candidate_lines = "\n".join(
        f"- {target.target_id}: {target.label} at {target.target_path}:{target.line_start}-{target.line_end}"
        for target in candidates.targets
    )
    return f"""你是代码文档表达层。只依据下面的 FileCard、SymbolCard、组内边和封闭候选集写一篇中文密描述。
簇：{cluster.name}；目的：{cluster.purpose}；批次：{plan.batch_id}。

必须输出 JSON 对象，字段严格为：body、selected_target_ids、covered_symbol_ids。
body 必须保留四个二级标题：## 初始化、## 请求流程、## 响应阶段、## 异常处理；每节至少一句具体描述。
selected_target_ids 只能逐字从 Candidates 选择，不得写路径、URL、Markdown 链接或自行发明 id。
covered_symbol_ids 只能逐字从本批 SymbolCard 选择。不要复述本提示，不要读取或猜测源码。

FileCards:
{file_lines}

SymbolCards:
{symbol_lines}

组内边（caller -> callee）：
{edge_lines}

Candidates（封闭集合）：
{candidate_lines}
"""


def parse_page_draft(raw: str | Mapping[str, Any], *, plan: BatchPlan) -> PageDraft:
    payload: object
    if isinstance(raw, Mapping):
        payload = raw
    else:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].lstrip()
        payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise ValueError("producer output must be a JSON object")
    allowed = {"body", "selected_target_ids", "covered_symbol_ids"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"producer output has unknown fields: {sorted(unknown)}")
    body = payload.get("body")
    selected = payload.get("selected_target_ids")
    covered = payload.get("covered_symbol_ids", list(plan.symbol_ids))
    if not isinstance(body, str) or not isinstance(selected, (list, tuple)) or not isinstance(covered, (list, tuple)):
        raise ValueError("producer output fields have invalid shapes")
    return PageDraft(
        body=body,
        selected_target_ids=tuple(str(item) for item in selected),
        covered_symbol_ids=tuple(str(item) for item in covered),
    )


def validate_page_draft(
    draft: PageDraft,
    *,
    plan: BatchPlan,
    candidates: CandidateSet,
    ledger: SemanticLedger,
) -> PageDraft:
    assert_model_body_has_no_links(draft.body)
    missing_sections = [title for title in SECTION_TITLES if f"## {title}" not in draft.body]
    if missing_sections:
        raise ValueError(f"missing four-section headings: {missing_sections}")
    for title in SECTION_TITLES:
        section_start = draft.body.find(f"## {title}") + len(title) + 3
        next_positions = [
            draft.body.find(f"## {other}", section_start)
            for other in SECTION_TITLES
            if draft.body.find(f"## {other}", section_start) >= 0
        ]
        section = draft.body[section_start : min(next_positions) if next_positions else None].strip()
        if not section:
            raise ValueError(f"empty four-section heading: {title}")
    if any(symbol_id not in set(plan.symbol_ids) for symbol_id in draft.covered_symbol_ids):
        raise ValueError("covered_symbol_ids contains a symbol outside this batch")
    validate_selection(draft.selected_target_ids, candidates, ledger_value=ledger)
    return draft


def deterministic_degraded_draft(plan: BatchPlan, cluster: ClusterRecord, reason: str) -> PageDraft:
    """Visible deterministic fallback used when the full router chain is exhausted."""

    facts = "；".join(
        f"{card.path}（{len(card.symbol_ids)} 个符号，revision {card.revision[:18]}）"
        for card in cluster.files
        if card.path in plan.file_paths
    ) or "本批次没有可枚举符号"
    names = "、".join(
        symbol.qualified_name for symbol in cluster.symbols if symbol.symbol_id in set(plan.symbol_ids)
    )
    summary = names[:500] or "无符号事实"
    body = f"""<!-- residual: {reason} -->
## 初始化
确定层文件卡表明本批次属于「{cluster.name}」功能簇；文件事实为：{facts}。
## 请求流程
本次 LLM 表达未完成，确定层只保留批次边界与符号名，不推断运行时调用顺序。
## 响应阶段
本批次覆盖的符号事实为：{summary}。
## 异常处理
表达层残差：{reason}。待下一次有额度的批量调用重新生成，不能把本段当作源码语义。
"""
    selected = f"page:{plan.batch_id}"
    return PageDraft(
        body=body,
        selected_target_ids=(selected,),
        covered_symbol_ids=tuple(plan.symbol_ids),
    )


def produce_batch(
    plan: BatchPlan,
    cluster: ClusterRecord,
    candidates: CandidateSet,
    *,
    ledger: SemanticLedger,
    invoker: BatchInvoker,
) -> ProducedBatch:
    """Produce exactly one primary batch request, then at most one gate escalation."""

    prompt = build_batch_prompt(plan, cluster, candidates)
    attempts = 0
    rejection_reason: str | None = None
    last_provider = "router"
    fallback_used = False
    is_substitute = False
    requested_primary: str | None = None
    resolved_tier: str | None = None
    fallback_chain_requested: tuple[str, ...] = ()
    route_attempts: tuple[tuple[str, str, str], ...] = ()
    source_receipt_id: str | None = None
    for pass_number in range(2):
        attempts += 1
        task_name = f"variant-c-{plan.batch_id.replace(':', '-')}-pass-{pass_number + 1}"
        try:
            invocation = invoker.invoke(prompt, task_name=task_name)
            last_provider = invocation.provider
            fallback_used = fallback_used or invocation.fallback_used
            is_substitute = is_substitute or invocation.is_substitute
            requested_primary = invocation.requested_primary or requested_primary
            resolved_tier = invocation.resolved_tier or resolved_tier
            fallback_chain_requested = (
                invocation.fallback_chain_requested or fallback_chain_requested
            )
            route_attempts = invocation.route_attempts or route_attempts
            source_receipt_id = invocation.source_receipt_id or source_receipt_id
            draft = parse_page_draft(invocation.text, plan=plan)
            return ProducedBatch(
                plan=plan,
                draft=validate_page_draft(draft, plan=plan, candidates=candidates, ledger=ledger),
                candidates=candidates,
                receipt=BatchReceipt(
                    batch_id=plan.batch_id,
                    status="success",
                    attempts=attempts,
                    provider=last_provider,
                    fallback_used=fallback_used,
                    is_substitute=is_substitute,
                    requested_primary=requested_primary,
                    resolved_tier=resolved_tier,
                    fallback_chain_requested=fallback_chain_requested,
                    route_attempts=route_attempts,
                    source_receipt_id=source_receipt_id,
                    rejection_reason=rejection_reason,
                ),
            )
        except ClosedCitationError as exc:
            rejection_reason = str(exc)
            prompt = (
                prompt
                + "\n提交被封闭引用闸拒绝。只从 Candidates 原样选择 selected_target_ids，"
                "不要输出任何 Markdown 链接；重新输出严格 JSON。"
            )
        except RouterDispatchError as exc:
            rejection_reason = f"{type(exc).__name__}: {exc}"
            requested_primary = exc.requested_primary or requested_primary
            resolved_tier = exc.resolved_tier or resolved_tier
            fallback_chain_requested = (
                exc.fallback_chain_requested or fallback_chain_requested
            )
            route_attempts = exc.route_attempts or route_attempts
            is_substitute = is_substitute or exc.is_substitute
            fallback_used = fallback_used or exc.is_substitute
            source_receipt_id = exc.source_receipt_id or source_receipt_id
            break
        except (ValueError, json.JSONDecodeError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            rejection_reason = f"{type(exc).__name__}: {exc}"
            break
    residual_reason = rejection_reason or "router returned no accepted draft"
    degraded = deterministic_degraded_draft(plan, cluster, residual_reason)
    # The deterministic page target is always in the closed set built by the pipeline.
    degraded = validate_page_draft(degraded, plan=plan, candidates=candidates, ledger=ledger)
    return ProducedBatch(
        plan=plan,
        draft=degraded,
        candidates=candidates,
        receipt=BatchReceipt(
            batch_id=plan.batch_id,
            status="degraded",
            attempts=attempts,
            provider="deterministic-fallback",
            fallback_used=fallback_used,
            is_substitute=is_substitute,
            requested_primary=requested_primary,
            resolved_tier=resolved_tier,
            fallback_chain_requested=fallback_chain_requested,
            route_attempts=route_attempts,
            source_receipt_id=source_receipt_id,
            rejection_reason=rejection_reason,
            residual_reason=residual_reason,
        ),
    )
