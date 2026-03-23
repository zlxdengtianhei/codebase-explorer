#!/usr/bin/env python3
"""检查文档对源代码的覆盖率。

命令行用法：
    python check_coverage.py <docs_dir> <source_dir> [--format json|text]

退出码：
    0 - 所有检查通过
    1 - 覆盖率低于阈值
    2 - 用法错误 / IO 错误
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 被视为"可文档化"的源文件扩展名
SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".swift",
        ".kt",
        ".scala",
        ".php",
        ".lua",
        ".ex",
        ".exs",
        ".erl",
        ".hs",
        ".ml",
        ".mli",
    }
)

# 扫描源代码时要跳过的文件/目录
SKIP_PATTERNS: frozenset[str] = frozenset(
    {
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "egg-info",
    }
)

# 最低通过阈值
MIN_FILE_DISCOVERY_RATE = 0.80   # 文件发现率最低 80%
MIN_MODULE_COVERAGE = 0.80       # 模块覆盖率最低 80%
MIN_TOKEN_COMPLIANCE_RATE = 0.80 # Token 预算合规率最低 80%


# ---------------------------------------------------------------------------
# doc-meta 解析（仅使用标准库，与 validate_doc_links.py 相同）
# ---------------------------------------------------------------------------

_DOC_META_BLOCK_RE = re.compile(
    r"<!--\s*doc-meta\s*\n(.*?)\n-->", re.DOTALL
)

_YAML_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+)$")


def _parse_yaml_value(raw: str) -> str | int | float | None:
    """解析简单的 YAML 标量值。"""
    stripped = raw.strip()
    if stripped.lower() in ("null", "~", ""):
        return None
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1]
    return stripped


def parse_doc_meta(content: str) -> dict[str, Any] | None:
    """提取 doc-meta HTML 注释块并以字典形式返回。"""
    match = _DOC_META_BLOCK_RE.search(content)
    if match is None:
        return None

    raw_yaml = match.group(1)
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if current_key is not None and current_list is not None:
                result[current_key] = list(current_list)
                current_key = None
                current_list = None
            continue

        list_match = _YAML_LIST_ITEM_RE.match(line)
        if list_match and current_key is not None:
            if current_list is None:
                current_list = []
            current_list.append(list_match.group(1).strip())
            continue

        if current_key is not None and current_list is not None:
            result[current_key] = list(current_list)
            current_key = None
            current_list = None

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = _parse_yaml_value(value)
                current_key = None
                current_list = None
            else:
                current_key = key
                current_list = None

    if current_key is not None and current_list is not None:
        result[current_key] = list(current_list)
    elif current_key is not None:
        result[current_key] = None

    return result


# ---------------------------------------------------------------------------
# 源文件发现
# ---------------------------------------------------------------------------


def _should_skip(path: Path) -> bool:
    """如果 *path* 或其任意祖先路径匹配跳过模式，则返回 True。"""
    for part in path.parts:
        if part in SKIP_PATTERNS:
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def discover_source_files(source_dir: Path) -> list[Path]:
    """返回 *source_dir* 下所有源文件的排序列表。"""
    files: list[Path] = []
    for p in sorted(source_dir.rglob("*")):
        if not p.is_file():
            continue
        if _should_skip(p):
            continue
        if p.suffix in SOURCE_EXTENSIONS:
            files.append(p)
    return files


def discover_modules(source_dir: Path) -> set[str]:
    """发现顶级模块（包含源文件的直接子目录）。"""
    modules: set[str] = set()
    for child in sorted(source_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            if _should_skip(child):
                continue
            # 是否至少包含一个源文件？
            has_source = any(
                f.suffix in SOURCE_EXTENSIONS
                for f in child.rglob("*")
                if f.is_file() and not _should_skip(f)
            )
            if has_source:
                modules.add(child.name)
    # 将源根目录中的独立文件视为伪模块
    root_sources = [
        f
        for f in source_dir.iterdir()
        if f.is_file() and f.suffix in SOURCE_EXTENSIONS
    ]
    if root_sources:
        modules.add("__root__")
    return modules


# ---------------------------------------------------------------------------
# 加载 doc-index.json
# ---------------------------------------------------------------------------


def load_doc_index(docs_dir: Path) -> dict[str, Any] | None:
    """从 *docs_dir* 加载 doc-index.json。如果文件不存在则返回 None。"""
    index_path = docs_dir / "doc-index.json"
    if not index_path.is_file():
        return None
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Token 估算
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """粗略的 Token 估算：英文/代码约每 4 个字符一个 Token。"""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# 核心分析
# ---------------------------------------------------------------------------


def check_coverage(docs_dir: Path, source_dir: Path) -> dict[str, Any]:
    """运行覆盖率分析并返回结果字典。"""
    docs_dir = docs_dir.resolve()
    source_dir = source_dir.resolve()

    # -- 源代码分析 --
    source_files = discover_source_files(source_dir)
    source_modules = discover_modules(source_dir)

    source_file_relpaths: set[str] = {
        str(f.relative_to(source_dir)) for f in source_files
    }

    # -- 加载 doc-index.json --
    doc_index = load_doc_index(docs_dir)

    documented_files: set[str] = set()
    documented_modules: set[str] = set()
    doc_entries: list[dict[str, Any]] = []
    max_depth = 0

    if doc_index is not None:
        doc_entries = doc_index.get("docs", [])
        max_depth = doc_index.get("max_depth", 0)

        for entry in doc_entries:
            # 收集已文档化的源文件
            for sf in entry.get("source_files", []):
                documented_files.add(sf)

            # 从目标标识符推断模块（取点分隔标识符的第一段）
            target = entry.get("target", "")
            if target:
                top_module = target.split(".")[0]
                if top_module:
                    documented_modules.add(top_module)
                    # 将 "root" 视为等同于 "__root__" 以进行覆盖率匹配
                    if top_module == "root":
                        documented_modules.add("__root__")

    # -- 文件发现率 --
    file_discovery_rate = (
        len(documented_files & source_file_relpaths) / len(source_file_relpaths)
        if source_file_relpaths
        else 1.0
    )

    # -- 模块覆盖率 --
    module_coverage = (
        len(documented_modules & source_modules) / len(source_modules)
        if source_modules
        else 1.0
    )

    # -- Token 预算合规性 --
    token_compliance = _check_token_budget_compliance(docs_dir, doc_entries)

    # -- 深度分析 --
    depth_analysis = _analyse_depth(doc_entries, max_depth)

    # -- 状态 --
    status = "PASS" if (
        file_discovery_rate >= MIN_FILE_DISCOVERY_RATE
        and module_coverage >= MIN_MODULE_COVERAGE
        and token_compliance["rate"] >= MIN_TOKEN_COMPLIANCE_RATE
        and depth_analysis["dynamic_depth_working"]
    ) else "FAIL"

    return {
        "source_files": len(source_files),
        "documented_files": len(documented_files & source_file_relpaths),
        "file_discovery_rate": round(file_discovery_rate, 3),
        "total_modules": len(source_modules),
        "documented_modules": len(documented_modules & source_modules),
        "module_coverage": round(module_coverage, 3),
        "token_budget_compliance": token_compliance,
        "depth_analysis": depth_analysis,
        "status": status,
    }


def _check_token_budget_compliance(
    docs_dir: Path,
    doc_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """验证每个文档的 token_budget 与 actual_tokens。

    当文档的实际 Token 数不超过声明的 Token 预算的 20% 时，
    该文档被视为*合规*。
    """
    total_docs = 0
    compliant = 0

    for entry in doc_entries:
        doc_path = docs_dir / entry.get("path", "")
        if not doc_path.is_file():
            continue

        total_docs += 1

        # 从 doc-index 条目获取预算
        budget = entry.get("token_budget")
        # 也从文件中的 doc-meta 检查预算
        content = doc_path.read_text(encoding="utf-8", errors="replace")
        meta = parse_doc_meta(content)
        if meta and budget is None:
            budget = meta.get("token_budget")

        if budget is None:
            # 未声明预算——视为合规（无约束）
            compliant += 1
            continue

        actual = entry.get("token_count")
        if actual is None:
            actual = estimate_tokens(content)

        # 允许 20% 超出
        if actual <= budget * 1.2:
            compliant += 1

    rate = compliant / total_docs if total_docs > 0 else 1.0

    return {
        "total_docs": total_docs,
        "compliant": compliant,
        "rate": round(rate, 3),
    }


def _analyse_depth(
    doc_entries: list[dict[str, Any]],
    max_depth: int,
) -> dict[str, Any]:
    """分析文档深度分布。

    *动态深度正常工作*的条件：至少一个模块使用深度 >= 2，
    且并非所有模块都具有相同的深度——即深度适应复杂度
    而非硬编码。
    """
    # 收集每个顶级模块（目标标识符的第一段）的最大深度
    module_depths: dict[str, int] = {}
    for entry in doc_entries:
        target = entry.get("target", "")
        level = entry.get("level", 0)
        top_module = target.split(".")[0] if target else ""
        if top_module:
            module_depths[top_module] = max(
                module_depths.get(top_module, 0), level
            )

    modules_with_depth_gte_2 = sum(
        1 for d in module_depths.values() if d >= 2
    )
    modules_with_depth_eq_1 = sum(
        1 for d in module_depths.values() if d == 1
    )

    # 动态深度正常工作的条件：
    #   1. 至少一个模块深度 >= 2
    #   2. 且并非每个模块都有完全相同的深度（除非只有一个模块）
    distinct_depths = set(module_depths.values())
    dynamic_depth_working = (
        modules_with_depth_gte_2 > 0
        and (len(distinct_depths) > 1 or len(module_depths) <= 1)
    )

    return {
        "max_depth": max_depth if max_depth else max(module_depths.values(), default=0),
        "modules_with_depth_gte_2": modules_with_depth_gte_2,
        "modules_with_depth_eq_1": modules_with_depth_eq_1,
        "dynamic_depth_working": dynamic_depth_working,
    }


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------


def _format_text(report: dict[str, Any]) -> str:
    """将报告格式化为可读的文本格式。"""
    lines: list[str] = []
    lines.append("文档覆盖率报告")
    lines.append("=" * 40)
    lines.append(f"源文件总数        : {report['source_files']}")
    lines.append(f"已文档化文件数    : {report['documented_files']}")
    lines.append(f"文件发现率        : {report['file_discovery_rate']:.1%}")
    lines.append(f"模块总数          : {report['total_modules']}")
    lines.append(f"已文档化模块数    : {report['documented_modules']}")
    lines.append(f"模块覆盖率        : {report['module_coverage']:.1%}")
    lines.append("")

    tc = report["token_budget_compliance"]
    lines.append("Token 预算合规性：")
    lines.append(f"  文档总数   : {tc['total_docs']}")
    lines.append(f"  合规数量   : {tc['compliant']}")
    lines.append(f"  合规率     : {tc['rate']:.1%}")
    lines.append("")

    da = report["depth_analysis"]
    lines.append("深度分析：")
    lines.append(f"  最大深度              : {da['max_depth']}")
    lines.append(f"  深度 >= 2 的模块数    : {da['modules_with_depth_gte_2']}")
    lines.append(f"  深度 == 1 的模块数    : {da['modules_with_depth_eq_1']}")
    lines.append(f"  动态深度正常          : {da['dynamic_depth_working']}")
    lines.append("")

    lines.append(f"状态 : {report['status']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "通过比较源文件与 doc-index.json 和 doc-meta 元数据，"
            "检查文档覆盖率。"
        ),
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="文档目录的路径（必须包含 doc-index.json）。",
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="源代码目录的路径。",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认：json）。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    docs_dir: Path = args.docs_dir.resolve()
    source_dir: Path = args.source_dir.resolve()

    if not docs_dir.is_dir():
        print(f"错误：{docs_dir} 不是一个目录。", file=sys.stderr)
        return 2
    if not source_dir.is_dir():
        print(f"错误：{source_dir} 不是一个目录。", file=sys.stderr)
        return 2

    report = check_coverage(docs_dir, source_dir)

    if args.output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_text(report))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
