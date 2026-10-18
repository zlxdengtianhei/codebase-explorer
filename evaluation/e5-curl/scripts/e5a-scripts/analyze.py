import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, csv, collections, decimal, re, datetime, hashlib, sys
from pathlib import Path
from cbe.docs import layer_metrics
from cbe.token_budget import count_text_tokens
from cbe.host_run import _identity_corrections, _answer_fallbacks
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
usage_path = Path(sys.argv[1]) if len(sys.argv) > 1 else scripts / 'usage.csv'
rows = list(csv.DictReader(usage_path.open()))
fields = ('input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens', 'reasoning_tokens')

def dt(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))

def totals(hits):
    return {'requests': len(hits), **{k: sum((int(r.get(k) or 0) for r in hits)) for k in fields}, 'cost_usd': str(sum((decimal.Decimal(r.get('cost_usd') or '0') for r in hits), decimal.Decimal(0))), 'status': dict(collections.Counter((r.get('status') for r in hits))), 'served_models': dict(collections.Counter((r.get('served_model') for r in hits))), 'requested_models': dict(collections.Counter((r.get('requested_model') for r in hits))), 'identity_anomalies': [r['request_id'] for r in hits if r.get('swapped') == 'true' or (r.get('status') == '200' and r.get('served_model') not in ('zai/glm-5.3-flash', 'glm-5.3-flash')) or r.get('requested_model') != 'zai/glm-5.3-flash']}
