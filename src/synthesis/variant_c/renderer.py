"""Deterministic nested-page renderer for Variant C."""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass, replace
from pathlib import Path
from collections.abc import Mapping, Sequence

from src.semantic.models import SemanticLedger

from .anchors import AnchorReport, page_anchor, render_selected_citations, verify_rendered_links
from .incremental import build_page_state
from .models import MAX_DETAIL_LINES, MAX_DETAIL_SYMBOLS, PageArtifact, PageState, SECTION_TITLES
from .producer import ProducedBatch


_HEADER = "<!-- generated:codebase-explorer-variant-c -->"
_ROOT_PAGE_ID = "root"
_PAGE_RANGE_FRAGMENT = "L2-L2"


@dataclass(frozen=True, slots=True)
class RenderResult:
    documents: Mapping[str, str]
    pages: tuple[PageArtifact, ...]
    page_states: tuple[PageState, ...]
    anchor_report: AnchorReport
    degraded_batch_ids: tuple[str, ...]

    @property
    def metrics(self) -> dict[str, object]:
        calls = len({page.receipt.batch_id for page in self.pages})
        return {
            "llm_batch_calls": calls,
            "render_pages": len(self.pages),
            "degraded_batches": len(self.degraded_batch_ids),
            "anchor_total": self.anchor_report.total_links,
            "anchor_resolved": self.anchor_report.resolved_links,
            "anchor_resolved_rate": self.anchor_report.anchor_resolved,
            "dangling_links": len(self.anchor_report.dangling_links),
            "max_detail_lines": max(
                (content.count("\n") for path, content in self.documents.items() if path != "INDEX.md"),
                default=0,
            ),
        }


def _cluster_symbols(batch: ProducedBatch, symbol_ids: Sequence[str]) -> list[object]:
    wanted = set(symbol_ids)
    # ``ProducedBatch`` deliberately carries only the plan; facts are in the
    # candidate set/covered ids.  The symbol roster is reconstructed from the
    # candidate targets and remains ledger-derived.
    return [target for target in batch.candidates.targets if target.target_id in wanted]


def _body_with_four_sections(body: str) -> str:
    """Keep model headings visible; reject accidental alternate section names."""

    missing = [title for title in SECTION_TITLES if f"## {title}" not in body]
    if missing:
        raise ValueError(f"cannot render body without four sections: {missing}")
    return body.strip()


def _href(current_path: str, target_path: str, anchor: str) -> str:
    current_dir = posixpath.dirname(current_path) or "."
    path = "" if target_path == current_path else posixpath.relpath(target_path, current_dir)
    return f"{path}#{anchor}" if path else f"#{anchor}"


def _link(label: str, current_path: str, target_path: str, anchor: str) -> str:
    return f"[{label}]({_href(current_path, target_path, anchor)})"


def _navigation_lines(
    *,
    output_path: str,
    batch: ProducedBatch,
    part_number: int,
    part_count: int,
) -> list[str]:
    """Give every rendered page an explicit up edge and every continuation a down edge."""

    lines = ["## 导航", "", f"- {_link('↑ 根 INDEX', output_path, 'INDEX.md', page_anchor(_ROOT_PAGE_ID))}"]
    if part_number > 1:
        previous_path = batch.plan.part_paths[part_number - 2]
        lines.append(
            f"- {_link('← 上一页', output_path, previous_path, page_anchor(batch.plan.batch_id))}"
        )
    if part_number < part_count:
        next_path = batch.plan.part_paths[part_number]
        lines.append(
            f"- {_link('下一页 →', output_path, next_path, page_anchor(batch.plan.batch_id))}"
        )
    lines.append("")
    return lines


