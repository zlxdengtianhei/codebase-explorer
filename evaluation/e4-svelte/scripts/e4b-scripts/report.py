import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, statistics, decimal, collections, re
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
ms = json.loads((scripts / 'all-metrics.json').read_text())
complete = [m for m in ms if m['complete']]

def pct(x):
    return f'{x * 100:.3f}%' if x is not None else 'NA'

def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))

def f(x):
    return f'{x:,}' if isinstance(x, int) else f'{x:.6f}'.rstrip('0').rstrip('.') if isinstance(x, float) else str(x)

def flag_summary(flags):
    out = collections.Counter()
    for flag, count in flags.items():
        if flag.startswith(('answer_fallback:', 'id_corrected:')):
            continue
        category = flag.split(': ', 1)[1] if ': ' in flag else flag
        category = re.sub('\\[\\d+\\]', '[n]', category)
        out[category] += count
    return dict(out)
lines = ['# E4b：svelte 三次 CBE 生成与网关记账', '', f"完整运行 {len(complete)}/3；verify 通过 {sum((bool(m['verify'].get('ok')) for m in ms))}/3。下表区间只纳入 complete；费用来自网关 cost_usd，墙钟只记录。", '同输入与同模型的 CodeWiki 对照、覆盖度语义判分由主会话另行完成；本报告本身不宣称费用或质量优势。', '', f'代码 HEAD=`a87674ddf570b1cc9fd2c322982a83e011132668`；import=`{root}/eval-cbe2/src/cbe/__init__.py`。', f'输入=`{root}/eval/svelte-be645b4`；440 文件，531,705 o200k_base token；图=`runs/e1c/svelte-be645b4-default.graph.json`，只读复用。', f'产物根 `R{1}`—`R{3}`=`{root}/runs/e4/cbe-svelte-r<n>`；最终 docs、catalog、context 在各 `R<n>/run/`；指标 `R<n>/metrics.json`。', '启动前可用磁盘 32 GiB；r1/r2 并行，首个完成 verify 后起 r3，最多两次生成；PYTHONDONTWRITEBYTECODE=1。', '', '```sh', 'export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/eval-cbe2/src"', '# execute.py 只在内存读 environment MAGPIE_API_KEY 的 providers.magpie.apiKey 到 CBE_API_KEY', 'codebase-explorer/.venv/bin/python -m cbe generate "$PWD/eval/svelte-be645b4" --host api --jobs 2 --base-url http://127.0.0.1:3425/v1 --api-key-env CBE_API_KEY --model zai/glm-5.3-flash --graph "$PWD/runs/e1c/svelte-be645b4-default.graph.json" --run-dir "$R/run" --config "$R/api-config.json"', '# 唯一附加配置 extra_headers: X-Magpie-Agent=codebase-explorer, X-Magpie-Session=e4-cbe-svelte-r<n>', '# 未 complete 且冻结检查通过时原命令加 --resume 一次；verify: python -m cbe host verify --run-dir "$R/run"', 'magpie usage --csv --last 24h > runs/e4/e4b-scripts/usage.csv', '```', '实际命令经 `e4b-scripts/audited_cli.py` 调原 CLI：仅包装 plan 返回点，独立核 STATUS/context 与 440 文件逐字节重组后才允许下一步；不改 CBE 文件或生成参数。', '每次完整命令、首轮与续跑时间在 phases.json；stdout/stderr 在 first.log/resume.log；导入路径与提交在 e4b-scripts/r<n>-driver.log。', '']
lines += ['实际默认：推理 low、JSON 模式、输出上限 49,152、批目标/上限 8,000/10,000；额外配置仅上述两个请求头。逻辑任务类型 ' + '; '.join((f"r{m['run']}={js(m['task_kinds'])}" for m in ms)) + '；r3 sample review 触发默认 repair，语义审查记录见 metrics.json。']
lines += ['', '|运行/阶段|UTC 开始|UTC 结束|墙钟秒|返回码|', '|---|---|---|---:|---:|']
for m in ms:
    for p in m['phases']:
        lines.append(f"|r{m['run']}/{p['phase']}|{p['start']}|{p['end']}|{p['wall_seconds']:.3f}|{p['returncode']}|")