all_metrics = []
for n in (1,):
    out = root / 'runs/e5/cbe-curl'
    run = out / 'run'
    phases = json.loads((out / 'phases.json').read_text())
    state = json.loads((run / 'host/state.json').read_text())
    summary = json.loads((run / 'summary.json').read_text()) if (run / 'summary.json').exists() else None
    session = 'e5-cbe-curl'
    hits = [r for r in rows if r.get('session') == session and r.get('agent') == 'codebase-explorer']
    with (out / 'gateway-requests.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(hits)
    per_phase = {}
    for p in phases:
        if p['phase'] in ('first', 'resume1', 'resume2'):
            selected = [r for r in hits if dt(p['start']) <= dt(r['time']) <= dt(p['end'])]
            per_phase[p['phase']] = totals(selected)
    calls = list(csv.DictReader((run / 'calls.csv').open())) if (run / 'calls.csv').exists() else []
    raw_totals = collections.Counter()
    raw_models = collections.Counter()
    raw_variants = {}
    for path in list(out.glob('*-raw/*.api.json')) + list((run / 'raw').glob('*.api.json')):
        payload = path.read_bytes()
        raw_variants[path.name, hashlib.sha256(payload).hexdigest()] = payload
    for payload in raw_variants.values():
        r = json.loads(payload)
        raw_models[r.get('actual_model', '')] += 1
        raw_totals.update({k: int((r.get('usage') or {}).get(k) or 0) for k in ('input', 'output', 'cache')})
        raw_totals['reasoning'] += int(((r.get('provider_usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens') or 0)
    gateway = totals(hits)
    layers = layer_metrics(run) if (run / 'catalog.json').exists() else None
    docs = list((run / 'docs').rglob('*.md'))
    stripped = sum((count_text_tokens(''.join((line for line in p.read_text().splitlines(keepends=True) if not re.match('^\\s*\\[f\\d+\\]:', line)))) for p in docs)) if docs else None
    first_call_rows = list(csv.DictReader((out / 'first-calls.csv').open())) if (out / 'first-calls.csv').exists() else []
    overwritten_call_labels = [{'row': i, 'task': a['task'], 'attempt': a['attempt'], 'first_result': a['result'], 'final_result': b['result']} for i, (a, b) in enumerate(zip(first_call_rows, calls)) if a != b]
    call_totals = {k: sum((int(r.get(k) or 0) for r in calls)) for k in ('input_tokens', 'output_tokens', 'cache_tokens')}
    flags = collections.Counter((flag for t in state['tasks'].values() for flag in t.get('flags', [])))
    verify = json.loads((out / 'verify.log').read_text())
    final_complete = bool(summary and summary.get('status') == 'complete')
    first_summary = json.loads((out / 'first-summary.json').read_text()) if (out / 'first-summary.json').exists() else None
    summary_delta = None
    if summary:
        mapping = {'requests': 'calls', 'input_tokens': 'input_tokens', 'cache_read_tokens': 'cache_tokens', 'output_tokens': 'output_tokens'}
        summary_delta = {k: gateway[k] - summary[v] if isinstance(summary.get(v), (int, float)) else None for k, v in mapping.items()}
        for key in ('reasoning_tokens', 'cache_write_tokens', 'cost_usd'):
            summary_delta[key] = str(decimal.Decimal(str(gateway[key])) - decimal.Decimal(str(summary[key]))) if isinstance(summary.get(key), (int, float, str)) else None
    first_state = json.loads((out / 'first-state.json').read_text()) if (out / 'first-state.json').exists() else state
    m = {'run': n, 'phases': phases, 'first_complete': bool(first_summary and first_summary.get('status') == 'complete'), 'first_pending': first_summary.get('pending', []) if first_summary else None, 'first_pending_errors': {k: first_state['tasks'].get(k, {}).get('errors', []) for k in (first_summary or {}).get('pending', [])}, 'complete': final_complete, 'verify': verify, 'gateway': gateway, 'gateway_by_phase': per_phase, 'gateway_outside_phases': len(hits) - sum((v['requests'] for v in per_phase.values())), 'gateway_minus_summary': summary_delta, 'summary_usage_fields': {k: summary[k] for k in summary if any((word in k for word in ('token', 'cost', 'call')))} if summary else None, 'calls': len(calls), 'calls_tokens': call_totals, 'gateway_minus_calls': {k: gateway[g] - call_totals[k] for k, g in [('input_tokens', 'input_tokens'), ('output_tokens', 'output_tokens'), ('cache_tokens', 'cache_read_tokens')]}, 'raw_totals': dict(raw_totals), 'raw_api_variants': len(raw_variants), 'raw_actual_models': dict(raw_models), 'gateway_minus_raw': {k: gateway[g] - raw_totals[k] for k, g in [('input', 'input_tokens'), ('output', 'output_tokens'), ('cache', 'cache_read_tokens'), ('reasoning', 'reasoning_tokens')]}, 'results': dict(collections.Counter((r['result'] for r in calls))), 'overwritten_first_call_labels': overwritten_call_labels, 'first_results_snapshot': dict(collections.Counter((r['result'] for r in first_call_rows))), 'attempts': dict(collections.Counter((r['attempt'] for r in calls))), 'retry_calls': sum((int(r['attempt']) > 1 for r in calls)), 'logical_tasks_called': len(set((r['task'] for r in calls))), 'task_kinds': dict(collections.Counter((t['kind'] for t in state['tasks'].values()))), 'semantic_review': summary.get('semantic_review') if summary else None, 'task_status': dict(collections.Counter((t['status'] for t in state['tasks'].values()))), 'failed_tasks': {k: {x: t.get(x) for x in ('attempts', 'errors', 'flags')} for k, t in state['tasks'].items() if t['status'] != 'done'}, 'task_flags': dict(flags), 'id_corrected': _identity_corrections(state), 'answer_fallback': _answer_fallbacks(state), 'units': summary.get('units') if summary else None, 'pages': len(docs), 'layers': layers, 'published_without_file_refs_tokens': stripped, 'source_denominator': 1741311, 'sizes': {name: (run / name).stat().st_size if (run / name).exists() else None for name in ('context.json', 'catalog.json')}, 'aggregation': state.get('aggregation', {}), 'regions': len(state.get('aggregation', {}).get('regions', [])), 'frozen_audit': json.loads((out / 'frozen-audit.json').read_text())}
    m['phase_summary'] = {p['phase']: json.loads((out / (p['phase'] + '-summary.json')).read_text()) for p in phases if p['phase'] != 'verify' and (out / (p['phase'] + '-summary.json')).exists()}
    context = json.loads((run / 'context.json').read_text())
    diagnostics = context.get('diagnostics', [])
    m['diagnostic_counts'] = dict(collections.Counter((d.get('code') for d in diagnostics)))
    m['diagnostic_files'] = {code: sorted(set((d.get('path', '') for d in diagnostics if d.get('code') == code))) for code in m['diagnostic_counts']}
    accepted = m['frozen_audit']['accepted_source_tokens']
    m['ratios_by_denominator'] = {str(d): {'model_body_ratio': layers['model_body_tokens'] / d, 'published_ratio': layers['semantic_tokens'] / d} for d in (1741311, accepted)} if layers else None
    (out / 'metrics.json').write_text(json.dumps(m, ensure_ascii=False, indent=2))
    all_metrics.append(m)
    print(n, 'complete', final_complete, 'gateway', gateway, 'delta', summary_delta, flush=True)
(scripts / 'all-metrics.json').write_text(json.dumps(all_metrics, ensure_ascii=False, indent=2))
