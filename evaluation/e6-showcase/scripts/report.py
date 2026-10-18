import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, decimal, re
from pathlib import Path
BASE = Path(os.path.expandvars('$WORK/runs/e6'))
REPORT = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e6/e6_result.md'))

def j(x):
    text = json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    fence = '`' * (1 + max((len(s) for s in re.findall('`+', text)), default=0))
    return fence + ' ' + text + ' ' + fence

def scope_brief(s):
    return {'files': s['files'], 'source_tokens': s['source_tokens'], 'source_share': f"{100 * s['source_share']:.3f}%", 'tasks': [{k: v for k, v in t.items() if k not in ('last_error', 'source_share')} for t in s['tasks']]}

def pct(v):
    return f'{100 * v:.3f}%' if v is not None else 'NA'
ms = json.loads((BASE / 'all-metrics.json').read_text())
inputs = json.loads((BASE / 'inputs.json').read_text())
lines = ['# E6：六个展示小仓的 CBE 单次生成与记账', '', f"完成读数：{sum((m['complete'] for m in ms))}/{len(inputs)} complete；verify 通过 {sum((bool(m.get('verify', {}).get('ok')) for m in ms))}/{len(inputs)}。网关累计 cost_usd=" + str(sum((decimal.Decimal(m['gateway']['cost_usd']) for m in ms), decimal.Decimal(0))) + '。含全部续跑，未超2美元封顶或单仓粗估上限3倍。单次展示，不打分；不代表文档语义正确，也未发布 GitHub。', '', '实现提交 `a87674ddf570b1cc9fd2c322982a83e011132668`；import=`$WORK/eval-cbe2/src/cbe/__init__.py`。Python=`codebase-explorer/.venv/bin/python`，环境 `PYTHONPATH=$ROOT/eval-cbe2/src PYTHONDONTWRITEBYTECODE=1`。', '$ROOT=`$WORK`；`O=$ROOT/runs/e6/<仓>`；生成源码只读，未改 CBE，未提交/推送。', '', '命令：`git -C <来源> archive <完整SHA> <路径…>` → tar 导出；实际完整参数在每仓 input.json。`python -m cbe graph build <副本> --output $O/graph.json --joern-home $ROOT/tools/joern/joern-cli --depcruise-bin $ROOT/tools/npm/node_modules/.bin/depcruise --timeout 3600`，外包 `/usr/bin/time -l`；失败才试 `--joern-heap 8g`。', '生成：`python runs/e6/scripts/audited_cli.py generate <副本> --host api --jobs 2 --base-url http://127.0.0.1:3425/v1 --api-key-env CBE_API_KEY --model zai/glm-5.3-flash --graph $O/graph.json --run-dir $O/run --config $O/api-config.json`；fmt 图与生成另加 `--header-language cpp`；续跑原命令加 `--resume`，最多两次。', '`api-config.json` 仅 extra_headers（X-Magpie-Agent=codebase-explorer，X-Magpie-Session=e6-cbe-<仓>）；key 只从 environment MAGPIE_API_KEY 读到子进程环境。verify：`python -m cbe host verify --run-dir <绝对run目录>`。', '每轮 UTC、命令、退出码、墙钟在 `$O/phases.json`；运行日志 `$O/<phase>.log`。plan 返回、首次模型调用前审计 frozen_sources 全文件逐字节重组，审计 `$O/frozen-audit.json`。', '', '|仓|提交/内容标识|副本（eval/）|源码文件/token（预期→实测）|清单核对|', '|---|---|---|---|---|']
problems = [m['repo'] for m in ms if not m['complete'] or not (m.get('verify') or {}).get('ok')]
if problems:
    lines[4:4] = ['**未完整或verify失败：' + ', '.join(problems) + '。** 原样产物、失败范围和全部费用均保留。', '']
lines[6 if problems else 4:6 if problems else 4] = ['**运行环境限制：** 固定解释器路径在启动进程观测为Python3.12.13，末尾为3.13.11，Ruby语法包可用性也不同；代码HEAD与tracked diff仍冻结。各仓依赖/解释器版本未逐次落盘，变动时点与原因未定位，不能宣称全程相同依赖环境；证据runs/e6/environment-current.json与environment-observations.md。', '']
for r in inputs:
    m = next((m for m in ms if m['repo'] == r['name']), None)
    lines.append(f"|{r['name']}|`{r['sha']}`|{Path(r['copy']).name}|{r['expected_files']}/{r['expected_tokens']} → {r['files']}/{r['tokens']}|" + ('逐文件 hash 再核一致' if m and (not m['input_recheck_mismatches']) else '尚未完核') + '|')
