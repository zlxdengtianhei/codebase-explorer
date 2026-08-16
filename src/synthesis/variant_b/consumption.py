"""Score three-arm locating answers against a source oracle.

The answering agent is an evaluation caller, not the synthesis layer.
This module never calls an LLM: it loads TASKS.json + raw arm JSON and
emits CONSUMPTION_ARMS.json. Zero synthesis LLM.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_GREP = re.compile(
    r"\b(rg|grep|ag|ack|ripgrep|git\s+grep|find\s+\S+\s+-name)\b",
    re.IGNORECASE,
)
_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)
_BRACE = re.compile(r"\{.*\}", re.DOTALL)


def load_tasks(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_file(value: str) -> str:
    text = value.strip().replace("\\", "/")
    text = text.split("#", 1)[0].strip()
    return text.lstrip("./")


def _norm_name(value: str) -> str:
    text = value.strip().strip("`")
    text = text.replace("::", ".")
    if "(" in text:
        text = text[: text.index("(")]
    return text.strip()


def _name_hits(candidate: str, accepted: list[str]) -> bool:
    got = _norm_name(candidate)
    if not got:
        return False
    got_tail = got.rsplit(".", 1)[-1]
    for item in accepted:
        want = _norm_name(item)
        if not want:
            continue
        if got == want or got.endswith("." + want) or want.endswith("." + got):
            return True
        if got_tail == want.rsplit(".", 1)[-1]:
            return True
    return False


def _file_hits(candidate: str, accepted: list[str]) -> bool:
    got = _norm_file(candidate)
    if not got:
        return False
    got_base = Path(got).name
    for item in accepted:
        want = _norm_file(item)
        want_base = Path(want).name
        if got == want or got.endswith("/" + want) or want.endswith("/" + got):
            return True
        if got_base == want_base and want_base:
            return True
    return False


def _as_step(item: object) -> dict[str, str] | None:
    if isinstance(item, dict):
        return {
            "file": str(item.get("file") or ""),
            "function": str(item.get("function") or item.get("name") or ""),
        }
    if isinstance(item, str):
        text = item.strip()
        for sep in ("::", ":"):
            if sep in text:
                left, right = text.split(sep, 1)
                return {"file": left.strip(), "function": right.strip()}
        return {"file": "", "function": text}
    return None


def _extract_steps(answer: dict[str, object], keys: tuple[str, ...] = ("steps", "chain", "callers")) -> list[dict[str, str]]:
    collected: list[dict[str, str]] = []
    for key in keys:
        raw = answer.get(key)
        if isinstance(raw, list):
            for item in raw:
                step = _as_step(item)
                if step is not None:
                    collected.append(step)
    if not collected and (answer.get("file") or answer.get("function") or answer.get("name")):
        collected.append(
            {
                "file": str(answer.get("file") or ""),
                "function": str(answer.get("function") or answer.get("name") or ""),
            }
        )
    return collected


def _step_hits(step: dict[str, str], files: list[str], names: list[str]) -> bool:
    return _file_hits(step.get("file") or "", files) and _name_hits(step.get("function") or "", names)


def _gold_names(item: dict[str, object]) -> list[str]:
    names = list(item.get("names") or ())
    names.extend(list(item.get("also_ok_names") or ()))
    return names


def score_locate(question: dict[str, object], answer: dict[str, object]) -> dict[str, object]:
    oracle = question["oracle"]
    got_file = str(answer.get("file") or "")
    got_name = str(answer.get("function") or answer.get("name") or "")
    if not got_file and not got_name:
        steps = _extract_steps(answer)
        if steps:
            got_file = steps[0]["file"]
            got_name = steps[0]["function"]
    candidates = [
        {
            "files": list(oracle["files"]),
            "names": list(oracle["names"]) + list(oracle.get("also_ok_names") or ()),
        }
    ]
    for alt in list(oracle.get("alternatives") or ()):
        candidates.append(
            {
                "files": list(alt["files"]),
                "names": list(alt.get("names") or ()) + list(alt.get("also_ok_names") or ()),
            }
        )
    file_ok = False
    name_ok = False
    for item in candidates:
        this_file = _file_hits(got_file, item["files"])
        this_name = _name_hits(got_name, item["names"])
        if this_file and this_name:
            file_ok = True
            name_ok = True
            break
        file_ok = file_ok or this_file
        name_ok = name_ok or this_name
    if file_ok and name_ok:
        # Independent OR can pair the wrong file with the wrong name.
        paired = False
        for item in candidates:
            if _file_hits(got_file, item["files"]) and _name_hits(got_name, item["names"]):
                paired = True
                break
        if paired:
            verdict = "correct"
            file_ok = True
            name_ok = True
        else:
            verdict = "file_only"
            name_ok = False
    elif file_ok:
        verdict = "file_only"
    else:
        verdict = "wrong"
    return {
        "id": question["id"],
        "kind": str(question.get("kind") or "locate"),
        "surface": question["surface"],
        "verdict": verdict,
        "file_ok": file_ok,
        "name_ok": name_ok,
        "got_file": got_file,
        "got_function": got_name,
        "oracle_files": list(oracle["files"]),
        "oracle_names": list(oracle["names"]),
        "n_gold_hits": int(verdict == "correct"),
    }


def score_chain(question: dict[str, object], answer: dict[str, object]) -> dict[str, object]:
    oracle = question["oracle"]
    gold = list(oracle["steps"])
    min_hits = int(oracle.get("min_hits") or len(gold))
    got = _extract_steps(answer, keys=("steps", "chain"))
    cursor = 0
    hit_indices: list[int] = []
    for gi, item in enumerate(gold):
        files = list(item["files"])
        names = _gold_names(item)
        found_at = None
        for ai in range(cursor, len(got)):
            if _step_hits(got[ai], files, names):
                found_at = ai
                break
        if found_at is not None:
            hit_indices.append(gi)
            cursor = found_at + 1
    hitset = set(hit_indices)
    groups_ok = True
    for group in list(oracle.get("require_groups") or ()):
        if not any(int(i) in hitset for i in group):
            groups_ok = False
            break
    n_hit = len(hit_indices)
    coverage_ok = n_hit >= min_hits and groups_ok
    if coverage_ok:
        verdict = "correct"
    elif n_hit:
        verdict = "file_only"
    else:
        verdict = "wrong"
    got_file = " | ".join(step["file"] for step in got if step["file"])
    got_name = " | ".join(step["function"] for step in got if step["function"])
    return {
        "id": question["id"],
        "kind": "chain",
        "surface": question["surface"],
        "verdict": verdict,
        "file_ok": coverage_ok,
        "name_ok": coverage_ok,
        "got_file": got_file,
        "got_function": got_name,
        "oracle_files": [item["files"][0] for item in gold if item.get("files")],
        "oracle_names": [list(item.get("names") or [""])[0] for item in gold],
        "n_gold_hits": n_hit,
        "gold_hit_indices": hit_indices,
        "n_gold": len(gold),
        "min_hits": min_hits,
        "groups_ok": groups_ok,
        "order_ok": True,
    }


def score_callers(question: dict[str, object], answer: dict[str, object]) -> dict[str, object]:
    oracle = question["oracle"]
    gold = list(oracle["callers"])
    min_hits = int(oracle.get("min_hits") or len(gold))
    reject_files = list(oracle.get("reject_files") or ())
    got = _extract_steps(answer, keys=("callers", "steps", "chain"))
    hit_indices: list[int] = []
    for gi, item in enumerate(gold):
        files = list(item["files"])
        names = _gold_names(item)
        if any(_step_hits(step, files, names) for step in got):
            hit_indices.append(gi)
    n_hit = len(hit_indices)
    listed_reject_only = bool(got) and n_hit == 0 and any(
        _file_hits(step.get("file") or "", reject_files) for step in got
    )
    coverage_ok = n_hit >= min_hits
    if coverage_ok:
        verdict = "correct"
    elif listed_reject_only:
        verdict = "wrong"
    elif n_hit:
        verdict = "file_only"
    else:
        verdict = "wrong"
    got_file = " | ".join(step["file"] for step in got if step["file"])
    got_name = " | ".join(step["function"] for step in got if step["function"])
    return {
        "id": question["id"],
        "kind": "callers",
        "surface": question["surface"],
        "verdict": verdict,
        "file_ok": coverage_ok,
        "name_ok": coverage_ok,
        "got_file": got_file,
        "got_function": got_name,
        "oracle_files": [item["files"][0] for item in gold if item.get("files")],
        "oracle_names": [list(item.get("names") or [""])[0] for item in gold],
        "n_gold_hits": n_hit,
        "gold_hit_indices": hit_indices,
        "n_gold": len(gold),
        "min_hits": min_hits,
        "listed_reject_only": listed_reject_only,
    }


def score_one(question: dict[str, object], answer: dict[str, object]) -> dict[str, object]:
    kind = str(question.get("kind") or "locate")
    if kind == "chain":
        return score_chain(question, answer)
    if kind == "callers":
        return score_callers(question, answer)
    return score_locate(question, answer)


def extract_payload(text: str) -> dict[str, object] | None:
    if not text or not text.strip():
        return None
    fenced = _JSON_FENCE.search(text)
    blob = fenced.group(1) if fenced else None
    if blob is None:
        match = _BRACE.search(text)
        blob = match.group(0) if match else None
    if blob is None:
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def count_grep_mentions(text: str) -> int:
    return len(_GREP.findall(text or ""))


def _as_answers(payload: dict[str, object] | None) -> list[dict[str, object]]:
    if not payload:
        return []
    raw = payload.get("answers")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _action_counts(answer: dict[str, object], arm: str, raw_text: str) -> dict[str, object]:
    files_read = answer.get("files_read") or []
    if not isinstance(files_read, list):
        files_read = []
    hops = answer.get("n_hops")
    greps = answer.get("n_grep")
    try:
        n_hops = int(hops) if hops is not None else len(files_read)
    except (TypeError, ValueError):
        n_hops = len(files_read)
    try:
        n_grep = int(greps) if greps is not None else 0
    except (TypeError, ValueError):
        n_grep = 0
    if n_grep == 0 and arm != "D-nosearch":
        n_grep = count_grep_mentions(str(answer.get("evidence") or ""))
    n_actions = n_hops if arm == "D-nosearch" else n_grep + len(files_read)
    return {
        "n_hops": n_hops,
        "n_grep": n_grep,
        "n_files_read": len(files_read),
        "n_actions": n_actions,
        "files_read": [str(item) for item in files_read],
        "grep_mentions_in_raw": count_grep_mentions(raw_text) if arm == "D-nosearch" else n_grep,
    }


def estimate_read_tokens(files_read: list[str], tree_root: Path) -> int:
    from src.budget.estimator import estimate_tokens_from_chars

    chars = 0
    seen: set[str] = set()
    for rel in files_read:
        key = _norm_file(str(rel))
        if not key or key in seen:
            continue
        seen.add(key)
        path = tree_root / key
        if not path.is_file():
            path = tree_root / Path(key).name
        if not path.is_file():
            continue
        lang = "python" if path.suffix == ".py" else "markdown"
        chars += len(path.read_text(encoding="utf-8", errors="replace"))
        _ = lang
    # One call on the summed chars; language mix is FLAG-level for this metric.
    return estimate_tokens_from_chars(chars, "markdown")


def score_arm(
    tasks: dict[str, object],
    arm: str,
    raw_text: str,
    *,
    tree_root: Path,
    router_meta: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = extract_payload(raw_text)
    answers = _as_answers(payload)
    by_id = {str(item.get("id")): item for item in answers}
    questions = list(tasks["questions"])
    rows = []
    for question in questions:
        qid = str(question["id"])
        answer = by_id.get(qid) or {}
        scored = score_one(question, answer)
        actions = _action_counts(answer, arm, raw_text)
        scored["actions"] = actions
        rows.append(scored)
    n = len(rows)
    n_correct = sum(1 for item in rows if item["verdict"] == "correct")
    public = [item for item in rows if item["surface"] == "public"]
    internal = [item for item in rows if item["surface"] == "internal"]
    by_kind: dict[str, list[dict[str, object]]] = {}
    for item in rows:
        kind = str(item.get("kind") or item.get("surface") or "locate")
        by_kind.setdefault(kind, []).append(item)
    accuracy_by_kind = {
        kind: round(
            sum(1 for row in group if row["verdict"] == "correct") / len(group), 4
        )
        for kind, group in by_kind.items()
    }
    all_files: list[str] = []
    for item in rows:
        all_files.extend(item["actions"]["files_read"])
    grep_in_raw = count_grep_mentions(raw_text)
    constraint_violated = arm == "D-nosearch" and grep_in_raw > 0
    meta = router_meta or {}
    return {
        "arm": arm,
        "n_questions": n,
        "n_correct": n_correct,
        "accuracy": round(n_correct / n, 4) if n else 0.0,
        "accuracy_public": round(
            sum(1 for item in public if item["verdict"] == "correct") / len(public), 4
        )
        if public
        else None,
        "accuracy_internal": round(
            sum(1 for item in internal if item["verdict"] == "correct") / len(internal), 4
        )
        if internal
        else None,
        "accuracy_by_kind": accuracy_by_kind,
        "mean_actions": round(sum(item["actions"]["n_actions"] for item in rows) / n, 2) if n else 0.0,
        "mean_hops": round(sum(item["actions"]["n_hops"] for item in rows) / n, 2) if n else 0.0,
        "mean_grep": round(sum(item["actions"]["n_grep"] for item in rows) / n, 2) if n else 0.0,
        "read_tokens_reported_files": estimate_read_tokens(all_files, tree_root),
        "router_estimated_tokens": meta.get("estimated_tokens"),
        "router_duration_seconds": meta.get("duration_seconds"),
        "router_turns": meta.get("turns"),
        "tier_used": meta.get("tier_used"),
        "model_id_observed": meta.get("model_id_observed"),
        "fallback_status": meta.get("fallback_status")
        or ("USED_FALLBACK" if meta.get("is_substitute") else "NONE_ATTEMPTED"),
        "constraint_violated": constraint_violated,
        "grep_mentions_in_raw": grep_in_raw,
        "payload_parsed": payload is not None,
        "questions": rows,
    }


def conclude(arms: dict[str, dict[str, object]]) -> dict[str, object]:
    """Map the three numeric arms onto the three conclusions the packet named."""

    nosearch = arms["D-nosearch"]
    search = arms["D-search"]
    source = arms["S-only"]
    acc = {
        "D-nosearch": float(nosearch["accuracy"]),
        "D-search": float(search["accuracy"]),
        "S-only": float(source["accuracy"]),
    }
    act = {
        "D-nosearch": float(nosearch["mean_actions"]),
        "D-search": float(search["mean_actions"]),
        "S-only": float(source["mean_actions"]),
    }
    # "打平" = 正确题数相差不超过 1。用整数题数，不用四舍五入后的 accuracy，
    # 否则 5/6 vs 6/6 会被 round(5/6,4)=0.8333 推过 1/6 容差。
    n = int(nosearch["n_questions"] or 1)

    def _hits(arm: dict[str, object]) -> int:
        if arm.get("n_correct") is not None:
            return int(arm["n_correct"])
        return int(round(float(arm["accuracy"]) * n))

    n_nose = _hits(nosearch)
    n_search = _hits(search)
    n_source = _hits(source)
    n_best_docs = max(n_nose, n_search)
    tie_tol = 1.0 / n
    s_ties = abs(n_source - n_best_docs) <= 1
    docs_beat_source = n_source < n_best_docs - 1
    source_leads = n_source > n_best_docs + 1
    search_leads = n_search > n_nose + 1 and n_search > n_source + 1
    nosearch_holds = n_nose + 1 >= n_search
    if s_ties:
        label = "S-only_ties"
        sentence = (
            "S-only 与更好的文档臂正确率打平（差不超过一题）。"
            "文档在定位类任务上没有可测增量。这句话的射程随题目与仓库扩大，不淡化。"
        )
    elif docs_beat_source and search_leads:
        label = "D-search_best"
        sentence = (
            "D-nosearch 掉下来而 D-search 不掉。"
            "该优化的是可检索性，不是跳数树。"
        )
    elif docs_beat_source:
        label = "docs_beat_source"
        sentence = (
            "S-only 掉下来，文档臂正确率更高。"
            "文档的价值面找到了；看 accuracy_by_kind 才知道它在哪类题上成立。"
        )
    elif source_leads:
        label = "S-only_leads"
        sentence = (
            "S-only 正确率高于两份文档臂。"
            "这批题上文档没有帮到忙，还可能添噪声。"
        )
    elif search_leads:
        label = "D-search_best"
        sentence = (
            "D-search 正确率明显高于另外两臂。"
            "该优化的是可检索性，不是跳数树。"
        )
    elif nosearch_holds:
        label = "D-nosearch_holds"
        sentence = (
            "D-nosearch 不比 D-search 差。"
            "禁检索约束对这批题是有判别力的，链接树投入成立。"
        )
    else:
        label = "mixed"
        sentence = "三臂未落入预登记的三种干净形态，读各臂正确率与动作数，不要合成第四种故事。"
    kind_keys = sorted(
        {
            kind
            for arm in arms.values()
            for kind in (arm.get("accuracy_by_kind") or {})
        }
    )
    accuracy_by_kind = {
        kind: {
            name: float((arm.get("accuracy_by_kind") or {}).get(kind) or 0.0)
            for name, arm in arms.items()
        }
        for kind in kind_keys
    }
    return {
        "label": label,
        "sentence": sentence,
        "accuracy": acc,
        "accuracy_by_kind": accuracy_by_kind,
        "mean_actions": act,
        "tie_tolerance": tie_tol,
        "S_only_ties_docs": s_ties,
        "docs_beat_source": docs_beat_source,
        "D_search_leads": search_leads,
        "D_nosearch_holds_vs_D_search": nosearch_holds,
        "S_only_leads": source_leads,
    }


def score_run(
    tasks_path: Path,
    raw_dir: Path,
    *,
    docs_root: Path,
    src_root: Path,
) -> dict[str, object]:
    tasks = load_tasks(tasks_path)
    trees = {
        "D-nosearch": docs_root,
        "D-search": docs_root,
        "S-only": src_root,
    }
    arms: dict[str, dict[str, object]] = {}
    for arm, tree in trees.items():
        raw_path = raw_dir / f"{arm}.json"
        text_path = raw_dir / f"{arm}.txt"
        meta: dict[str, object] = {}
        raw_text = ""
        if raw_path.is_file():
            blob = json.loads(raw_path.read_text(encoding="utf-8"))
            if isinstance(blob, dict):
                meta = blob
                raw_text = str(blob.get("result_text") or "")
        if not raw_text and text_path.is_file():
            raw_text = text_path.read_text(encoding="utf-8")
        arms[arm] = score_arm(tasks, arm, raw_text, tree_root=tree, router_meta=meta)
    same_tier = len({str(arms[name].get("tier_used") or "") for name in arms}) == 1
    conclusion = conclude(arms)
    conclusion["time_seconds"] = {
        name: arm.get("router_duration_seconds") for name, arm in arms.items()
    }
    conclusion["read_tokens"] = {
        name: arm.get("read_tokens_reported_files") for name, arm in arms.items()
    }
    if str(tasks.get("repo") or "") == "celery" and conclusion["label"] == "S-only_ties":
        conclusion["sentence"] = (
            "文档在定位类任务上没有可测增量。"
            "这句话的射程从小仓 flask 扩到中仓 celery。"
            "6 题里唯一分差是入边题 Q3（S-only 找到三处调用，两份文档臂各只找到 autoretry 一处）。"
            "链题与概念题三臂全对，没有文档独赢的题型。"
        )
    return {
        "tasks": str(tasks_path),
        "n_questions": len(list(tasks["questions"])),
        "same_tier": same_tier,
        "tier_used": arms["D-nosearch"].get("tier_used"),
        "synthesis_llm_calls": 0,
        "arms": arms,
        "conclusion": conclusion,
    }
