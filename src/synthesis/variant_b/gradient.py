"""0/1/3/9 extra-LLM contrast. Not the mainline (mainline stays 0 calls).

Each budget writes a copy of the 0-call tree plus optional injected prose.
Metrics are mechanical: prose tokens, INDEX line count, symbol-name hit rate.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.pipeline import load_ledger, render_variant_b
from src.synthesis.variant_b.scan import density, page_line_counts
from src.synthesis.variant_b.text import first_sentence, one_liner, tail

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PROSE_MARK = re.compile(r"<<<PROSE>>>(.*?)<<<END>>>", re.S)
REPO = Path("/Users/lexuanzhang/context-infra")
PYTHON = "python3"


def _facts(repo: Path, ledger: SemanticLedger, traces_path: Path) -> dict[str, object]:
    traces = json.loads(traces_path.read_text(encoding="utf-8")) if traces_path.is_file() else {}
    top = []
    for symbol_id, record in list(ledger.symbols.items())[:40]:
        if record.is_fresh:
            top.append({"id": symbol_id, "one_liner": one_liner(record)})
    return {
        "repo_name": repo.name,
        "n_symbols": ledger.totals.symbols,
        "n_files": len(ledger.files),
        "traces": traces.get("traces", []),
        "sample_oneliners": top[:20],
        "known_tails": sorted({tail(symbol_id) for symbol_id in ledger.symbols})[:200],
    }


def _prompt(budget_index: int, role: str, facts: dict[str, object]) -> str:
    return (
        "你是对照实验的写作者，不是变体 B 的主线。只根据下面 JSON 事实写中文散文。\n"
        "禁止发明 JSON 里没有的符号名。禁止写系统角色/地位/架构重要性。\n"
        "输出必须是：\n<<<PROSE>>>\n(正文)\n<<<END>>>\n"
        f"本篇角色：{role}\n本篇序号：{budget_index}\n"
        "事实 JSON：\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)[:12000]
    )


def _invoke_router(prompt: str, workdir: Path, task_name: str) -> dict[str, object]:
    prompt_path = workdir / f"{task_name}.prompt.md"
    out_path = workdir / f"{task_name}.stdout.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    cmd = [
        PYTHON,
        "-m",
        "tools.cli_agent.router",
        "--primary",
        "grok-build:xhigh",
        "--fallback",
        "gpt:luna-max",
        "claude-zai:high",
        "--task-name",
        task_name,
        "--workdir",
        str(REPO),
        "--timeout",
        "300",
    ]
    try:
        completed = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=str(REPO),
            timeout=360,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "tier_used": None,
            "fallback": True,
            "error": str(exc),
            "prose": "",
            "cmd": cmd,
        }
    blob = (completed.stdout or "") + "\n" + (completed.stderr or "")
    out_path.write_text(blob, encoding="utf-8")
    marked = _PROSE_MARK.search(completed.stdout or "")
    prose = (marked.group(1).strip() if marked else (completed.stdout or "").strip())[:4000]
    fallback = False
    tier = "grok-build:xhigh"
    if '"fallback_status": "NONE_ATTEMPTED"' in blob or '"fallback_status":"NONE_ATTEMPTED"' in blob:
        fallback = False
    elif '"is_error": false' in blob or '"is_error":false' in blob:
        if '"tier_used": "grok-build:xhigh"' in blob or '"tier_used":"grok-build:xhigh"' in blob:
            fallback = False
        elif "gpt:luna-max" in blob and '"tier_used"' in blob:
            tier = "gpt:luna-max"
            fallback = True
        elif "claude-zai:high" in blob and '"tier_used"' in blob:
            tier = "claude-zai:high"
            fallback = True
    if "primary failed" in blob.lower() or "falling back" in blob.lower():
        fallback = True
    return {
        "ok": completed.returncode == 0 and bool(prose),
        "returncode": completed.returncode,
        "tier_used": tier,
        "fallback": fallback,
        "prose": prose,
        "error": None if completed.returncode == 0 else (completed.stderr or "")[-800],
        "cmd": cmd,
    }


def _name_hit_rate(prose: str, known: set[str]) -> float:
    tokens = [tok for tok in _IDENT.findall(prose) if len(tok) > 2]
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok in known)
    return round(hits / len(tokens), 4)


def _inject(index_path: Path, sections: list[str]) -> None:
    if not sections or not index_path.is_file():
        return
    text = index_path.read_text(encoding="utf-8")
    block = "\n\n## 对照散文（非主线）\n\n" + "\n\n".join(sections) + "\n"
    # Keep public-surface names in the first 60 lines: append at end.
    index_path.write_text(text.rstrip() + block, encoding="utf-8")


def run_gradient(
    repo_root: str | Path,
    ledger_path: Path,
    out_dir: Path,
    *,
    budgets: tuple[int, ...] = (0, 1, 3, 9),
) -> dict[str, object]:
    root = Path(repo_root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / "0"
    if not (base / "INDEX.md").is_file():
        render_variant_b(root, ledger_path, base)
    ledger = load_ledger(ledger_path, root)
    facts = _facts(root, ledger, base / "flow_traces.json")
    known = set(facts["known_tails"]) | {root.name}
    roles = [
        "用台账首句写一段「这是什么库」（≤120 字）",
        "为符号数最多的簇写一段功能说明（≤120 字）",
        "为符号数第二多的簇写一段功能说明（≤120 字）",
        "把主迹改写成四句请求/调用故事，每句点一个已有 tail",
        "为第三簇写功能说明",
        "为第四簇写功能说明",
        "为第五簇写功能说明",
        "写一段「从公共面进去该先读哪条迹」",
        "写一段残差/未解析绑定怎么读",
    ]
    curve: list[dict[str, object]] = []
    workdir = out_dir / "_prompts"
    workdir.mkdir(parents=True, exist_ok=True)

    need = max(budgets) if budgets else 0
    pool: list[dict[str, object]] = []
    for index in range(need):
        role = roles[index] if index < len(roles) else f"补充段落 {index+1}"
        result = _invoke_router(_prompt(index, role, facts), workdir, f"vb-g-{index}")
        row = {
            "index": index,
            "role": role,
            "ok": result["ok"],
            "tier_used": result["tier_used"],
            "fallback": result["fallback"],
            "error": result["error"],
            "prose": result["prose"],
            "prose_chars": len(result["prose"]),
            "name_hit_rate": _name_hit_rate(result["prose"], known),
        }
        pool.append(row)
        if result.get("fallback"):
            (workdir / f"FALLBACK_{index}.txt").write_text(
                json.dumps({k: v for k, v in result.items() if k != "prose"}, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )

    for budget in budgets:
        dest = out_dir / str(budget)
        if dest.resolve() != base.resolve():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(base, dest)
        used = pool[:budget]
        injected = [
            f"### 调用 {item['index']+1}\n\n{first_sentence(str(item['prose']))}\n\n{item['prose']}"
            for item in used
            if item["prose"]
        ]
        if injected:
            _inject(dest / "INDEX.md", injected)
        calls = [{k: v for k, v in item.items() if k != "prose"} for item in used]
        dens = density(dest)
        lines = page_line_counts(dest)
        curve.append(
            {
                "budget": budget,
                "llm_calls_requested": budget,
                "llm_calls_ok": sum(1 for item in calls if item["ok"]),
                "calls": calls,
                "index_lines": lines.get("INDEX.md"),
                "index_over_150": (lines.get("INDEX.md") or 0) > 150,
                "density": dens,
                "injected_sections": len(injected),
            }
        )
    report = {
        "variant": "B-gradient",
        "note": "对照数据。主线仍是 budget=0。",
        "curve": curve,
    }
    (out_dir / "CURVE.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