def _render_page(
    batch: ProducedBatch,
    *,
    page_id: str,
    output_path: str,
    symbol_ids: Sequence[str],
    part_number: int,
    part_count: int,
) -> str:
    body = _body_with_four_sections(batch.draft.body)
    lines = [
        _HEADER,
        f'<a id="{_PAGE_RANGE_FRAGMENT}"></a>',
        f"# {batch.plan.cluster_name} · {batch.plan.layer}",
        "",
        f'<a id="{page_anchor(batch.plan.batch_id)}"></a>',
        f"- 功能簇：`{batch.plan.cluster_id}`；本批次一次调用，渲染页 {part_number}/{part_count}。",
        f"- 生成状态：`{batch.receipt.status}`；provider：`{batch.receipt.provider}`。",
        "",
    ]
    if part_number == 1:
        lines.extend(body.splitlines())
        lines.append("")
    else:
        first_path = batch.plan.part_paths[0]
        current_dir = posixpath.dirname(output_path) or "."
        first_href = (
            f"{posixpath.relpath(first_path, current_dir)}#{page_anchor(batch.plan.batch_id)}"
        )
        lines.extend(
            [
                "## 批次续页",
                "",
                f"本页是 `{batch.plan.batch_id}` 的确定性分页；密描述见 [首篇]({first_href}).",
                "",
            ]
        )
    lines.extend(["## 覆盖符号", ""])
    target_by_id = {target.target_id: target for target in batch.candidates.targets}
    for symbol_id in symbol_ids:
        target = target_by_id.get(symbol_id)
        if target is None or target.kind != "symbol":
            continue
        lines.extend(
            [
                (
                    f"<!-- symbol:{target.source_symbol_id} -->"
                    f'<a id="{target.anchor}"></a>'
                    f'<a id="L{target.line_start}-L{target.line_end}"></a>'
                ),
                f"### `{target.label}`",
                "",
                f"- 源码位置：`{target.source_path}:{target.line_start}-{target.line_end}`",
                "- 该符号已由确定层纳入本批次；详细行为以四节密描述和下层事实为准。",
                "",
            ]
        )
    lines.extend(render_selected_citations(batch.draft.selected_target_ids, batch.candidates, current_path=output_path))
    lines.extend(
        _navigation_lines(
            output_path=output_path,
            batch=batch,
            part_number=part_number,
            part_count=part_count,
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def render_document_tree(
    batches: Sequence[ProducedBatch],
    *,
    ledger_value: object,
    file_revisions: Mapping[str, str] | object,
    public_surface: Mapping[str, str | None] | Sequence[str] = (),
    output_dir: str | Path | None = None,
) -> RenderResult:
    """Render nested pages and an INDEX; optionally write the returned tree."""

    ledger = ledger_value if isinstance(ledger_value, SemanticLedger) else SemanticLedger.model_validate(ledger_value)
    # Re-map symbol targets to the deterministic part page that will contain them.
    symbol_page_path: dict[str, str] = {}
    for batch in batches:
        chunks = [batch.plan.symbol_ids[index : index + MAX_DETAIL_SYMBOLS] for index in range(0, len(batch.plan.symbol_ids), MAX_DETAIL_SYMBOLS)] or [()]
        paths = batch.plan.part_paths
        for index, chunk in enumerate(chunks):
            path = paths[min(index, len(paths) - 1)]
            for symbol_id in chunk:
                symbol_page_path[symbol_id] = path
    documents: dict[str, str] = {}
    pages: list[PageArtifact] = []
    page_states: list[PageState] = []
    for batch in batches:
        chunks = [batch.plan.symbol_ids[index : index + MAX_DETAIL_SYMBOLS] for index in range(0, len(batch.plan.symbol_ids), MAX_DETAIL_SYMBOLS)] or [()]
        part_count = len(chunks)
        if part_count != len(batch.plan.part_paths):
            raise ValueError(f"batch {batch.plan.batch_id} has inconsistent deterministic part paths")
        for index, chunk in enumerate(chunks, start=1):
            output_path = batch.plan.part_paths[index - 1]
            page_id = batch.plan.batch_id if index == 1 else f"{batch.plan.batch_id}#part-{index}"
            content = _render_page(
                batch,
                page_id=page_id,
                output_path=output_path,
                symbol_ids=chunk,
                part_number=index,
                part_count=part_count,
            )
            if content.count("\n") > MAX_DETAIL_LINES:
                raise ValueError(f"detail page exceeds {MAX_DETAIL_LINES} lines: {output_path}")
            documents[output_path] = content
            artifact = PageArtifact(
                page_id=page_id,
                output_path=output_path,
                cluster_id=batch.plan.cluster_id,
                cluster_name=batch.plan.cluster_name,
                # Each deterministic part owns only its symbol slice for the
                # incremental closure. The first part additionally owns the
                # cluster file cards because it carries the overview prose.
                draft=replace(
                    batch.draft,
                    covered_symbol_ids=tuple(chunk),
                ),
                candidates=batch.candidates,
                receipt=batch.receipt,
                part_number=index,
                part_count=part_count,
            )
            pages.append(artifact)
            page_states.append(
                build_page_state(
                    artifact,
                    ledger_value=ledger,  # type: ignore[arg-type]
                    file_revisions=file_revisions,
                    dependency_file_paths=batch.plan.file_paths if index == 1 else (),
                    rendered_body=content,
                )
            )

    index_lines = [
        _HEADER,
        f'<a id="{page_anchor(_ROOT_PAGE_ID)}"></a>',
        "# 代码库功能索引",
        "",
        "这份入口按功能簇组织；每个批次只调用一次表达层，页内引用由确定层从封闭候选集展开。",
        "",
        "## 功能簇",
        "",
    ]
    for batch in batches:
        first_path = batch.plan.part_paths[0]
        cluster_link = _link(
            f"{batch.plan.cluster_name} {_PAGE_RANGE_FRAGMENT}",
            "INDEX.md",
            first_path,
            _PAGE_RANGE_FRAGMENT,
        )
        index_lines.append(
            f"- {cluster_link}：{len(batch.plan.file_paths)} 个文件，"
            f"{len(batch.plan.symbol_ids)} 个符号，层次 `{batch.plan.layer}`。"
        )
    if isinstance(public_surface, Mapping):
        surface_entries = {str(name): (str(symbol_id) if symbol_id else None) for name, symbol_id in public_surface.items()}
    else:
        surface_entries = {str(name): None for name in public_surface}
    if surface_entries:
        surface_path = "public-surface/DETAIL.md"
        surface_lines = [
            _HEADER,
            "# 公共面绑定",
            "",
            "以下名称来自确定层公共面 overlay；未解析的名称保留为可见残差，不编造成符号。",
            "",
            f"- {_link('↑ 根 INDEX', surface_path, 'INDEX.md', page_anchor(_ROOT_PAGE_ID))}",
            "",
        ]
        surface_ranges: dict[str, tuple[int, int]] = {}
        for name, symbol_id in sorted(surface_entries.items()):
            entry_line = len(surface_lines) + 1
            entry_fragment = f"L{entry_line}-L{entry_line}"
            surface_ranges[name] = (entry_line, entry_line)
            surface_lines.extend(
                [
                    f'<a id="{page_anchor("surface:" + name)}"></a><a id="{entry_fragment}"></a>',
                    f"## `{name}`",
                    "",
                ]
            )
            target_path = symbol_page_path.get(symbol_id or "")
            if symbol_id and target_path and symbol_id in ledger.symbols:
                record = ledger.symbols[symbol_id]
                line_fragment = f"L{record.span[0]}-L{record.span[1]}"
                href = posixpath.relpath(target_path, posixpath.dirname(surface_path) or ".")
                surface_lines.append(
                    f"- 实现锚点：[{record.qualified_name} {line_fragment}]({href}#{line_fragment})"
                )
            else:
                surface_lines.append("- 实现锚点：未解析到唯一符号；仅保留公共绑定事实。")
            surface_lines.append("")
        documents[surface_path] = "\n".join(surface_lines).rstrip() + "\n"
        index_lines.extend(["", "## 公共面", ""])
        for name in sorted(surface_entries):
            symbol_id = surface_entries[name]
            target_path = symbol_page_path.get(symbol_id or "")
            if symbol_id and target_path and symbol_id in ledger.symbols:
                record = ledger.symbols[symbol_id]
                line_fragment = f"L{record.span[0]}-L{record.span[1]}"
                href = _href("INDEX.md", target_path, line_fragment)
                index_lines.append(f"- [`{name}` {line_fragment}]({href})")
            else:
                start, end = surface_ranges[name]
                line_fragment = f"L{start}-L{end}"
                href = _href("INDEX.md", surface_path, line_fragment)
                index_lines.append(f"- [`{name}` {line_fragment}]({href})")
    index_lines.extend(
        [
            "",
            "## 结构约束",
            "",
            "- 模型只提交 `selected_target_ids`；链接、锚点和行区间由渲染器生成。",
            "- 页状态记录 `cited_symbol_ids` 与每个被引文件的 revision；无关文件变化不触发本页重写。",
            "",
        ]
    )
    degraded = sorted({batch.plan.batch_id for batch in batches if batch.receipt.status == "degraded"})
    index_lines.extend(["## 残差", ""])
    if degraded:
        index_lines.extend(f"- `{batch_id}`：表达层失败，页内保留确定性事实与 residual 标记。" for batch_id in degraded)
    else:
        index_lines.append("- 无表达层残差。")
    index_lines.append("")
    documents["INDEX.md"] = "\n".join(index_lines)
    aggregate_payload = {
        "schema": "cbe-variant-c-page-ledger-1",
        "cited_symbol_ids": sorted(
            {
                symbol_id
                for state in page_states
                for symbol_id in state.cited_symbol_ids
            }
        ),
        "nodes": {
            state.page_id: {
                "id": state.page_id,
                "kind": "page",
                "path": state.output_path,
                "is_fresh": state.status == "fresh",
                "cited_symbol_ids": list(state.cited_symbol_ids),
                "file_revisions": dict(state.file_revisions),
                "page_hash": state.page_hash,
            }
            for state in page_states
        },
    }
    documents["aggregates/aggregate_ledger.json"] = json.dumps(
        aggregate_payload,
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    anchor_report = verify_rendered_links(documents)
    result = RenderResult(
        documents=dict(sorted(documents.items())),
        pages=tuple(pages),
        page_states=tuple(page_states),
        anchor_report=anchor_report,
        degraded_batch_ids=tuple(degraded),
    )
    if output_dir is not None:
        write_documents(result.documents, output_dir)
    return result


def write_documents(documents: Mapping[str, str], output_dir: str | Path) -> None:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in sorted(documents.items()):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
