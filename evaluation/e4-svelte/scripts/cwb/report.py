"""Render final experiment report only after all required work or an authorized stop."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, datetime, sys
from pathlib import Path
R = Path(__file__).resolve().parent
OUT = Path(os.path.expandvars('$TASK_DIR/scratch/opt_e4/e4q_result.md'))

def load(name):
    return json.loads((R / name).read_text())

def pct(value):
    return 'NA' if value is None else f'{value * 100:.4f}'
a = load('aggregate.json')
reports = a['reports']
gates = load('budget-gates.json')
labels = load('svelte-leaf-labels.json')
reason = sys.argv[1] if len(sys.argv) > 1 else ''
assert 'codewiki-1' in reports or reason, 'Missing paired result requires explicit authorized stop/timeout reason'
lines = ['# E4q：Svelte 同判官文档覆盖度', '', f'写成 UTC：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。产物根 `$R`＝`{R}/`。', '']
if 'codewiki-1' in reports:
    pair = a['pairs']['cbe-r1__codewiki-1']
    lo, hi = pair['bootstrap_95_ci']
    lines += [f"第一轮 CBE r1 加权 {reports['cbe-r1']['weighted_score'] * 100:.4f}%，CodeWiki 1 加权 {reports['codewiki-1']['weighted_score'] * 100:.4f}%；未加权通过率差 CBE−CodeWiki 为 {pair['unweighted_difference'] * 100:+.4f} 个百分点，按叶子配对 bootstrap 95% 区间 [{lo * 100:.4f}, {hi * 100:.4f}]。{pair['interpretation']}。", '']
else:
    lines += [f"仅完成 CBE r1：加权 {reports['cbe-r1']['weighted_score'] * 100:.4f}%，未加权 {reports['cbe-r1']['passed']}/96。CodeWiki 未判，不能给两边覆盖度之差。原因：{reason}。", '']
lines += ['范围按 D-66 在出分前确定：CBE 取 E4b 中编号最小的 complete、verify 通过的 r1；条件允许的下一次为 r2。CodeWiki 按 E4c 完整性说明选最小编号；不按分数挑选，残缺产物不作对手。', '同一输入为 svelte@be645b4 的 440 文件剪枝副本；生成模型两边均为 zai/glm-5.3-flash。判官固定 codex/gpt-6.1-sol，经 Magpie；使用原版 CodeWikiBench 提示与 grep_docs/read_section 工具；每叶一次，至多两次错误重判，并发最多四。', '上游重试计数从 0 开始，max_retries=2 实际会发三次重判；运行时传 1，以落实最多两次重判。两边同参数，不改源码或 venv。最终解析失败或错误标 NA，主结果记 0；有效叶子另算。', '', f"`.svelte` 标注在 {labels['created_utc']} 写成：96 叶中 {sum((x['svelte_related'] for x in labels['leaves']))} 叶为是；只凭叶子 requirements 判断单文件语法/解析/编译是否为主，纯运行时 API 不算。逐条理由在 `$R/svelte-leaf-labels.json`，写成后只读，SHA-256 复核未变。标签文件 basis 的“Only leaf requirements”描述过强：提取时曾显示含父节点文字的完整 rubric，故不满足对父项上下文盲法的严格口径；判前未看生成文档或判词，标签未事后改写。该偏离只影响相关叶标注的解释，不改动原 96 叶判分。", 'rubric 来自指定 HF raw_data/svelte.json 的 rubrics 字段，8 顶层、96 叶；叶权重 1/2/3 各 17/57/22。文件只留本地写域，不提交或发布。', '', '|运行|节点/Markdown 页|根/Parent 行|docs_tree bytes|o200k token|解析核对|', '|---|---:|---:|---:|---:|---|']
for k in reports:
    c = load(k + '-conversion-check.json')
    t = load(k + '-tree-size.json')
    lines.append(f"|{k}|{c['tree_nodes']}/{c.get('flat_pages', c.get('flat_pages_excluding_overview', 0) + 1)}|{c['roots']}/{c.get('parent_lines', 'NA')}|{t['bytes']}|{t['o200k_base_tokens']}|通过，缺页 {(len(c['missing']) if 'missing' in c else 0)}|")
lines += ['', 'CBE 使用冻结转换脚本原样转换，节点页数=树节点数，Parent 行数=页数−根数，INDEX→overview；CodeWiki 直接用 --flat 产物。两边均经原版 codewikibench parse，未修改生成文档。判官每次请求带整份 docs_tree，树体积差会影响费用与导航。', '', '记账探针在开正式 pilot 前验证：X-Magpie-Agent=codewikibench，X-Magpie-Session=e4q-judge-<运行>，网关按 session、agent、response_id 精确匹配。运行时为 OpenAI、httpx/httpx2 加头，并设 User-Agent=codewikibench/1.0；密钥仅在进程环境与内存中。', '首个探针 session 可分，但 agent 显示 AsyncOpenAI；修正 User-Agent 后第二个探针显示 codewikibench。各 4,230 token、cost_usd 0.000718，均剔出判分。早期 pilot 误启动后立即终止的 4 条 HTTP 499 无保留判词，网关 token 为 0、费用空白，开销单列为未知，不当作免费。', '', f'CBE 八叶 pilot：1,117,083 token ×12＝13,404,996，<=15M，故按既定闸先判完 CBE。CBE 96 叶实测 11,451,940 token，推算/实测在 `$R/budget-gates.json`；pilot 叶子未重复判。', f"CodeWiki 八叶 pilot：{int(gates['codewiki_pilot']['actual_gateway_tokens']):,} token ×12＝{int(gates['codewiki_pilot']['projection_96_tokens']):,}；加 CBE 已完成实测 {int(gates['combined_first_round_gate']['cbe_actual']):,}，第一轮合计推算 {int(gates['combined_first_round_gate']['combined_tokens']):,}，<=30M，故继续 CodeWiki 余下叶子，未触发超预算升级。", f"第二轮预算闸：第一轮两份实测合计 {int(gates['second_round_gate']['first_round_actual_combined_tokens']):,} token，>20M，所以各一次生成参与覆盖度判分，第二轮不跑，生成之间的差未测；此决定在配对得分聚合前只按 token 写入 budget-gates.json。", '', '|运行|加权总分 %|未加权通过/96|通过率 %|NA|仅有效叶加权 %|仅有效叶通过率 %|', '|---|---:|---:|---:|---:|---:|---:|']
for k, x in reports.items():
    lines.append(f"|{k}|{x['weighted_score'] * 100:.4f}|{x['passed']}/96|{x['unweighted_pass_rate'] * 100:.4f}|{x['NA']}|{pct(x['valid_only_weighted_score'])}|{pct(x['valid_only_pass_rate'])}|")
lines += ['', '96 个同叶二值判词全部相同；共同判 0 的叶子是 1.1.2（signal 的 .s subscribers 字段）和 2.0.0（工厂返回带 mount/update/destroy 钩子的片段）。这是原判词读数，没有据此改 rubric 或重判。', '加权分用 CodeWikiBench calculate_scores_bottom_up/compute_overall_score 自底向上算；另从原始逐叶判词独立递归重算，两者及保存的得分相等。非叶权重也参与，不能把它换成简单叶权重平均。', '', '|顶层主题|' + '|'.join(reports) + '|', '|---|' + '|'.join(('---:' for _ in reports)) + '|']
for i in range(8):
    lines.append('|' + reports['cbe-r1']['topics'][i]['name'] + '|' + '|'.join((f"{x['topics'][i]['score'] * 100:.4f}%" for x in reports.values())) + '|')
lines += ['', '|运行|.svelte 相关通过/47|其余通过/49|删去相关叶后加权 %|', '|---|---:|---:|---:|']
for k, x in reports.items():
    lines.append(f"|{k}|{x['svelte_related_passed']}/47|{x['without_svelte_passed']}/49|{x['without_svelte_weighted_score'] * 100:.4f}|")
lines += ['', '删叶与仅有效叶计算：移除叶子，空分支也移除，在每层对保留子项重新归一权重；不是将移除叶子记 0。', '']
for k, p in a['pairs'].items():
    lo, hi = p['bootstrap_95_ci']
    lines.append(f"配对 {k}：未加权差 {p['unweighted_difference'] * 100:+.4f} pp，95% CI [{lo * 100:.4f}, {hi * 100:.4f}] pp；{p['interpretation']}。按同叶差值重采样，种子 20261017，10,000 次，NA=0；加权差只报点估计 {p['weighted_difference'] * 100:+.4f} pp。")
for k, v in a['within_tool_variation'].items():
    lines.append(f"生成间变化 {k}（后−前）：加权 {v['weighted_second_minus_first'] * 100:+.4f} pp，未加权 {v['unweighted_second_minus_first'] * 100:+.4f} pp，{len(v['changed_leaves'])} 叶改变。")
if not a['pairs']:
    lines += ['配对差、bootstrap 区间与生成之间的差：未测到，缺少合格 CodeWiki 判词；不以 CBE 单组结果补造。']
lines += ['', '|运行|请求（HTTP）|非缓存输入|缓存读|输出|cost_usd|每叶平均 token|', '|---|---|---:|---:|---:|---:|---:|']
for k in reports:
    u = load(k + '-usage.json')
    scored = u['requests'] - u.get('leaf_usage', {}).get('unmapped', {}).get('requests', 0)
    lines.append(f"|{k}|{scored} scored / {u['requests']} session；{json.dumps(u['status'])}|{int(u['input_tokens'])}|{int(u['cache_read_tokens'])}|{int(u['output_tokens'])}|{u['cost_usd']:.6f}|{u['total_tokens'] / 96:.2f}|")
lines += ['', '判分 token 总量：CBE 11,451,940，CodeWiki 14,018,641，合计 25,470,581；已记录判分 cost_usd 合计 18.348230，探针与费用未知的早期取消另列。', '缓存写全部为 0；推理 token 已含在输出，不能再相加。费用直接加网关 cost_usd，不用未知价表补算。逐请求原始 CSV、每叶归属、HTTP/服务模型与 API 对照在 `$R/*-requests.csv`、`*-usage.json`、`*-http.jsonl`、`verification.json`。', '所有已完成判词请求的 requested_model=codex/gpt-6.1-sol，provider=codex，served_model=gpt-6.1-sol，swapped=false；规范身份一致，但 served_model 字面省略 codex/，所以不声称完整字符串字面相等。四条早期取消无服务模型，不混入已判请求的身份结论。', 'CBE、CodeWiki 相对任务粗估“每份约 10M”分别为 1.1452、1.4019 倍。E1 原始 Svelte 线性试算其实是按两份 Flask 烟测合计推 9,989,712 token（不是各一份 10M）；真实 Svelte 树更大，不能把原试算当实测上限。', '']
audit = R / 'sample-six-review.md'
if audit.exists():
    lines += [audit.read_text().strip(), '']
else:
    lines += ['六叶对照核查尚未完成：需先有两组判词，按种子 20261017 从不同判法取四叶、相同取两叶；不以单组样本冒充配对核查。', '']
if 'codewiki-1' in reports:
    caveats = load('codewiki-input-caveats.json')
    lines += ['', 'CodeWiki 1 的 6 个顶层概览页只有读子模块后再写概览的开场句，未改、未删，照原样判；结构完整不代表正文完整。以下为文件名和字节数：', '']
    lines += [f"- `{p['name']}`：{p['bytes']} bytes。" for p in caveats['1']['short_top_level_pages']]
    lines += ['', 'parse 只读选中输出目录顶层 *.md；docs/ 与 temp/ 未递归进入判官输入。两份生成输出的 docs/ 各有 3、4 个首轮写错位置、顶层已有同名页的 Markdown；temp/ 内有中间产物，均未作为文档补入。详情在 `$R/codewiki-input-caveats.json`。']
lines += ['公开背景：CodeWikiBench 论文 Table 1（https://arxiv.org/html/2510.24428#S4.T1）Svelte CodeWiki 71.96 ±3.73，覆盖 80/96；DeepWiki 68.51 ±3.31。论文生成 Claude Sonnet 4，判官 Gemini 2.5 Flash、GPT OSS 120B、Kimi K2 Instruct。', 'CodeWiki README benchmark results（https://github.com/FSoft-AI4Code/CodeWiki#benchmark-results；本地 README.md:196）2026-09 重跑：DeepWiki 69.83、CodeWiki 1.0 73.21、2.0 80.09。README 未写判官名与 Svelte 精确 artifacts 开关。这些数的判官、生成模型和/或设置不同，只作背景，不能直接与本实验排名。', '', '局限：单一判官、每叶一次；判官能看到 CBE 程序标签；两边树大小不同；CBE 没有 .svelte 解析器，相关叶子标注存在边界判断；rubric 测“提到/解释”，不等于逐条文档事实正确；只有 Svelte 一仓，不能外推全部仓。', '已核：冻结标注与起判时刻、转换/解析计数、每份 96 个原始叶结果、独立递归复算与上游一致、逐 response_id 网关归属、API 与网关 token 合计一致、服务规范身份、凭据未落盘。详见 `$R/verification.json`。作者自验可交主会话独立验收；没有另派 agent。']
if reason:
    lines += ['', f'未做成与原因：{reason}。']
lines += ['', '完整产物：`$R/svelte-leaf-labels.json`、`*-parsed/`、`*-leaves/`、`*-judged.json`、`aggregate.json`、`budget-gates.json`、`sample-six*.json/md`（如有）、`public-background.json`、`verification.json`；命令与运行轨迹见 `$R/execution.md` 和运行脚本。未改 CBE、CodeWiki、CodeWikiBench 或 venv；未提交、推送或发布 rubric。']
OUT.write_text('\n'.join(lines) + '\n')
print(OUT, 'lines', len(lines))
