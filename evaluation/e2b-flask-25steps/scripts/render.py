"""Render the requested approximately 100-line report from raw-derived metrics."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json
from pathlib import Path
E = Path(__file__).resolve().parent
m = json.loads((E / 'metrics.json').read_text())
R = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e2/e2b_result.md'))
A = ['S', 'C0', 'C', 'W']
P = ['C-S', 'C0-S', 'C-C0', 'C0-W', 'C-W']
f = lambda x: 'NA' if x is None else f'{x:.2f}'
pct = lambda x: 'NA' if x is None else f'{100 * x:.1f}%'

def contrast(x):
    ci = x['bootstrap95']
    return 'NA' if x['mean'] is None else f"{x['mean']:+.2f} [{ci[0]:+.2f}, {ci[1]:+.2f}], n={x['n']}；{x['interpretation']}"
lines = ['# E2b：Flask 25 步四组 × 24 题（预先声明的次要比较）', '', f"25 步 C−S：{contrast(m['all24']['C-S'])}。同 24 题 10 步 C−S：{contrast(m['ten_same24']['C-S'])}。两档点估计方向{('一致' if m['direction_consistency']['C-S'] else '不一致')}。", 'D-63 已规定 10 步全部 48 题是主比较；本报告只报次要比较和同题对照，不判断哪档步数正确。', '', '设置：冻结 CBE 9c6499e / SWE-QA c13deac；作答 zai/glm-5.3-flash，经 Magpie；判官 codex/gpt-6.1-sol，每题 3 次、逐维中位数求和。', '只改产物目录和步数上限 25；20,000 字符单观察、240 秒单请求、无答案完整重跑最多 2 次、判官失败重判最多 2 次均沿用 E1/E2a。', '四组目录、提示、sandbox、venv、harness 均复用 E1；按题轮转，作答并发≤4，增量判官并发≤4。', '开跑磁盘剩余 11 GiB；预算闸当时用 E2a 已完成 147 次新作答：39,811.9 输入 token/答案，按 D-63 放缩约 1,139 万 <2,000 万，保留补抽 14 题。偏离：未等最后5份落盘才开跑；其后152份齐时复核为41,263.5/答案、放缩约1,180万，仍低于闸，见 `budget-gate-final-e2a.json`。', 'SHA：68 个 harness 文件核过；5 个修改文件从原上游和冻结 patch 重建后逐字节/SHA-256 相同；ToolHandler 冒烟 21/21，C 放行与 S/C0/W 拦截均实测。', f'原件根目录 E=`{E}`；`harness-sha-check.json`、`tool-layer-smoke.json`、`reuse-manifest.json` 给完整 SHA 和回执。', '', '复用与新跑（题号从 0 起）：', '试点十题=' + str(m['reuse']['pilot10']) + '。', '补抽十四题=' + str(m['reuse']['extra14']) + '。', 'S、C0 复用 E1 各 10 题；C、W 各复用 [4,6,14,32,41] 五题，C 为放行后目录，未使用 __bash-blocked。', '新作答 S=14、C0=14、C=19、W=19，共 66；复用 30，共 96 份答案与判分。复用原件以 symlink 引用，SHA 存清单；E1/E2 只读。', '答案/尝试/逐步 history 在 `answers/<组>-25-r0/qNN.json`，三判和失败重判在对应 `judge/`，汇总 `metrics.json`。', '', '四组读数：NA 每题计 5、每维计 1；五维顺序为正确/完整/相关/清楚/推理。', '', '|组|有效作答|NA|总分均值|五维中位数|命中25步|观察累计字符|', '|---|---:|---:|---:|---|---:|---:|']
for a in A:
    g = m['groups'][a + '-25-r0']
    lines.append(f"|{a}|{g['valid_answers']}/24 ({pct(g['valid_answer_rate'])})|{g['NA']}|{f(g['mean_total_na5'])}|" + '/'.join((f(v) for v in g['dimensions_median'].values())) + f"|{pct(g['limit_hit_rate'])}|{g['observations_chars_total']:,}|")
lines += ['', '|组|全部未解析/回复（含合法最终答案）|重提示未解析/循环回复|', '|---|---:|---:|']
for a in A:
    p = m['groups'][a + '-25-r0']['agent_protocol']
    lines.append(f"|{a}|{p['unparsed_all_replies']}/{p['all_agent_replies']} ({pct(p['unparsed_all_ratio'])})|{p['unparsed_loop_replies']}/{p['loop_replies_excluding_final_answers']} ({pct(p['unparsed_loop_ratio'])})|")
lines += ['', '配对差：按题配对 bootstrap 10,000 次，种子 20261017，percentile 95% 区间；仅描述，不作多重比较结论。', '', '|对比|均差 [95% 区间] / n 与口径|', '|---|---|'] + [f"|{p}|{contrast(m['all24'][p])}|" for p in P]
lines += ['', '敏感性（同五个配对）：', '', '|范围|C−S|C0−S|C−C0|C0−W|C−W|', '|---|---|---|---|---|---|']
for k, title in [('exclude_pilot', '去试点10题'), ('exclude_q32', '去题32'), ('exclude_q4_11_47', '去题4/11/47'), ('valid_only', '只算各配对两边有效判分题')]:
    lines.append('|' + title + '|' + '|'.join((contrast(m['sensitivity'][k][p]) for p in P)) + '|')
lines += ['', '同 24 题，25 步减 10 步（非独立重抽，试点复用原分数）：', '', '|组|总分配对变化 [95% 区间]|命中率10→25|变化百分点|', '|---|---|---|---:|']
for a in A:
    x = m['step_comparison'][a]
    lines.append(f"|{a}|{contrast(x)}|{pct(x['limit_hit_rate_10'])} → {pct(x['limit_hit_rate_25'])}|{x['hit_change_percentage_points']:+.1f}|")
lines += ['', '|配对|10 步（同24题）|25 步|点估计方向一致|', '|---|---|---|---|']
for p in ['C-S', 'C0-W']:
    lines.append(f"|{p}|{contrast(m['ten_same24'][p])}|{contrast(m['all24'][p])}|{('是' if m['direction_consistency'][p] else '否')}|")
lines += ['', '难度校准：沿用 E2a 原始 llm_direct；阈值按全部 48 题直答总分中位数，high≥阈值，另报 80；下面只取本次 24 题。']
d = m['difficulty_calibration']
if d['status'] == 'complete':
    lines += ['', '|切档|阈值|档|25步 C−S [95% 区间]|', '|---|---:|---|---|']
    for k, x in d['strata'].items():
        for tier in ['high', 'low']:
            lines.append(f"|{k}|{x['threshold']}|{tier}|{contrast(x[tier])}|")
else:
    lines += ['待补：E2a 48 题直答判分尚未完成；不以残缺分数定中位数。']
if d['status'] == 'complete':
    lines.append('阈值80的高档仅1题，bootstrap区间退化为一点，不能表达总体不确定性；25步仍有75.0%—83.3%的答案命中上限。')
c = m['groups']['C-25-r0']['cbe_agent_layer']
lines += ['', f"C 组 find/query（不含 help）：请求 {c['tool_attempts']}，执行 {c['executed_count']}（find {c['find_executed']}/query {c['query_executed']}），成功 {c['successful_count']}，拦截 {c['blocked_attempts']}；请求成功率 {pct(c['success_rate_attempted'])}，执行成功率 {pct(c['success_rate_executed'])}。", '每题 `qid:请求/执行/成功(find执行/query执行)`：' + ', '.join((f"{x['qid']}:{x['tool_attempts']}/{x['find_executed'] + x['query_executed']}/{x['successes']}({x['find_executed']}/{x['query_executed']})" for x in c['per_question'])) + '。', '完整命令、返回码、输出和 help 分开记录于 `agent-layer-audit.json`；作者冒烟不计入。', '']
for kind in ['find', 'query']:
    events = [e for e in c['events'] if e['kind'] == kind and (not e['help'])]
    lines.append(f"C 组 {kind}：请求 {sum((e['through_tool_handler'] for e in events))}，执行 {sum((e['executed'] for e in events))}，成功 {sum((e['success'] for e in events))}。")
ac = m['accounting_new_only']
lines += [f"66 次新作答墙钟：{ac['started_utc']} 至 {ac['last_judge_utc']}，{ac['wall_seconds']:.1f} 秒（{ac['wall_seconds'] / 3600:.3f} 小时）；止点为最后新判分落盘。", f"新作答输入/输出 token={ac['answer_tokens']['input']:,}/{ac['answer_tokens']['output']:,}；新判官={ac['judge_tokens']['input']:,}/{ac['judge_tokens']['output']:,}；完整作答尝试 {ac['answer_attempts']} 次，判官抽样 {ac['judge_draws']} 次/请求 {ac['judge_calls']} 次。", f"无 usage 的失败：作答 {ac['answer_unknown_usage_attempts']} 次，判官 {ac['judge_unknown_usage_calls']} 次；token 是客户端观测下界，输入含缓存，重跑成本已含。", '约每20次作答的累计墙钟/分开token见 `checkpoints.jsonl`，运行活性见 `STATUS.json`；检查点只计已落盘任务，进行中请求完成后入账。', '', '|组|新答案数|新作答输入/输出 token|每新答案输入/输出|E1同组25步每答案输入/输出|', '|---|---:|---|---|---|']
for a in A:
    x = ac['by_arm'][a]
    lines.append(f"|{a}|{x['new_answers']}|{x['tokens']['input']:,}/{x['tokens']['output']:,}|{f(x['per_new_answer']['input'])}/{f(x['per_new_answer']['output'])}|{f(x['E1_per_answer']['input'])}/{f(x['E1_per_answer']['output'])}|")
lines += ['', '新题与 E1 试点的题目构成不同；每答案 token 比较只作描述。', '局限：上游 ls、grep、find 参数未转义，各组都能经参数启动第二条命令；E2a 的 `runs/e2/limitations-tool-smoke.json` 24/24 证据沿用，沙箱仍挡住越界读写，本次未改 harness。命令执行成功不等于语义正确。', 'grep 是基本正则：把 `a|b` 当交替会返回空。下表比例为含未转义 | 的实际 grep / 全部实际 grep（含失败尝试与复用）；W/q12 一次 arguments 字符串导致工具报错，未执行 grep，故不进执行分母。', '', '|组|含竖线grep/全部grep|比例|其中空输出|占全部工具比例|', '|---|---:|---:|---:|---:|']
for a in A:
    x = m['grep_literal_pipe'][a]
    lines.append(f"|{a}|{x['literal_pipe_calls']}/{x['grep_calls']}|{pct(x['pipe_fraction_of_grep'])}|{x['pipe_empty_output_calls']}|{pct(x['pipe_fraction_of_all_tools'])}|")
lines += ['', '其余边界：分层固定24题不是48题全量；复用试点不提供新的独立样本；参考答案问题按冻结敏感性处理。', '单一作答/判官模型、共享网关负载和上游文本工具协议限制外推；直答提示要求短答且 rubric 对短答扣分，难度只按该操作定义。', '作者按 verification skill 核题号、分母、SHA、原题、三判中位数与NA；`verification.json` 是作者自验，非作者验收由协调者承担。', f"未做成项：{('无运行缺项；独立验收待协调者。' if d['status'] == 'complete' else '难度两档待 E2a 直答完成后补；独立验收待协调者。')}"]
audit_path = E / 'gateway-model-audit.json'
if audit_path.exists():
    ga = json.loads(audit_path.read_text())
    lines.insert(-1, f"共享网关窗口的补充模型身份核查：候选请求 {ga['candidate_rows']} 条，服务模型未知 {ga['unknown_served']} 条，不符 {len(ga['served_mismatches'])} 条；含并行任务，仅核身份，不用于本任务 token 归属。原件 `gateway-model-audit.json`。")
R.parent.mkdir(parents=True, exist_ok=True)
R.write_text('\n'.join(lines) + '\n')
print(R, len(lines), 'lines')
