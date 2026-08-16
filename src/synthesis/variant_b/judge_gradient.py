"""Blind 0/1/3/9 INDEX copies and ask an independent judge for readability scores."""

from __future__ import annotations

import json
import re
from pathlib import Path

_CALL_HEADING = re.compile(r"^### 调用 \d+\s*$", re.M)
_LINE_ID = re.compile(r'<a id="L\d+-L\d+"></a>')


def blind_text(text: str) -> str:
    text = _LINE_ID.sub("", text)
    text = text.replace("<!-- tgt:page:INDEX.md -->", "")
    text = text.replace("<!-- /tgt:page:INDEX.md -->", "")
    text = text.replace("<!-- generated:codebase-explorer-variant-b -->", "")
    text = text.replace("综合层 0 次 LLM。", "")
    text = text.replace("- 综合层 LLM 调用：0", "")
    text = text.replace("## 对照散文（非主线）", "## 补充说明")
    text = _CALL_HEADING.sub("### 段落", text)
    # Collapse leftover blank runs but keep markdown structure.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def write_blinded(
    gradient_dir: Path,
    out_dir: Path,
    *,
    mapping: dict[str, int],
) -> dict[str, object]:
    """mapping: blind_id → budget. Inverse is not written into the judge prompt."""

    out_dir.mkdir(parents=True, exist_ok=True)
    bodies: dict[str, str] = {}
    for blind_id, budget in mapping.items():
        src = gradient_dir / str(budget) / "INDEX.md"
        blinded = blind_text(src.read_text(encoding="utf-8"))
        dest = out_dir / f"{blind_id}.md"
        dest.write_text(blinded, encoding="utf-8")
        bodies[blind_id] = blinded
    (out_dir / "MAP.json").write_text(
        json.dumps(
            {
                "note": "评委看不到本文件。blind_id → 综合层额外调用次数。",
                "mapping": mapping,
                "inverse": {str(budget): blind_id for blind_id, budget in mapping.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"mapping": mapping, "bodies": bodies}


def build_prompt(bodies: dict[str, str]) -> str:
    order = sorted(bodies)
    parts = [
        "你是独立评委，只根据下面四份入口页打分。",
        "四份文档经过盲化：已去掉能标识「额外模型调用次数」的标题、页脚和注释。",
        "不要猜测它们的生产预算。不要引用本提示之外的仓库文件。",
        "",
        "对每一份文档打 1-5 整数分（1 差，5 好）：",
        "1. what_is_this：打开入口页能否判断这是什么库、它对外提供什么。",
        "2. scan_functions：功能是否可分条扫读，而不是一个大桶。",
        "3. richness：入口页有没有可执行的事实（迹、名字、职责），而不只是目录。",
        "4. noise：重复、套话、元数据是否干扰阅读（5=几乎无噪音）。",
        "",
        "只输出一个 JSON 对象，不要 markdown 围栏，字段必须是：",
        '{"docs":{"W":{"what_is_this":n,"scan_functions":n,"richness":n,"noise":n,"one_sentence":"..."},'
        '"X":{...},"Y":{...},"Z":{...}},'
        '"ranking_what_is_this":["...","...","...","..."],'
        '"note":"一句话：哪一份最能让读者知道这是什么库"}',
        "",
        "本清单未覆盖：DETAIL 页质量、导航跳数、符号覆盖率。",
        "",
    ]
    for blind_id in order:
        parts.append(f"===== 文档 {blind_id} 开始 =====")
        parts.append(bodies[blind_id])
        parts.append(f"===== 文档 {blind_id} 结束 =====")
        parts.append("")
    return "\n".join(parts)