lines += ['', '|运行|首轮 complete / 最终 complete / verify|调用/重试调用；attempt 分布|结果分布|', '|---|---|---|---|']
for m in ms:
    lines.append(f"|r{m['run']}|{m['first_complete']}/{m['complete']}/{m['verify'].get('ok')}|{m['calls']}/{m['retry_calls']}；{js(m['attempts'])}|{js(m['results'])}|")
lines += ['', '|运行|answer_fallback / id_corrected|其余 task flags|tree 分区数|', '|---|---|---|---:|']
for m in ms:
    lines.append(f"|r{m['run']}|{len(m['answer_fallback'])}/{len(m['id_corrected'])}|{js(flag_summary(m['task_flags']))}|{m['regions']}|")
lines += ['其余 flags 按原因汇总计数，逐项原文见 metrics.json；answer_fallback/id_corrected 已单列，不在原因汇总中重复计数。']
lines += ['所有冻结检查记录在 frozen-audit.json：' + '; '.join((f"r{m['run']} files={m['frozen_audit'].get('files')}, fallback={m['frozen_audit']['source_reassembly_fallback']}, ok={m['frozen_audit']['ok']}" for m in ms)) + '；每次运行首个模型调用前读取 STATUS/context，拼回并与输入字节核对。', '', '|运行/阶段|请求|非缓存输入|缓存读|缓存写|输出|推理|cost_usd|HTTP|', '|---|---:|---:|---:|---:|---:|---:|---:|---|']
for m in ms:
    for phase, g in m['gateway_by_phase'].items():
        lines.append(f"|r{m['run']}/{phase}|{g['requests']}|{g['input_tokens']}|{g['cache_read_tokens']}|{g['cache_write_tokens']}|{g['output_tokens']}|{g['reasoning_tokens']}|{g['cost_usd']}|{js(g['status'])}|")
    lines.append(f"|r{m['run']}/总和|" + '|'.join((str(m['gateway'][k]) for k in ('requests', 'input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens', 'reasoning_tokens', 'cost_usd'))) + '|' + js(m['gateway']['status']) + '|')
lines += ['网关按 agent+唯一 session 筛，再核 first/resume 时间窗；原始导出 e4b-scripts/usage.csv，各次精确归属 gateway-requests.csv。', '请求 id 均核 zai/glm-5.3-flash；服务名 glm-5.3-flash 为同供应商路由名（无 zai/ 前缀）；identity_anomalies=' + js([m['gateway']['identity_anomalies'] for m in ms]) + '。', '网关 − summary（requests、input、cache-read、output；推理/缓存写/费用未被 summary 记录则 NA）：' + '; '.join((f"r{m['run']}={js(m['gateway_minus_summary'])}" for m in ms)) + '。', '网关 − calls.csv（input/output/cache）与 raw API（input/output/cache/reasoning）见 metrics.json：' + '; '.join((f"r{m['run']}={js(m['gateway_minus_calls'])}/{js(m['gateway_minus_raw'])}" for m in ms)) + '。', 'summary 的 priced_usd 若为 null 表示未配置价表，费用差值 NA；直接报网关 cost_usd，不另作未知价表折算。', '', '|运行|单元/Markdown 页|模型正文 token / 源码|发布 Markdown token / 源码|去 [fN]: 后 token|context/catalog 字节|', '|---|---:|---:|---:|---:|---:|']
for m in ms:
    l = m['layers'] or {}
    lines.append(f"|r{m['run']}|{m['units']}/{m['pages']}|{l.get('model_body_tokens', 'NA')}/{pct(m['body_ratio'])}|{l.get('semantic_tokens', 'NA')}/{pct(m['published_ratio'])}|{m['published_without_file_refs_tokens']}|{m['sizes']['context.json']}/{m['sizes']['catalog.json']}|")
