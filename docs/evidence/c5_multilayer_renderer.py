#!/usr/bin/env python3
"""C5 多层递归 INDEX/DETAIL 渲染器原型。

消费 C4 analyze_codebase 的确定性产出（03_feature_cones.json + 01_structure.json +
06_function_deps.json），按 Feature Cone 功能架构递归产 INDEX/DETAIL 树，带纯决策递归守卫。

设计对应：cbe/design/CBE_multilayer_design.md §2.1/§2.2（render_multilayer 独占遍历渲染，
递归守卫为纯决策单元：仅 (depth, symbol_count) -> LEAF/DESCEND/DEPTH_CAPPED）。

纯决策守卫：不读 cone 内容/ledger/源码/文档，只接收 (depth, symbol_count, has_substructure)
返回 LEAF / DESCEND / DEPTH_CAPPED。这是 A-03 递归深度上限的实现。
"""
from __future__ import annotations
import json, sys, os, argparse
from pathlib import Path

MAX_DEPTH_DEFAULT = 4
LEAF_THRESHOLD = 6  # 符号数低于此直接叶子；高于此且有子结构则继续分


def guard(depth: int, symbol_count: int, has_substructure: bool) -> str:
    """纯决策守卫（A-03）。只看 depth/symbol_count/has_substructure。"""
    if depth >= MAX_DEPTH_RUNTIME:
        # 达上限仍想下分（还有子结构或符号多）-> 截断平铺
        if has_substructure or symbol_count > LEAF_THRESHOLD:
            return "DEPTH_CAPPED"
        return "LEAF"
    if not has_substructure or symbol_count <= LEAF_THRESHOLD:
        return "LEAF"
    return "DESCEND"


