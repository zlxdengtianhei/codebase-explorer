"""Configured public provider command for module-first production.

CBE owns claims and delivery verification. The provider command is an external
executable supplied by the host; this module never imports host-private code.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from cbe import module_facts, module_workflow
from cbe.store import LedgerStore, TaskRecord


def _config(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("argv"), list) or not value["argv"]:
        raise ValueError("provider config needs a nonempty argv array")
    if not all(isinstance(part, str) and part for part in value["argv"]):
        raise ValueError("provider argv must contain nonempty strings")
    for key in ("cwd", "receipt_dir"):
        if not isinstance(value.get(key), str) or not Path(value[key]).is_absolute():
            raise ValueError(f"provider config {key} must be an absolute path")
    model = value.get("model", "gpt-6-sol")
    if not isinstance(model, str) or not model:
        raise ValueError("provider config model must be a nonempty string")
    if "max_output_tokens" in value:
        limit = value["max_output_tokens"]
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("provider config max_output_tokens must be a positive integer")
    return value


def _format_argv(template: list[str], values: dict[str, str]) -> list[str]:
    try:
        return [part.format_map(values) for part in template]
    except KeyError as exc:
        raise ValueError(f"unknown provider command placeholder: {exc}") from exc


def _stamp_requested_model(run_dir: Path, call_id: str, model: str) -> None:
    from cbe.store import LedgerStore, mark_call

    def mutate(current: dict[str, Any]) -> dict[str, Any]:
        if call_id not in (current.get("calls") or {}):
            raise ValueError(f"unknown call to stamp: {call_id}")
        mark_call(current, call_id, extra={"requested_model": model})
        return current

    LedgerStore(run_dir).mutate(mutate)


def produce(run_dir: Path, ident: str, *, scope: str, kind: str, owner: str,
            provider_config: Path, resume: bool = False,
            max_source_tokens: int = 24000,
            full_context: bool = False,
            review_ids: list[str] | None = None,
            review_question: str | None = None) -> dict[str, Any]:
    """Run one claimed task once or reconcile a prior call with durable evidence.

    A missing receipt on resume is ambiguous: no automatic resend is allowed.
    """
    if scope not in {"fact", "module", "system"} or kind not in {"author", "review"}:
        raise ValueError("scope must be fact/module/system and kind must be author/review")
    run_dir = Path(run_dir).resolve()
    config = _config(provider_config)
    task_id = (f"task:{scope}_{kind}" if scope == "system"
               else f"task:{'fact' if scope == 'fact' else 'module'}_{kind}:{ident}")
    ledger = LedgerStore(run_dir).open()
    task_raw = (ledger.get("tasks") or {}).get(task_id)
    if task_raw is None:
        raise ValueError(f"unknown production task: {task_id}")
    task = TaskRecord.from_dict(task_raw)
    if task.state == "committed":
        return {"task_id": task_id, "state": "committed", "idempotent": True}
    if resume:
        if task.state != "leased" or not task.extra.get("call_id"):
            raise ValueError("resume needs a leased task with a prepared call")
        call = ledger["calls"][task.extra["call_id"]]
        claimed = {"task_id": task_id, "call_id": call["call_id"],
                   "prompt_path": call["extra"]["prompt_path"],
                   "result_path": str(run_dir / "raw" / f"{call['call_id']}.json")}
    else:
        if task.state == "leased":
            raise ValueError("task already leased; inspect its receipt and use --resume, never resend")
        if scope == "fact":
            claimed = module_facts.claim(run_dir, ident, owner=owner, kind=kind,
                                         full_context=full_context, review_ids=review_ids,
                                         review_question=review_question)
        elif scope == "system":
            from cbe import system_workflow
            claimed = system_workflow.claim(run_dir, kind=f"system_{kind}", owner=owner)
        else:
            claimed = module_workflow.claim(run_dir, ident, owner=owner,
                                            kind=f"module_{kind}",
                                            max_source_tokens=max_source_tokens)
    call_id = claimed["call_id"]
    receipt = Path(config["receipt_dir"]) / f"{call_id}.json"
    result = Path(claimed["result_path"])
    evidence_path = (run_dir / "reviews" / f"{call_id}.md"
                     if kind == "review" else None)
    if resume:
        if not receipt.is_file() or not result.is_file():
            return {"task_id": task_id, "call_id": call_id,
                    "state": "needs_reconciliation", "reason": "receipt or raw output missing; no resend"}
    else:
        if receipt.exists() or result.exists():
            raise ValueError("new claim output paths already exist; no overwrite or resend")
        model = str(config.get("model", "gpt-6-sol"))
        values = {"model": model, "call_id": call_id,
                  "prompt_path": claimed["prompt_path"], "receipt_path": str(receipt),
                  "cwd": config["cwd"], "sandbox": "workspace-write",
                  "timeout": str(config.get("timeout", 900)),
                  "result_path": str(result)}
        argv = _format_argv(config["argv"], values)
        if config.get("max_output_tokens") and not any(
            part == "--max-output-tokens" for part in argv
        ):
            argv += ["--max-output-tokens", str(config["max_output_tokens"])]
        # Stamp the requested model on the prepared call so delivery verification
        # can bind the observed model to what this producer actually configured.
        _stamp_requested_model(run_dir, call_id, model)
        if evidence_path and config.get("artifact_argv"):
            argv += _format_argv(config["artifact_argv"], {**values, "evidence_path": str(evidence_path)})
        receipt.parent.mkdir(parents=True, exist_ok=True)
        result.parent.mkdir(parents=True, exist_ok=True)
        call_dir = run_dir / "provider" / call_id
        call_dir.mkdir(parents=True, exist_ok=True)
        with result.open("wb") as stdout, (call_dir / "stderr.log").open("wb") as stderr:
            completed = subprocess.run(argv, cwd=config["cwd"], stdout=stdout, stderr=stderr,
                                       check=False, timeout=int(config.get("timeout", 900)) + 60)
        if completed.returncode != 0:
            provider_status = None
            if receipt.is_file():
                try:
                    provider_status = json.loads(receipt.read_text(encoding="utf-8")).get("status")
                except (OSError, ValueError):
                    pass
            if provider_status in {"completed", "artifact_unverified"}:
                module_facts.mark_delivered(run_dir, task_id, receipt)
            return {"task_id": task_id, "call_id": call_id, "state": "provider_failed",
                    "returncode": completed.returncode, "receipt_path": str(receipt),
                    "provider_status": provider_status,
                    "stderr_path": str(call_dir / "stderr.log")}
    if evidence_path and not evidence_path.exists():
        # Text-only transports cannot write a reviewer artifact. Keep their
        # verbatim response under the deterministic evidence path, including
        # when resuming a completed dispatch after an interrupted import.
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(result.read_bytes())
    module_facts.mark_delivered(run_dir, task_id, receipt)
    if scope == "fact":
        imported = module_facts.import_result(run_dir, task_id, result)
    elif scope == "system":
        from cbe import system_workflow
        imported = system_workflow.import_result(run_dir, task_id, result)
    else:
        imported = module_workflow.import_result(run_dir, task_id, result)
    return {**imported, "call_id": call_id, "receipt_path": str(receipt),
            "result_path": str(result)}
