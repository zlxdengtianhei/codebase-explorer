"""Old vs new partition comparison for the 0-call evidence map."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_stats(index_path: Path) -> dict[str, object]:
    text = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    lines = text.splitlines()
    traces = 0
    in_func = False
    func_lines = 0
    for line in lines:
        if line.startswith("## 功能"):
            in_func = True
            continue
        if in_func and line.startswith("## "):
            in_func = False
        if in_func and line.startswith("- "):
            func_lines += 1
        if " → " in line and line.startswith("`"):
            traces += 1
    return {
        "lines": len(lines),
        "function_bullets": func_lines,
        "chars": len(text),
    }


def _largest_cluster(report: dict) -> dict[str, object]:
    clusters = report.get("clusters") or []
    if not clusters:
        return {"id": None, "symbols": 0, "share": None}
    total = sum(int(item.get("symbols") or 0) for item in clusters)
    top = max(clusters, key=lambda item: int(item.get("symbols") or 0))
    share = round(int(top.get("symbols") or 0) / total, 4) if total else None
    return {
        "id": top.get("id") or top.get("slug"),
        "display_or_slug": top.get("slug"),
        "symbols": top.get("symbols"),
        "files": top.get("files"),
        "share_of_clustered_symbols": share,
    }


def _page_hist(report: dict) -> dict[str, object]:
    lines = ((report.get("scan") or {}).get("page_lines") or {})
    values = list(lines.values())
    if not values:
        return {"n": 0}
    buckets = Counter()
    for n in values:
        if n <= 50:
            buckets["<=50"] += 1
        elif n <= 150:
            buckets["51-150"] += 1
        elif n <= 400:
            buckets["151-400"] += 1
        else:
            buckets[">400"] += 1
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "median": sorted(values)[len(values) // 2],
        "buckets": dict(buckets),
        "over_400": [page for page, n in lines.items() if n > 400],
        "over_150_index": [page for page, n in lines.items() if page.endswith("INDEX.md") and n > 150],
    }


def _side(label: str, report: dict, index_path: Path, pointing: dict | None) -> dict[str, object]:
    scan = report.get("scan") or {}
    hops = scan.get("hops") or {}
    anchors = scan.get("anchors") or {}
    return {
        "label": label,
        "llm_calls": report.get("llm_calls"),
        "n_clusters": report.get("n_clusters"),
        "n_partition_clusters": report.get("n_partition_clusters"),
        "n_traces": report.get("n_traces"),
        "n_traces_with_nodes": report.get("n_traces_with_nodes"),
        "traces_per_partition_cluster_ok": report.get("traces_per_partition_cluster_ok"),
        "n_pages": report.get("n_pages"),
        "index": _index_stats(index_path),
        "largest_cluster": _largest_cluster(report),
        "hops": {
            "max": hops.get("max_hops"),
            "over_3": hops.get("over_3_hops"),
            "unreachable": hops.get("unreachable"),
        },
        "dead_ends": scan.get("dead_ends"),
        "oversize": scan.get("oversize"),
        "page_hist": _page_hist(report),
        "n7_index_rate_resolved": anchors.get("rate_resolved"),
        "n7_index_links_total": anchors.get("links_total"),
        "pointing": pointing,
        "named_clusters": [
            {
                "id": item.get("id"),
                "slug": item.get("slug"),
                "symbols": item.get("symbols"),
                "purpose": (item.get("purpose") or "")[:80],
                "name_source": item.get("name_source"),
            }
            for item in (report.get("clusters") or [])
        ],
    }


def compare_pair(old_report: Path, old_index: Path, new_report: Path, new_index: Path) -> dict:
    old = _load(old_report)
    new = _load(new_report)
    pointing = new.get("pointing")
    pointing_path = new_report.parent / "pointing.json"
    if pointing_path.is_file():
        pointing = _load(pointing_path)
    return {
        "old": _side("module_id (r1)", old, old_index, None),
        "new": _side("shared-signature (r2)", new, new_index, pointing),
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# 新旧分区对比（变体 B，综合层 0 次 LLM）",
        "",
        "旧：ledger `module_id` 多数表决。新：clus 共享签名分区 + L2 能力名。",
        "综合层 LLM 调用仍是 0；梯度实验单独记，不算主线。",
        "",
        "复算：",
        "",
        "```",
        "P=adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer/.venv/bin/python",
        "$P -m src.synthesis.variant_b scan --docs <evidence/vb/flask>",
        "$P -m src.synthesis.variant_b pointing --docs <evidence/vb/flask>",
        "```",
        "",
    ]
    for repo, block in payload.items():
        if repo.startswith("_"):
            continue
        old, new = block["old"], block["new"]
        lines.extend(
            [
                f"## {repo}",
                "",
                "| 指标 | 旧 module_id | 新共享签名 |",
                "|---|---|---|",
                f"| 综合层 LLM | {old['llm_calls']} | {new['llm_calls']} |",
                f"| 簇数 | {old['n_clusters']} | {new.get('n_partition_clusters') or new['n_clusters']}（含残差簇则 {new['n_clusters']}） |",
                f"| 命名迹条数 | {old['n_traces']}（有节点 {old['n_traces_with_nodes']}） | {new['n_traces']}（有节点 {new['n_traces_with_nodes']}） |",
                f"| 每分区簇 ≥1 迹 | — | {new.get('traces_per_partition_cluster_ok')} |",
                f"| 入口页行数 | {old['index']['lines']} | {new['index']['lines']} |",
                f"| 入口页功能条目 | {old['index']['function_bullets']} | {new['index']['function_bullets']} |",
                f"| 入口页字符 | {old['index']['chars']} | {new['index']['chars']} |",
                f"| 页数 | {old['n_pages']} | {new['n_pages']} |",
                f"| 最大簇符号 | {old['largest_cluster']['symbols']}（占比 {old['largest_cluster']['share_of_clustered_symbols']}） | {new['largest_cluster']['symbols']}（占比 {new['largest_cluster']['share_of_clustered_symbols']}） |",
                f"| 最大跳数 | {old['hops']['max']} | {new['hops']['max']} |",
                f"| 死胡同 | {old['dead_ends']} | {new['dead_ends']} |",
                f"| 超页 | {old['oversize']} | {new['oversize']} |",
                f"| 页长 max | {old['page_hist'].get('max')} | {new['page_hist'].get('max')} |",
                f"| INDEX N7 rate_resolved | {old['n7_index_rate_resolved']}（{old['n7_index_links_total']} 链） | {new['n7_index_rate_resolved']}（{new['n7_index_links_total']} 链） |",
                "",
            ]
        )
        pointing = new.get("pointing") or {}
        hrefs = pointing.get("public_hrefs") or {}
        lines.extend(
            [
                f"页长分布（新）：`{new['page_hist'].get('buckets')}`。INDEX>150：{new['page_hist'].get('over_150_index')}。页>400：{new['page_hist'].get('over_400')}。",
                "",
                f"锚点指向性（新）：hit {pointing.get('hits')}/{pointing.get('links_checked')} = {pointing.get('rate_hit')}；公共面最大重复度 {hrefs.get('max_repeat')}。",
                "",
                "新簇名（能力语言）：",
                "",
            ]
        )
        for item in new.get("named_clusters") or []:
            purpose = item.get("purpose") or ""
            extra = f" — {purpose}" if purpose else ""
            lines.append(
                f"- `{item.get('slug')}`（{item.get('symbols')} 符号, {item.get('name_source')}）{extra}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_compare(
    *,
    flask_old_report: Path,
    flask_old_index: Path,
    flask_new_report: Path,
    flask_new_index: Path,
    httpx_old_report: Path,
    httpx_old_index: Path,
    httpx_new_report: Path,
    httpx_new_index: Path,
    out_path: Path,
) -> dict:
    payload = {
        "flask": compare_pair(flask_old_report, flask_old_index, flask_new_report, flask_new_index),
        "httpx": compare_pair(httpx_old_report, httpx_old_index, httpx_new_report, httpx_new_index),
    }
    out_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
