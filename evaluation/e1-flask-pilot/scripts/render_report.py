"""Render the bounded E1b result after raw runs and reductions finish."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import collections, csv, json, statistics
from pathlib import Path
E = Path(__file__).resolve().parent
DEST = Path(os.path.expandvars('$TASK_DIR/scratch/opt_e1/e1b_result.md'))

def read(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default
M = read(E / 'metrics.json', {})
G = M.get('groups', {})
S = read(E / 'cbe-flask/run/summary.json', {})
A = read(E / 'cbe-flask/accounting.json', {})
F = read(E / 'cbe-flask/first-summary.json', {})
R = read(E / 'cbe-flask/resume-summary.json', {})
B = read(E / 'blind-arm-guess/result.json', {})
probe = read(E / 'judge/model-probe.json', {})
sample = read(E / 'questions/sample.json', {})
w_ready = read(E / 'W-READY.json', {})

def num(v, d=1):
    return 'NA' if v is None else f'{v:,.{d}f}'

def pct(v, d=0):
    return 'NA' if v is None else f'{v * 100:.{d}f}%'
lines = []

def add(s=''):
    lines.append(s)
add('**E1b：Flask 试点结果（冻结 CBE `9c6499e`，SWE-QA `c13deac`）**')
add()
subset25 = read(E / 'questions/sample25.json', {}).get('qids', sample.get('qids', []))
complete = [a for a in ['S', 'C0', 'C', 'W'] if all((G.get(f'{a}-{s}-r0', {}).get('n') == (len(subset25) if a in ('C', 'W') and s == 25 else 10) for s in [10, 25]))]
dirs = []
for st in [10, 25]:
    d = M.get('paired', {}).get(str(st), {}).get('C-S', {})
    dirs.append(f'{st} 步 C−S ' + ('正向' if (d.get('mean') or 0) > 0 else '负向' if (d.get('mean') or 0) < 0 else '无可用配对或为零') + f"（n={d.get('n', 0)}，均差 {num(d.get('mean'))}）")
add(f"CBE 首轮状态 `{F.get('status', '未知')}`，最终 `{S.get('status', '未知')}`，verify={S.get('deterministic_checks_ok', '未知')}；完成两种步数试答的组为 {', '.join(complete) or '无'}。" + '；'.join(dirs) + '。这些是 10 题试点读数，不是 48 题主指标的结论。')
add()
add(f'**07:08Z 主会话范围调整（偏离 EVAL 第 8 节 E1）：** S/C0 的 10、25 步各保留完整 10 题；C/W 的 10 步仍各 10 题，25 步各只做同一固定 5 题 `{subset25}`（0 起）。种子仍为 20261017，类型配额 2/1/1/1 后层内分层，细则 `E/questions/sample25.json`；顺序为 C0/25→C/10→就绪的 W/10→C/25→W/25，并发不超过 4。两个步数档的 C−S 样本数不同，另报同五题的步数对照。')
add()
add(f'产物根目录 E＝`{E}`。原始答案、逐步历史和失败尝试在 `E/answers/<组>-<步数>-r<重复>/qNN.json`；三次判分与重判原件在 `E/judge/`；全部机器读数在 `E/metrics.json`。')
add()
add('**W 握手：** 由 E1a 在真正完成并核过后写 `E/W-READY.json`；complete=true 才运行，complete=false 则记录 reason 并跳过。尚无就绪标记时，沿用原任务“其余工作结束仍未完成则不跑 W”的例外。')
add()
add('**生成与记账。** 输入为只读 `eval/flask-85c5d93`（仅 src/tests，共 87 文件，其中 65 个 Python 文件进入 CBE）；先建图，再用冻结 src、既有 venv、api host、jobs=2 和默认 GLM 设置生成。正文/源码 token 比的分母是 CBE 冻结的 65 个 Python 文件，不含其余模板和资源。密钥只在父进程内存/环境中传递。')
add()
add('| 阶段 | UTC 开始 | UTC 结束 | 墙钟秒 | 返回码 |')
add('|---|---|---|---:|---:|')
for p in A.get('phases', []):
    add(f"| {p['phase']} | {p['start_utc']} | {p['end_utc']} | {num(p['wall_seconds'])} | {p['exit_code']} |")
add()
add(f"首轮 complete={F.get('status') == 'complete'}，首轮 verify={F.get('deterministic_checks_ok', '未知')}；" + ('按提示续跑一次，续跑状态 ' + str(R.get('status')) if R else '未续跑') + f"。最终 answer_fallback={S.get('answer_fallback_count', 0)}，id_corrected={S.get('id_corrected_count', 0)}；原件 `E/cbe-flask/first-summary.json`、`resume-summary.json`（若有）、`verify-final.log`。")
calls = list(csv.DictReader((E / 'cbe-flask/run/calls.csv').open())) if (E / 'cbe-flask/run/calls.csv').exists() else []
add(f"累计模型调用 {S.get('calls', '未知')}；逻辑任务 {len({r['task'] for r in calls})}，calls.csv 行数 {len(calls)}，attempt>1 行数 {sum((int(r.get('attempt') or 0) > 1 for r in calls))}，原始 result 分布 `{json.dumps(dict(collections.Counter((r.get('result') for r in calls))))}`。首轮与续跑的完整调用统计保留于各自 summary 快照；API 证据在 `run/raw/*.api.json`。")
layers = S.get('layers', {})
add(f"源码 {layers.get('source_tokens', S.get('source_tokens'))} o200k token；模型正文 {layers.get('model_body_tokens')}（占源码 {pct(layers.get('model_body_source_ratio'), 2)}）；发布 Markdown {layers.get('semantic_tokens')}（占源码 {pct(layers.get('published_markdown_source_ratio'), 2)}）。查询层大小 {json.dumps(A.get('query_layer_bytes', {}))} 字节，单独列示。")
add(f"网关窗口 {A.get('start_utc')}—{A.get('end_utc')}，同模型全部请求 {A.get('window_glm_requests')} 条；agent 分布 `{json.dumps(A.get('window_agent_counts', {}))}`。CBE agent 命中 {A.get('cbe_label_matches')}，按原始响应 ID 精确匹配 {A.get('exact_response_id_matches')}，最终归属 {A.get('attributed_requests')} / {A.get('raw_api_records')}，完整归属={A.get('attribution_complete')}。")
add(f"网关 CBE token `{json.dumps(A.get('gateway_token_totals', {}))}`；CBE API 原件 token `{json.dumps(A.get('api_usage_totals', {}))}`；CBE summary `{json.dumps(A.get('summary_tokens', {}))}`，网关减 summary 差值 `{json.dumps(A.get('gateway_minus_summary_tokens', {}))}`；服务模型异常 {len(A.get('model_mismatches', []))} 条；正文服务模型 `{json.dumps(A.get('raw_actual_models', {}))}`。保留 `E/usage-final.csv` 与 `E/cbe-flask/gateway-requests.csv`（若成功归属）；无公开价表，未折算费用。")
add()
add('**Harness 与隔离。** `E/harness.patch` 是对只读上游的完整差异；`E/requirements-freeze.txt` 固定试验 venv 依赖。批次入口为 `E/run_pilot.py`，直接复用上游 QAAgent；`continue_pipeline.py` 串行排作答批次，`watch_judge.py` 增量判分。')
add()
add('- `_build_instance_prompt` 加组别提示，输入与输出 question 保持原文；所有组要求只引用源码路径。C0/W 提示句仅 docs 绝对路径不同。')
add('- 观察上限统一 20,000 字符；实际呈现给模型的累计字符、截断次数与工具数逐题记录。步数上限 10/25 均实跑，达到上限后保留上游额外一次收尾模型调用。')
add('- 工具子进程 PATH 仅本试验解释器目录（内有系统工具符号链接）及 C 组 cbe 目录；C 提示给绝对 cbe 路径与绝对 run-dir，cbe wrapper 只加载冻结 src。')
add('- `LocalEnv` 统一通过 sandbox-exec 执行 bash/read_file/grep/ls，deny network*、deny file-read*、deny file-write*，只允许本组 repo/docs/run、解释器依赖与系统库；配置文件与参考答案未列入可读路径。系统运行需读根目录本身和文件元数据，未开放根目录下所有文件内容。')
add('- 每组独立无 .git 源码副本，源码文件只读；CBE docs/run 均在源码外。`E/sandbox-smoke.json` 实测源码可读，参考答案/Pi/Magpie 配置读被拒、网络被拒、写入被拒；`E/contract-smoke.json` 核相同文件 SHA 与原题不变。')
add('- 为控制悬挂请求，作答与判官显式设单请求 240 秒、禁 SDK 隐式重试，全部重跑由试验层记录；这是 EVAL 未规定的传输设置，四组一致。S/10 q6 首次第 3 步超时，第二次有效作答，完整消耗计入。CBE 保持冻结默认 1800 秒。')
add('- 无答案（空、Error、工具 JSON、异常/超限）最多完整重跑 2 次，仍失败为 no_answer/NA；有效低分答案照判。判官每次独立判分最多重判 2 次，仍失败为 judge_failure/NA。主表 NA=5，另给有效题均分。')
add(f"- 判官 `{probe.get('selected')}`，OpenAI 兼容接口；" + ('未换备用模型。' if probe.get('selected') == 'codex/gpt-6.1-sol' else '探针失败后按授权换备用，见 model-probe.json。') + ' 原 rubric 全文不变，移除 Azure 配置与非标准 thinking 请求体；每题 3 次、逐维取中位数再求和。判官输入只有原题、参考答案和候选答案。')
model_audit = read(E / 'model-identity-audit.json', {})
add()
add(f"共享网关服务模型另核：完整 E1 窗口筛到 OpenAI/zai 请求 {model_audit.get('gateway_requests')} 条（含 CodeWiki raw 阶段，不能全部归属本任务）；至少 {model_audit.get('received_model_calls_minimum')} 次本任务模型回复已被客户端记录；服务模型 `{json.dumps(model_audit.get('served_models', {}))}`，换模型异常 {len(model_audit.get('model_mismatches', []))}。范围与原件在 `E/model-identity-audit.json`；逐题请求 ID 未附加，因此逐题用量仍按可对应的客户端记录报告。")
add()
add('**题与主读数。** 48 题仅凭题面人工标 What/How/Why/Where 与四层；优先判设计/影响，再判跨单元流程、单元行为、定位。标签、每题理由与抽样算法在 `E/questions/labels.json`、`prepare.py`。')
add('48 题类型各 12 题；四层定位/单元行为/跨模块流程/影响与设计分别为 1/13/17/17 题。')
add(f"种子 `{sample.get('seed')}`，从 0 起的题号 `{sample.get('qids')}`。What/How/Why/Where 配额 3/3/2/2；唯一纯定位题 q41 必选，其余在类型内按层最大余数分配后随机抽。分层并非简单随机样本；E2 应全用 48 题并标出这 10 题。")
add()
add('| 组/上限 | 有效/计划 n | 重试/上下文超限 | 总分均值 NA=5 | 有效题均值 | 五维中位数 正/全/关/清/推 | 命中上限 | 工具观察累计/题均字符 | 批次墙钟秒 |')
add('|---|---:|---:|---:|---:|---|---:|---:|---:|')
for arm in ['S', 'C0', 'C', 'W']:
    for st in [10, 25]:
        g = G.get(f'{arm}-{st}-r0')
        if g:
            add(f"| {arm}/{st} | {g['valid_answers']}/{g['n']} | {g['attempts'] - g['n']}/{g['context_overflows']} | {num(g['mean_total_na5'])} | {num(g['valid_only_mean_total'])} | " + '/'.join((num(g['dimensions_median'][d]) for d in ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning'])) + f" | {pct(g['limit_hit_rate'])} | {g['observations_chars_total']:,}/{num(g['observations_chars_mean_per_question'], 0)} | {num(g['wall_seconds_batch'])} |")
        else:
            add(f'| {arm}/{st} | 未跑 | NA | NA | NA | NA | NA | NA | NA |')
add()
add(f"工具协议累计未解析回复 {sum((g.get('unparsed_reply_count', 0) for g in G.values()))} 次，强制收尾仍是工具 JSON 的失败 {sum((g.get('final_tool_json_failures', 0) for g in G.values()))} 次；上下文超限 {sum((g.get('context_overflows', 0) for g in G.values()))} 次，未返回 usage 的 API 失败尝试 {sum((g.get('failed_api_attempts_with_unknown_usage', 0) for g in G.values()))} 次（含噪声/校准）。逐组细项与截断次数在 metrics.json。")
add('总分为每题三判逐维中位数之和，再对题取均值；五维列进一步对本组题取中位数，NA 每维算 1。观察字符与 token 包含失败重跑消耗；墙钟为批次并发实际时间；共享网关和机器负载随时间变化，墙钟只记账、不归因到文档。未判完成项不能视为有效 NA。')
add()
add('25 步 C/W 只有固定 5 题，S/C0 为完整 10 题，所以上表跨组均值的题目构成不同；配对差只取共同题。')
add()
add('| 上限 | C−S (n/均差) | C0−S (n/均差) | C−C0 (n/均差) | C0−W (n/均差) |')
add('|---|---|---|---|---|')
for st in [10, 25]:
    p = M.get('paired', {}).get(str(st), {})
    add('| ' + str(st) + ' | ' + ' | '.join((f"{p.get(k, {}).get('n', 0)} / {num(p.get(k, {}).get('mean'))}" for k in ['C-S', 'C0-S', 'C-C0', 'C0-W'])) + ' |')
add()
add('固定五题的 C−S 步数对照：' + '；'.join((f"{st}步 n={M.get('matched_five_pairs', {}).get(str(st), {}).get('C-S', {}).get('n', 0)}，均差={num(M.get('matched_five_pairs', {}).get(str(st), {}).get('C-S', {}).get('mean'))}" for st in [10, 25])) + '。各配对细项见 metrics.json/matched_five_pairs。')
add()
length_adjustment = read(E / 'answer-length-covariate.json', {})
add('答案长度补充：对每题 C−S 分差与 log((C词数+1)/(S词数+1)) 做配对线性回归；截距是等长时的描述性估计，主读数仍为未调整配对差。长度本身也可能随文档变化，原始数据、5000次按题bootstrap及奇异重采样数见 `E/answer-length-covariate.json`。')
for st, entry in length_adjustment.get('results', {}).items():
    fit = entry.get('length_covariate_fit') or {}
    ci = entry.get('adjusted_intercept_bootstrap95', [None, None])
    rawci = entry.get('unadjusted_bootstrap95', [None, None])
    add(f"{st}步 n={entry['n']}：未调整差 {num(entry.get('unadjusted_mean'))}，bootstrap95%区间 [{num(rawci[0])}, {num(rawci[1])}]；等长截距 {num(fit.get('intercept'))}，区间 [{num(ci[0])}, {num(ci[1])}]。")
add()
add('**噪声与难度。** S/10 的前五个试点题各额外跑两次，总共每题三份答案；三份分别接受三次判分，范围同时包含作答与判官的剩余噪声。')
add()
add('| qid | 三次作答的总分 | 极差 | 样本标准差 |')
add('|---:|---|---:|---:|')
for n in M.get('noise', []):
    add(f"| {n['qid']} | {n['totals']} | {num(n['range'])} | {num(n['sd'])} |")
direct = G.get('direct', {})
directjs = [read(p) for p in (E / 'judge/direct').glob('q*.json')]
add()
add(f"无工具校准复用上游 llm_direct 的原始“最简、不解释、不引用”提示：有效 {direct.get('valid_answers', 0)}/10，总分均值 {num(direct.get('mean_total_na5'))}，平均答案词数 {num(direct.get('answer_words_mean'))}。提前定的 E1 操作阈值 ≥80：{sum(((r.get('total') or 5) >= 80 for r in directjs))}/10 题，<80：{sum(((r.get('total') or 5) < 80 for r in directjs))}/10。该提示与判官对短答案扣分相互影响，连续分数/词数必须同看；80 阈值是本次补充口径。")
add()
add('以下直答档 n 指十题中该档大小，C/W25 只取其中的固定子样本，各组实际 n 另存 metrics.json；配对 n 单列。')
add()
add('| 上限/直答档 | n | S/C0/C/W 总分均值 NA=5 | C−S 配对 n/均差 |')
add('|---|---:|---|---|')
for d in M.get('difficulty_calibration', {}).get('strata', []):
    add(f"| {d['steps']}/{d['tier']} | {d['n']} | " + '/'.join((num(d['groups'][a]['mean_total_na5']) for a in ['S', 'C0', 'C', 'W'])) + f" | {d['paired_C_minus_S']['n']}/{num(d['paired_C_minus_S']['mean'])} |")
add()
add('**判官一致性、标记与命令。** 下表极差是同一答案三次原始总分之差；本次为与长作答并行收集回执，采用增量判分、再从未改写答案汇总标记，和 EVAL 第 4 节“判前统计”的顺序不同，此处记为流程偏离。CBE 匹配 INDEX.md、单元 id、cbe 命令或名称，W 匹配 CodeWiki 或发布页模块文件名/一级标题（连字符、下划线和 CamelCase 统一成词）。模块名匹配为启发式，普通名称可能在 S 答案中出现；缺完整 CodeWiki 词表时列 NA，仅名称 CodeWiki 的计数另存 JSON；另记答案中含组名的绝对路径率 arm_path_marker_rate。')
add()
add('| 组/上限 | 判官极差 中位/最大 | CBE 标记率 | W 标记率 | CBE find/query 次数 | 成功率 | 判官失败/待判 |')
add('|---|---|---:|---:|---|---:|---|')
for arm in ['S', 'C0', 'C', 'W']:
    for st in [10, 25]:
        g = G.get(f'{arm}-{st}-r0')
        if not g:
            continue
        cc = collections.Counter((c['kind'] for c in g['cbe_calls']))
        add(f"| {arm}/{st} | {num(g['judge_range_median'])}/{num(g['judge_range_max'])} | {pct(g['cbe_marker_rate'])} | {pct(g['codewiki_marker_rate'])} | {cc['find']}/{cc['query']} | {pct(g['cbe_success_rate'])} | {g['judge_failures']}/{g['missing_judge']} |")
add()
add('CBE 调用排除 --help，按子进程返回码与错误文本判成功；具体命令、返回码见 metrics.json 的 cbe_calls 与原始 traces。管道可能掩盖前段退出码，是这项辅助指标的限制。源码引用辅助核验检查 .py 路径及唯一后缀、可解析行号范围；歧义和不存在的路径单列，原始提及在 metrics.json/citations，不检验事实支撑。')
zero_cli = [str(st) for st in [10, 25] if G.get(f'C-{st}-r0') and (not G[f'C-{st}-r0']['cbe_calls'])]
if zero_cli:
    add('C 的 ' + '、'.join(zero_cli) + ' 步档没有实际执行 find/query，成功率为 NA；author 冒烟的两条命令成功不计为模型调用。对应 C−C0 只能描述可用性条件差，不能归因为已使用命令的收益。')
add(f"只看 20 条匿名答案猜组别：模型 `{B.get('model')}`，猜对 {B.get('correct')}/{B.get('n')}（{pct(B.get('accuracy'))}），多数类基准 {pct(B.get('majority_baseline'))}；匿名输入、真值与原始输出见 `E/blind-arm-guess/`。匿名化移除外部组别标签，保留答案原文内的标记与路径；这只测答案能否暴露组别，不证明判官已无偏差。")
add()
add('**E2 量级推算（48 题×4组=192 次作答；576 次正常判分）。** 以下先算各组实测每题消耗，再对组等权合成（避免 25 步的 10/10/5/5 样本数造成不等权）；假设 E2 题的分布相同；四并发墙钟仅理想下界，不含排队、生成和额外校准。')
add()
add('| 上限 | 观测题数/组数 | 输入/输出 token 每题 | 作答秒/题 | E2 输入/输出 token | 作答串行小时/理想四并发小时 | 判官输入/输出 token |')
add('|---|---|---|---:|---|---|---|')
for st, p in M.get('projection', {}).items():
    add(f"| {st} | {p['observed_answers']}/{p['observed_arms']} | {num(p['input_tokens_per_question'], 0)}/{num(p['output_tokens_per_question'], 0)} | {num(p['answer_seconds_per_question'])} | {num(p['E2_input_tokens'], 0)}/{num(p['E2_output_tokens'], 0)} | {num(p['E2_answer_serial_hours'], 2)}/{num(p['E2_answer_four_workers_hours_ideal'], 2)} | {num(p['E2_judge_input_tokens'], 0)}/{num(p['E2_judge_output_tokens'], 0)} |")
add()
add('步数档位与 E2 预算闸交主会话结合上述读数决定；表中 192 次作答/576 次判分未含额外 48 题无工具校准及其 144 次正常判分。若 W 未完成，四组推算中的 W 是按已观测组均值代入，缺少 W 实测。API 超时等失败没有返回 usage 的请求，其 token 未估填：上表 token 是已观测下界，未知用量的失败尝试数见 metrics.json/projection；墙钟仍包含失败。作答/判官 prompt_tokens 含缓存，CBE 记账另列未缓存输入与缓存。E2 不应把这 10 题试点直接当独立的新样本。')
add()
add('**未成项、问题与核验边界。** ' + ('W 两种步数均已跑。' if 'W' in complete else '其余工作完成时 CodeWiki 尚未交完整产物，按任务约定未跑 W；没有用半成品充当 W。') + (' E1a 原因：' + str(w_ready.get('reason')) if w_ready.get('complete') is False else ''))
add('环境问题：独立 worktree 默认找不到已有 Joern，显式 --joern-home 后建图成功；预检日志留存。初始导入生成的 16 个 .pyc 已按时间戳清除恢复只读工作树，后续禁止字节码写入。最初沙箱拒绝 dyld 读根目录导致 abort，增加仅根目录本身的读权限后烟测通过。')
progress = (E / 'cbe-flask/run/progress.log').read_text() if (E / 'cbe-flask/run/progress.log').exists() else ''
import re
rejects = collections.Counter(re.findall('\\breject\\s+(\\w+)', progress))
add(f'生成结构返工按模块计数 `{json.dumps(dict(rejects))}`；原始 schema 错误与每次重新询问都在 progress.log、host/events.jsonl 和 raw/。已观察的错误包括 disposition 目标不对应当前单元、遗漏 inventory 条目、产生 inventory 以外的 unit id。它们是本轮模型输出/协议失败，不据此单独断定 CBE 代码缺陷。')
add('本轮还有两处目录树规范化：分别把 2 个、1 个未归属单元放到区域根节点；因此 id_corrected=0 不代表没有结构修补。定位为 progress.log 的 05:04:52Z、05:05:00Z；这里只核结构可遍历，未人工确认这三个单元的分组语义。')
add(f"CBE 本轮可见的修复/回退标记为 answer_fallback={S.get('answer_fallback_count', 0)}、id_corrected={S.get('id_corrected_count', 0)}；细项只在 summary 原件报告，未改冻结代码。驱动最初误写 `cbe verify`，因此 phases 保留该命令的非零返回码 2；之后用真实入口 `cbe host verify` 复核，结果在 verify-final.log，这项是实验脚本错误。上游文本工具协议在试答中有无法解析的回复而继续耗步，保留原行为并记录日志。")
add('大型图与 Joern JSON 的 gzip 归档及 SHA-256 见 `E/artifact-compression.json`；复用图时先 gzip -dk 解压。两份活动 context.json 保留明文，以便原 run 与 C 组直接执行 query/verify；未改源码或剪枝输入。')
add('核验脚本曾把静态配置选择器误判为凭据，已用 AST 限定豁免该读取节点，并以仅内存的正反例核实真实字面凭据仍可检出。共享冻结目录还出现未归属的 Python 字节码缓存，记录于核验原件；最终 src/ 与 9c6499e git archive 逐字节相同，未删除未归属缓存。')
add('自验已核：原题逐字匹配、四份源码 SHA 一致、无 .git、隔离正反例、答案失败识别、三判记录与中位数、完整分母；逐条核验账在 `E/final-verification.json`。按任务要求读过 verification skill；独立验收与参考答案抽核由主会话承担，本 worker 未派其他 agent。')
DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text('\n'.join(lines) + '\n')
print(str(DEST))
print('lines', len(lines))
