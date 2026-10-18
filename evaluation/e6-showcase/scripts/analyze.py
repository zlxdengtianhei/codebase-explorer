import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, csv, collections, decimal, re, datetime, hashlib, gzip, sys
from pathlib import Path
from cbe.docs import layer_metrics
from cbe.token_budget import count_text_tokens
from cbe.host_run import _identity_corrections, _answer_fallbacks
ROOT = Path(os.path.expandvars('$WORK'))
BASE = ROOT / 'runs/e6'

def load(p, default=None):
    if p.exists():
        return json.loads(p.read_text())
    if Path(str(p) + '.gz').exists():
        return json.loads(gzip.open(str(p) + '.gz', 'rt').read())
    return default

def dt(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
FIELDS = ('input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens', 'reasoning_tokens')

def totals(hits):
    return dict(requests=len(hits), **{k: sum((int(r.get(k) or 0) for r in hits)) for k in FIELDS}, cost_usd=str(sum((decimal.Decimal(r.get('cost_usd') or '0') for r in hits), decimal.Decimal(0))), http=dict(collections.Counter((r.get('status') for r in hits))), served_models=dict(collections.Counter((r.get('served_model') for r in hits))), requested_models=dict(collections.Counter((r.get('requested_model') for r in hits))), identity_anomalies=[r.get('request_id') for r in hits if r.get('swapped') == 'true' or r.get('served_model') not in ('zai/glm-5.3-flash', 'glm-5.3-flash') or r.get('requested_model') != 'zai/glm-5.3-flash'])

def failure_scope(snapshot, ctx, manifest, denominator, catalog=None):
    modules = {int(m['number']) + 1: m for m in snapshot.get('modules', [])}
    by_path = {m['path']: m for m in manifest}
    details = []
    all_paths = set()
    for tid, t in snapshot.get('tasks', {}).items():
        match = re.fullmatch('(?:module|repair)_(\\d+)', tid)
        if not match or t.get('status') == 'done':
            continue
        module = modules.get(int(match[1]), {})
        paths = module.get('files', [])
        all_paths.update(paths)
        tok = sum((by_path.get(p, {}).get('tokens') or 0 for p in paths))
        units = None if catalog is None else sum((any((r.get('path') in paths for r in u.get('ranges', []) if isinstance(r, dict))) for u in catalog.get('units', {}).values()))
        details.append(dict(task=tid, status=t.get('status'), files=paths, source_tokens=tok, source_share=tok / denominator, inventory_symbols=sum((len(snapshot.get('inventory', {}).get(p, {}).get('symbols', [])) for p in paths)), frozen_chunks=sum((c.get('path') in paths for c in ctx.get('chunks', []))), published_units=units, last_error=(t.get('errors') or [''])[-1]))
    tokens = sum((by_path.get(p, {}).get('tokens') or 0 for p in all_paths))
    return dict(tasks=details, files=sorted(all_paths), source_tokens=tokens, source_share=tokens / denominator)

def analyze(row):
    out = BASE / row['name']
    run = out / 'run'
    phases = load(out / 'phases.json', [])
    summary = load(run / 'summary.json', {})
    state = load(run / 'host/state.json', {})
    ctx = load(run / 'context.json', {})
    ctx.pop('graph', None)
    graph = load(out / 'graph.json', {})
    calls = list(csv.DictReader((run / 'calls.csv').open())) if (run / 'calls.csv').exists() else []
    first_calls = list(csv.DictReader((out / 'first-calls.csv').open())) if (out / 'first-calls.csv').exists() else []
    overwritten = [{'row': i, 'task': a['task'], 'attempt': a['attempt'], 'first_result': a['result'], 'final_result': b['result']} for i, (a, b) in enumerate(zip(first_calls, calls)) if a != b]
    hits = list(csv.DictReader((out / 'gateway-requests.csv').open())) if (out / 'gateway-requests.csv').exists() else []
    gateway = totals(hits)
    by_phase = {}
    summaries = {}
    deltas = {}
    for p in phases:
        label = p['phase']
        if label != 'first' and (not label.startswith('resume')):
            continue
        by_phase[label] = totals([r for r in hits if dt(p['start']) <= dt(r['time']) <= dt(p['end'])])
        summaries[label] = load(out / (label + '-summary.json'), {})
    delta = {k: gateway[k] - summary[v] if isinstance(summary.get(v), (int, float)) else None for k, v in {'requests': 'calls', 'input_tokens': 'input_tokens', 'cache_read_tokens': 'cache_tokens', 'output_tokens': 'output_tokens'}.items()}
    delta.update({k: str(decimal.Decimal(str(gateway[k])) - decimal.Decimal(str(summary[k]))) if isinstance(summary.get(k), (int, float, str)) else None for k in ('cost_usd', 'reasoning_tokens', 'cache_write_tokens')})
    layers = layer_metrics(run) if (run / 'catalog.json').exists() else None
    docs = sorted((run / 'docs').rglob('*.md'))
    stripped = sum((count_text_tokens(''.join((l for l in p.read_text().splitlines(keepends=True) if not re.match('^\\s*\\[f\\d+\\]:', l)))) for p in docs))
    tasks = state.get('tasks', {})
    flags = collections.Counter((f for t in tasks.values() for f in t.get('flags', [])))
    diag = collections.Counter((d.get('code') for d in ctx.get('diagnostics', [])))
    first = load(out / 'first-summary.json', {})
    try:
        verify = load(out / 'verify.log')
    except json.JSONDecodeError:
        verify = {'ok': False, 'raw': (out / 'verify.log').read_text()}
    for code in ('syntax_error', 'context_fallback', 'source_reassembly_fallback'):
        diag.setdefault(code, 0)
    if verify is None and (out / 'verify.log').exists():
        verify = {'raw': (out / 'verify.log').read_text()}
    graphs = {k: v for k, v in graph.items() if k not in ('nodes', 'edges')}
    rss = {}
    for p in phases:
        if p['phase'].startswith('graph'):
            text = (out / (p['phase'] + '.log')).read_text()
            m = re.search('(\\d+)\\s+maximum resident set size', text)
            rss[p['phase']] = int(m.group(1)) if m else None
    raw_tot = collections.Counter()
    variants = {}
    for p in list(out.glob('*-raw/*.api.json')) + list((run / 'raw').glob('*.api.json')):
        b = p.read_bytes()
        variants[p.name, hashlib.sha256(b).hexdigest()] = b
    for b in variants.values():
        d = json.loads(b)
        u = d.get('usage') or {}
        raw_tot.update({k: int(u.get(k) or 0) for k in ('input', 'output', 'cache')})
        raw_tot['reasoning'] += int(((d.get('provider_usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens') or 0)
    input_recheck = []
    chunk_by_file = {}
    error_files = {d.get('path') for d in ctx.get('diagnostics', []) if d.get('code') == 'syntax_error'}
    for f in ctx.get('files', []):
        path = f['path']
        chunks = [c for c in ctx.get('chunks', []) if c.get('path') == path]
        chunk_by_file[path] = {'syntax_error': path in error_files, 'chunks': len(chunks), 'kinds': dict(collections.Counter((c.get('kind') for c in chunks))), 'max_chunk_bytes': max((len(c.get('text', '').encode()) for c in chunks), default=0), 'max_chunk_lines': max((c.get('end_line', 0) - c.get('start_line', 0) + 1 for c in chunks), default=0)}
    for r in load(out / 'manifest.json', []):
        p = Path(row['copy']) / r['path']
        b = p.read_bytes()
        if len(b) != r['bytes'] or hashlib.sha256(b).hexdigest() != r['sha256']:
            input_recheck.append(r['path'])
    m = dict(repo=row['name'], input=row, phases=phases, graph_phases=[p for p in phases if p['phase'].startswith('graph')], graph_rss_bytes=rss, graph_nodes=len(graph.get('nodes', [])), graph_edges=len(graph.get('edges', [])), graph_files_without_nodes=sorted(set((f['path'] for f in graph.get('source_manifest', []))) - set((n.get('path') for n in graph.get('nodes', []) if n.get('path')))), graph_import_missing_path=sum((e.get('kind') == 'import' and (not e.get('path')) for e in graph.get('edges', []))), graph_import_empty_expression=sum((e.get('kind') == 'import' and e.get('expression') == '<empty>' for e in graph.get('edges', []))), graph_metadata=graphs, first_complete=first.get('status') == 'complete', complete=summary.get('status') == 'complete', verify=verify, resumes=sum((p['phase'].startswith('resume') for p in phases)), gateway=gateway, gateway_by_phase=by_phase, gateway_outside_phases=len(hits) - sum((v['requests'] for v in by_phase.values())), gateway_minus_summary=delta, summary_usage_fields={k: v for k, v in summary.items() if any((word in k for word in ('token', 'cost', 'call', 'priced')))}, summaries=summaries, first_results=dict(collections.Counter((r.get('result') for r in first_calls))), overwritten_first_call_labels=overwritten, calls=len(calls), retry_calls=sum((int(r.get('attempt') or 0) > 1 for r in calls)), attempts=dict(collections.Counter((r.get('attempt') for r in calls))), results=dict(collections.Counter((r.get('result') for r in calls))), task_kinds=dict(collections.Counter((t.get('kind') for t in tasks.values()))), task_flags=dict(flags), task_flag_reasons=dict(collections.Counter((f.split(': ', 1)[-1] for t in tasks.values() for f in t.get('flags', []) if not f.startswith(('answer_fallback:', 'id_corrected:'))))), answer_fallback=len(_answer_fallbacks(state)) if state else None, id_corrected=len(_identity_corrections(state)) if state else None, answer_fallback_details=_answer_fallbacks(state) if state else None, id_corrected_details=_identity_corrections(state) if state else None, units=summary.get('units'), pages=len(docs), layers=layers, source_denominator=row['tokens'], body_ratio=layers['model_body_tokens'] / row['tokens'] if layers else None, published_ratio=layers['semantic_tokens'] / row['tokens'] if layers else None, published_without_file_refs_tokens=stripped, diagnostics=dict(diag), chunk_by_file=chunk_by_file, chunk_bytes_by_kind={kind: sum((len(c.get('text', '').encode()) for c in ctx.get('chunks', []) if c.get('kind') == kind)) for kind in set((c.get('kind') for c in ctx.get('chunks', [])))}, chunk_kinds=dict(collections.Counter((c.get('kind') for c in ctx.get('chunks', [])))), context_status=(run / 'STATUS.md').read_text() if (run / 'STATUS.md').exists() else None, frozen_audit=load(out / 'frozen-audit.json'), memory=load(out / 'memory.json'), sizes={n: (run / n).stat().st_size if (run / n).exists() else None for n in ('context.json', 'catalog.json')}, failed_tasks={k: {x: t.get(x) for x in ('status', 'attempts', 'errors', 'flags')} for k, t in tasks.items() if t.get('status') != 'done'}, first_pending=first.get('pending'), first_failure_scope=failure_scope(load(out / 'first-state.json', {}), ctx, load(out / 'manifest.json', []), row['tokens'], load(out / 'first-catalog.json')), final_failure_scope=failure_scope(state, ctx, load(out / 'manifest.json', []), row['tokens'], load(run / 'catalog.json')), input_recheck_mismatches=input_recheck, raw_api_variants=len(variants), raw_totals=dict(raw_tot), gateway_minus_raw={k: gateway[g] - raw_tot[k] for k, g in [('input', 'input_tokens'), ('output', 'output_tokens'), ('cache', 'cache_read_tokens'), ('reasoning', 'reasoning_tokens')]})
    (out / 'metrics.json').write_text(json.dumps(m, indent=2, ensure_ascii=False))
    return m
if __name__ == '__main__':
    results = []
    for row in load(BASE / 'inputs.json', []):
        if (BASE / row['name'] / 'generation.done').exists():
            target = BASE / row['name'] / 'metrics.json'
            if '--force' not in sys.argv and target.exists() and (target.stat().st_mtime >= Path(__file__).stat().st_mtime) and (target.stat().st_mtime >= (BASE / row['name'] / 'generation.done').stat().st_mtime):
                m = load(target)
            else:
                m = analyze(row)
            results.append(m)
            print(m['repo'], m['complete'], m['gateway'], flush=True)
    (BASE / 'all-metrics.json').write_text(json.dumps(results, indent=2, ensure_ascii=False))
