"""三道闸：结构闸（闸 1）· 提问闸（闸 2）· 语义闸（闸 3）。

冻结架构 §1 的贯穿纪律：**下层不知道自己在仓库里的位置，上层不重读源码。**
两侧对称——输入面装不下地位信息（闸 1，`l1_packet.py`），提问面不许问地位（闸 2，本文件），
输出面装不下地位断言（`l1_facts.py`）。闸 3 检验前两道确定层能力真的起了作用。

闸 2 为什么可以做成硬门，而「措辞好不好」不可以：那九个词是**提问动作**本身，不是风格。
「给出系统角色」是一个 packet 答不了的问题，判定它不需要理解内容，只需要看提问面在不在
问它——这正是 `rules/code-and-agent.md` §1.2 说的「可机械判定的规范」。其余风格词只 FLAG，
因为判它们要理解内容，做成硬门只会误伤（同文件 §1）。

命令行自检（编排者可原样复制）::

    .venv/bin/python -m src.semantic.gates scan-source src/semantic/service.py
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Literal, Mapping, Sequence


Severity = Literal["BLOCK", "FLAG"]
Decision = Literal["BLOCK", "FLAG", "PASS"]

#: 硬阻断集（F1 §2.1 逐字）。命中即拒绝派发。
BLOCK_LEXEMES: Final[tuple[str, ...]] = (
    "系统角色",
    "地位",
    "重要性",
    "核心",
    "架构中",
    "在本仓库",
    "role in the system",
    "importance",
    "architecture",
)

#: 风格 / 视角漂移词，只 FLAG。判它们是不是真问题要理解上下文，所以不阻断。
FLAG_LEXEMES: Final[tuple[str, ...]] = (
    "整体",
    "全局",
    "所属模块",
    "归属",
    "项目中",
    "代码库中",
    "上下游",
    "优雅",
    "专业",
    "全面",
    "关键",
    "主要作用",
    "overall",
    "globally",
    "across the codebase",
    "in the project",
    "cluster",
    "module id",
)

_ASCII_LEXEME_RE: Final = re.compile(r"^[\x00-\x7f]+$")


class GateBlocked(RuntimeError):
    """闸判红且严重度为 BLOCK。派发必须停在这里。"""


@dataclass(frozen=True)
class LexemeHit:
    lexeme: str
    severity: Severity
    line: int
    excerpt: str

    def as_dict(self) -> dict[str, object]:
        return {
            "lexeme": self.lexeme,
            "severity": self.severity,
            "line": self.line,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class GateVerdict:
    gate: str
    decision: Decision
    hits: tuple[LexemeHit, ...]
    subject: str = ""

    @property
    def blocked(self) -> bool:
        return self.decision == "BLOCK"

    def as_dict(self) -> dict[str, object]:
        return {
            "gate": self.gate,
            "subject": self.subject,
            "decision": self.decision,
            "block_hits": sum(hit.severity == "BLOCK" for hit in self.hits),
            "flag_hits": sum(hit.severity == "FLAG" for hit in self.hits),
            "hits": [hit.as_dict() for hit in self.hits],
        }


def _iter_lexeme_positions(text: str, lexeme: str) -> Iterable[int]:
    """ASCII 词用词边界匹配，CJK 用子串匹配（中文没有词边界可用）。"""

    if _ASCII_LEXEME_RE.fullmatch(lexeme):
        pattern = re.compile(r"(?<![0-9a-zA-Z_])" + re.escape(lexeme) + r"(?![0-9a-zA-Z_])", re.I)
        for match in pattern.finditer(text):
            yield match.start()
        return
    start = 0
    while True:
        found = text.find(lexeme, start)
        if found < 0:
            return
        yield found
        start = found + 1


def _excerpt(text: str, offset: int, width: int = 34) -> str:
    left = max(0, offset - width // 2)
    return text[left : offset + width].replace("\n", "\\n")


def scan_text(text: str, *, base_line: int = 1, subject: str = "") -> GateVerdict:
    """闸 2 的核心谓词：对一段提问文本给判决。"""

    hits: list[LexemeHit] = []
    for severity, lexemes in (("BLOCK", BLOCK_LEXEMES), ("FLAG", FLAG_LEXEMES)):
        for lexeme in lexemes:
            for offset in _iter_lexeme_positions(text, lexeme):
                line = base_line + text.count("\n", 0, offset)
                hits.append(
                    LexemeHit(
                        lexeme=lexeme,
                        severity=severity,  # type: ignore[arg-type]
                        line=line,
                        excerpt=_excerpt(text, offset),
                    )
                )
    ordered = tuple(sorted(hits, key=lambda hit: (hit.line, hit.severity, hit.lexeme)))
    decision: Decision = (
        "BLOCK"
        if any(hit.severity == "BLOCK" for hit in ordered)
        else "FLAG"
        if ordered
        else "PASS"
    )
    return GateVerdict(gate="gate2_question_surface", decision=decision, hits=ordered, subject=subject)


def assert_prompt_dispatchable(prompt: str, *, subject: str = "") -> GateVerdict:
    """派发前调用。BLOCK 即抛，不给调用方「记得检查返回值」的机会。"""

    verdict = scan_text(prompt, subject=subject)
    if verdict.blocked:
        offenders = sorted({hit.lexeme for hit in verdict.hits if hit.severity == "BLOCK"})
        raise GateBlocked(
            f"gate2 blocked dispatch for {subject or 'prompt'}: "
            f"asks for information the L1 packet cannot support: {offenders}"
        )
    return verdict


def _prompt_string_nodes(tree: ast.AST) -> list[ast.Constant]:
    """取赋给 prompt-ish 名字的字符串常量（含隐式拼接与显式 + 拼接）。"""

    collected: list[ast.Constant] = []
    for node in ast.walk(tree):
        targets: list[str] = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value: ast.expr | None = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        else:
            continue
        if not any("prompt" in name.lower() for name in targets) or value is None:
            continue
        for child in ast.walk(value):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                collected.append(child)
    return collected


def scan_python_source(path: str | Path, *, all_strings: bool = False) -> GateVerdict:
    """扫一个 .py 文件里的提问面，行号是文件真实行号。

    默认只看赋给 `*prompt*` 的字符串常量。`all_strings=True` 时扫全部字符串常量——
    那个模式会把本模块自己的 lexeme 常量也扫出来，是预期行为，不是 bug。
    """

    source_path = Path(path)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=source_path.as_posix())
    if all_strings:
        nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
    else:
        nodes = _prompt_string_nodes(tree)

    # 行号取文件真实行，不取 AST 节点行：CPython 把相邻字符串的隐式拼接并成一个
    # Constant，其 lineno 是拼接组的**首行**。按它报行号，会把 service.py:813 报成 812,
    # 而编排者要按行号去核对的是源文件那一行。所以在节点的行区间内逐行扫原文。
    lines = source.splitlines()
    hits: list[LexemeHit] = []
    seen: set[tuple[str, int]] = set()
    for node in nodes:
        start = node.lineno
        end = getattr(node, "end_lineno", None) or node.lineno
        for line_number in range(start, min(end, len(lines)) + 1):
            piece = scan_text(
                lines[line_number - 1], base_line=line_number, subject=source_path.as_posix()
            )
            for hit in piece.hits:
                key = (hit.lexeme, hit.line)
                if key not in seen:
                    seen.add(key)
                    hits.append(hit)
        # 兜底：被物理换行切断的 lexeme 在逐行扫里看不见，用合并文本再扫一遍，
        # 命中但未被逐行扫覆盖的锚到节点首行并标注。
        merged = scan_text(str(node.value), subject=source_path.as_posix())
        for hit in merged.hits:
            if not any(existing.lexeme == hit.lexeme for existing in hits if start <= existing.line <= end):
                key = (hit.lexeme, start)
                if key not in seen:
                    seen.add(key)
                    hits.append(
                        LexemeHit(
                            lexeme=hit.lexeme,
                            severity=hit.severity,
                            line=start,
                            excerpt=f"[跨行拼接] {hit.excerpt}",
                        )
                    )
    ordered = tuple(sorted(hits, key=lambda hit: (hit.line, hit.severity, hit.lexeme)))
    decision: Decision = (
        "BLOCK"
        if any(hit.severity == "BLOCK" for hit in ordered)
        else "FLAG"
        if ordered
        else "PASS"
    )
    return GateVerdict(
        gate="gate2_question_surface",
        decision=decision,
        hits=ordered,
        subject=source_path.as_posix(),
    )


# ---------------------------------------------------------------------------
# 闸 3：语义抽检（确定层只做抽样与打包，判定归独立判定者）
# ---------------------------------------------------------------------------

GATE3_SAMPLE_SIZE: Final = 30

#: 判定者不得与生产者同族。今天的生产者走 `codex exec`（GPT 家族），所以判定者取 GLM，
#: fallback 取 DeepSeek —— 两者都不是 GPT 家族。Gemini 全档禁止进评委位（SEM-05 追加裁定）。
GATE3_JUDGE_PRIMARY: Final = "claude-zai:high"
GATE3_JUDGE_FALLBACKS: Final = ("deepseek-go:pro", "kimi-code:high")

GATE3_QUESTION: Final = (
    "下面每项是一段代码解释。逐项判断：这句话里有没有关于该符号在仓库中的重要性、"
    "位置或归属的断言？只能回答 有 / 疑似 / 无 / 判不了 四选一。"
    "回答「有」或「疑似」时必须逐字引用原句中的那一小段作为证据，不得转述。"
)

GATE3_VERDICT_VALUES: Final[frozenset[str]] = frozenset({"有", "疑似", "无", "判不了"})


def sample_for_gate3(
    explanations: Mapping[str, str], *, size: int = GATE3_SAMPLE_SIZE
) -> tuple[tuple[str, str], ...]:
    """确定性抽样：按 sha256(symbol_id) 排序取前 N。同一批解释永远抽出同一批样本。

    不用随机数，因为抽检结果要能被编排者原样复算；一个不可复算的抽检，它的绿不携带信息。
    """

    ordered = sorted(
        explanations.items(),
        key=lambda item: hashlib.sha256(item[0].encode("utf-8")).hexdigest(),
    )
    return tuple(ordered[:size])


def build_gate3_packet(explanations: Mapping[str, str], *, size: int = GATE3_SAMPLE_SIZE) -> dict[str, object]:
    """判定者的输入面：匿名序号 + 解释正文。不给 path、不给源码、不给簇名。

    给 path 会让判定者能自己推断归属，于是它判的是「这个归属对不对」而不是
    「这句话里有没有归属断言」——问题就被换掉了。
    """

    sample = sample_for_gate3(explanations, size=size)
    return {
        "question": GATE3_QUESTION,
        "allowed_verdicts": sorted(GATE3_VERDICT_VALUES),
        "items": [
            {"index": index, "explanation": text}
            for index, (_symbol_id, text) in enumerate(sample, start=1)
        ],
        "_sample_symbol_ids": [symbol_id for symbol_id, _text in sample],
    }


@dataclass(frozen=True)
class Gate3Result:
    total: int
    counts: Mapping[str, int]
    violations: tuple[Mapping[str, object], ...]

    @property
    def violation_rate(self) -> float:
        return round((self.counts.get("有", 0) + self.counts.get("疑似", 0)) / self.total, 4) if self.total else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "gate": "gate3_semantic_sample",
            "total": self.total,
            "counts": dict(self.counts),
            "violation_rate": self.violation_rate,
            "violations": [dict(item) for item in self.violations],
        }


def collect_gate3_result(
    verdicts: Sequence[Mapping[str, object]], symbol_ids: Sequence[str]
) -> Gate3Result:
    """把判定者的四值输出折成读数。判「有」而不引原句的，降级为「判不了」。

    理由：一个没有证据指向 claim 本身的判决，无法被编排者复算，因此不能计入违规。
    这条会低估违规率，是有意为之——宁可漏报也不让不可复算的判决驱动升档。
    """

    counts: dict[str, int] = {value: 0 for value in sorted(GATE3_VERDICT_VALUES)}
    violations: list[Mapping[str, object]] = []
    for row in verdicts:
        verdict = str(row.get("verdict", "")).strip()
        quote = str(row.get("quote", "")).strip()
        index = row.get("index")
        if verdict not in GATE3_VERDICT_VALUES:
            verdict = "判不了"
        if verdict in {"有", "疑似"} and not quote:
            verdict = "判不了"
        counts[verdict] += 1
        if verdict in {"有", "疑似"}:
            position = index - 1 if isinstance(index, int) and 0 < index <= len(symbol_ids) else None
            violations.append(
                {
                    "index": index,
                    "symbol_id": symbol_ids[position] if position is not None else None,
                    "verdict": verdict,
                    "quote": quote,
                }
            )
    return Gate3Result(total=len(verdicts), counts=counts, violations=tuple(violations))


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="src.semantic.gates", description="L1 三道闸")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_source = sub.add_parser("scan-source", help="扫一个 .py 文件的提问面（闸 2）")
    scan_source.add_argument("path")
    scan_source.add_argument("--all-strings", action="store_true")

    scan_prompt = sub.add_parser("scan-prompt", help="扫 stdin 的提问文本（闸 2）")

    sample = sub.add_parser("gate3-packet", help="从解释 JSON 生成闸 3 判定者输入")
    sample.add_argument("explanations_json", help="{symbol_id: text} 的 JSON 文件")
    sample.add_argument("--size", type=int, default=GATE3_SAMPLE_SIZE)

    args = parser.parse_args(argv)

    if args.command == "scan-source":
        verdict = scan_python_source(args.path, all_strings=args.all_strings)
    elif args.command == "scan-prompt":
        verdict = scan_text(sys.stdin.read(), subject="<stdin>")
    else:
        payload = json.loads(Path(args.explanations_json).read_text(encoding="utf-8"))
        print(json.dumps(build_gate3_packet(payload, size=args.size), ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(verdict.as_dict(), ensure_ascii=False, indent=2))
    return 1 if verdict.blocked else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(_main())
