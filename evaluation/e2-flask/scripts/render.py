"""Render coordinator-facing E2a result from raw reductions."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json
from pathlib import Path
E = Path(__file__).resolve().parent
OUT = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e2/e2a_result.md'))

def main():
    m = json.loads((E / 'metrics.json').read_text())
    a = m['accounting_new_only']
    v = json.loads((E / 'verification.json').read_text())
    cs = m['all48']['pairs']['C-S']
    audit = m['groups']['C-10-r0']['cbe_agent_layer']

    def ci(x, point=True):
        if not x or x.get('bootstrap95') is None:
            return 'NA'
        lo, hi = x['bootstrap95']
        return (f"{x['mean']:+.2f} " if point else '') + f'[{lo:+.2f}, {hi:+.2f}]'

    def pct(x):
        return f'{x * 100:.1f}%' if x is not None else 'NA'
    lines = ['# E2a：Flask 48 题、10 步四组比较', '', f"152/152 次新作答及其判分已齐；另复用 E1 的 40 次作答与 120 次判分。主指标 C−S 为 **{ci(cs)}**（按题 bootstrap 95% 区间，n=48）；{cs['interpretation']}。新跑从首次作答启动到最后一次判分结束共 {a['wall_hours']:.3f} 小时，是 E1b2 全 192 次理想四并发时间 3.40 小时的 {a['ratio_to_full192']:.3f} 倍；按 152 次缩放后为 {a['ratio_to_new152']:.3f} 倍。25 步部分由主会话按 D-60 决定。", '', f'产物根 E=`{E}`。本次是作者实测与程序自验；非作者验收由主会话承担。', '', '## 设置与复用', '', '- 冻结 CBE `9c6499eb710f51aba58cbece354f4d82cee2fcce`；SWE-QA 上游 `c13deac7a0d99b0ca2e593e004c4739475785b08`。直接加载只读 E1 harness、venv、arms、提示句和 sandbox；C 使用 E1b2 限定放行后的版本。', '- 作答仅 Magpie `zai/glm-5.3-flash`；判官仅 `codex/gpt-6.1-sol`，每题三次、逐维中位数后求和；无备用模型。10 步（达到上限后保留上游额外收尾模型调用）、观察上限 20,000 字符、单请求 240 秒、无答案完整重跑最多两次、单判失败最多重判两次，均沿用 E1。', '- 启动前磁盘 16 GiB 可用。`harness-sha-check.json` 保存 68 文件 SHA-256：5 个修改文件的 Git blob SHA 与 E1 `harness.patch` 一致，另从固定上游加该 patch 在内存重建，逐字节及完整 SHA-256 复核通过；其余文件与固定上游逐字节一致；结束前再核 SHA。', '- `tool-layer-smoke.json`：21/21 通过，入口为 ToolHandler.execute_action；C find/query/help 实际执行成功，普通 bash、复合命令、禁止字符与 S/C0/W 对照均被拦。冒烟不计作答工具调用。', '- 复用 E1：q=[4,6,11,12,14,20,32,41,46,47]，S/C0/C/W 的 `answers/<arm>-10-r0/qNN.json` 与 `judge/` 同路径结构链接入 E；C 未链接 `__bash-blocked`。80 份链接及来源 SHA 见 `reuse-manifest.json`。', '- 新跑：其余 38 题×四组，题号与清单见 `metrics.json/reuse`；原件在 `answers/`、三判与重试在 `judge/`。每题四组齐后才进下一题，作答并发≤4，判官增量并发≤4；`run.log` 留轮转记录，`checkpoints.jsonl` 留 40/80/120/152 次累计墙钟与分项 token（检查点只计已落盘任务，进行中请求在完成后入账）。', '', '## 四组读数（全部 48 题）', '', '| 组 | 有效作答/48 | NA | 总分均值 NA=5 | 五维中位数 正/全/关/清/推 | 命中上限 | 工具观察累计字符 | 未解析/全部回复 | 重提示/循环回复 |', '|---|---:|---:|---:|---|---:|---:|---:|---:|']
    for arm in ['S', 'C0', 'C', 'W']:
        g = m['groups'][f'{arm}-10-r0']
        p = g['agent_protocol']
        dims = '/'.join((f"{g['dimensions_median'][d]:g}" for d in ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning']))
        lines.append(f"| {arm} | {g['valid_answers']}/48 ({pct(g['valid_answer_rate'])}) | {g['NA']} | {g['mean_total_na5']:.2f} | {dims} | {pct(g['limit_hit_rate'])} | {g['observations_chars_total']:,} | {p['unparsed_all_replies']}/{p['all_agent_replies']} ({pct(p['unparsed_all_ratio'])}) | {p['unparsed_loop_replies']}/{p['loop_replies_excluding_final_answers']} ({pct(p['unparsed_loop_ratio'])}) |")
    lines += ['', 'NA 含作答失败或三判最终不齐，按每维 1、总分 5。有效作答率只看是否产生有效答案；“只算有效题”要求答案有效且三判齐。观察字符及协议比例含失败重跑；命中上限率按每题最终尝试。全部未解析包括合法最终答案，循环未解析只计触发重提示的协议失败。', '', '## 配对差与敏感性', '', '| 范围 | n（C−S） | C−S | C0−S | C−C0 | C0−W | C−W |', '|---|---:|---|---|---|---|---|']
    for name, r in [('全部48题', m['all48'])] + list(m['sensitivity'].items()):
        pairs = r['pairs']
        lines.append('| ' + name + f" | {pairs['C-S']['n']} | " + ' | '.join((ci(pairs[k]) + (f" n={pairs[k]['n']}" if name == 'valid_only' else '') for k in ['C-S', 'C0-S', 'C-C0', 'C0-W', 'C-W'])) + ' |')
    lines += ['', '区间含 0 的比较均记“没有测出差别”。按题配对 bootstrap 10,000 次、百分位区间；主配对种子 20262017 加配对序号，敏感性与分层用事先写入脚本的固定偏移，完整种子公式见 `metrics.json/bootstrap`。不删参考答案有问题的题；敏感性分别去掉试点、q32、q4/11/47，及只算每对两组均有效的题。', '', '## 分类分报（仅报区间，不作优劣结论）', '', '| 分类 | n | S均值区间 | C0均值区间 | C均值区间 | W均值区间 | C−S区间 | C0−S区间 | C−C0区间 | C0−W区间 | C−W区间 |', '|---|---:|---|---|---|---|---|---|---|---|---|']
    for name, r in m['categories'].items():
        lines.append('| ' + name + f" | {r['n']} | " + ' | '.join((ci(r['groups'][k], False) for k in ['S', 'C0', 'C', 'W'])) + ' | ' + ' | '.join((ci(r['pairs'][k], False) for k in ['C-S', 'C0-S', 'C-C0', 'C0-W', 'C-W'])) + ' |')
    lines += ['', '题型与四层沿用 E1 全 48 题仅按题面标注，含逐题理由的 `questions/labels.json`。定位层只有 1 题，其 bootstrap 区间退化为同一点，不能表达总体不确定性。', '', '## C 组命令与引用辅助核查', '', f"C 组 find/query 请求 {audit['tool_attempts']}，执行 {audit['executed_count']}，成功 {audit['successful_count']}，拦截 {audit['blocked_attempts']}；请求成功率 {pct(audit['success_rate_attempted'])}、执行成功率 {pct(audit['success_rate_executed'])}。另有 help 执行 {audit['help_executed']} 次，已排除；到达上限后未执行的工具 JSON 单列于审计原件。成功只指返回码 0 且无错误前缀。", '', '每题分布 `qid:请求/执行/成功/拦截(find执行/query执行)`（包含复用 E1）：', '']
    position = next((i for i, line in enumerate(lines) if line.startswith('每题分布 `qid:')))
    kind_lines = ['| 命令 | 请求 | 执行 | 成功 |', '|---|---:|---:|---:|']
    for kind in ['find', 'query']:
        events = [event for event in audit['events'] if event['kind'] == kind and (not event['help'])]
        kind_lines.append(f"| {kind} | {sum((event['through_tool_handler'] for event in events))} | {sum((event['executed'] for event in events))} | {sum((event['success'] for event in events))} |")
    kind_lines += ['', '两次执行失败分别为 q22 query 缺 `--id`、q40 find 缺 `--term`；q32 的一次 query 因包含管道/重定向被拦（复用 E1）。', '']
    lines[position:position] = kind_lines
    entries = [f"{r['qid']}:{r['tool_attempts']}/{r['find_executed'] + r['query_executed']}/{r['successes']}/{r['blocked_attempts']}({r['find_executed']}/{r['query_executed']})" for r in audit['per_question']]
    for offset in range(0, len(entries), 12):
        lines.append('`' + ', '.join(entries[offset:offset + 12]) + '`')
    lines += ['', '`agent-layer-audit.json` 保留逐次请求、实际执行匹配、返回码与输出；完整输出见答案历史。命令可用的条件差不等于模型实际用过命令的因果收益。', '', '| 组 | .py路径提及 | 存在 | 不存在 | 歧义 | 显式行号/可核/存在 |', '|---|---:|---:|---:|---:|---|']
    for arm in ['S', 'C0', 'C', 'W']:
        c = m['groups'][f'{arm}-10-r0']['citations']
        lines.append(f"| {arm} | {c['n']} | {c['valid_paths']} | {c['missing_paths']} | {c['ambiguous_paths']} | {c['line_references']}/{c['checked_line_references']}/{c['valid_lines']} |")
    lines += ['', '沿用 E1：检查 .py 路径、唯一后缀与显式 `:行号`/`#L行号` 范围。其他文件类型或散文式行号不计；本批未检出该语法的显式行号，行号存在性无可核样本；路径存在不代表支持答案事实。逐次记录见 `metrics.json/groups/*/citations`。', '', '## 新跑墙钟与 token（不含复用 E1）', '', f"- 起点 {a['started_utc']}，终点 {a['last_judge_utc']}；墙钟 {a['wall_seconds']:,.1f} 秒 = {a['wall_hours']:.3f} 小时。起点是首次提交四组作答前，终点取最后新判分产物落盘时间；后台监控轮询尾差不计。", f"- 作答 input/output token：{a['answer_tokens']['input']:,} / {a['answer_tokens']['output']:,}；判官：{a['judge_tokens']['input']:,} / {a['judge_tokens']['output']:,}，完整作答尝试 {a['answer_attempts']} 次（含 {a['answer_attempts'] - 152} 次重跑），判官抽样 {a['judge_draws']} 次、请求 {a['judge_calls']} 次。", f"- 无 usage 的失败：作答尝试 {a['answer_unknown_usage_attempts']}，判官请求 {a['judge_unknown_usage_calls']}；token 为客户端可观测下界，prompt 含缓存，沿 E1 口径；未将共用网关上 svelte 的调用归进来。", f"- E1b2 理想时间 3.40 小时对应 192 次作答；原分母比值 {a['ratio_to_full192']:.3f}。新跑 152 次的同量缩放基准为 {a['ideal_new152_hours']:.4f} 小时，比值 {a['ratio_to_new152']:.3f}。实际分子含判分尾部与按题轮转等待，理想基准只算作答；两者定义均保留，不替主会话解释 D-60 或决定 25 步。", '', '## 核验与边界', '', f"程序自验 {sum(v['checks'].values())}/{len(v['checks'])} 项通过，见 `verification.json`：完整分母、原题一致、重试上界、三判中位数与 NA、模型请求、E1 复用 SHA、harness SHA、四份源码、提示句与凭据扫描。初版字节扫描把配置选择器与公开CLI名误报为凭据；已沿用E1的AST定域规则并通过六个内存正反例，初版与纠正见 `verification-initial.json`、`verification-recovery.json`。新JSON均未超过10 MB，无需gzip，检查记录见 `compression.json`；E1 原件与活动 C run 不改。", '主结果只覆盖 Flask 的这 48 题、一个作答模型及这份文档；试点复用不算独立重复。判官仍是单一模型族，未再做盲猜；参考答案缺陷用预定敏感性表达。未跑 25 步、未发布 GitHub，均不在本任务新跑范围。待主会话非作者验收后用于对外结果。']
    dc = m['difficulty_calibration']
    da = dc['new_only_accounting']
    extra = ['## D-63：无工具难度校准', '', f"主比较判分结束后补跑其余 38 题直答，复用 E1 10 题，合计有效 {dc['valid_answers']}/48，NA={dc['NA']}。每题一份作答（无答案沿 E1 规则重跑）、三次判分逐维中位数；原始提示函数逐字从上游提取，原件与 SHA 在 `direct/prompt-provenance.json`，答案、判分和复用清单均在 `direct/`。", f"全48题直答总分中位数={dc['median']:g}；高档定义为分数≥阈值、低档<阈值，按中位数切档时阈值上的并列数={dc['strata']['median']['ties_at_threshold']}。另保留阈值80，E1十题在该阈值下全属低档。", '', '| 切档/档位 | n | S均分/有效率/NA | C0均分/有效率/NA | C均分/有效率/NA | W均分/有效率/NA | C−S [95%区间] |', '|---|---:|---|---|---|---|---|']
    for split in ['median', 'threshold80']:
        for tier in ['high', 'low']:
            r = dc['strata'][split][tier]
            cells = []
            for arm in ['S', 'C0', 'C', 'W']:
                g = r['groups'][arm]
                cells.append(f"{g['mean_total_na5']:.2f}/{pct(g['valid_answer_rate'])}/{g['NA']}" if g['n'] else 'NA')
            extra.append(f"| {split}/{tier} | {r['n']} | " + ' | '.join(cells) + ' | ' + ci(r['C-S']) + ' |')
    extra += ['', f"校准新增墙钟 {da['wall_seconds'] / 3600:.3f} 小时；作答输入/输出 {da['answer_tokens']['input']:,}/{da['answer_tokens']['output']:,}，判官 {da['judge_tokens']['input']:,}/{da['judge_tokens']['output']:,} token；无usage失败 作答/判官={da['answer_unknown_usage_attempts']}/{da['judge_unknown_usage_calls']}。这部分不进入上文152次主比较耗时比。分档五维中位数、逐题分数及固定种子区间见 `direct/metrics.json`。", '原始 llm_direct 提示要求最简短、不解释、不引用，判官又对短答案扣分，因此这里的高低档只代表这份提示与判官下的操作性难度；中位数分档是 D-63 增补的描述性分析。', '', '上游 ls、grep、find 三个工具的参数未转义，各组都能经它们启动第二条命令，沙箱仍挡住越界读写（`limitations-tool-smoke.json`，24/24通过）；本次照实记录，未改 harness。grep 使用基本正则，模式写成 `a|b` 时 `|` 为字面字符，通常返回空；下表统计实际执行的 grep 中含未转义 `|` 的比例，含失败重跑与复用 E1。', '', '| 组 | 含未转义竖线/grep执行 | 比例 | 其中返回空 | 占全部观察到的工具调用 |', '|---|---:|---:|---:|---:|']
    for arm in ['S', 'C0', 'C', 'W']:
        g = m['grep_literal_pipe'][arm]
        extra.append(f"| {arm} | {g['literal_pipe_calls']}/{g['grep_calls']} | {pct(g['pipe_fraction_of_grep'])} | {g['pipe_empty_output_calls']} | {pct(g['pipe_fraction_of_all_tools'])} |")
    extra += ['', '逐次模式、返回码与空输出记录见 `grep-literal-pipe-audit.json`；这项只描述工具调用，不把返回空自动判为答题错误。', '']
    index = lines.index('## 核验与边界')
    lines[index:index] = extra
    gp = E / 'gateway-model-audit.json'
    if gp.exists():
        gateway = json.loads(gp.read_text())
        index = lines.index('## 核验与边界')
        lines[index:index] = [f"补充模型身份核查：共享网关窗口筛到 {gateway['candidate_rows']} 条目标模型候选请求，服务模型名未知 {gateway['unknown_served']} 条、与请求名不符 {len(gateway['served_mismatches'])} 条；范围与逐请求证据见 `gateway-model-audit.json`、`gateway-window-model-requests.csv`。这些候选请求含并行任务，未用于本次 token 归属；主账仍是可逐题对应的客户端 usage。", '']
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(lines) + '\n')
    print(OUT, 'lines', len(lines))
if __name__ == '__main__':
    main()
