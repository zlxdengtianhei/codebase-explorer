"""L1 输出面：`L1SymbolFact` + 四条确定层后置检查（L1-a..d）。

F1 §2.1 逐字：**这张表里没有 `role`、没有 `importance`、没有 `module`、没有 `is_core`。**
输入面装不下地位信息，输出面装不下地位断言，两侧对称。4(a) 于是由结构承载，不由 prompt
措辞承载——措辞可以被下一个人改回去，schema 不行。

`unresolved` 是诚实空缺通道。今天的四个 residual CODE（`SYNTAX_ERROR_FILE` /
`TYPE_CHECKING_STUB` / `GENERATED_CODE` / `VENDORED_THIRD_PARTY`，`service.py:88-95`）
全是「这个文件不该被解释」，没有一个能表达「我读了但我看不出来」。缺这条通道，
模型唯一的出路是编。`UNRESOLVED_CODES` 补的就是这一格。

四条后置检查跑在 submit 时，零模型。它们的负对照读数在
`runs/r004_.../evidence/core/negative_control_L1.json`——**一条从不变红的判据，
它的绿不携带信息**（r003 教训逐字）。
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, Literal, Mapping, Sequence


class Effect(StrEnum):
    PURE = "pure"
    READS_FS = "reads_fs"
    WRITES_FS = "writes_fs"
    NET_IO = "net_io"
    MUTATES_SELF = "mutates_self"
    MUTATES_ARG = "mutates_arg"
    GLOBAL_STATE = "global_state"
    RAISES = "raises"
    SPAWNS = "spawns"
    BLOCKING = "blocking"


Confidence = Literal["low", "medium", "high"]

ONE_LINER_MAX_CHARS: Final = 160

#: 诚实空缺的允许前缀。带 `:` 的可以挂具体对象（如 `NEEDS_CALLEE_SEMANTICS:path.py::f`）。
UNRESOLVED_CODES: Final[tuple[str, ...]] = (
    "LOCAL_SEMANTICS_UNCLEAR",
    "NEEDS_CALLEE_SEMANTICS",
    "DYNAMIC_DISPATCH_UNRESOLVED",
    "EXTERNAL_CONTRACT_UNKNOWN",
    "SIDE_EFFECT_UNVERIFIABLE",
)

L1_FACT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "symbol_id",
        "one_liner",
        "behavior",
        "effects",
        "inputs_outputs",
        "failure_modes",
        "identifiers_used",
        "unresolved",
        "confidence",
    }
)

#: 输出面禁止承载的东西。同 `l1_packet`，判据是白名单的补集；本表只为报错点名。
KNOWN_FORBIDDEN_FACT_FIELDS: Final[tuple[str, ...]] = (
    "role",
    "importance",
    "module",
    "module_id",
    "is_core",
    "cluster",
    "cluster_id",
    "rank",
    "centrality",
)


class L1FactError(ValueError):
    """`L1SymbolFact` 构造期拒收。"""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise L1FactError(f"{field} must be a non-empty string")
    return value


def _str_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise L1FactError(f"{field} must be a tuple of non-empty strings")
    return value


@dataclass(frozen=True)
class L1SymbolFact:
    """一个符号的局部事实。没有任何字段能承载「它在仓库里是什么地位」。"""

    symbol_id: str
    one_liner: str
    behavior: str
    effects: tuple[Effect, ...]
    inputs_outputs: str
    failure_modes: tuple[str, ...]
    identifiers_used: tuple[str, ...]
    unresolved: tuple[str, ...]
    confidence: Confidence

    def __post_init__(self) -> None:
        _text(self.symbol_id, "symbol_id")
        one_liner = _text(self.one_liner, "one_liner")
        if len(one_liner) > ONE_LINER_MAX_CHARS:
            raise L1FactError(f"one_liner must be at most {ONE_LINER_MAX_CHARS} characters")
        _text(self.behavior, "behavior")
        _text(self.inputs_outputs, "inputs_outputs")
        if not isinstance(self.effects, tuple) or not self.effects:
            raise L1FactError("effects must be a non-empty tuple")
        for effect in self.effects:
            if not isinstance(effect, Effect):
                raise L1FactError(f"effects must contain Effect members: {effect!r}")
        if len(set(self.effects)) != len(self.effects):
            raise L1FactError("effects must be unique")
        if Effect.PURE in self.effects and len(self.effects) > 1:
            raise L1FactError("pure cannot be combined with other effects")
        _str_tuple(self.failure_modes, "failure_modes")
        _str_tuple(self.identifiers_used, "identifiers_used")
        _str_tuple(self.unresolved, "unresolved")
        for item in self.unresolved:
            code = item.split(":", 1)[0]
            if code not in UNRESOLVED_CODES:
                raise L1FactError(f"unresolved code is not allowed: {item!r}")
        if self.confidence not in ("low", "medium", "high"):
            raise L1FactError("confidence must be low, medium or high")

    def to_payload(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "one_liner": self.one_liner,
            "behavior": self.behavior,
            "effects": [effect.value for effect in self.effects],
            "inputs_outputs": self.inputs_outputs,
            "failure_modes": list(self.failure_modes),
            "identifiers_used": list(self.identifiers_used),
            "unresolved": list(self.unresolved),
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# L1-b 的词表：把「复述名字」变成可机械判定的谓词
# ---------------------------------------------------------------------------

#: 代码里最常见的动词/名词到中文的对照。L1-b 需要它才能把英文符号名与中文一行解释对上：
#: `handle_request` 的复述是「处理请求」，两边不共享任何字面。
_NAME_GLOSS: Final[Mapping[str, tuple[str, ...]]] = {
    "handle": ("处理", "处置"),
    "process": ("处理", "加工"),
    "request": ("请求",),
    "response": ("响应", "回应"),
    "get": ("获取", "取得", "返回"),
    "fetch": ("获取", "拉取"),
    "set": ("设置", "设定"),
    "parse": ("解析",),
    "build": ("构建", "构造", "创建"),
    "make": ("创建", "构造"),
    "create": ("创建", "新建"),
    "init": ("初始化",),
    "initialize": ("初始化",),
    "validate": ("校验", "验证"),
    "check": ("检查", "校验"),
    "verify": ("验证", "核验"),
    "render": ("渲染",),
    "load": ("加载", "载入"),
    "save": ("保存", "存储"),
    "store": ("存储", "保存"),
    "write": ("写入", "写"),
    "read": ("读取", "读"),
    "cache": ("缓存",),
    "config": ("配置",),
    "configure": ("配置",),
    "file": ("文件",),
    "path": ("路径",),
    "error": ("错误", "异常"),
    "exception": ("异常",),
    "client": ("客户端",),
    "server": ("服务端", "服务器"),
    "session": ("会话",),
    "token": ("令牌",),
    "run": ("运行", "执行"),
    "execute": ("执行", "运行"),
    "update": ("更新",),
    "delete": ("删除",),
    "remove": ("移除", "删除"),
    "send": ("发送",),
    "receive": ("接收",),
    "connect": ("连接",),
    "close": ("关闭",),
    "open": ("打开",),
    "resolve": ("解析", "求解"),
    "format": ("格式化",),
    "encode": ("编码",),
    "decode": ("解码",),
    "serialize": ("序列化",),
    "normalize": ("归一化", "规范化"),
    "count": ("计数", "统计"),
    "list": ("列出", "列表"),
    "add": ("添加", "新增"),
    "append": ("追加",),
    "apply": ("应用",),
    "register": ("注册",),
    "dispatch": ("派发", "分发"),
    "iter": ("遍历", "迭代"),
    "walk": ("遍历",),
    "scan": ("扫描",),
    "collect": ("收集", "汇集"),
    "emit": ("产出", "发出"),
    "report": ("报告",),
    "record": ("记录",),
    "log": ("日志", "记录"),
}

#: 通用动词 / 填充词。只由它们组成的一行解释等于什么都没说。
_GENERIC_TERMS: Final[frozenset[str]] = frozenset(
    {
        "处理", "逻辑", "相关", "功能", "实现", "用于", "进行", "完成", "操作", "方法",
        "函数", "本函数", "该函数", "本方法", "该方法", "本类", "该类", "这个", "一个",
        "内容", "数据", "信息", "对象", "结果", "各种", "若干", "以及", "并且", "然后",
        "返回", "接受", "接收", "提供", "负责", "包含", "支持", "工具", "辅助", "通用",
        "handles", "handle", "processes", "process", "performs", "perform", "does", "do",
        "returns", "return", "provides", "provide", "implements", "implement", "related",
        "logic", "function", "method", "class", "helper", "utility", "generic", "various",
        "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "this", "that",
        "it", "its", "is", "are", "be", "as", "by", "from", "into", "then",
    }
)

_STOPWORD_CHARS: Final[frozenset[str]] = frozenset("的了着地得与和或在是把被将对为其之所且")
_PUNCT_RE: Final = re.compile(r"[\s,，。、；;：:（）()\[\]{}<>\"'`\-_/\\|.!?！？+*=#$%^&~@0-9]+")
_ASCII_WORD_RE: Final = re.compile(r"[a-zA-Z][a-zA-Z0-9]*")
_CJK_RE: Final = re.compile(r"[一-鿿]")


def _split_name_tokens(qualified_name: str) -> frozenset[str]:
    """把 `HttpClient.send_request` 拆成 {http, client, send, request}。"""

    tokens: set[str] = set()
    for chunk in re.split(r"[.\s_\-]+", qualified_name):
        if not chunk:
            continue
        for piece in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", chunk):
            if piece:
                tokens.add(piece.lower())
    return frozenset(tokens)


def _restatement_vocabulary(qualified_name: str) -> frozenset[str]:
    name_tokens = _split_name_tokens(qualified_name)
    vocabulary: set[str] = set(name_tokens) | set(_GENERIC_TERMS)
    for token in name_tokens:
        vocabulary.update(_NAME_GLOSS.get(token, ()))
    for token in _GENERIC_TERMS:
        vocabulary.update(_NAME_GLOSS.get(token, ()))
    return frozenset(vocabulary)


def residual_content_terms(text: str, vocabulary: frozenset[str]) -> tuple[str, ...]:
    """返回 `text` 里**超出词表**的实词。空元组 = 这句话没说词表以外的任何东西。

    中文没有分词器可用，所以走词表最长匹配：能被词表吃掉的连续片段消费掉，
    吃不掉的连续 CJK 片段（长度 ≥2）与吃不掉的 ASCII 词计为实词。
    这个方向是保守的——词表越小越容易判「说了新东西」，即越不容易误伤。
    """

    ordered = sorted(vocabulary, key=len, reverse=True)
    residual: list[str] = []
    for segment in _PUNCT_RE.split(text):
        if not segment:
            continue
        index = 0
        buffer: list[str] = []
        while index < len(segment):
            matched = ""
            lowered = segment[index:].lower()
            for term in ordered:
                if term and lowered.startswith(term.lower()):
                    matched = term
                    break
            if matched:
                if buffer:
                    residual.append("".join(buffer))
                    buffer = []
                index += len(matched)
                continue
            char = segment[index]
            if char in _STOPWORD_CHARS:
                if buffer:
                    residual.append("".join(buffer))
                    buffer = []
            else:
                buffer.append(char)
            index += 1
        if buffer:
            residual.append("".join(buffer))
    meaningful: list[str] = []
    for run in residual:
        if _CJK_RE.search(run):
            if len(run) >= 2:
                meaningful.append(run)
        else:
            for word in _ASCII_WORD_RE.findall(run):
                if word.lower() not in vocabulary and len(word) > 1:
                    meaningful.append(word.lower())
    return tuple(meaningful)


# ---------------------------------------------------------------------------
# L1-a..d
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {"check": self.check, "passed": self.passed, "detail": self.detail}


def check_l1a_identifier_closure(
    fact: L1SymbolFact, *, source_body: str, callee_signatures: Sequence[tuple[str, str]] = ()
) -> CheckResult:
    """L1-a：`identifiers_used` 每一项必须出现在源码或 callee 签名里。"""

    haystack = source_body + "\n" + "\n".join(f"{callee}\n{signature}" for callee, signature in callee_signatures)
    missing = tuple(item for item in fact.identifiers_used if item not in haystack)
    return CheckResult(
        check="L1-a",
        passed=not missing,
        detail="" if not missing else f"identifiers absent from packet: {list(missing)}",
    )


def check_l1b_name_restatement(
    fact: L1SymbolFact, *, qualified_name: str, tier: str = "T1"
) -> CheckResult:
    """L1-b：一行解释不能只是把符号名换成中文再说一遍。

    T0 模板层豁免——模板产出本来就是 AST 事实陈述，复述名字是它的规格不是它的缺陷。
    这是四条里唯一有误伤风险的一条，所以处置是升档重跑，不是直接判死（见 `tiering.escalate`）。
    """

    if tier.upper() == "T0":
        return CheckResult(check="L1-b", passed=True, detail="T0 template tier is exempt")
    vocabulary = _restatement_vocabulary(qualified_name)
    residual = residual_content_terms(fact.one_liner, vocabulary)
    return CheckResult(
        check="L1-b",
        passed=bool(residual),
        detail=""
        if residual
        else f"one_liner restates the symbol name and generic verbs only: {fact.one_liner!r}",
    )


def check_l1c_gap_consistency(fact: L1SymbolFact) -> CheckResult:
    """L1-c：`confidence == low` 时 `unresolved` 必须非空。

    低置信而不说不清哪里不清楚，等于把「我编的」写成了「我不太确定」。
    """

    ok = fact.confidence != "low" or bool(fact.unresolved)
    return CheckResult(
        check="L1-c",
        passed=ok,
        detail="" if ok else "confidence=low requires a non-empty unresolved list",
    )


def check_l1d_schema(payload: Mapping[str, object]) -> CheckResult:
    """L1-d：字段集恰等 `L1_FACT_FIELDS`（两向都判）。"""

    present = set(payload)
    extra = sorted(present - L1_FACT_FIELDS)
    missing = sorted(L1_FACT_FIELDS - present)
    ok = not extra and not missing
    return CheckResult(
        check="L1-d",
        passed=ok,
        detail="" if ok else f"field set mismatch; forbidden={extra} missing={missing}",
    )


def run_l1_checks(
    fact: L1SymbolFact,
    *,
    source_body: str,
    qualified_name: str,
    callee_signatures: Sequence[tuple[str, str]] = (),
    tier: str = "T1",
) -> tuple[CheckResult, ...]:
    """四条一起跑。返回全部结果，不短路——短路会让后面的检查永远没有读数。"""

    return (
        check_l1a_identifier_closure(fact, source_body=source_body, callee_signatures=callee_signatures),
        check_l1b_name_restatement(fact, qualified_name=qualified_name, tier=tier),
        check_l1c_gap_consistency(fact),
        check_l1d_schema(fact.to_payload()),
    )


def failed_checks(results: Sequence[CheckResult]) -> tuple[str, ...]:
    return tuple(result.check for result in results if not result.passed)


def parse_l1_fact_payload(payload: Mapping[str, object]) -> L1SymbolFact:
    """从 JSON 对象构造 `L1SymbolFact`。字段集先过 L1-d，再构造。"""

    schema = check_l1d_schema(payload)
    if not schema.passed:
        raise L1FactError(schema.detail)
    effects_raw = payload["effects"]
    if not isinstance(effects_raw, (list, tuple)):
        raise L1FactError("effects must be a list")
    effects = tuple(Effect(item) for item in effects_raw)
    return L1SymbolFact(
        symbol_id=str(payload["symbol_id"]),
        one_liner=str(payload["one_liner"]),
        behavior=str(payload["behavior"]),
        effects=effects,
        inputs_outputs=str(payload["inputs_outputs"]),
        failure_modes=tuple(str(item) for item in payload["failure_modes"]),  # type: ignore[arg-type]
        identifiers_used=tuple(str(item) for item in payload["identifiers_used"]),  # type: ignore[arg-type]
        unresolved=tuple(str(item) for item in payload["unresolved"]),  # type: ignore[arg-type]
        confidence=payload["confidence"],  # type: ignore[arg-type]
    )


def try_parse_l1_fact_text(text: str) -> L1SymbolFact | None:
    """解释正文若是 L1 fact JSON 就解析，否则返回 None（legacy 自由文本）。"""

    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "one_liner" not in payload:
        return None
    try:
        return parse_l1_fact_payload(payload)
    except (L1FactError, ValueError, KeyError, TypeError):
        return None


def t0_template_fact(
    *,
    symbol_id: str,
    source_body: str,
    qualified_name: str,
    kind: str,
) -> L1SymbolFact:
    """T0：零 LLM 的 AST 事实陈述。L1-b 对它豁免。

    它不声称自己读懂了代码。`confidence=low` 且 `unresolved` 非空，
    所以诚实空缺是开着的。回退链里 T0 只因 L1-a..d 失败才升档，
    不因 low+unresolved 升档——那是 T1 以后的触发器。
    """

    names: list[str] = []
    params: list[str] = []
    has_raise = False
    try:
        tree = ast.parse(source_body)
    except SyntaxError:
        tree = None
    if tree is not None:
        names = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name)})
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                has_raise = True
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not params:
                args = node.args
                params = [item.arg for item in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
                if args.vararg:
                    params.append("*" + args.vararg.arg)
                if args.kwarg:
                    params.append("**" + args.kwarg.arg)
    one_liner = f"AST 模板：{kind} {qualified_name} 的词法形参与直接名字"
    if len(one_liner) > ONE_LINER_MAX_CHARS:
        one_liner = one_liner[:ONE_LINER_MAX_CHARS]
    visible = ", ".join(names[:24]) or "无"
    return L1SymbolFact(
        symbol_id=symbol_id,
        one_liner=one_liner,
        behavior=(
            f"T0 模板。限定名 {qualified_name}。形参 {params or '[]'}。"
            f"源码可见名字：{visible}。"
        ),
        effects=(Effect.RAISES,) if has_raise else (Effect.PURE,),
        inputs_outputs=f"形参 {params or '[]'}；返回值未从 AST 判定",
        failure_modes=("T0 模板不判定失败路径",),
        identifiers_used=tuple(names[:24]),
        unresolved=("LOCAL_SEMANTICS_UNCLEAR",),
        confidence="low",
    )
