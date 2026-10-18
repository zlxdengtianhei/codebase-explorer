import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, pathlib, datetime
root = pathlib.Path(os.path.expandvars('$WORK'))
out = root / 'runs/e5/cbe-curl'
m = json.loads((out / 'metrics.json').read_text())
pre = json.loads((out / 'preflight.json').read_text())
a = m['frozen_audit']
g = m['gateway']
l = m['layers']
lines = []

def add(s=''):
    lines.append(s)
add('# E5a：curl 一次 CBE 生成与网关记账')
add(f"最终 complete={m['complete']}；verify={m['verify'].get('ok')}。网关请求 {g['requests']}，cost_usd={g['cost_usd']}。")
add('本报告核实生成、记账与结构读数；不包含文档语义质量、覆盖度判分或后续问答。')
add('')
add('HEAD=a87674ddf570b1cc9fd2c322982a83e011132668；import=eval-cbe2/src/cbe/__init__.py（driver.log 原始输出）。')
add(f"输入 eval/curl-2c04412：{pre['input_files']} 文件、{pre['input_bytes']} bytes，manifest SHA 全匹配。")
add(f"manifest SHA256={pre['manifest_sha256']}。")
add(f"图复用 runs/e1d/curl.graph.json.gz，不重建；解压 {pre['graph_bytes']} bytes。")
add(f"graph SHA256={pre['graph_sha256']}；gzip SHA256={pre['graph_gzip_sha256']}。")
add('开跑可用磁盘 22 GiB；memory_pressure 初次36%、预检33%、重开36%，均≥15%，无需等待。')
add('')
add('```sh')
add('PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/eval-cbe2/src" codebase-explorer/.venv/bin/python runs/e5/e5a-scripts/audited_cli.py generate "$PWD/eval/curl-2c04412" --host api --jobs 2 --base-url http://127.0.0.1:3425/v1 --api-key-env CBE_API_KEY --model zai/glm-5.3-flash --graph "$PWD/runs/e5/cbe-curl/graph.json" --run-dir "$PWD/runs/e5/cbe-curl/run" --config "$PWD/runs/e5/cbe-curl/api-config.json"')
add('# 续跑仅加 --resume；verify: python -m cbe host verify --run-dir $WORK/runs/e5/cbe-curl/run')
add('```')
add('配置只有 extra_headers：X-Magpie-Agent=codebase-explorer，X-Magpie-Session=e5-cbe-curl；其余默认。')
add('密钥从 environment MAGPIE_API_KEY 的 providers.magpie.apiKey 只读到进程环境；未落盘或打印。')
add('')
add(f"冻结核对：{a['files']} 个 CBE 接收源码逐字节重组成功，fallback={a['source_reassembly_fallback']}、mismatches={a['input_mismatches']}。")
add('最初审计误要求重组所有506个输入，plan后中止、未调模型；plan-abort/abort-usage.csv 核 session 请求0。')
add('按协调者 msg_da1fd97864ae 改为全部485个接收源码，保存原审计并移除中止run后重开首轮；不占续跑额度。')
add('另外21个非源码输入被默认发现规则排除；逐项原因见 frozen-audit.json 的 excluded_manifest_files。')
add(f"双分母：全输入 1,741,311；实际485个接收源码 {a['accepted_source_tokens']} o200k_base token。")
add('')
add('|阶段|UTC开始|UTC结束|墙钟秒|返回码|')
add('|---|---|---|---:|---:|')
for p in m['phases']:
    add(f"|{p['phase']}|{p['start']}|{p['end']}|{p['wall_seconds']:.3f}|{p['returncode']}|")
for name, s in m['phase_summary'].items():
    add(f"{name}：status={s.get('status')}；stopped={s.get('stopped')}；usage_complete={s.get('usage_complete')}；pending数={len(s.get('pending', []))}。")
add(f"首轮 complete=False，pending共{len(m['first_pending'])}项；完整列表metrics.json first_pending。最终失败任务={m['failed_tasks']}。")
add('首轮 module_91 attempt2 遇HTTP429而停；同轮module_88（lib/mime.c）有虚构ID/缺disposition，resume1已恢复。')
add('resume1只剩module_148（src/tool_dirhie.c）的grp ID前缀错误；resume2恢复后重生成分区树，最终无失败任务。')
add(f"生成总墙钟={sum((p['wall_seconds'] for p in m['phases'] if p['phase'] != 'verify')):.3f}秒，约6小时59分；只记录，不作机器间速度比较。")
add(f"verify失败项={[c for c in m['verify'].get('checks', []) if not c.get('ok')]}；完整输出verify.log。")
add('各轮 summary、state、calls、raw 快照保留；续跑不得改参数或手修产物。')
add('')
add(f"调用 {m['calls']}；重试调用 {m['retry_calls']}；attempt分布={m['attempts']}；结果分布={m['results']}。")
import collections
flag_reasons = collections.Counter()
for flag, n in m['task_flags'].items():
    if flag.startswith(('answer_fallback:', 'id_corrected:')):
        continue
    flag_reasons[flag.split(': ', 1)[-1]] += n
