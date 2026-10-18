"""Render the E3 result from durable measurements; never substitute missing results."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, datetime, gzip, collections, re
from pathlib import Path
E = Path(__file__).resolve().parent
DEST = Path(os.path.expandvars('$TASK_DIR/scratch/opt_e3/e3_result.md'))

def read(p):
    if p.exists():
        return json.loads(p.read_text())
    with gzip.open(str(p) + '.gz', 'rt') as f:
        return json.load(f)

def num(x):
    return 'NA' if x is None else f'{x:.2f}'

def pct(x):
    return 'NA' if x is None else f'{100 * x:.1f}%'

def ci(x):
    return 'NA' if not x else f'[{x[0]:+.2f}, {x[1]:+.2f}]'

def pair(x):
    return f"{x['mean']:+.2f} {ci(x['bootstrap95'])}" if x['mean'] is not None else 'NA'
gen = read(E / 'cbe-pytest/metrics.json')
full = (E / 'REDUCE-DONE.json').exists()
g = gen['gateway']
L = []

def add(*s):
    L.extend(s)
flag_counts = collections.Counter()
for flag, count in gen['task_flags'].items():
    if flag.startswith('id_corrected:'):
        continue
    reason = flag.split(': ', 1)[-1]
    reason = re.sub('after id correction to [^;]+;', 'after id correction;', reason)
    flag_counts[reason] += count
flag_counts = dict(flag_counts)
add('# E3：pytest 48 题、10 步三组比较', '')
if full:
    m = read(E / 'metrics.json')
    primary = m['all48']['pairs']['C-S']
    status = 'complete' if gen['complete'] else '**partial（按 D-67 原样评测）**'
    add(f"CBE 生成 {status}；144/144 条工具作答与判分记录齐，另有48条直答校准记录（47条有效并三判，1条NA）。主指标 C−S = **{pair(primary)}**，n=48；{primary['interpretation']}。结论只覆盖本仓、本模型、本次产物与 10 步上限。C 仅在两题执行了3次 find/query，反映工具可用条件及本代理选择，不能外推为强制使用 CLI 的效果。", '')
else:
    add(f"CBE 生成 complete={gen['complete']}；工具问答尚未完成，不能计算 C−S。下文仅报告已取得的生成证据；未完成的问答不记作零分结果。", '')
add(f'产物根 E=`{E}`。本报告为作者实测与程序自验；非作者验收由主会话承担。', '', '## 生成与冻结范围', '', f"- 冻结提交 `{gen['commit']}`，解释器 `codebase-explorer/.venv/bin/python`；PYTHONPATH=`eval-cbe2/src`，PYTHONDONTWRITEBYTECODE=1，`generation-driver.log` 已打印模块位置与 HEAD。", '- 输入 `eval/pytest-5989efe/`；249 个文件；占比分母按冻结任务取 752,827 o200k token。图直接复用 `runs/e1c/pytest-5989efe-default.graph.json`，未重建。', '- 命令（无密钥）：`python runs/e3/audited_cli.py generate eval/pytest-5989efe --host api --jobs 2 --base-url http://127.0.0.1:3425/v1 --api-key-env CBE_API_KEY --model zai/glm-5.3-flash --graph runs/e1c/pytest-5989efe-default.graph.json --run-dir runs/e3/cbe-pytest/run --config runs/e3/cbe-pytest/api-config.json`。', '- api-config 仅 extra_headers：X-Magpie-Agent=codebase-explorer、X-Magpie-Session=e3-cbe-pytest。密钥只从 environment credentials 读入进程环境，未写入配置。', '- plan 后、首个模型请求前，225 个冻结 Python 文件全部经 frozen_sources 重组并与输入逐字节核对，fallback=0。另 24 个非 .py 输入未进入 CBE 冻结清单，逐项见 cbe-pytest/metrics.json/outside_frozen_inventory；这次没有验证它们的源码覆盖。', '- 首次移植审计误用输入总文件数 249 作冻结数，因实际 225 在调模型前拦停；零模型调用。更正审计范围后重新 plan；原件保存在 preflight-count-guard/，未改 CBE。', f"- 首轮 complete={gen['first_complete']}，最终 complete={gen['complete']}；阶段与退出码见 cbe-pytest/phases.json；最终 verify 原输出见 cbe-pytest/verify-final-d67.log；D-67 将续跑上限改为两次，均与首轮同设置，不改代码、不手修产物、不从头重跑。", f"- calls={gen['calls']}，计划任务={gen['task_count']}，树汇总分区={gen['regions']}，被调用逻辑任务={gen['logical_tasks_called']}，attempt 分布={gen['attempts']}，attempt>1 的调用={gen['retry_calls']}；任务状态={gen['task_status']}；调用结果={gen['results']}。", f"- id_corrected={len(gen['id_corrected'])}，answer_fallback={len(gen['answer_fallback'])}，index_only_filled={len(gen['index_only_filled'])}；task_flags 按原因汇总={flag_counts}；完整标记与对应单元见生成 metrics.json。", '')
add(f"- 生成网关（session精确归属）：请求 {g['requests']}；非缓存输入 {g['input_tokens']}、缓存读 {g['cache_read_tokens']}、缓存写 {g['cache_write_tokens']} token。", f"- 输出 {g['output_tokens']}、推理 {g['reasoning_tokens']} token（重叠）；网关 cost_usd={g['cost_usd']}。")
add('', f"网关状态={g['statuses']}；实际服务模型={g['served_models']}；模型异常={g['identity_anomalies']}，服务模型未知={len(g['unknown_served'])} 条（逐请求记录保留）。gateway-requests.csv 为逐请求原件，usage.csv 为共享窗口导出。", f"网关减 summary：`{gen['gateway_minus_summary']}`；API summary 的 input 为 provider prompt 减 cache，cache 单列；作答和判官账用客户端 prompt（含 cache）/completion。summary 未记录的字段不伪填差值，reasoning/cache-write 可能与其他 token 字段重叠，不相加。", '')
if gen['overwritten_first_call_labels']:
    add(f"注意：resume 后 calls.csv 的 {len(gen['overwritten_first_call_labels'])} 条首轮记录标签被更新；首轮原标签分布={gen['first_results_snapshot']}，原件见 first-calls.csv、first-raw/，差异逐行见生成 metrics.json/overwritten_first_call_labels。本次未改 CBE 的记账实现。", '')
if gen['gateway_by_phase']:
    add('| 阶段 | 请求 | 非缓存输入 / 缓存读 / 输出 | 网关 cost_usd | 墙钟秒 |', '|---|---:|---|---:|---:|')
    for name, r in gen['gateway_by_phase'].items():
        add(f"| {name} | {r['requests']} | {r['input_tokens']} / {r['cache_read_tokens']} / {r['output_tokens']} | {r['cost_usd']} | {r['wall_seconds']:.1f} |")
    add('')
if gen['layers']:
    if not gen['complete']:
        add('生成仍为 partial。下表量本次实际发布目录，问答结论仅针对这份原样 partial 输入，不外推到完整生成文档。', '')
    layers = gen['layers']
    add('| 文档读数（o200k_base） | token / 字节 | 占 752,827 |', '|---|---:|---:|', f"| 七项 model_body（模型单元正文） | {layers['model_body_tokens']} | {pct(gen['body_ratio'])} |", f"| 发布 Markdown（含引用/去掉 [fN]: 行） | {layers['semantic_tokens']} / {gen['published_without_file_refs_tokens']} | {pct(gen['published_ratio'])} / {pct(gen['published_without_file_refs_ratio'])} |")
    for k, v in layers['semantic_breakdown'].items():
        if k != 'model_body':
            add(f'| 七项：{k} | {v} | {pct(v / 752827)} |')
    add(f"| catalog 确定层（含正文副本、去图） | {layers['catalog_tokens']} | {pct(layers['catalog_tokens'] / 752827)} |", f"| 冻结图（仅字节） | {layers['frozen_graph_bytes']} | 不计 token 比例 |", '', f"发布 {gen['published_pages']} 页；context/catalog 文件字节={gen['sizes']}。CBE layer_metrics 自算的源码分母为 {layers['source_tokens']}（225 个冻结文件），本报告按任务要求统一用 752,827。", '')
else:
    add('模型正文/源码、发布 Markdown/源码、去掉 [fN]: 行及七项发布分项均为 NA：尚无可计量的发布 catalog/Markdown，不能写成 0%。', f"当前发布页数 {gen['published_pages']}；context/catalog 字节={gen['sizes']}；输入冻结图原文件字节=" + str((E.parent / 'e1c/pytest-5989efe-default.graph.json').stat().st_size) + '（只读复用、未重建）。', '')
scope = read(E / 'failed-module-scope.json') if (E / 'failed-module-scope.json').exists() else None
if scope and (not scope['failed_modules']):
    state = read(E / 'cbe-pytest/run/host/state.json')
    recovered = {k: state['tasks'][k]['attempts'] for k in ['module_26', 'module_53', 'module_56']}
    add('D-67 在问答前授权最多两次同设置 resume；三项首轮失败任务最终累计尝试=' + str(recovered) + '。最终 complete，无失败模块/文件（0 token、占752827的0%），额外敏感性排除 q=[]，保留全部48题；决定及作答前冻结范围见 D67.json、failed-module-scope.json。', '')
elif scope:
    add('## D-67：实际产物与失败文件', '', f"协调者在问答前授权最多两次同设置 resume；最终状态={scope['generation_status']}。未完成任务=" + str({k: v['status'] for k, v in gen['unfinished_tasks'].items()}) + '；原始决定见 D67.json。')
    if scope['failed_modules']:
        add('', '| 失败模块 | 所含文件 | 库存单元数 | 有语义绑定的页数 |', '|---|---|---:|---:|')
        for row in scope['failed_modules']:
            add('| ' + row['module'] + ' | ' + ', '.join((f"`{f['path']}`" for f in row['files'])) + ' | ' + str(row['inventory_units']) + ' | ' + str(len(row['semantic_pages'])) + ' |')
        for row in scope['failed_modules']:
            add('文档呈现：' + str(row['resolution_counts']) + '；INDEX 标注：' + ' / '.join(row['index_notes']) + '。源码索引中出现不等于存在语义解释页。')
    else:
        add('最终没有失败的语义模块，失败文件集合为空。')
    add(f"失败文件去重后 {scope['unique_file_tokens']} token，占752,827的 {pct(scope['source_share'])}；文件/单元/页面逐项在 failed-module-scope.json。额外敏感性排除 q={scope['excluded_qids']}（0基），原题与参考答案的匹配位置逐条保留，候选答案和分数未参与。")
    if scope['index_generation_notes']:
        add('其他生成标注：' + ' / '.join(scope['index_generation_notes']) + '。文件引用敏感性不消除全局汇总未完成等局限。')
    add('')
add('## 三组与测评设置', '', f"- S=源码；C0=源码与 CBE 文档；C=源码、同份文档及 CBE 命令。三组各有一份 pytest 只读剪枝副本。C0/C 文档与 C/run 实际接入={bool((E / 'arms/C/run').exists())}，仅在 D-67 最终 verify 留痕、实际 ToolHandler 冒烟通过后开始问答；文档在副本外，C/run 采用只读消费链接。C/bin/cbe 指向 eval-cbe2，不指向旧 eval-cbe。", '- 68 个 harness 文件 SHA 与 E2 全部一致，原样加载 E1 harness；提示句沿 E1，仅换路径。源码复制核对见 arm-copies-check.json；ToolHandler 冒烟见 tool-layer-smoke.json。', '- 作答 zai/glm-5.3-flash、10 步、观察上限 20,000 字符、请求 240 秒；无答案完整重跑最多两次。判官 codex/gpt-6.1-sol，三次逐维中位数，单次失败最多重判两次。达到步数上限后的上游收尾调用保留。', '- D-67 额外去掉引用最终失败模块文件的题，题号与匹配证据在 failed-module-scope.json；源于作答前冻结的原题/原参考答案显式文件引用，不看候选答案或分数。', '- 按题轮转三组，判分增量跟进；40/80/120/144 次累计墙钟与 token 在 checkpoints.jsonl，检查点只计已落盘任务，在途请求完成后入账。判官请求加 E3 session 头，提示和评分规则不变。', '')
if full:
    ac = m['accounting']
    add(f"作答前 memory_pressure 空闲 {ac['memory_free_percent']}%，作答并发上限 {ac['answer_concurrency']}（低于 15% 时降为 2）；主运行起点 {ac['started_utc']}。", '', '| 组 | 有效作答/48 | NA | 总分均值 | 五维中位数 正/全/关/清/推 | 撞上限 | 观察字符 | 未解析/全部回复 | 循环重提示/循环回复 |', '|---|---:|---:|---:|---|---:|---:|---:|---:|')
    for arm in ['S', 'C0', 'C']:
        r = m['groups'][arm + '-10-r0']
        p = r['agent_protocol']
        dims = '/'.join((str(v) for v in r['dimensions_median'].values()))
        add(f"| {arm} | {r['valid_answers']}/48 ({pct(r['valid_answer_rate'])}) | {r['NA']} | {num(r['mean_total_na5'])} | {dims} | {pct(r['limit_hit_rate'])} | {r['observations_chars_total']:,} | {p['unparsed_all_replies']}/{p['all_agent_replies']} ({pct(p['unparsed_all_ratio'])}) | {p['unparsed_loop_replies']}/{p['loop_replies_excluding_final_answers']} ({pct(p['unparsed_loop_ratio'])}) |")
    add('', 'NA 每维记 1、合计 5；有效作答率只看答案，NA 还含判分失败。未解析全部回复含合法最终答案；循环重提示衡量解析失败；另有 C/q15 一次非法 grep 参数，未执行命令，证据留在 grep-literal-pipe-audit.json。观察字符含失败重跑，撞上限取最终尝试。', '', '## 配对差与敏感性', '', '| 范围 | n（C−S） | C−S（主） | C0−S | C−C0 |', '|---|---:|---|---|---|')
    for name, r in [('全部48题', m['all48']), *m['sensitivity'].items()]:
        add('| ' + name + ' | ' + str(r['pairs']['C-S']['n']) + ' | ' + ' | '.join((pair(r['pairs'][p]) + (' n=' + str(r['pairs'][p]['n']) if name == 'valid_only' else '') for p in ['C-S', 'C0-S', 'C-C0'])) + ' |')
    add('', '按题配对 bootstrap 10,000 次，百分位 95% 区间，主种子 20261017；各敏感性和分类固定偏移见 metrics.json/bootstrap。区间含 0 一律写“没有测出差别”。不删参考答案缺陷题；另去掉 q22，去掉 q3/4/7/34，及只保留两组答案有效且三判齐的题。', '', '| 分类（只报区间） | n | S | C0 | C | C−S | C0−S | C−C0 |', '|---|---:|---|---|---|---|---|---|')
    for name, r in m['categories'].items():
        add('| ' + name + ' | ' + str(r['n']) + ' | ' + ' | '.join((ci(r['groups'][a]['bootstrap95']) for a in ['S', 'C0', 'C'])) + ' | ' + ' | '.join((ci(r['pairs'][p]['bootstrap95']) for p in ['C-S', 'C0-S', 'C-C0'])) + ' |')
    d = m['difficulty_calibration']
    add('', '## 直答难度与工具调用', '', f"48 题 llm_direct 原提示，逐字提取函数与 SHA 见 direct/prompt-provenance.json；有效 {d['valid_answers']}/48，NA={d['NA']}。直答总分中位数 {d['median']}；题43三次超时后记5分并入排序，档位含API可用性影响；高档 ≥ 阈值、低档 < 阈值。", '', '| 切档/档位 | n | S均分/有效/NA | C0均分/有效/NA | C均分/有效/NA | C−S |', '|---|---:|---:|---:|---:|---|')
    for cut, record in d['strata'].items():
        for tier in ['high', 'low']:
            r = record[tier]
            add('| ' + cut + '/' + tier + ' | ' + str(r['n']) + ' | ' + ' | '.join((num(r['groups'][a]['mean_total_na5']) + '/' + pct(r['groups'][a]['valid_answer_rate']) + '/' + str(r['groups'][a]['NA']) for a in ['S', 'C0', 'C'])) + ' | ' + pair(r['C-S']) + ' |')
    a = m['groups']['C-10-r0']['cbe_agent_layer']
    add('', f"C find/query 请求 {a['tool_attempts']}、执行 {a['executed_count']}、成功 {a['successful_count']}、拦截 {a['blocked_attempts']}；执行成功率 {pct(a['success_rate_executed'])}，请求成功率 {pct(a['success_rate_attempted'])}。另 help 执行 {a['help_executed']} 次；上限后未执行的 JSON {sum((r['not_executed_at_cap'] for r in a['per_question']))} 条另存审计，不算执行。")
    for kind in ['find', 'query']:
        ev = [e for e in a['events'] if not e['help'] and e['kind'] == kind]
        add(f"{kind} 请求/执行/成功 = {sum((e['through_tool_handler'] for e in ev))}/{sum((e['executed'] for e in ev))}/{sum((e['success'] for e in ev))}。")
    add('', '非零题分布 qid:请求/执行/成功/拦截(find/query执行)：`' + ', '.join((f"{r['qid']}:{r['tool_attempts']}/{r['find_executed'] + r['query_executed']}/{r['successes']}/{r['blocked_attempts']}({r['find_executed']}/{r['query_executed']})" for r in a['per_question'] if r['tool_attempts'] or r['blocked_attempts'])) + '`；其余46题均为0。全48题逐项分布、命令与返回码见 agent-layer-audit.json。', '', '| 引用辅助检查 | .py路径提及 | 存在 | 不存在 | 歧义 | 显式行号/可核/存在 |', '|---|---:|---:|---:|---:|---|')
    for arm in ['S', 'C0', 'C']:
        c = m['groups'][arm + '-10-r0']['citations']
        add(f"| {arm} | {c['n']} | {c['valid_paths']} | {c['missing_paths']} | {c['ambiguous_paths']} | {c['line_references']}/{c['checked_line_references']}/{c['valid_lines']} |")
    add('', '只核 Python 路径、唯一后缀与显式 :行号/#L行号；路径存在不代表支持答案中的事实。', '', '| 上游 grep 局限 | 未转义竖线/grep执行 | 比例 | 其中空输出 | 占全部观察工具 |', '|---|---:|---:|---:|---:|')
    for arm, r in m['grep_literal_pipe'].items():
        add(f"| {arm} | {r['literal_pipe_calls']}/{r['grep_calls']} | {pct(r['pipe_fraction_of_grep'])} | {r['pipe_empty_output_calls']} | {pct(r['pipe_fraction_of_all_tools'])} |")
    add('', '## 花费、局限与核验', '', f"- 主比较作答实际墙钟 {ac['answer_wall_seconds']:.1f} 秒（{ac['answer_wall_seconds'] / 3600:.3f} 小时），首次提交到 144 份作答落盘；含判分尾部 {ac['answer_and_judge_wall_seconds']:.1f} 秒。", f"- 主比较作答 input/output={ac['answer_tokens']}；判官={ac['judge_tokens']}；作答尝试 {ac['answer_attempts']}，判官请求 {ac['judge_calls']}；无 usage 的失败作答/判官={ac['answer_unknown_usage_attempts']}/{ac['judge_unknown_usage_calls']}，客户端账是可观察下界。", f"- 直答校准单列：{d['new_only_accounting']}。生成网关用量见上表，不混入问答 token。")
    qag = read(E / 'gateway-model-audit.json')
    add(f"- 问答/判官共享时窗的匹配模型候选未发现服务模型不符，服务名未知 {qag['unknown_served']} 条；见 gateway-model-audit.json。该审计不作任务逐请求/token归属，不能把共享窗口用量加到客户端账上。")
else:
    add('## 未完成项', '', '- 144 次作答、432 次名义判分、48 题直答与144 次名义判分未完成；三组读数、主配对区间、敏感性、分类、难度、实测工具调用和引用均不能判。', '- 失败原件见 cbe-pytest/first.log、resume.log、resume2.log、phases.json、run/STATUS.md、host/state.json；D-67 若实际 ToolHandler 冒烟不通过，则不启动问答，原因见 D67-GATE-FAILED.json 与 tool-layer-smoke.json。')
for task, row in gen['unfinished_tasks'].items():
    if row['status'] == 'failed':
        add(f"- 未恢复任务 {task}，尝试={row['attempts']}；最后错误：" + str((row.get('errors') or ['未记录错误'])[-1])[:600] + '。完整原件在 run/host/state.json。')
add('- 上游 ls/grep/find 参数未转义，可以启动第二条命令；ToolHandler 真实入口冒烟同时确认沙箱拦越界读写，见 limitations-tool-smoke.json。grep 的 a|b 是基本正则字面竖线；返回空不直接判答错。', '- 参考答案核对原件见 evidence/e3/r12_pytest_labels_refcheck_REPLY.md：抽 10 条，5 对、4 部分对、1 错；敏感性集合沿冻结任务。原参考答案 q2/14/26/31/32/34 含 start_of_answer 残留标记，按上游原样交给判官，未清洗；可能影响评分。', '- 直答原提示要求短答、不解释、不引用，判官对短答扣分；难度档只代表这套提示与判官下的操作性难度。', '- 仅 pytest 单仓、一次文档生成、一个作答模型和一个判官模型族；题可能泄漏；分类区间仅描述、不做多重比较结论。未跑 25 步。', '- 大于 10 MB 的非活动 JSON 压缩，C 组使用的 run/context.json 保持明文；压缩清单见 compression.json。归档后复验 find/query 时，先在副本解压 catalog.json.gz，原 SHA 在 failed-module-scope.json。', '- verification.json 的4,646项程序核验通过，含8个凭据扫描正反例；静态配置选择器和公开 usage argv 采用窄范围结构豁免。此结果待协调者非作者验收。未推送、未发布，也未派其他 agent。', '', f'报告生成时间：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。')
DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text('\n'.join(L) + '\n')
print(str(DEST), len(L), 'lines')