lines += ['冻结图只报字节（UTF-8 紧凑 JSON、ensure_ascii=False；从比例中排除）：' + '; '.join((f"r{m['run']}={(m['layers'] or {}).get('frozen_graph_bytes')}" for m in ms)) + '。', 'D-53 七项（依次 model_body/signature_location/heading_anchor/relations/footer/index/node_text；合计等于发布 Markdown token）：']
for m in ms:
    lines.append(f"r{m['run']}: " + js((m['layers'] or {}).get('semantic_breakdown')) + '。')
lines += ['分母固定 531,705；模型正文为已发布单元 explain/summary/extras/uncertainties；发布比只含 docs/**/*.md；catalog/context 与冻结图字节不混入比例。', '', '|完整运行指标|最小—最大|中位数|', '|---|---:|---:|']
measures = [('网关请求', lambda m: m['gateway']['requests']), ('非缓存输入 token', lambda m: m['gateway']['input_tokens']), ('缓存读 token', lambda m: m['gateway']['cache_read_tokens']), ('输出 token', lambda m: m['gateway']['output_tokens']), ('推理 token', lambda m: m['gateway']['reasoning_tokens']), ('网关 cost_usd', lambda m: float(m['gateway']['cost_usd'])), ('单元数', lambda m: m['units']), ('页数', lambda m: m['pages']), ('模型正文 token', lambda m: m['layers']['model_body_tokens']), ('发布 Markdown token', lambda m: m['layers']['semantic_tokens']), ('模型正文/源码', lambda m: m['body_ratio']), ('发布 Markdown/源码', lambda m: m['published_ratio']), ('去引用行 Markdown token', lambda m: m['published_without_file_refs_tokens'])]
for label, get in measures:
    vals = [get(m) for m in complete]
    fmt = pct if '/源码' in label else f
    lines.append(f'|{label}|{fmt(min(vals))}—{fmt(max(vals))}|{fmt(statistics.median(vals))}|' if vals else f'|{label}|NA|NA|')
lines += ['', '三次最终均完整；首轮 partial 已在阶段表单列，区间采用含唯一续跑的各次总和。', '收尾压缩明细见 e4b-scripts/compression.json；每次 context/catalog 留明文（磁盘不足 10 GiB 时按任务规定仅留 r1 明文）。', '核验：已读指定 verification skill；输入 SHA、页/token 重算、分项合计、网关请求/时窗/模型/summary 差值与输出身份见 e4b-scripts/verification.json。作者自验可交主会话复核；不含文档语义真值与覆盖度独立验收。', 'CBE 记账问题：续跑重建 region 任务时复用 task/attempt，_mark_result 会改写 calls.csv 首个匹配行的结果标签；首轮快照 first-calls.csv 与 first-raw/ 已保留，受影响行见 metrics.json 的 overwritten_first_call_labels。表中 result/attempt 分布为 CBE 最终 CSV 原样读数，含此标签归属限制；网关/summary/原始 API 的 token 与请求数独立核对，不受此标签改写影响。', 'CBE 首轮具体失败：r1 module_31 的 dispositions 含占位 ID/未定义单元，module_56 缺 disposition，module_61 返回 inventory 外 ID；r2 module_43 缺少 100/100 inventory dispositions；r3 module_12 缺少 80/170 dispositions，module_58 引用未定义的占位单元。首轮完整缺失任务与错误分别见 metrics.json 的 first_pending/first_pending_errors，早期失败快照 e4b-scripts/first-failures.json；按规定各只续跑一次，最终未完成任务及错误见各 metrics.json 的 failed_tasks。', 'CBE 观察：默认 schema 重试/末轮规范化可能保留 answer_fallback、id_corrected 或其他标记，不能把 complete/verify 当作文档语义正确；具体任务、错误与标记在 metrics.json、host/state.json、raw/。']
path = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e4/e4b_result.md'))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text('\n'.join(lines) + '\n')
print(path, len(lines), 'lines')
