#!/usr/bin/env python3
"""验证文档目录中的所有 Markdown 链接和 doc-meta 父子关系一致性。

命令行用法：
    python validate_doc_links.py <docs_dir> [--format json|text]

退出码：
    0 - 所有检查通过
    1 - 检测到验证失败
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
# doc-meta 解析（仅使用标准库，通过正则表达式解析 YAML 子集）
# ---------------------------------------------------------------------------

_DOC_META_BLOCK_RE = re.compile(
    r"<!--\s*doc-meta\s*\n(.*?)\n-->", re.DOTALL
)

_YAML_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+)$")


def _parse_yaml_value(raw: str) -> str | int | float | None:
    """解析简单的 YAML 标量值（不依赖 pydantic / PyYAML）。"""
    stripped = raw.strip()
    if stripped.lower() in ("null", "~", ""):
        return None
    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False
    # 整数
    try:
        return int(stripped)
    except ValueError:
        pass
    # 浮点数
    try:
        return float(stripped)
    except ValueError:
        pass
    # 字符串（如果有引号则去除）
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1]
    return stripped


def parse_doc_meta(content: str) -> dict[str, Any] | None:
    """提取 doc-meta HTML 注释并以字典形式返回。

    支持 doc-meta 块中使用的 YAML 子集：
    - ``key: value`` 标量
    - ``key:`` 后跟 ``- item`` 的列表项
    - 带缩进的嵌套映射键（``metrics:\\n  file_count: 12``）

    未找到 doc-meta 块时返回 *None*。
    """
    match = _DOC_META_BLOCK_RE.search(content)
    if match is None:
        return None

    raw_yaml = match.group(1)
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in raw_yaml.splitlines():
        # 跳过空行和注释行
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            # 刷新待处理的列表
            if current_key is not None and current_list is not None:
                result[current_key] = list(current_list)
                current_key = None
                current_list = None
            continue

        # 列表项续行
        list_match = _YAML_LIST_ITEM_RE.match(line)
        if list_match and current_key is not None:
            if current_list is None:
                current_list = []
            current_list.append(list_match.group(1).strip())
            continue

        # 刷新前一个列表
        if current_key is not None and current_list is not None:
            result[current_key] = list(current_list)
            current_key = None
            current_list = None

        # key: value 格式
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                result[key] = _parse_yaml_value(value)
                current_key = None
                current_list = None
            else:
                # 可能是列表或嵌套映射——开始收集
                current_key = key
                current_list = None  # 将在第一个 ``- item`` 时填充

    # 刷新尾部
    if current_key is not None and current_list is not None:
        result[current_key] = list(current_list)
    elif current_key is not None:
        # 键后面没有值且没有列表项
        result[current_key] = None

    return result


# ---------------------------------------------------------------------------
# 链接提取
# ---------------------------------------------------------------------------

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def extract_md_links(content: str) -> list[tuple[str, str]]:
    """返回每个 Markdown 链接的 ``[(文本, href), ...]`` 列表。

    跳过 URL（http/https）、锚点（``#...``）和 ``mailto:`` 链接。
    """
    links: list[tuple[str, str]] = []
    for text, href in _MD_LINK_RE.findall(content):
        href_stripped = href.strip()
        if href_stripped.startswith(("http://", "https://", "mailto:", "#")):
            continue
        # 从本地路径中剥离锚点（例如 "OVERVIEW.md#section"）
        path_part = href_stripped.split("#")[0]
        if path_part:
            links.append((text, path_part))
    return links


# ---------------------------------------------------------------------------
# 核心验证
# ---------------------------------------------------------------------------


def _resolve_link(source_file: Path, href: str, docs_dir: Path) -> Path:
    """将相对链接目标解析为绝对路径。"""
    return (source_file.parent / href).resolve()


def validate(docs_dir: Path) -> dict[str, Any]:
    """运行所有验证并返回结果字典。"""
    docs_dir = docs_dir.resolve()
    md_files = sorted(docs_dir.rglob("*.md"))

    # 收集每个文件的数据
    file_metas: dict[Path, dict[str, Any] | None] = {}
    file_links: dict[Path, list[tuple[str, str]]] = {}

    for md in md_files:
        content = md.read_text(encoding="utf-8", errors="replace")
        file_metas[md] = parse_doc_meta(content)
        file_links[md] = extract_md_links(content)

    # ---- 1. 检查链接目标是否存在 ----
    total_links = 0
    valid_links = 0
    broken_links: list[dict[str, str]] = []

    for md, links in file_links.items():
        for text, href in links:
            total_links += 1
            target = _resolve_link(md, href, docs_dir)
            if target.exists():
                valid_links += 1
            else:
                broken_links.append(
                    {
                        "source": str(md.relative_to(docs_dir)),
                        "text": text,
                        "href": href,
                        "expected": str(target.relative_to(docs_dir))
                        if target.is_relative_to(docs_dir)
                        else str(target),
                    }
                )

    # ---- 2. 查找孤立文档（从未被任何其他文档引用）----
    referenced_paths: set[Path] = set()
    for md, links in file_links.items():
        for _, href in links:
            target = _resolve_link(md, href, docs_dir)
            referenced_paths.add(target)

    # 同时添加通过 doc-meta children/parent 引用的路径
    for md, meta in file_metas.items():
        if meta is None:
            continue
        children = meta.get("children")
        if isinstance(children, list):
            for child in children:
                referenced_paths.add((md.parent / child).resolve())
        parent = meta.get("parent")
        if parent and isinstance(parent, str):
            referenced_paths.add((md.parent / parent).resolve())

    orphaned_docs: list[str] = []
    for md in md_files:
        if md not in referenced_paths:
            rel = str(md.relative_to(docs_dir))
            # INDEX.md（层级 0）是根节点——按定义从不孤立
            meta = file_metas.get(md)
            if meta and meta.get("level") == 0:
                continue
            # 如果只有一个文档，跳过孤立检查
            if len(md_files) <= 1:
                continue
            orphaned_docs.append(rel)

    # ---- 3. 父子双向一致性检查 ----
    parent_child_errors: list[dict[str, str]] = []

    for md, meta in file_metas.items():
        if meta is None:
            continue

        md_rel = str(md.relative_to(docs_dir))

        # 检查：如果 A 列出父节点 B，则 B.children 应包含 A
        parent = meta.get("parent")
        if parent and isinstance(parent, str):
            parent_abs = (md.parent / parent).resolve()
            parent_meta = file_metas.get(parent_abs)
            if parent_meta is not None:
                parent_children = parent_meta.get("children")
                if isinstance(parent_children, list):
                    # 计算从父节点到当前文档的相对路径
                    try:
                        child_rel = str(md.relative_to(parent_abs.parent))
                    except ValueError:
                        child_rel = str(
                            Path(
                                _relpath(md, parent_abs.parent)
                            )
                        )

                    # 将父节点的所有子节点解析为绝对路径以进行可靠比较
                    parent_children_abs = {
                        (parent_abs.parent / c).resolve()
                        for c in parent_children
                    }
                    if md not in parent_children_abs:
                        parent_child_errors.append(
                            {
                                "type": "parent_missing_child",
                                "doc": md_rel,
                                "parent": str(parent_abs.relative_to(docs_dir))
                                if parent_abs.is_relative_to(docs_dir)
                                else parent,
                                "detail": (
                                    f"{md_rel} 声明 parent={parent}，"
                                    f"但父节点未将其列为子节点"
                                ),
                            }
                        )

        # 检查：如果 A 列出子节点 C，则 C.parent 应指向 A
        children = meta.get("children")
        if isinstance(children, list):
            for child in children:
                child_abs = (md.parent / child).resolve()
                child_meta = file_metas.get(child_abs)
                if child_meta is not None:
                    child_parent = child_meta.get("parent")
                    if child_parent and isinstance(child_parent, str):
                        declared_parent_abs = (
                            child_abs.parent / child_parent
                        ).resolve()
                        if declared_parent_abs != md:
                            parent_child_errors.append(
                                {
                                    "type": "child_wrong_parent",
                                    "doc": md_rel,
                                    "child": child,
                                    "detail": (
                                        f"{md_rel} 列出子节点 {child}，"
                                        f"但子节点声明 parent={child_parent} "
                                        f"（解析为 {declared_parent_abs}）"
                                    ),
                                }
                            )
                    elif child_parent is None:
                        parent_child_errors.append(
                            {
                                "type": "child_no_parent",
                                "doc": md_rel,
                                "child": child,
                                "detail": (
                                    f"{md_rel} 列出子节点 {child}，"
                                    f"但子节点在 doc-meta 中没有 parent 字段"
                                ),
                            }
                        )

    parent_child_consistent = len(parent_child_errors) == 0

    # ---- 构建结果 ----
    status = "PASS" if (
        not broken_links
        and not orphaned_docs
        and parent_child_consistent
    ) else "FAIL"

    report: dict[str, Any] = {
        "total_docs": len(md_files),
        "total_links": total_links,
        "valid_links": valid_links,
        "broken_links": broken_links,
        "orphaned_docs": orphaned_docs,
        "parent_child_consistency": parent_child_consistent,
        "parent_child_errors": parent_child_errors,
        "status": status,
    }
    return report


def _relpath(target: Path, base: Path) -> str:
    """纯 Python 实现的相对路径（即使在不同驱动器上也能工作）。"""
    try:
        return str(target.relative_to(base))
    except ValueError:
        # 回退到 os.path.relpath 方式
        import os
        return os.path.relpath(str(target), str(base))


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------


def _format_text(report: dict[str, Any]) -> str:
    """将报告格式化为可读的文本格式。"""
    lines: list[str] = []
    lines.append(f"文档链接验证报告")
    lines.append(f"{'=' * 40}")
    lines.append(f"文档总数     : {report['total_docs']}")
    lines.append(f"链接总数     : {report['total_links']}")
    lines.append(f"有效链接数   : {report['valid_links']}")
    lines.append(f"断开链接数   : {len(report['broken_links'])}")
    lines.append(f"孤立文档数   : {len(report['orphaned_docs'])}")
    lines.append(
        f"父子关系一致 : {report['parent_child_consistency']}"
    )
    lines.append(f"状态         : {report['status']}")
    lines.append("")

    if report["broken_links"]:
        lines.append("断开的链接：")
        for bl in report["broken_links"]:
            lines.append(
                f"  - [{bl['text']}]({bl['href']}) 在 {bl['source']}"
            )
        lines.append("")

    if report["orphaned_docs"]:
        lines.append("孤立文档（未被任何其他文档引用）：")
        for od in report["orphaned_docs"]:
            lines.append(f"  - {od}")
        lines.append("")

    if report["parent_child_errors"]:
        lines.append("父子关系一致性错误：")
        for err in report["parent_child_errors"]:
            lines.append(f"  - [{err['type']}] {err['detail']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "验证文档目录中的 Markdown 链接和 doc-meta 父子关系一致性。"
        ),
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="要验证的文档目录路径。",
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
    if not docs_dir.is_dir():
        print(f"错误：{docs_dir} 不是一个目录。", file=sys.stderr)
        return 2

    report = validate(docs_dir)

    if args.output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_text(report))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
