"""屎山的机械判定、双触发升档、失败回退链（F1 §2.2 / 冻结架构 §4.1）。

用户裁定：「聚类、深度思考及分析复杂代码（如屎山代码）时，必须使用性能更好的模型」。
这要求「屎山」有机械判据，否则「必须」落不到实处。

**屎山的可操作定义：局部理解成本高，即读完这段代码本身仍答不出它做什么。**
语句数多 ≠ 屎山；一个 200 行的直筒状态机比一个 30 行的五层嵌套 + 吞异常好读得多。

双触发（两个都要，不合成一条，因为它们的失败方向相反）：
- 只用绝对绊线：整体差的仓库把 60% 的符号送进强模型，成本爆掉；整体干净的仓库里最差的
  那批可能一条绊线都不触。
- 只用仓内分位：干净仓库的 top decile 其实不需要强模型；而全仓都难的库，分位会把
  绝大多数真难的符号判成「相对不难」。

**阈值是种子不是结论。** 校准判据写死为：任一绊线在某仓库上命中率 > 30% 即判该绊线设错
（它本该是尾部判据），必须重标而不是接受。`self_check()` 就是这条，必须随分级一起跑。

命令行（编排者可原样复制）::

    .venv/bin/python -m src.semantic.tiering scan <repo_root> --name flask
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Final, Iterable, Mapping, Sequence

from src.semantic.inventory import enumerate_python_files


METRIC_NAMES: Final[tuple[str, ...]] = (
    "cyc",
    "depth",
    "stmts",
    "params",
    "nonlocal_writes",
    "dyn",
    "swallow",
)

#: 绝对绊线：任一成立即 T3。数值取自对 flask / httpx 的粗看，未做跨仓标定 —— 种子，不是结论。
ABSOLUTE_TRIPWIRES: Final[Mapping[str, int]] = {
    "depth": 5,
    "cyc": 15,
    "stmts": 120,
    "swallow": 1,
    "dyn": 2,
    "params": 8,
}

#: 命中率超过它即判绊线设错（本该是尾部判据）。
TRIPWIRE_MISCALIBRATION_RATE: Final = 0.30

#: 仓内分位：top decile 升 T3。
TOP_DECILE: Final = 0.90

_DYNAMIC_NAMES: Final[frozenset[str]] = frozenset(
    {"getattr", "setattr", "delattr", "eval", "exec", "__import__", "globals", "locals"}
)

#: 档位绑定（冻结架构 §4.1）。链内成员同档或更强；禁止静默降到更弱的档。
TIER_CHAINS: Final[Mapping[str, tuple[str, ...]]] = {
    "T0": (),
    "T1": ("deepseek-go:flash", "kimi-ollama:medium", "composer-cursor:medium"),
    "T2": ("glm-ollama:high", "deepseek-go:pro"),
    "T3": ("grok-build:xhigh", "gpt:luna-max", "claude-zai:high"),
}

TIER_ORDER: Final[tuple[str, ...]] = ("T0", "T1", "T2", "T3")
MANUAL_QUEUE: Final = "MANUAL"


# ---------------------------------------------------------------------------
# 七个纯 AST 指标
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SymbolMetrics:
    symbol_id: str
    path: str
    qualified_name: str
    cyc: int
    depth: int
    stmts: int
    params: int
    nonlocal_writes: int
    dyn: int
    swallow: int

    def values(self) -> tuple[int, ...]:
        return tuple(getattr(self, name) for name in METRIC_NAMES)

    def tripped(self) -> tuple[str, ...]:
        return tuple(
            name for name, threshold in ABSOLUTE_TRIPWIRES.items() if getattr(self, name) >= threshold
        )

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol_id": self.symbol_id,
            "path": self.path,
            "qualified_name": self.qualified_name,
        }
        payload.update({name: getattr(self, name) for name in METRIC_NAMES})
        return payload


def _decision_points(node: ast.AST) -> int:
    """路径数：读者要同时持有的分支状态。"""

    total = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)):
            total += 1
        elif isinstance(child, ast.BoolOp):
            total += max(0, len(child.values) - 1)
        elif isinstance(child, (ast.comprehension,)):
            total += len(child.ifs)
        elif isinstance(child, ast.match_case):
            total += 1
    return 1 + total


def _max_depth(node: ast.AST, *, current: int = 0) -> int:
    """每层嵌套是一条读者必须记住的前置条件。"""

    nesting = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)
    best = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # 嵌套定义自成一个符号，不计进宿主的深度
        step = current + 1 if isinstance(child, nesting) else current
        best = max(best, _max_depth(child, current=step), step)
    return best


def _statement_count(node: ast.AST) -> int:
    return sum(
        1
        for child in ast.walk(node)
        if isinstance(child, ast.stmt) and child is not node
    )


def _param_count(node: ast.AST) -> int:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    args = node.args
    return (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )


def _nonlocal_writes(node: ast.AST) -> int:
    """副作用不在返回值里，读者看不见。"""

    total = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.Global, ast.Nonlocal)):
            total += len(child.names)
        elif isinstance(child, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            for target in targets:
                for inner in ast.walk(target):
                    if isinstance(inner, ast.Attribute):
                        total += 1
                        break
    return total


def _dynamic_uses(node: ast.AST) -> int:
    """静态不可判——真正的屎山标志：连 IR 都建不出正确的边。"""

    total = 0
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in _DYNAMIC_NAMES:
                total += 1
            if any(keyword.arg is None for keyword in child.keywords):
                total += 1  # **kwargs 转发
        elif isinstance(child, ast.Name) and child.id in _DYNAMIC_NAMES:
            total += 0
    return total


def _swallowed_exceptions(node: ast.AST) -> int:
    """失败路径被抹掉，失败条件无法从源码读出。"""

    total = 0
    for child in ast.walk(node):
        if isinstance(child, ast.ExceptHandler):
            bare = child.type is None
            body_is_pass = len(child.body) == 1 and isinstance(child.body[0], ast.Pass)
            if bare or body_is_pass:
                total += 1
    return total


def measure_symbol(node: ast.AST, *, symbol_id: str, path: str, qualified_name: str) -> SymbolMetrics:
    return SymbolMetrics(
        symbol_id=symbol_id,
        path=path,
        qualified_name=qualified_name,
        cyc=_decision_points(node),
        depth=_max_depth(node),
        stmts=_statement_count(node),
        params=_param_count(node),
        nonlocal_writes=_nonlocal_writes(node),
        dyn=_dynamic_uses(node),
        swallow=_swallowed_exceptions(node),
    )


def measure_repository(repo_root: str | Path) -> tuple[SymbolMetrics, ...]:
    """对一个仓库的每个词法符号量七个指标。零 LLM。

    符号识别口径与 `inventory.enumerate_semantic_inventory` 一致（同一套 AST 遍历与
    限定名规则），所以分级的分母与台账分母对得上。
    """

    root = Path(repo_root).resolve()
    # 按 symbol_id 去重，后定义覆盖先定义 —— 与 `inventory.enumerate_semantic_inventory`
    # 的 `symbols[symbol_id] = record` 同口径。不去重会把 `@overload` / 条件重定义
    # 各算一遍，flask 上就是 442 vs 416 的那 26 个差额，分级分母会悄悄大于台账分母。
    collected: dict[str, SymbolMetrics] = {}
    for file_path in enumerate_python_files(root):
        relative = file_path.relative_to(root).as_posix()
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=relative)
        except (OSError, SyntaxError):
            continue
        stack: list[str] = []

        def walk(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name)
                    qualified = ".".join(stack)
                    symbol_id = f"{relative}::{qualified}"
                    collected[symbol_id] = measure_symbol(
                        child,
                        symbol_id=symbol_id,
                        path=relative,
                        qualified_name=qualified,
                    )
                    walk(child)
                    stack.pop()
                else:
                    walk(child)

        walk(tree)
    return tuple(collected[key] for key in sorted(collected))


# ---------------------------------------------------------------------------
# 双触发分级 + 自检
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TierAssignment:
    symbol_id: str
    tier: str
    absolute_trips: tuple[str, ...]
    mess_score: float
    top_decile: bool

    @property
    def reason(self) -> str:
        if self.absolute_trips and self.top_decile:
            return "both"
        if self.absolute_trips:
            return "absolute"
        if self.top_decile:
            return "decile"
        return "baseline"


def _normalized(values: Sequence[int]) -> tuple[float, ...]:
    low, high = min(values), max(values)
    if high == low:
        return tuple(0.0 for _ in values)
    span = float(high - low)
    return tuple((value - low) / span for value in values)


def mess_scores(metrics: Sequence[SymbolMetrics]) -> tuple[float, ...]:
    """六/七项在本仓内各自归一后求和。归一是仓内的，所以它衡量的是「相对本仓有多难」。"""

    if not metrics:
        return ()
    columns = {
        name: _normalized([getattr(item, name) for item in metrics]) for name in METRIC_NAMES
    }
    return tuple(
        round(sum(columns[name][index] for name in METRIC_NAMES), 6)
        for index in range(len(metrics))
    )


def assign_tiers(metrics: Sequence[SymbolMetrics]) -> tuple[TierAssignment, ...]:
    """双触发：绝对绊线 ∨ 仓内 top decile 升 T3。两个触发器分别留痕，不合成。"""

    if not metrics:
        return ()
    scores = mess_scores(metrics)
    ordered = sorted(scores)
    cut_index = min(len(ordered) - 1, int(TOP_DECILE * len(ordered)))
    threshold = ordered[cut_index]
    assignments: list[TierAssignment] = []
    for item, score in zip(metrics, scores):
        trips = item.tripped()
        # 分位阈值处可能有并列；`>=` 会把整片并列都拉进 top decile，所以并列时
        # 只有严格大于阈值的才算，除非阈值本身就是最大值。
        in_decile = score > threshold or (score == threshold == ordered[-1] and score > ordered[0])
        assignments.append(
            TierAssignment(
                symbol_id=item.symbol_id,
                tier="T3" if (trips or in_decile) else "T1",
                absolute_trips=trips,
                mess_score=score,
                top_decile=in_decile,
            )
        )
    return tuple(assignments)


@dataclass(frozen=True)
class TripwireCalibration:
    metric: str
    threshold: int
    hits: int
    total: int

    @property
    def rate(self) -> float:
        return round(self.hits / self.total, 4) if self.total else 0.0

    @property
    def miscalibrated(self) -> bool:
        return self.rate > TRIPWIRE_MISCALIBRATION_RATE

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric,
            "threshold": self.threshold,
            "hits": self.hits,
            "total": self.total,
            "rate": self.rate,
            "verdict": "MISCALIBRATED" if self.miscalibrated else "ok",
        }


def self_check(metrics: Sequence[SymbolMetrics]) -> tuple[TripwireCalibration, ...]:
    """任一绊线命中率 > 30% 即判该绊线设错。必须随分级一起跑，否则分级会静默退化。"""

    total = len(metrics)
    return tuple(
        TripwireCalibration(
            metric=name,
            threshold=threshold,
            hits=sum(getattr(item, name) >= threshold for item in metrics),
            total=total,
        )
        for name, threshold in ABSOLUTE_TRIPWIRES.items()
    )


# ---------------------------------------------------------------------------
# 失败回退链
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Attempt:
    tier: str
    failed_checks: tuple[str, ...]
    confidence: str
    unresolved: tuple[str, ...]
    payload: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "tier": self.tier,
            "failed_checks": list(self.failed_checks),
            "confidence": self.confidence,
            "unresolved": list(self.unresolved),
            "payload": dict(self.payload) if self.payload is not None else None,
        }


@dataclass(frozen=True)
class EscalationState:
    """一个符号的升档轨迹。`attempts` 只增不改——上一档的产出保留，不覆盖。"""

    symbol_id: str
    tier: str
    attempts: tuple[Attempt, ...] = ()
    manual_queue_reason: str = ""

    @property
    def exhausted(self) -> bool:
        return self.tier == MANUAL_QUEUE

    def as_dict(self) -> dict[str, object]:
        return {
            "symbol_id": self.symbol_id,
            "tier": self.tier,
            "attempts": [attempt.as_dict() for attempt in self.attempts],
            "manual_queue_reason": self.manual_queue_reason,
        }


def _next_tier(current: str) -> str:
    if current not in TIER_ORDER:
        raise ValueError(f"unknown tier: {current}")
    index = TIER_ORDER.index(current)
    return TIER_ORDER[index + 1] if index + 1 < len(TIER_ORDER) else MANUAL_QUEUE


def initial_tier(assigned: str) -> str:
    """双触发判为 T3 的从 T3 起；其余从 T0 模板起。"""

    return "T3" if assigned == "T3" else "T0"


def should_escalate(
    *,
    failed_checks: Sequence[str],
    confidence: str,
    unresolved: Sequence[str],
    tier: str = "T1",
) -> bool:
    """回退链的触发谓词。

    T0 只因 L1-a..d 失败才升档——模板的 `confidence=low ∧ unresolved 非空`
    是规格，不是缺陷。T1 起：任一后置检查失败 ∨（低置信 ∧ 有显式空缺）。
    """

    if tier == "T0":
        return bool(failed_checks)
    return bool(failed_checks) or (confidence == "low" and bool(unresolved))


def record_attempt(
    state: EscalationState,
    *,
    failed_checks: Sequence[str],
    confidence: str,
    unresolved: Sequence[str],
    payload: Mapping[str, Any] | None = None,
) -> EscalationState:
    """记一次尝试并决定去哪。三档全失败落 `unresolved` 进人工队列。

    L1-b 的特殊处置（F1 §2.1 逐字）：命中一次升档重跑，第二次仍命中则落 `unresolved`
    并进人工抽检队列，**不静默通过**。这条由下面的 `l1b_strikes` 承担。
    """

    attempt = Attempt(
        tier=state.tier,
        failed_checks=tuple(failed_checks),
        confidence=confidence,
        unresolved=tuple(unresolved),
        payload=payload,
    )
    attempts = state.attempts + (attempt,)
    if not should_escalate(
        failed_checks=failed_checks,
        confidence=confidence,
        unresolved=unresolved,
        tier=state.tier,
    ):
        return replace(state, attempts=attempts)

    l1b_strikes = sum("L1-b" in item.failed_checks for item in attempts)
    if l1b_strikes >= 2:
        return replace(
            state,
            tier=MANUAL_QUEUE,
            attempts=attempts,
            manual_queue_reason="L1-b hit twice: one_liner keeps restating the symbol name",
        )

    following = _next_tier(state.tier)
    if following == MANUAL_QUEUE:
        return replace(
            state,
            tier=MANUAL_QUEUE,
            attempts=attempts,
            manual_queue_reason=f"all tiers exhausted; last failures={list(failed_checks)}",
        )
    return replace(state, tier=following, attempts=attempts)


def dispatch_chain(tier: str) -> tuple[str, ...]:
    """该档的 primary + fallback 链。派发时必须显式带上，不依赖 router 默认降级。"""

    if tier not in TIER_CHAINS:
        raise ValueError(f"unknown tier: {tier}")
    return TIER_CHAINS[tier]


def router_argv(
    tier: str,
    *,
    task_name: str,
    workdir: str,
    python: str = "python3",
) -> tuple[str, ...]:
    """带 `--fallback` 的 router 命令。T0 无模型，返回空元组。"""

    chain = dispatch_chain(tier)
    if not chain:
        return ()
    primary, *fallback = chain
    command = [
        python,
        "-m",
        "tools.cli_agent.router",
        "--primary",
        primary,
    ]
    if fallback:
        command.append("--fallback")
        command.extend(fallback)
    command.extend(["--task-name", task_name, "--workdir", workdir])
    return tuple(command)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def scan_report(repo_root: str | Path, *, name: str = "") -> dict[str, Any]:
    metrics = measure_repository(repo_root)
    assignments = assign_tiers(metrics)
    calibration = self_check(metrics)
    tier_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for assignment in assignments:
        tier_counts[assignment.tier] = tier_counts.get(assignment.tier, 0) + 1
        reason_counts[assignment.reason] = reason_counts.get(assignment.reason, 0) + 1
    return {
        "repo": name or Path(repo_root).name,
        "repo_root": Path(repo_root).resolve().as_posix(),
        "symbol_count": len(metrics),
        "tier_counts": tier_counts,
        "trigger_counts": reason_counts,
        "tripwire_calibration": [item.as_dict() for item in calibration],
        "miscalibrated": [item.metric for item in calibration if item.miscalibrated],
        "top_mess": [
            {"symbol_id": assignment.symbol_id, "mess_score": assignment.mess_score,
             "trips": list(assignment.absolute_trips)}
            for assignment in sorted(assignments, key=lambda item: -item.mess_score)[:10]
        ],
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="src.semantic.tiering", description="屎山分级与自检")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="扫一个仓库，出分级读数与绊线命中率自检")
    scan.add_argument("repo_root")
    scan.add_argument("--name", default="")
    scan.add_argument("--out", default="")
    args = parser.parse_args(argv)

    report = scan_report(args.repo_root, name=args.name)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if report["miscalibrated"] else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(_main())