lines += ['', f"六仓实测源码合计 {sum((r['files'] for r in inputs))} 文件、{sum((r['tokens'] for r in inputs))} o200k_base token；预期291文件、494619 token，差异仅来自下述gson范围。", 'gson 差异已定位：调研 reproduce.sh:17 读 gson/src/main，包含 java-templates/com/google/gson/internal/GsonBuildConfig.java（248 token）；D-68 指定 java 子目录，本次照此，实际为 86 文件、159691 token。', 'polyglot 旧 f6c7d17349fe2e0d 无可复现命令，协调者回信 msg_cd4cb26dfcf6 作废并独立复现新数：按相对路径排序，对全部 23 文件输出 `sha256 + 两空格 + 相对路径 + 换行` 再 sha256，取前16位=6b19d76603fb65d1。含 mystery.xyz，CBE 不读它；源码仍22文件/1708 token。', '每仓 `$O/manifest.json` 记录所有导出文件的路径、字节、sha256、是否源码与源码 token；副本导出后 chmod 只读。Ruby lib 的29模板等非源码保留但不计分母。', '', '|仓|首轮→最终 complete / verify|续跑|调用/重试|answer_fallback/id_corrected|单元/页|模型正文/源码|Markdown/源码|去[fN]: token|', '|---|---|---:|---:|---:|---:|---:|---:|---:|']
for m in ms:
    v = m['verify'].get('ok') if isinstance(m['verify'], dict) else None
    lines.append(f"|{m['repo']}|{m['first_complete']}→{m['complete']} / {v}|{m['resumes']}|{m['calls']}/{m['retry_calls']}|{m['answer_fallback']}/{m['id_corrected']}|{m['units']}/{m['pages']}|{pct(m['body_ratio'])}|{pct(m['published_ratio'])}|{m['published_without_file_refs_tokens']}|")
