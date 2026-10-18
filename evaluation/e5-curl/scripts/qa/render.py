"""Human report rendered only from independently recomputed metrics and gateway receipts."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, statistics, datetime
from pathlib import Path
E = Path(__file__).resolve().parent
R = E.parents[2]
read = lambda p: json.loads(p.read_text())
REPORT = Path(os.path.expandvars('$TASK_DIR/scratch/opt_e5/e5qa_result.md'))

def num(v):
    return 'NA' if v is None else f'{v:.2f}'

def pct(v):
    return 'NA' if v is None else f'{v * 100:.1f}%'

def ci(record, point=True):
    if not record or record['n'] == 0:
        return 'NA'
    low, high = record['ci95']
    return (f"{record['mean']:+.2f} " if point else '') + f'[{low:+.2f}, {high:+.2f}]'

def main():
    m = read(E / 'metrics.json')
    g = m['groups']
    gate = read(E / 'secondary-gate.json')
    bill = read(E / 'gateway-usage.json')
    lines = []
    u = read(E / 'STATUS.json')['usage']
    primary_tokens = u['answer_main']['input'] + u['answer_main']['output']
    primary_judge_tokens = sum((u[k]['input'] + u[k]['output'] for k in ['five_main', 'rubric_main']))

    def add(*xs):
        lines.extend(xs)
    primary = m['main']['rubric']['pairs']['C-S']
    five = m['main']['five']['pairs']['C-S']
    floor = m['floor_ceiling']
    floor_label = '未到顶亦未到底' if floor == 'neither' else floor
    five_conclusion = '没有测出差别' if five['ci95'][0] <= 0 <= five['ci95'][1] else '区间不含0（单次探索性读数）'
    conclusion = '这把尺子到顶' if floor == '到顶' else '这把尺子到底' if floor == '到底' else '没有测出差别' if primary['ci95'][0] <= 0 <= primary['ci95'][1] else '配对差区间不含 0（单次探索性读数）'
    add('# E5qa：curl 自出题三组问答测评', '', f'主比较 120/120 次作答与两种判分记录齐；rubric C−S **{ci(primary)}**，{conclusion}。五维 C−S **{ci(five)}**，{five_conclusion}。curl整体仍为EVAL次要指标，不作多重比较总体结论；结论仅覆盖 curl、一次 CBE 文档生成、一个作答模型、一个判官模型族与 10 步设置；判分抽查由主会话另派。', '', f'产物根 E=`{E}`。数值已用另一段程序核算194条评分记录：有三判原件的五维182条、rubric153条逐条复算；五维12条、rubric1条依NA规则核算。这是作者自验，未代替语义抽查。', '', '## 输入、隔离与冒烟', '')
    add('- 冻结 MANIFEST 8/8 相同；SHA 全文如下（相对 runs/e5q/freeze/，含裁定文件）。', '```text')
    for row in read(E / 'freeze-check.json'):
        add(row['sha256'] + '  ' + row['path'])
    add('```', '', f"- 按 cid 排序为 q00—q39，题面为 question + 空行 + `Build assumptions: ` + 原文；题文件 `questions/all.jsonl` SHA256={read(E / 'questions/manifest.json')['sha256']}。三组、直答、两判官使用同份完整题面；rubric 原脚本还保留单独 build_assumptions 字段。", '- 68 个 harness 文件与 E3 SHA 全同，未改 harness。S=源码，C0=源码+文档，C=源码+相同文档+cbe；目录 arms/{S,C0,C}；每组各506文件的独立只读curl副本；源码规模沿E5a为1,741,311 o200k_base token（CBE接收485文件），docs在repo外，C/run 只读消费 E5a 原件。', '- CBE 源为 eval-cbe2@a87674d；E5a complete、verify 通过（3863 单元、401 页），无 partial 敏感性排除。C/bin/cbe 通过 PYTHONPATH 导入冻结 src，私有 cbe-venv 使用 Homebrew Python 3.12.13；未改共用 venv。', '- 冻结提交没有锁文件，依赖按 pyproject 精确版本装、tiktoken 钉 0.14.0（主会话授权）；最初 uv sync --frozen 的失败原件在 venv-sync.log。pip freeze 全文：', '```text', *(E / 'pip-freeze.txt').read_text().splitlines(), '```', '', '- ToolHandler 冒烟 19/19：C find/query 放行，S/C0 拦截；三组 read_file 读冻结题均被 sandbox 拦截；query --help 与真实 find 各连跑 5 次成功，无 −6/dyld 崩溃。原件 tool-layer-smoke.json。', '- 作答与直答用 `zai/glm-5.3-flash`，两类判官用 `codex/gpt-6.1-sol`，均经 Magpie。rubric 每条三判取多数，正条按权重计分、每条负条扣1、按正条总权重归一到0—100且最低0；核心全满足率指每题所有核心正条均满足。五维每维1—20，三判取各维中位数再求和。', '- 初始磁盘13 GiB；按题轮转三组，作答并发上限4（开跑空闲比例见 main-start.json），请求240秒（rubric原脚本600秒）、观察20000字符、10步、无答案最多完整重跑2次。主比较每40答案的累计墙钟/token在 checkpoints.jsonl；解释器复核在 interpreter-checks.jsonl。', '', '## 主比较与配对差', '', '| 组 | 有效/40 | rubric NA | rubric均分 | 五维NA/均分 | 五维中位数 正/全/关/清/推 | 核心全满足 | 撞10步上限 |', '|---|---:|---:|---:|---:|---|---:|---:|')
    for arm in ['S', 'C0', 'C']:
        x = g[f'{arm}-10-r0']
        add(f"| {arm} | {x['valid']}/40 ({pct(x['valid'] / 40)}) | {x['rubric_NA']} | {num(x['rubric_mean'])} | {x['five_NA']}/{num(x['five_mean'])} | " + '/'.join((num(x['dimension_medians'][d]) for d in ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning'])) + f" | {pct(x['core_all_rate'])} | {pct(x['limit_hit_rate'])} |")
    add('', f"到顶/到底先判：S={g['S-10-r0']['rubric_mean']:.2f}、C={g['C-10-r0']['rubric_mean']:.2f}；判定={floor_label}。NA：rubric=0，五维每维1、合计5；不删题，主比较NA为C/A04，直答各题原因见review/direct/qNN/NA.json。", '', '| 评分/范围 | C−S | C0−S | C−C0 |', '|---|---|---|---|')
    for metric in ['rubric', 'five']:
        for title, section in [('全部40题', m['main']), ('仅有效题', m['valid_only'])]:
            add('| ' + metric + '/' + title + ' | ' + ' | '.join((ci(section[metric]['pairs'][pair]) + f" (n={section[metric]['pairs'][pair]['n']})" for pair in ['C-S', 'C0-S', 'C-C0'])) + ' |')
    add('', '按题配对 bootstrap 10000次、95%百分位区间，种子20261018（各表独立复用同种子）。主比较rubric C−C0和五维三项对照区间均含0，没有测出差别；两种分方向不同仍照报，不选择评分器。子组仅报区间，不作比较结论。', '', '## 冻结分报', '', '| 分组 | n | rubric C−S / C0−S / C−C0 | 五维 C−S / C0−S / C−C0 |', '|---|---:|---|---|')
    for label, section in m['categories'].items():
        add(f"| {label} | {section['rubric']['pairs']['C-S']['n']} | " + ' / '.join((ci(section['rubric']['pairs'][p], False) for p in ['C-S', 'C0-S', 'C-C0'])) + ' | ' + ' / '.join((ci(section['five']['pairs'][p], False) for p in ['C-S', 'C0-S', 'C-C0'])) + ' |')
    direct = g['direct']
    add('', f"直答40题（上游 llm_direct 原提示）有效{direct['valid']}/40、五维NA={direct['five_NA']}，五维均分{direct['five_mean']:.2f}；各维中位数=" + str(direct['dimension_medians']) + '。直答也受240秒请求时限约束，超时NA按协议记5，均值同时反映限时可用性，不能把NA都解释成知识错误。难度两档按冻结闭卷 rubric =0（28题）/>0（12题），不按直答中位数重切；完整档内三组均分/区间在 metrics.json/categories。', '', '## 过程与效率', '', '| 组 | 观察字符/截断(记录+补回) | 最终平均步数 | 平均答案词/字符 | 未解析/全部回复 | 多调用回复/比例 | 写出未执行调用 | bash被拦 | cbe崩溃 | grep含竖线/全部 |', '|---|---|---:|---|---|---|---:|---:|---:|---|')
    for arm in ['S', 'C0', 'C']:
        x = g[f'{arm}-10-r0']
        t = x['telemetry']
        add(f"| {arm} | {t.get('observation_chars', 0)}/{t.get('truncations', 0) + t.get('truncations_missing_field_recovered', 0)}({t.get('truncations', 0)}+{t.get('truncations_missing_field_recovered', 0)}) | {num(x['mean_final_steps'])} | {num(x['mean_answer_words'])}/{num(x['mean_answer_chars'])} | {t.get('unparsed_replies', 0)}/{t['all_replies']} | {t.get('multi_call_replies', 0)}/{pct(t['multi_call_ratio'])} | {t.get('written_not_executed', 0)} | {t.get('bash_blocked', 0)} | {t.get('cbe_crashes', 0)} | {t.get('grep_with_pipe', 0)}/{t.get('grep_executed', 0)} ({pct(t.get('grep_pipe_ratio'))}) |")
    add('按组答案字面标记（CBE/组路径/CodeWiki）：' + '；'.join((arm + '=' + str(g[f'{arm}-10-r0']['markers']['cbe']) + '/' + str(g[f'{arm}-10-r0']['markers']['arm_path']) + '/' + str(g[f'{arm}-10-r0']['markers']['codewiki_literal']) for arm in ['S', 'C0', 'C'])) + '；标记仅作风格计数。')
    if (E / 'secondary-answer-reconciliation.json').exists():
        add('次要 C/A08 第1次尝试发生 AttributeError：usage已保存，1条响应未进入history；2次Timeout才是请求usage未知。次要过程计数以已保存history为准；旧客户端error计数包含该本地异常，详 secondary-answer-reconciliation.json。')
    t = g['C-10-r0']['telemetry']
    add('', f"C find/query：写出{t.get('find_query_written', 0)}、经ToolHandler请求{t.get('find_query_requested', 0)}、实际执行{t.get('find_query_executed', 0)}、成功{t.get('find_query_success', 0)}、拦截{t.get('find_query_blocked', 0)}、写出未执行{t.get('find_query_written_not_executed', 0)}；help 执行{t.get('help_executed', 0)}。逐题、命令、返回码见 process-audit.json 的 C-10-r0 字段。这衡量命令可用时agent的实际选择，不能据此外推强制使用CLI的效果。", '“写出未执行”指未送入 ToolHandler（并列调用非第一个或步数上限后的工具JSON），与送入后被过滤拦截分开；多调用分母为全部助手回复。未解析比例含合法最终答案，循环重提示单列在 metrics.json。缺字段的截断次数由观察尾标恢复，主表同时给出总数与“已记录+补回”；E3原已记录字段仍单列在 metrics.json。', '', '## 次要比较、限制与抽查', '', f"预算闸输入（含缓存并补未知）={gate['gate_input_including_cache']:,.2f}，阈值12,000,000；次要计划20题（层1—4=1/4/9/6，种子20261019）×S/C×25步：" + ('已启动；实际完成部分见下表。' if gate['run'] else '未启动（超过阈值）。'))
    add('次要闸门补账口径与停止线在主比较进行中由主会话补充；补充时次要作答尚未开始。原包只按客户端账，此处按最新指令改为两账补后取大；题与评分规则未改。')
    add(f"客户端原始已知输入{gate['client_known_input_including_cache']:,}；未知{gate['client_unknown_requests']}次，按每请求均值{gate['mean_known_request_input']:,.2f}补{gate['client_imputed_input']:,.2f}，补后{gate['client_augmented_input']:,.2f}。")
    if gate['gateway_available']:
        add(f"网关原始输入（非缓存+缓存读）{gate['gateway_raw_input_including_cache']:,.0f}；无usage的499共{gate['gateway_unknown_499_requests']}次，补{gate['gateway_imputed_input']:,.2f}，补后{gate['gateway_augmented_input']:,.2f}。网关减客户端：原始差{gate['raw_gateway_minus_client']:+,.0f}，补后差{gate['augmented_gateway_minus_client']:+,.2f}；本次采用" + ('网关补后账。' if gate['gate_source'].startswith('gateway') else '客户端补后账。'))
    else:
        add('网关没有可用的作答session记录，按客户端已知回复的每请求均值补未知后判闸；详secondary-gate.json。')
    add('超时请求多发生在后几步的长上下文，均值补账仍可能低估其输入；补值仅用于预算闸，费用表保留原始已记录账。')
    if not m['secondary'] and (E / 'secondary-budget-plan.json').exists():
        b = read(E / 'secondary-budget-plan.json')
        add(f"次要预算计划：作答客户端输入停止线15,000,000；两判官停止线=1.5×40×({b['main_judge_tokens']:,}/120)={b['judge_limit']:,.1f} token，主比较每答案判官合计{b['main_judge_tokens_per_answer']:,.2f} token。未通过闸门时不消耗该预算。")
    if m['secondary']:
        b = m['secondary_budget']
        pc = m['secondary_pair_coverage']
        cov = m['secondary_coverage']
        unattempted = [m['tables']['S-10-r0'][str(q)]['cid'] for q in pc['planned_qids'] if q not in pc['answered_qids']]
        add('', f"次要作答停止线为15,000,000客户端输入token，实测输入{b['answer_input']:,}、输出{b['answer_output']:,}，触线={b['answer_stopped']}；两种判官停止线=1.5×40×({b['main_judge_tokens']:,}/120)={b['judge_limit']:,.1f} token，实测{b['judge_tokens']:,}，触线={b['judge_stopped']}（主会话授权口径）。停止以同题S/C配对为单位：触线后完成已启动配对，再停止该部分的新配对；实测可超过停止线一个配对的消耗。为此，次要作答与判分分阶段收集。", f"次要覆盖（每组计划20）：S作答{cov['S']['attempted']}份、C作答{cov['C']['attempted']}份；rubric记录{pc['rubric_answer_records']}份、五维记录{pc['five_answer_records']}份（含NA）。有效三判：rubric S/C={cov['S']['rubric_judged']}/{cov['C']['rubric_judged']}，五维 S/C={cov['S']['five_judged']}/{cov['C']['five_judged']}。", '两判官评分记录齐的配对题：' + ', '.join(pc['rubric_judged_cids']) + '；未判的已作答题：' + (', '.join(pc['unjudged_answer_cids']) or '无') + '；未尝试题：' + (', '.join(unattempted) or '无') + '。下表“含NA”仅覆盖实际判分的配对题；“有效”只算两组答案有效且该种判官三判齐的题。未尝试或预算未判题不伪填NA；若覆盖不足计划，不作完整20题比较结论。')
        add('', '| 评分/25步 | S均分 | C均分 | C−S（n） |', '|---|---:|---:|---|')
        for metric in ['rubric', 'five']:
            for title, section in [('含NA', m['secondary']), ('有效', m['secondary_valid_only'])]:
                s = section[metric]
                add(f"| {metric}/{title} | {num(s['groups']['S']['mean'])} | {num(s['groups']['C']['mean'])} | {ci(s['pairs']['C-S'])} (n={s['pairs']['C-S']['n']}) |")
    if m['secondary'] and all((m['secondary'][metric]['pairs']['C-S']['ci95'][0] <= 0 <= m['secondary'][metric]['pairs']['C-S']['ci95'][1] for metric in ['rubric', 'five'])):
        add('实际已判17题的两种C−S区间均含0，没有测出差别；与10步结果方向不同仍保留。')
    add('', '- 本次题型各10；层1—4为3/8/18/11、层3+4占72.5%，偏离原计划4/8/14/14与格内配额。闭卷筛选≥70，55候选剔除0；选中40题有28题闭卷0分，判官要求具体函数/条件，严格度影响读数。本次沿用冻结分数，未重新筛题；闭卷过滤阶段曾有成功响应落盘前丢失后重答，继承限制见 e5q2_result.md。', '- 题与文档都与同一Joern图有关；已按分派锚点14/非分派26和文档在30/不在10分报；“在”表示核心出处的每个（文件，函数）在catalog中均有同文件同名的独立或分组单元，不代表说明正确。E5a有153文件的syntax_error，复用图有一处reaching_defs截断；complete/verify不证明语义正确。不能由子组区间推因果。上游每回复只执行首个工具调用，bash默认被拦，grep未转义竖线易空输出；这些局限按冻结harness保留。', '- 本次未新增已证实的错误rubric/参考题；未全量重审源码真值。D-61主结果保留所有题；如主会话抽查发现错误，须补去错题敏感性分析，不能改冻结判分。', '- 判分抽查由主会话另派；审阅入口 `review/{S,C0,C}-10-r0/qNN/`（question.txt、answer.txt、rubric-1/2/3.json、fivedim-1/2/3.json各成文件；无答案NA没有判词，NA.json说明原因）。原完整响应仍在 rubric/、judge/。', '- 程序复算只核算术、原始判词字段与引文子串；不声称独立语义验收或多仓普遍效果。直答原提示要求短答、不解释不引用，五维判官对短答可能扣分。', '', '## 花费与核验', '', '| Session | 请求 | 非缓存输入 | 缓存读 | 输出 | 网关cost_usd |', '|---|---:|---:|---:|---:|---:|')
    for name, b in bill.items():
        add(f"| {name} | {b['requests']} | {b['input_tokens']:,.0f} | {b['cache_read_tokens']:,.0f} | {b['output_tokens']:,.0f} | {b['cost_usd']:.6f} |")
    add('', f'主比较作答已知输入+输出{primary_tokens:,} token；停止线13,575,000=1.5×预算上界9,050,000，未触线，相对该上界{(primary_tokens / 9050000 - 1) * 100:+.1f}%。实际开销包含无答案全重跑及每步重复输入增长的历史。两判官已知输入+输出合计{primary_judge_tokens:,}，未触18,150,000停止线。')
    audit = read(E / 'gateway-reconciliation.json')
    add(f"逐行复核：{audit['request_rows']:,}条回执、已记录费用合计${audit['known_recorded_cost_usd']:.6f}；64条499无usage（主作答16、次要作答2、直答45、主rubric1）未估填。可用上游ID共3418条且均唯一；request_id缺1070条、response_id缺64条，两者都缺64条。3条同秒无ID的直答499标准字段相同，按回执行保留；客户端74次直答尝试与74条网关记录一致，未按空ID或重复展示字段去重；详gateway-reconciliation.json。")
    wall = read(E / 'main-answers-done.json')['wall_seconds']
    add('', f"主比较作答墙钟={wall:.1f}秒（{wall / 3600:.3f}小时），含判分尾部墙钟={read(E / 'main-done.json')['wall_seconds']:.1f}秒；直答墙钟={read(E / 'direct-done.json')['wall_seconds']:.1f}秒；次要作答墙钟=" + (f"{read(E / 'sec-answers-done.json')['wall_seconds']:.1f}秒。" if gate['run'] else 'NA。'), '网关逐请求原件 gateway-requests.csv，按独立session精确筛选；费用为网关已记录的价表值；空费用和空token不估填，缺失数见gateway-usage.json。输出含推理，reasoning_tokens不重复加；缓存写/推理/状态/实际服务模型详 gateway-usage.json。客户端token为含缓存输入/输出；检查点的作答requests为未埋点占位0，请求数一律以网关为准；失败无usage部分不估填，详 accounting.json（逐session核对网关与客户端差值）。', '冻结与harness、源码副本校验、工具层冒烟及从原始判词重算的回执分别为 freeze-check.json、harness-sha-check.json、arm-copies-check.json、tool-layer-smoke.json、recompute-verification.json；未改冻结题/代码/harness，未提交、推送或派其他agent。', '大于10MB的活动外JSON收尾gzip，清单 compression.json；C组run/context.json与catalog.json保留明文。后续独立语义抽查与发布由主会话负责。', f'生成时间：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。')
    lines = [line for i, line in enumerate(lines) if not (line == '' and i + 1 < len(lines) and lines[i + 1].startswith('## '))]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text('\n'.join(lines) + '\n')
    print(str(REPORT), len(lines), 'lines')
if __name__ == '__main__':
    main()