add(f"answer_fallback={len(m['answer_fallback'])}；id_corrected={len(m['id_corrected'])}；其余flags按原因汇总={dict(flag_reasons)}。逐项原文和任务定位见metrics.json。")
add(f"任务类型={m['task_kinds']}；语义review原样={m['semantic_review']}。")
add(f"单元={m['units']}；Markdown页={m['pages']}；tree分区数={m['regions']}；分区结构见metrics.json aggregation。")
add('')
add('|阶段|请求|非缓存输入|缓存读|缓存写|输出|推理|cost_usd|HTTP|')
add('|---|---:|---:|---:|---:|---:|---:|---:|---|')
for phase, t in list(m['gateway_by_phase'].items()) + [('总和', g)]:
    add('|' + phase + '|' + '|'.join((str(t[k]) for k in ('requests', 'input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens', 'reasoning_tokens', 'cost_usd', 'status'))) + '|')
add(f"请求模型={g['requested_models']}；实际服务模型={g['served_models']}；身份异常={g['identity_anomalies']}。")
add('HTTP 429 的 served_model 为空，表示未服务而非已换模型；该请求账单 token=0、cost_usd为空，求和按0但不另行估费。')
add(f"网关−summary={m['gateway_minus_summary']}；未记费用/推理/缓存写字段差值为NA。")
add('summary因HTTP429的usage缺失而usage_complete=False、cache_tokens=null；observed_cache_tokens=2052480，与网关缓存读差0。')
add('各阶段累计网关−对应summary（请求/非缓存输入/输出）均为0；缓存读−observed_cache_tokens也逐阶段为0，原cache_tokens=null仍记NA（phase-summary-differences.json）。')
add(f"网关−calls={m['gateway_minus_calls']}；网关−去重raw API={m['gateway_minus_raw']}；阶段窗外请求={m['gateway_outside_phases']}。")
add('usage-final.csv 为原始导出，gateway-requests.csv 按agent/session筛选；UTC时窗逐轮归属。每约1小时累计在进度文件。')
add('')
if l:
    add(f"模型正文={l['model_body_tokens']} token；发布Markdown={l['semantic_tokens']} token；去[fN]:行={m['published_without_file_refs_tokens']} token。")
    for d, r in m['ratios_by_denominator'].items():
        add(f"分母{d}：模型正文/源码={100 * r['model_body_ratio']:.3f}%；发布Markdown/源码={100 * r['published_ratio']:.3f}%。")
    add(f"D-53七项={l['semantic_breakdown']}；合计={sum(l['semantic_breakdown'].values())}（等于发布Markdown）。")
    add(f"确定层仅catalog：{l['catalog_tokens']} token；冻结图只报紧凑UTF-8 JSON字节={l['frozen_graph_bytes']}。")
add(f"context/catalog字节={m['sizes']}；两者留明文供后续问答。")
add(f"诊断计数={m['diagnostic_counts']}；各诊断文件清单见metrics.json diagnostic_files。")
diag = json.loads((out / 'diagnostics-analysis.json').read_text())
add('context_fallback=0、source_reassembly_fallback=0；复用图另有reaching_defs_truncated=1（50000边上限，省略486150条），沿用E1d，未重建。')
add(f"syntax_error涉及{diag['syntax_error_files']}个文件；切分统计={diag['group_stats']}。")
add('错误组15个文件只含residual，其余138个仍有细分chunk；共10248个chunk，源码覆盖逐字节不丢失。未跑无宏/替代解析器对照，不能归因或声称切分无影响。')
add('')
add('产物根：$WORK/runs/e5/cbe-curl；docs/catalog/context 位于 run/。')
add('脚本 runs/e5/e5a-scripts/；phases.json 保存无密钥命令与各轮UTC；verify.log 为原始verify输出。')
add('大于10MB的JSON收尾gzip，context.json与catalog.json留明文；压缩清单 compression.json；graph.json现为graph.json.gz，可按需解压。')
add('收尾df可用8.2 GiB；按要求只压缩本写域内大JSON，context/catalog保留明文，未触碰其他实验目录。')
add('CBE记账问题：resume2重用region task/attempt后，改写resume1已成功的4行result为schema_error（region0006/0009/0010/0013，attempt1）；详见call-label-differences.json。')
add('调用/attempt/result分布按CBE最终CSV原样报，标签有上述归属限制；各轮calls/raw快照已保留，网关与token总账不受影响。')
add('verification-independent.json：19项作者自验全通过；输入SHA与token、Markdown与去引用token由独立tiktoken从原件重算；主会话可独立复核。')
add('未做：语义真值与问答测评，依任务包另派；不得用complete/verify替代语义正确结论。')
path = pathlib.Path(os.path.expandvars('$TASK_DIR/scratch/opt_e5/e5a_result.md'))
path.write_text('\n'.join(lines) + '\n')
print(path, len(lines))
