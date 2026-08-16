"""Enrich library + flow pages via the fallback-aware CLI router.

Default primary ``grok-build:xhigh``, fallback ``gpt:luna-max``. A downgrade
is recorded in the cost log; it is never silent. If the whole chain fails the
deterministic page stays and a residual is appended.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.gates import GateContext, compute_page_hash
from src.synthesis.variant_a.models import (
    RejectedClaim,
    SynthesisClaim,
    SynthesisClaimKind,
    SynthesisPage,
    SynthesisResidual,
)
from src.synthesis.variant_a.submit import submit_claims


PRIMARY_TIER = "grok-build:xhigh"
FALLBACK_TIERS = ("gpt:luna-max",)
ENRICH_PAGE_IDS = frozenset({"library", "flow-main"})


class CostLog:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record(self, row: dict[str, Any]) -> None:
        self.calls.append(row)

    def as_json(self) -> dict[str, Any]:
        ok = sum(1 for row in self.calls if row.get("ok"))
        return {
            "calls": self.calls,
            "n_calls": len(self.calls),
            "n_ok": ok,
            "n_failed": len(self.calls) - ok,
            "primary": PRIMARY_TIER,
            "fallback": list(FALLBACK_TIERS),
            "used_fallback": any(row.get("used_fallback") for row in self.calls),
            "latency_s_total": round(sum(float(row.get("latency_s") or 0) for row in self.calls), 4),
        }


def _monorepo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tools" / "cli_agent" / "router.py").exists():
            return parent
    raise RuntimeError("cannot locate context-infra tools/cli_agent/router.py")


def _parse_claims(content: str) -> list[dict[str, object]]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return []
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(payload, dict) and isinstance(payload.get("result_text"), str):
        inner = payload["result_text"].strip()
        try:
            payload = json.loads(inner)
        except json.JSONDecodeError:
            payload = payload
    rows = payload.get("claims") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _first_sentence(text: str) -> str:
    clipped = " ".join(text.split())
    for sep in ("。", ". ", "！", "!"):
        if sep in clipped:
            return clipped.split(sep, 1)[0] + ("" if sep == ". " else sep)
    return clipped[:240]


def build_enrich_prompt(page: SynthesisPage, ledger: SemanticLedger, ctx: GateContext) -> str:
    citeable = []
    for symbol_id in page.cited_symbol_ids[:12]:
        record = ledger.symbols[symbol_id]
        text = record.explanation.text if record.explanation else ""
        citeable.append(
            {
                "symbol_id": symbol_id,
                "name": record.qualified_name,
                "first_sentence": _first_sentence(text),
            }
        )
    surfaces = [
        {"surface_id": sid, "name": ctx.surface.by_id[sid].name}
        for sid in page.cited_surface_ids[:20]
        if sid in ctx.surface.by_id
    ]
    packet = {
        "page_id": page.page_id,
        "page_kind": page.page_kind.value,
        "symbols": citeable,
        "surfaces": surfaces,
        "existing_claim_ids": [claim.claim_id for claim in page.claims],
    }
    return (
        "Write at most two additional overview/role claims for one documentation page.\n"
        "Use ONLY the provided symbol_id and surface_id values.\n"
        "Every sentence must cite at least one of them.\n"
        "Do not invent names that are not in the lists.\n"
        "Each text <= 280 characters.\n"
        "Return JSON only, no markdown, no tool use, no file edits.\n"
        'Shape: {"claims":[{"claim_id":"...","text":"...",'
        '"cited_symbol_ids":[],"cited_surface_ids":[],"claim_kind":"overview"}]}\n\n'
        + json.dumps(packet, ensure_ascii=False)
    )


def call_router(
    prompt: str,
    *,
    task_name: str,
    prompt_path: Path,
    log_path: Path,
    cost: CostLog,
    timeout_s: int = 240,
) -> dict[str, Any]:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    root = _monorepo_root()
    scratch = prompt_path.parent / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        "-m",
        "tools.cli_agent.router",
        "--primary",
        PRIMARY_TIER,
        "--fallback",
        *FALLBACK_TIERS,
        "--task-name",
        task_name,
        "--workdir",
        str(scratch),
        "--timeout",
        str(timeout_s),
        "--max-turns",
        "6",
    ]
    t0 = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=str(root),
            env=env,
            timeout=timeout_s + 30,
            check=False,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(stdout + "\n--- STDERR ---\n" + stderr, encoding="utf-8")
        used_fallback = False
        try:
            envelope = json.loads(stdout)
            used_fallback = str(envelope.get("tier_used") or "") not in {"", PRIMARY_TIER}
            if str((envelope.get("route_decision") or {}).get("fallback_status") or "") not in {
                "",
                "NONE_ATTEMPTED",
                "NONE",
            }:
                if str(envelope.get("tier_used") or "") != PRIMARY_TIER:
                    used_fallback = True
            else:
                used_fallback = str(envelope.get("tier_used") or PRIMARY_TIER) != PRIMARY_TIER
        except json.JSONDecodeError:
            used_fallback = False
        row = {
            "ok": proc.returncode == 0 and bool(stdout.strip()),
            "returncode": proc.returncode,
            "latency_s": round(time.perf_counter() - t0, 4),
            "used_fallback": used_fallback,
            "primary": PRIMARY_TIER,
            "fallback": list(FALLBACK_TIERS),
            "task_name": task_name,
            "prompt_path": str(prompt_path),
            "log_path": str(log_path),
            "stdout_chars": len(stdout),
            "failure_mode": None if proc.returncode == 0 else f"exit_{proc.returncode}",
        }
        cost.record(row)
        return {**row, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        row = {
            "ok": False,
            "latency_s": round(time.perf_counter() - t0, 4),
            "used_fallback": False,
            "failure_mode": "timeout",
            "task_name": task_name,
        }
        cost.record(row)
        return row


def merge_enriched(
    page: SynthesisPage,
    extra: SynthesisPage,
    ctx: GateContext,
) -> SynthesisPage:
    by_id = {claim.claim_id: claim for claim in page.claims}
    for claim in extra.claims:
        by_id.setdefault(claim.claim_id, claim)
    merged_claims = tuple(by_id.values())
    cited_sym = tuple(dict.fromkeys((*page.cited_symbol_ids, *extra.cited_symbol_ids)))
    cited_surf = tuple(dict.fromkeys((*page.cited_surface_ids, *extra.cited_surface_ids)))
    digest = compute_page_hash(
        source_revision=ctx.ledger.source_revision,
        surface=ctx.surface,
        cited_symbol_ids=cited_sym,
        cited_surface_ids=cited_surf,
        ledger=ctx.ledger,
    )
    return page.model_copy(
        update={
            "producer": f"{page.producer}+router:{PRIMARY_TIER}",
            "cited_symbol_ids": cited_sym,
            "cited_surface_ids": cited_surf,
            "explained_content_hash": digest,
            "claims": merged_claims,
        }
    )


def enrich_pages(
    pages: list[SynthesisPage],
    *,
    ledger: SemanticLedger,
    ctx: GateContext,
    cost: CostLog,
    work_dir: Path,
) -> tuple[list[SynthesisPage], list[RejectedClaim], list[SynthesisResidual]]:
    rejected: list[RejectedClaim] = []
    residuals: list[SynthesisResidual] = []
    out: list[SynthesisPage] = []
    for page in pages:
        if page.page_id not in ENRICH_PAGE_IDS:
            out.append(page)
            continue
        prompt = build_enrich_prompt(page, ledger, ctx)
        log_path = work_dir / "prompts" / f"enrich_{page.page_id}.log"
        prompt_path = work_dir / "prompts" / f"enrich_{page.page_id}.md"
        if log_path.is_file():
            cached = log_path.read_text(encoding="utf-8")
            if _parse_claims(cached):
                cost.record(
                    {
                        "ok": True,
                        "latency_s": 0.0,
                        "used_fallback": False,
                        "task_name": f"va-enrich-{page.page_id}",
                        "reused_log": str(log_path),
                        "primary": PRIMARY_TIER,
                    }
                )
                result = {"ok": True, "stdout": cached, "used_fallback": False}
            else:
                result = call_router(
                    prompt,
                    task_name=f"va-enrich-{page.page_id}",
                    prompt_path=prompt_path,
                    log_path=log_path,
                    cost=cost,
                )
        else:
            result = call_router(
                prompt,
                task_name=f"va-enrich-{page.page_id}",
                prompt_path=prompt_path,
                log_path=log_path,
                cost=cost,
            )
        if result.get("used_fallback"):
            residuals.append(
                SynthesisResidual(
                    residual_id=f"llm-fallback-{page.page_id}",
                    reason=f"primary {PRIMARY_TIER} missed; used fallback {FALLBACK_TIERS}",
                )
            )
        if not result.get("ok"):
            residuals.append(
                SynthesisResidual(
                    residual_id=f"llm-degraded-{page.page_id}",
                    reason=f"router failed ({result.get('failure_mode')}); kept deterministic claims",
                )
            )
            out.append(page)
            continue
        drafts: list[SynthesisClaim] = []
        for raw in _parse_claims(str(result.get("stdout") or "")):
            kind_raw = str(raw.get("claim_kind") or "overview")
            try:
                kind = SynthesisClaimKind(kind_raw)
            except ValueError:
                kind = SynthesisClaimKind.OVERVIEW
            if kind is SynthesisClaimKind.FLOW_STEP:
                continue
            text = str(raw.get("text") or "").strip()
            if not text:
                continue
            drafts.append(
                SynthesisClaim(
                    claim_id=str(raw.get("claim_id") or f"llm-{page.page_id}-{len(drafts)}"),
                    text=text,
                    cited_symbol_ids=tuple(
                        str(item) for item in (raw.get("cited_symbol_ids") or []) if isinstance(item, str)
                    ),
                    cited_surface_ids=tuple(
                        str(item) for item in (raw.get("cited_surface_ids") or []) if isinstance(item, str)
                    ),
                    claim_kind=kind,
                )
            )
        extra, fails = submit_claims(
            page_id=page.page_id,
            page_kind=page.page_kind,
            producer=f"router:{PRIMARY_TIER}",
            drafts=drafts,
            ctx=ctx,
        )
        rejected.extend(fails)
        if extra is None:
            residuals.append(
                SynthesisResidual(
                    residual_id=f"llm-no-claim-{page.page_id}",
                    reason="router returned no claim that passed S1-S5; kept deterministic page",
                )
            )
            out.append(page)
            continue
        out.append(merge_enriched(page, extra, ctx))
    return out, rejected, residuals