def render(root: Path, gen_dir: Path, out_dir: Path, max_depth: int, cap_log: list):
    global MAX_DEPTH_RUNTIME
    MAX_DEPTH_RUNTIME = max_depth
    cones_j = json.load(open(gen_dir / "03_feature_cones.json"))
    struct_j = json.load(open(gen_dir / "01_structure.json"))
    fd_j = json.load(open(gen_dir / "06_function_deps.json"))
    files_by_path = {f["filepath"]: f for f in struct_j["files"]}
    # function deps keyed by filepath if available
    fdeps = fd_j.get("function_deps", [])

    layers = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    out_dir.mkdir(parents=True, exist_ok=True)

    def symbols_of(filepath: str):
        f = files_by_path.get(filepath, {})
        return list(f.get("function_names", [])) + list(f.get("class_names", []))

    # L0 entry
    layers[0] += 1
    l0 = out_dir / "L0_INDEX.md"
    cone_ids = list(cones_j["cones"].keys())
    body = ["# L0 入口 — 项目功能架构总览",
            "",
            f"- project_id: {cones_j['project_id']}",
            f"- 策略: {cones_j['strategy_used']}",
            f"- 功能模块(cone)数: {cones_j['cone_count']}",
            f"- 基础设施文件数: {len(cones_j['infrastructure_files'])}",
            f"- MAX_DEPTH={max_depth}（本轮渲染上限）",
            "",
            "## 功能模块索引"]
    for cid in cone_ids:
        body.append(f"- [{cid}](L1/{cid}/INDEX.md) — 入口: {cones_j['cones'][cid].get('entry_point')}")
    body += ["", "## 基础设施文件", ""] + [f"- {f}" for f in cones_j["infrastructure_files"]]
    l0.write_text("\n".join(body) + "\n")
    (out_dir / "L1").mkdir(exist_ok=True)

    for cid, cone in cones_j["cones"].items():
        cdir = out_dir / "L1" / cid
        cdir.mkdir(parents=True, exist_ok=True)
        cfiles = cone.get("exclusive_files", [])
        # cone-level symbol count
        cone_syms = sum(len(symbols_of(fp)) for fp in cfiles)
        # L1 decision: depth=1
        has_sub = len(cfiles) > 1
        decision = guard(1, cone_syms, has_sub)
        layers[1] += 1
        idx = ["# L1 INDEX — 功能模块: %s" % cid, "",
               "- 入口: %s" % cone.get("entry_point"),
               "- 文件: %s" % ", ".join(cfiles),
               "- 共享依赖: %s" % ", ".join(cone.get("shared_deps", [])),
               "- token_count: %s" % cone.get("token_count"),
               "- 守卫决策(depth=1, sym=%d, has_sub=%s): %s" % (cone_syms, has_sub, decision),
               ""]
        if decision == "DESCEND":
            idx.append("## 子文件索引")
            for fp in cfiles:
                idx.append("- [%s](L2/%s.md) — 符号数 %d" % (fp, fp.replace("/", "__"), len(symbols_of(fp))))
        elif decision == "DEPTH_CAPPED":
            cap_log.append({"layer": "L1", "cone": cid, "depth": 1, "symbol_count": cone_syms,
                            "decision": "DEPTH_CAPPED", "reason": "depth>=MAX_DEPTH and still divisible"})
            idx.append("## 符号（depth_capped，平铺）")
            for fp in cfiles:
                for s in symbols_of(fp):
                    idx.append("- %s::%s" % (fp, s))
        else:  # LEAF
            idx.append("## 符号（叶子，内联）")
            for fp in cfiles:
                for s in symbols_of(fp):
                    idx.append("- %s::%s" % (fp, s))
        (cdir / "INDEX.md").write_text("\n".join(idx) + "\n")

        # L2 per file (only if DESCEND at L1)
        if decision == "DESCEND":
            for fp in cfiles:
                syms = symbols_of(fp)
                d2 = guard(2, len(syms), len(syms) > LEAF_THRESHOLD)
                layers[2] += 1
                fp_doc = out_dir / "L2" / (fp.replace("/", "__") + ".md")
                fp_doc.parent.mkdir(parents=True, exist_ok=True)
                d2body = ["# L2 DETAIL — %s" % fp, "",
                          "- 模块: %s" % cid,
                          "- 符号数: %d" % len(syms),
                          "- 守卫决策(depth=2, sym=%d): %s" % (len(syms), d2),
                          ""]
                if d2 == "DEPTH_CAPPED":
                    cap_log.append({"layer": "L2", "file": fp, "depth": 2, "symbol_count": len(syms),
                                    "decision": "DEPTH_CAPPED", "reason": "depth>=MAX_DEPTH, symbols would be split but capped"})
                    d2body.append("## 符号（depth_capped，平铺，未下分到 L3）")
                    for s in syms:
                        d2body.append("- %s" % s)
                else:
                    d2body.append("## 符号")
                    for s in syms:
                        d2body.append("- %s" % s)
                fp_doc.write_text("\n".join(d2body) + "\n")
                # L3 symbol detail (if DESCEND at L2)
                if d2 == "DESCEND":
                    for s in syms:
                        layers[3] += 1
                        sdoc = out_dir / "L3" / (cid + "__" + fp.replace("/", "__") + "__" + s + ".md")
                        sdoc.parent.mkdir(parents=True, exist_ok=True)
                        sdoc.write_text("# L3 DETAIL — %s::%s\n\n- 模块: %s\n- 文件: %s\n- 守卫(depth=3): LEAF\n\n(符号级语义解释占位；生产态由 semantic ledger explained 填充)\n" % (fp, s, cid, fp))
    return layers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--max-depth", type=int, default=4)
    args = ap.parse_args()
    gen = Path(args.gen_dir)
    out = Path(args.out_dir)
    cap_log = []
    layers = render(gen, gen, out, args.max_depth, cap_log)
    report = {
        "max_depth": args.max_depth,
        "out_dir": str(out),
        "layer_node_counts": {k: v for k, v in layers.items() if v > 0},
        "max_layer_reached": max([k for k, v in layers.items() if v > 0], default=0),
        "depth_capped_events": cap_log,
    }
    (out / "_render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()