lines += ['', 'D-53：分母为上表每仓实测源码 o200k_base token；模型正文仅已发布单元 explain/summary/extras/uncertainties；发布仅 docs/**/*.md。catalog 是确定层，context 与冻结图不进比例；冻结图只报字节。七项分解合计等于 Markdown token，原值见 metrics.json.layers。', '', '|仓/阶段|UTC开始 → 结束|秒/退出码|请求|非缓存输入|缓存读|缓存写|输出|推理|cost_usd|', '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
for m in ms:
    for p in m['phases']:
        label = p['phase']
        g = m['gateway_by_phase'].get(label)
        if g:
            lines.append(f"|{m['repo']}/{label}|{p['start']} → {p['end']}|{p['wall_seconds']:.1f}/{p['returncode']}|{g['requests']}|{g['input_tokens']}|{g['cache_read_tokens']}|{g['cache_write_tokens']}|{g['output_tokens']}|{g['reasoning_tokens']}|{g['cost_usd']}|")
lines += ['', '|仓|图退出/秒/峰值RSS字节（各次）|节点/边|生成合计秒|内存等待秒|诊断|', '|---|---|---:|---:|---:|---|']
for m in ms:
    gp = [f"{p['phase']}:{p['returncode']}/{p['wall_seconds']:.1f}/{m['graph_rss_bytes'].get(p['phase'])}" for p in m['graph_phases']]
    gen = sum((p['wall_seconds'] for p in m['phases'] if p['phase'] == 'first' or p['phase'].startswith('resume')))
    lines.append(f"|{m['repo']}|{'; '.join(gp)}|{m['graph_nodes']}/{m['graph_edges']}|{gen:.1f}|{max(0, len(m['memory']['samples']) - 1) * 180}|{j(m['diagnostics'])}|")
lines += ['', '网关原导出 `$O/usage.csv`（`magpie usage --csv --last 48h`，每仓完成后等150秒再导出），按 agent+session 留 `$O/gateway-requests.csv`，逐请求 UTC 按首轮/续跑窗口归属；指标 `$O/metrics.json`。原始requested_model均为zai/glm-5.3-flash；served_model的glm-5.3-flash为同路由服务短名（E4b相同口径），未见换模型标记。HTTP、实际模型、身份异常、差值如下（output_tokens已含reasoning_tokens，推理列为子集；未被summary记录=NA/null）。', '']
for m in ms:
    g = m['gateway']
    lines.append(f"- {m['repo']}: 总请求={g['requests']}，cost={g['cost_usd']}；HTTP={j(g['http'])}；实际模型={j(g['served_models'])}；身份异常={j(g['identity_anomalies'])}；窗口外请求={m['gateway_outside_phases']}；网关−summary={j(m['gateway_minus_summary'])}。")
lines += ['', '调用、标记、七分项与图质量（完整字段、失败任务/错误均在每仓 metrics.json）：', '']
for m in ms:
    if not m['first_complete']:
        lines.append(f"- {m['repo']}首轮缺口={j(scope_brief(m['first_failure_scope']))}；inventory_symbols是任务清单ID数，frozen_chunks是context切分块数，published_units是这些文件已发布单元数；快照见first-state.json、first-catalog.json(.gz)、first-docs/及render-snapshots.json。")
    if not m['complete']:
        lines.append(f"- {m['repo']}最终缺口={j(scope_brief(m['final_failure_scope']))}；最终错误详见metrics.json.failed_tasks与run/STATUS.md。")
    lines.append(f"- {m['repo']}: attempt={j(m['attempts'])}；result={j(m['results'])}；其余 task flags={j(m['task_flag_reasons'])}。")
    layers = m.get('layers') or {}
    lines.append(f"  七项={j(layers.get('semantic_breakdown'))}；正文={layers.get('model_body_tokens')}，发布={layers.get('semantic_tokens')}；catalog token={layers.get('catalog_tokens')}；冻结图字节={layers.get('frozen_graph_bytes')}；context/catalog字节={j(m['sizes'])}。")
    meta = m.get('graph_metadata', {})
    q = meta.get('quality', {})
    qbrief = {k: q.get(k) for k in ('empty_graph', 'backend_completed', 'frontend_failures')}
    qbrief.update({k: q.get(k, {}).get('count') for k in ('dangling_edges', 'nodes_outside_manifest', 'nodes_missing_files')})
    qbrief['files_without_graph_nodes'] = m['graph_files_without_nodes']
    qbrief['diagnostics'] = meta.get('diagnostics', [])
    qbrief['incomplete'] = [{k: c.get(k) for k in ('language', 'graph', 'status', 'limitations')} for c in q.get('incomplete_capabilities', [])]
    if len(qbrief['incomplete']) > 8:
        caps = qbrief['incomplete']
        qbrief['incomplete'] = {status: sorted((c['language'] + '/' + c['graph'] for c in caps if c['status'] == status)) for status in sorted({c['status'] for c in caps})}
        gd = meta.get('diagnostics', [])
        qbrief['diagnostics'] = {code: sum((d.get('code') == code for d in gd)) for code in sorted({d.get('code', 'unknown') for d in gd})}
    lines.append(f"  图质量={j(qbrief)}；冻结审计文件数={m['frozen_audit']['files']}, fallback={m['frozen_audit']['source_reassembly_fallback']}, ok={m['frozen_audit']['ok']}。")
    if m['repo'] in ('ruby_llm', 'gson'):
        lines.append(f"  首次真实仓观察：图import缺path={m['graph_import_missing_path']}，expression为`<empty>`={m['graph_import_empty_expression']}；import capability={j([c for c in meta.get('capabilities', []) if c.get('graph') == 'import'])}。")
    if m['repo'] == 'gson':
        lines.append('  Java定位问题：35个`<clinit>`合成method节点的path均为`<empty>`，因此被记为清单外/文件不存在；这不是35个真实Java文件漏导出。五个package-info.java与module-info.java没有method/CFG节点，源码仍全部冻结；见gson/observations.md。')
    if m['repo'] == 'polyglot':
        lines.append('  夹具当前环境：C#/Kotlin/PHP/Ruby/Rust/Swift六种grammar不可导入，加SQL共7文件走全文context回退；PHP前端找不到php，Rust项目加载失败，Python import缺grimp。源码重组仍22/22，complete/verify不表示14种语言均有语法/图覆盖；见polyglot/observations.md与环境记录。')
    if m['repo'] in ('cjson', 'fmt'):
        coarse = sorted(m['chunk_by_file'].items(), key=lambda x: x[1]['max_chunk_bytes'], reverse=True)[:3]
        lines.append(f"  切分kind总数={j(m['chunk_kinds'])}，各kind字节={j(m['chunk_bytes_by_kind'])}；最大块前三文件={j(dict(coarse))}。")
    if m['repo'] == 'cjson':
        lines.append('  C宏反例：cJSON.c:165–168的internal_malloc与:173–176的internal_realloc（_MSC_VER分支），context均误命名为function::CJSON_CDECL，取了调用约定宏而非函数名；源字节未丢，正文是否补偿未打分。定位见cjson/observations.md。')
    if m['repo'] == 'fmt':
        lines.append('  fmt续跑异常：resume1/resume2均退出2，日志只有“grp:format-h-dragon”（无栈），任务遗留leased；最终verify失败。原始完整模型JSON在run/host/raw/module_1.attempt-6.txt，组ID本身有定义，具体根因未定位。summary少记6次请求；网关与原始API总量一致。28个节点页的依赖说明在续跑后丢失（如nodes/os-impl-file.md），见fmt/observations.md；未手修。')
    if m['repo'] == 'fmt' and (not m['first_complete']):
        lines.append('  首轮文档呈现：first-docs/INDEX.md:227 原文“- 2 module page(s) are pending: module_1, module_3.”，此提示未列文件名/源码占比；首轮258发布单元、49页，两个缺失头文件各发布0单元。')
    if m['repo'] == 'fmt':
        lines.append('  宏切分反例：core.h:280空宏FMT_END_EXPORT在:928调用；context却登记为function，覆盖928–1755行并切74段（s0–s73）。core.h首轮最后缺3/612个disposition而失败（自动补齐上限2）。format.h首响应输入84550、输出49152（推理37374）截断；详见fmt/observations.md与run/raw/module_1-1.api.json，后续尝试全计账。')
lines += ['', 'INDEX 原文素材集中在 `$ROOT/runs/e6/index-excerpts.md`，每仓摘3—5行并标源文件行号；不作宣传改写。', '', '初始磁盘22 GiB、内存空闲36%；各仓开始的 memory_pressure 原输出与等待时长在 memory.json。建图和生成均串行；E3未读未改。大于10MB JSON已gzip（context/catalog留明文）；graph与API/阶段快照均有原件或.gz。', '', 'CBE 问题与边界：C/C++ 的 syntax_error 不等于生成失败；宏/预处理可能让声明切分变粗，具体每文件诊断和chunk分布见 context.json 与 metrics.json。没有宏展开对照，不能由这些计数单独判定语义切分准确度。没有语义打分，不能由verify证明所有文档事实正确。Java/Ruby的图定位缺口、缺能力与未解析/歧义目标已列明；多语言夹具另有前端失败，不把结构complete称为图完备。', '', 'CBE调用状态限制：calls.csv会先写API临时ok，fmt随后抛组ID异常而任务仍leased；不把ok标签当提交成功。这里照录最终CSV分布，各轮calls/state/summary/raw快照可核对；fmt的summary停在首轮，网关与原始API总量一致。', '', '核验：已读指定 verification skill；作者从清单重核输入sha256、从原件重算调用/token/比例/图质量/网关差值，verify为真实CLI。fmt的summary对账不一致已保留，其他数据核对见runs/e6/verification.json。独立验收由协调者接收时完成；本报告仅可交验。未做GitHub发布、上游许可搬入展示仓及polyglot许可声明（按任务写域与阶段边界留开源阶段）。', '']
missing = [r['name'] for r in inputs if r['name'] not in [m['repo'] for m in ms]]
lines.append('未做成/缺口：未完整或verify失败=' + (', '.join(problems) or '无') + '；未运行完或读数尚未收齐=' + (', '.join(missing) or '无') + '。')
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text('\n'.join(lines) + '\n')
print(REPORT, len(lines), 'lines')
