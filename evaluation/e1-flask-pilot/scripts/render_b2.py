"""Short E1b2 report, kept separate from the original blocked-C experiment."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json
from pathlib import Path
E = Path(__file__).resolve().parent
B = E / 'b2'
m = json.loads((E / 'metrics.json').read_text())
out = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e1/e1b2_result.md'))
rows = []

def add(s=''):
    rows.append(s)

def num(x):
    return 'NA' if x is None else f'{x:.2f}'

def pct(x):
    return 'NA' if x is None else f'{100 * x:.1f}%'

def pair(steps, name):
    p = m['paired'][str(steps)][name]
    ci = p.get('bootstrap95')
    return f"{num(p['mean'])} [{num(ci[0])}, {num(ci[1])}], n={p['n']}" if ci else f"NA, n={p['n']}"
decision = m['b2']['W_decision']
done = m['b2']['status'] == 'complete'
add('# E1b2：C 工具层修复与重跑' + ('' if done else '（运行中，非交回终稿）'))
add()
add('接续 [E1b](e1b_result.md)。E1b 的 C 组把工具层阻断误读为 agent 未使用；作者预检绕过 ToolHandler，没发现这一点。生成 CBE、S/C0、噪声与直接答题数据继续沿用，旧 C 只作故障历史。')
add('E=$WORK/runs/e1；旧 C 答案/判分同名归档在 answers、judge 下的 `C-{10,25}-r0__bash-blocked`，旧 metrics 在 `E/b2/old-metrics.json`。')
add()
add('**修复与实测边界**')
add()
add('第5处 harness 修改：仅 C 的 bash 工具允许命令以 C/bin/cbe 绝对路径加边界开头，且全串无分号、&、竖线、反引号、美元符、重定向符或换行；其余按默认拦截。由 run_pilot.py 仅在 arm=C 时设置 filter.cbe_executable。命令仍经 sandbox-exec，四组提示 SHA 未改，S/C0/W 的默认 blocklist、工具集不变。')
add('`E/b2/tool-layer-smoke.json`：经 ToolHandler.execute_action 的 find/query/--help 各一次成功，ls、复合 find、bash -c 各一次被拦；加禁止字符与非 C 对照共21/21通过。这3个预检执行未计入下面的作答调用。')
add('作答仍为 zai/glm-5.3-flash、判官 codex/gpt-6.1-sol，每答案三次独立判分取各维中位数，超时/重试/观测上限同 E1b，作答并发≤4。C/10全10题，C/25同固定5题[4,6,14,32,41]。')
if decision is None:
    add('W：等待 E1a 独占写入的 W-READY.json，每5分钟检查一次，截止2026-10-17 13:30CEST（11:30UTC）；尚未作出运行/跳过决定。')
elif decision['run']:
    stats = '; '.join((f"W/{s}={m['groups'].get(f'W-{s}-r0', {}).get('n', 0)}/{m['groups'].get(f'W-{s}-r0', {}).get('valid_answers', 0)}/{m['groups'].get(f'W-{s}-r0', {}).get('judged', 0)}(题/有效/已判)" for s in [10, 25]))
    add('W：E1a attested complete=true 后复制 docs_path 的40份Markdown；' + ('已完成' if done else '执行中') + ' W/10十题、W/25同五题，默认工具拦截保留；' + stats + '。回执见 `E/b2/W-decision.json`。')
else:
    add('W：未跑；原因：' + decision['reason'].replace('\n', ' ')[:450] + '。握手/有界等待原件见 `E/b2/W-decision.json`、`W-observations.jsonl`。')
add()
add('**新旧 C 分开读**')
add()
add('| 条件 | 题数/有效/已判 | 均分（NA=5） | find/query请求/执行/成功/拦截 | 请求成功率/执行成功率 | help执行 |')
add('|---|---:|---:|---:|---:|---:|')
for steps in [10, 25]:
    for suffix, label in [('__bash-blocked', '旧：bash被拦'), ('', '新：限定放行')]:
        g = m['groups'].get(f'C-{steps}-r0' + suffix)
        if not g:
            continue
        a = g['cbe_agent_layer']
        add(f"| C/{steps} {label} | {g['n']}/{g['valid_answers']}/{g['judged']} | {num(g['mean_total_na5'])} | {a['tool_attempts']}/{a['executed_count']}/{a['successful_count']}/{a['blocked_attempts']} | {pct(a['success_rate_attempted'])}/{pct(a['success_rate_executed'])} | {a['help_executed']} |")
add('find/query排除--help；请求含工具层被拦事件，执行须有匹配的 LocalEnv 命令记录，成功须返回码0且无错误前缀；空命中另记。完整逐次返回码与输出见 `E/b2/agent-layer-audit.json`。')
for steps in [10, 25]:
    g = m['groups'].get(f'C-{steps}-r0')
    if not g:
        continue
    a = g['cbe_agent_layer']
    add(f'C/{steps}每题分布 `qid:find/query/成功/拦截`：' + ', '.join((f"{p['qid']}:{p['find_executed']}/{p['query_executed']}/{p['successes']}/{p['blocked_attempts']}" for p in a['per_question'])) + '。')
add('C失败原件：10步q32的 query 带重定向和竖线，被工具层拦；25步q4、q14各一次 query 的 id 无效，CBE返回2，输出unknown unit, symbol or file。')
add()
add('**配对读数与步数**')
add()
add('| 步数 | C−S：均差[95%区间],n | C−C0：均差[95%区间],n | C0−W：均差[95%区间],n |')
add('|---|---|---|---|')
for s in [10, 25]:
    add(f"| {s} | {pair(s, 'C-S')} | {pair(s, 'C-C0')} | {pair(s, 'C0-W')} |")
add('区间为按题配对 bootstrap 10000次、固定种子20261017派生；W缺席记NA，绝不按零分填。这里只是10/5题试点，未做48题主比较；区间含0按冻结口径记“没有测出差别”。')
matched = m['matched_five_pairs']
add('同五题的 C−S：10步 ' + num(matched['10']['C-S']['mean']) + '，25步 ' + num(matched['25']['C-S']['mean']) + '（各n=' + str(matched['25']['C-S']['n']) + '）；总量10题对5题的点估计不能直接作步数收益。')
add()
add('**文本工具协议稳定性**')
add()
add('前列为全部 agent 回复中 parse_action=None（含合法最终答案）；后列为触发重提示的未解析回复 /（工具观测回复+重提示回复），用来隔开合法结束与格式问题。含所有重试，原件为逐次 history。')
add()
add('| 条件 | 全部未解析/回复（比例） | 触发重提示/循环回复（比例） |')
add('|---|---:|---:|')
for a in ['S', 'C0', 'C', 'W']:
    for s in [10, 25]:
        g = m['groups'].get(f'{a}-{s}-r0')
        if not g:
            add(f'| {a}/{s} | 未跑 | 未跑 |')
            continue
        p = g['agent_protocol']
        add(f"| {a}/{s} | {p['unparsed_all_replies']}/{p['all_agent_replies']}（{pct(p['unparsed_all_ratio'])}） | {p['unparsed_loop_replies']}/{p['loop_replies_excluding_final_answers']}（{pct(p['unparsed_loop_ratio'])}） |")
add('最终仍输出工具JSON的无答案尝试：' + ', '.join((f"{a}/{s}={m['groups'][f'{a}-{s}-r0']['final_tool_json_failures']}" for a in ['S', 'C0', 'C', 'W'] for s in [10, 25] if f'{a}-{s}-r0' in m['groups'])) + '；按同一规则触发全程重跑，成本已累计。')
add()
add('**E2预算重算**')
add()
add('| 步数 | 实测组/题数 | 192答案输入/输出token | 答题串行h/理想4并发h | 576判分输入/输出token、串行h |')
add('|---|---|---:|---:|---:|')
for s in [10, 25]:
    p = m['projection'][str(s)]
    add(f"| {s} | {p['observed_answers_per_arm']} | {p['E2_input_tokens']:.0f}/{p['E2_output_tokens']:.0f} | {p['E2_answer_serial_hours']:.2f}/{p['E2_answer_four_workers_hours_ideal']:.2f} | {p['E2_judge_input_tokens']:.0f}/{p['E2_judge_output_tokens']:.0f}、{p['E2_judge_serial_hours']:.2f} |")
add('各实测组先按题均摊再等权；仅用新 C 与 W（若有），旧 C 不进入外推；无 W 时以已测组均值暂代 W。失败请求无usage使token为观测下界，重试耗时已纳入；理想并发时间不含排队与生成成本。')
add()
add('**交验与限制**')
add()
v = json.loads((B / 'verification.json').read_text()) if (B / 'verification.json').exists() else None
add(('作者程序核验全部通过；' if v and v['all_author_checks_pass'] else '作者最终核验尚未收口；') + '证据索引：`E/harness.patch`、`E/metrics.json`、`E/b2/verification.json`。检查源字节、四份源码、原rubric、题目/分母/中位数、默认动作回放、工具层与真实调用；待主会话非作者复核并决定 E2 步数与 C 做法。')
add('凭据扫描对两份JSON回执的公开CLI argv[0]做结构豁免；同一对象其他字段若写入凭据，内存阳性测试仍检出。')
add('范围：CBE本体未改；执行成功率只核命令运行，语义正确性仍按原SWE-QA判分。E1b 的20份盲猜含旧C，未把它当新C的盲性证据；本次未重跑盲猜或S/C0/噪声/直接答题。')
out.write_text('\n'.join(rows) + '\n')
print('Report lines', len(rows), str(out))
