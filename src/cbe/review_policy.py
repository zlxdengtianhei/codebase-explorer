"""Optional semantic review over mandatory import-time mechanical checks.

This module never invents a model call, delivery evidence, or reviewer. Existing
calls and strong review records are immutable when a future policy changes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from cbe.store import LedgerStore, iso

MODES = ("none", "sample", "full")
MECHANICAL = "mechanically_validated"
BOUNDARY = ("Mechanical checks cover schema, required fields, claim identity, frozen source "
            "and citation binding, coverage and structured syntax facts. Narrative semantics "
            "remain unverified without an independent semantic review. Sampling does not "
            "guarantee complete error detection; full LLM review is not a proof.")


def mode(ledger: dict) -> str | None:
    return (ledger.get("review_policy") or {}).get("mode")


def selected(ledger: dict, ids: list[str]) -> list[str]:
    current = mode(ledger)
    if current == "none":
        return []
    if current == "full":
        return list(ids)
    if current == "sample":
        # Stable and reproducible; at least one member in every nonempty batch.
        ordered = sorted(ids, key=lambda sid: hashlib.sha256(sid.encode()).digest())
        return ordered[:max(1, (len(ordered) + 9) // 10)] if ordered else []
    return list(ids)  # The historical strategy lives in module_facts.


def configure(run_dir: Path, requested: str | None, *, preview: dict | None = None) -> dict:
    store = LedgerStore(run_dir)
    before = preview if preview is not None else store.open()
    if requested is None:
        # Only a genuinely unstarted run gets the new default. No prepared call
        # is inferred unsent, and existing runs require explicit migration.
        if (mode(before) is not None or before.get("calls")
            or before.get("fact_workflow_version") and before.get("native_default_review_mode") != "none"):
            return before
        requested = "none"
    if requested not in MODES:
        raise ValueError("review mode must be none, sample or full")
    if mode(before) == requested:
        return before
    def update(ledger):
        policy = ledger.setdefault("review_policy", {"version": 1, "history": []})
        policy.setdefault("history", []).append({"previous": policy.get("mode", "legacy"),
            "mode": requested, "set_at": iso(), "scope": "future unleased obligations"})
        policy["mode"] = requested
        return ledger
    return store.mutate(update)


def _bound_author(ledger: dict, task: dict) -> bool:
    call = ledger.get("calls", {}).get((task.get("extra") or {}).get("call_id")) or {}
    return (task.get("state") == "committed" and call.get("state") == "imported"
            and call.get("task_id") == task.get("task_id")
            and call.get("input_hash") == task.get("input_hash")
            and bool(call.get("role_session_id"))
            and bool((call.get("extra") or {}).get("delivery_receipt")))


def _busy(ledger: dict, task: dict) -> bool:
    return task.get("state") == "leased" or any(call.get("task_id") == task.get("task_id")
        and call.get("state") in {"prepared", "sent", "uncertain"}
        for call in ledger.get("calls", {}).values())


def apply(run_dir: Path, *, preview: dict | None = None) -> dict:
    """Settle only hash-bound imported drafts; preserve historical risk and calls."""
    from cbe import module_facts, module_workflow, system_workflow
    from cbe.module_explanations import explanation_content_sha256
    store = LedgerStore(run_dir)
    if mode(preview if preview is not None else store.open()) is None:
        return {"changed": False}
    changed = []
    def update(ledger):
        current = mode(ledger)
        for tid, review in ledger.get("tasks", {}).items():
            kind = review.get("kind")
            if kind not in {"fact_review", "module_review", "system_review"} or _busy(ledger, review):
                continue
            extra = review.setdefault("extra", {})
            if extra.get("tombstone") or extra.get("superseded") or extra.get("canonical_delegations"):
                continue
            author = ledger["tasks"].get(tid.replace("_review", "_author", 1)) or {}
            if not _bound_author(ledger, author):
                continue
            if kind == "fact_review":
                if extra.get("audit_mode") or extra.get("reader_question"):
                    continue  # A new reader question is not satisfied by the old same-hash review.
                ids = list(review.get("input_ids") or [])
                if not ids or any(sid not in ledger.get("details", {}) for sid in ids):
                    continue
                # Do not erase actionable historical findings or targeted audits.
                targeted = set(extra.get("audit_review_ids") or [])
                targeted.update(item.get("symbol_id") for item in review.get("residual") or [] if isinstance(item, dict))
                if review.get("residual"):
                    targeted.update(ids)
                required = set(selected(ledger, ids)) | (targeted & set(ids))
                old_required = extra.get("required_review_ids")
                if old_required != sorted(required):
                    extra.setdefault("prior_policy_required_ids", old_required or [])
                    extra["required_review_ids"] = sorted(required)
                    changed.append(tid)
                for sid in ids:
                    detail = ledger["details"][sid]
                    evidence = ledger.get("fact_reviews", {}).get(sid) or {}
                    digest = module_facts._sha_json(detail)
                    if evidence.get("content_sha256") != digest:
                        continue
                    if sid not in required and evidence.get("state") == "author_fact":
                        evidence.update(state=MECHANICAL, checked_source=False,
                            mechanical_checks="import-contract-v1", semantic_review="not_performed")
                        changed.append(sid)
                outstanding = [sid for sid in required if
                    (ledger.get("fact_reviews", {}).get(sid) or {}).get("state") != "source_checked"]
                if outstanding and review.get("state") == "committed":
                    # The mode change adds semantic obligations; generation advances
                    # only after every prior call reached a terminal state.
                    review.update(state="pending", owner=None, lease_until=None,
                                  generation=review.get("generation", 0) + 1)
                    changed.append(tid)
                elif not outstanding and not review.get("residual") and all(module_facts.accepted_fact(ledger, sid) for sid in ids):
                    if review.get("state") != "committed":
                        review["state"] = "committed"
                        extra["completed_without_dispatch"] = "mechanical_policy_settlement"
                        changed.append(tid)
            else:
                ident = author.get("input_ids", ["system"])[0]
                draft = (ledger.get("module_records") or {}).get(ident) if kind == "module_review" else ledger.get("system_record")
                if not draft or draft.get("findings") or review.get("residual") or extra.get("reader_question"):
                    continue
                digest_fn = explanation_content_sha256 if kind == "module_review" else system_workflow._content_hash
                digest = digest_fn(draft["record"])
                strong = (draft["record"].get("review") or {}).get("decision") == "accepted"
                must_review = current == "full" or (current == "sample" and
                    (kind == "system_review" or bool(selected(ledger, sorted(ledger.get("module_records") or {})))
                     and ident in selected(ledger, sorted(ledger.get("module_records") or {}))))
                if strong:
                    continue
                if must_review:
                    if draft.get("state") == "accepted":
                        module_workflow.retain_accepted_history(draft)
                        draft["state"] = "draft"
                        draft["record"].pop("review", None)
                        review.update(state="pending", owner=None, lease_until=None,
                            generation=review.get("generation", 0) + 1, input_hash=digest)
                        changed.append(tid)
                elif draft.get("state") == "draft":
                    draft["record"]["review"] = {"decision": MECHANICAL,
                        "content_sha256": digest, "source_revision": ledger["source_revision"],
                        "mechanical_checks": "import-contract-v1", "semantic_review": "not_performed"}
                    draft["state"] = "accepted"
                    review["state"] = "committed"
                    extra["completed_without_dispatch"] = "mechanical_policy_settlement"
                    changed.append(tid)
        return ledger if changed else None
    store.mutate(update)
    return {"changed": bool(changed), "objects": changed}


def summary(ledger: dict) -> dict:
    return {"mode": mode(ledger) or "legacy", "mechanical_boundary": BOUNDARY,
            "mechanical_fact_count": sum(item.get("state") == MECHANICAL
                for item in (ledger.get("fact_reviews") or {}).values()),
            "semantic_guarantee": "none"}


def check_syntax_assertions(ledger: dict, symbol_id: str, value: object) -> None:
    """Compare explicitly structured claims to existing frozen AST projections.

    Absence of an assertion is not an assertion of absence. Dynamic/runtime
    claims are not accepted as syntax facts. Free prose is outside this proof.
    """
    if value is None:
        return
    from cbe.callable_contracts import contracts_for, prompt_contract
    from cbe.static_literals import _frozen_source, _top_level_literals, _literal_return_keys
    if not isinstance(value, dict) or set(value) - {"callable", "literals", "return_keys"}:
        raise ValueError("syntax_assertions must contain only callable, literals or return_keys")
    symbol = ledger["inventory"]["symbols"].get(symbol_id)
    if not symbol:
        raise ValueError("syntax_assertions need a canonical frozen symbol")
    if "callable" in value:
        actual = contracts_for(ledger, [symbol_id]).get(symbol_id)
        if actual is None or actual.get("status") != "complete" or value["callable"] != prompt_contract(actual):
            raise ValueError("syntax_assertions.callable disagrees with frozen declaration or is unknown")
    if "literals" in value or "return_keys" in value:
        if not symbol["path"].endswith(".py"):
            raise ValueError("literal/return-key syntax assertion is unsupported for this language")
        source = _frozen_source(ledger, symbol["path"])
        if "literals" in value:
            asserted = value["literals"]
            literals = _top_level_literals(source)
            if not isinstance(asserted, dict) or any(name not in literals or literals[name][0] != item
                for name, item in asserted.items()):
                raise ValueError("syntax_assertions.literals disagrees with frozen immutable literals")
        if "return_keys" in value:
            actual = _literal_return_keys(source, symbol)
            if actual is None or value["return_keys"] != actual["keys"]:
                raise ValueError("syntax_assertions.return_keys disagrees with frozen return syntax or is unknown")
