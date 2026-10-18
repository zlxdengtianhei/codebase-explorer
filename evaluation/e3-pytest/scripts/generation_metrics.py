"""Gateway attribution by E3 session; D-53 storage/body measurements."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import collections, csv, datetime, decimal, hashlib, json, re, subprocess
from pathlib import Path
from cbe.docs import layer_metrics
from cbe.token_budget import count_text_tokens
from cbe.host_run import _identity_corrections, _answer_fallbacks, _index_only_fills
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
O = E / 'cbe-pytest'
run = O / 'run'
with (O / 'usage.csv').open('w') as out, (O / 'usage.stderr').open('w') as err:
    subprocess.run(['magpie', 'usage', '--csv', '--last', '24h'], stdout=out, stderr=err, check=True)
rows = list(csv.DictReader((O / 'usage.csv').open()))
hits = [r for r in rows if r.get('session') == 'e3-cbe-pytest' and r.get('agent') == 'codebase-explorer']
with (O / 'gateway-requests.csv').open('w') as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(hits)
fields = ('input_tokens', 'cache_read_tokens', 'cache_write_tokens', 'output_tokens', 'reasoning_tokens')
gateway = {'requests': len(hits), **{k: sum((int(r.get(k) or 0) for r in hits)) for k in fields}, 'cost_usd': str(sum((decimal.Decimal(r.get('cost_usd') or '0') for r in hits), decimal.Decimal(0))), 'statuses': dict(collections.Counter((r.get('status') for r in hits))), 'served_models': dict(collections.Counter((r.get('served_model') for r in hits))), 'unknown_served': [r['request_id'] for r in hits if not r.get('served_model')], 'identity_anomalies': [r['request_id'] for r in hits if r.get('swapped') == 'true' or (r.get('served_model') and r.get('served_model') not in ('zai/glm-5.3-flash', 'glm-5.3-flash')) or r.get('requested_model') != 'zai/glm-5.3-flash']}
summary = json.loads((run / 'summary.json').read_text()) if (run / 'summary.json').exists() else None
phases = json.loads((O / 'phases.json').read_text())
gateway_by_phase = {}

def dt(s):
    return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
for phase in phases:
    if phase['phase'] not in ('first', 'resume', 'resume2'):
        continue
    selected = [r for r in hits if dt(phase['start']) <= dt(r['time']) <= dt(phase['end'])]
    gateway_by_phase[phase['phase']] = {'requests': len(selected), **{k: sum((int(r.get(k) or 0) for r in selected)) for k in fields}, 'cost_usd': str(sum((decimal.Decimal(r.get('cost_usd') or '0') for r in selected), decimal.Decimal(0))), 'wall_seconds': phase['wall_seconds']}
state = json.loads((run / 'host/state.json').read_text())
calls = list(csv.DictReader((run / 'calls.csv').open())) if (run / 'calls.csv').exists() else []
layers = layer_metrics(run) if (run / 'catalog.json').exists() else None
docs = list((run / 'docs').rglob('*.md'))
stripped = sum((count_text_tokens(''.join((line for line in p.read_text().splitlines(keepends=True) if not re.match('^\\s*\\[f\\d+\\]:', line)))) for p in docs)) if docs else None
source_files = {p.relative_to(R / 'eval/pytest-5989efe').as_posix() for p in (R / 'eval/pytest-5989efe').rglob('*') if p.is_file()}
context = json.loads((run / 'context.json').read_text())
frozen = {row['path'] for row in context['files']}
first_calls = list(csv.DictReader((O / 'first-calls.csv').open())) if (O / 'first-calls.csv').exists() else []
overwritten_labels = [{'row': i, 'task': a['task'], 'attempt': a['attempt'], 'first_result': a['result'], 'final_result': b['result']} for i, (a, b) in enumerate(zip(first_calls, calls)) if a != b]
first = json.loads((O / 'first-summary.json').read_text()) if (O / 'first-summary.json').exists() else None
m = {'commit': 'a87674ddf570b1cc9fd2c322982a83e011132668', 'first_complete': bool(first and first.get('status') == 'complete'), 'complete': bool(summary and summary.get('status') == 'complete'), 'phases': json.loads((O / 'phases.json').read_text()), 'summary': summary, 'frozen_audit': json.loads((O / 'frozen-audit.json').read_text()), 'input_files': len(source_files), 'frozen_files': len(frozen), 'outside_frozen_inventory': sorted(source_files - frozen), 'source_denominator': 752827, 'gateway': gateway, 'gateway_by_phase': gateway_by_phase, 'gateway_minus_summary': {key: gateway[key] - summary[skey] if summary and isinstance(summary.get(skey), (int, float)) else None for key, skey in [('requests', 'calls'), ('input_tokens', 'input_tokens'), ('cache_read_tokens', 'cache_tokens'), ('output_tokens', 'output_tokens')]}, 'layers': layers, 'body_ratio': layers['model_body_tokens'] / 752827 if layers else None, 'published_ratio': layers['semantic_tokens'] / 752827 if layers else None, 'published_without_file_refs_tokens': stripped, 'published_without_file_refs_ratio': stripped / 752827 if stripped is not None else None, 'calls': len(calls), 'results': dict(collections.Counter((row['result'] for row in calls))), 'first_results_snapshot': dict(collections.Counter((row['result'] for row in first_calls))), 'overwritten_first_call_labels': overwritten_labels, 'attempts': dict(collections.Counter((row['attempt'] for row in calls))), 'logical_tasks_called': len({row['task'] for row in calls}), 'retry_calls': sum((int(row['attempt']) > 1 for row in calls)), 'task_count': len(state['tasks']), 'regions': len(state.get('aggregation', {}).get('regions', [])), 'aggregation_limits': state.get('aggregation', {}).get('limits', {}), 'task_status': dict(collections.Counter((t['status'] for t in state['tasks'].values()))), 'unfinished_tasks': {k: {field: t.get(field) for field in ('status', 'attempts', 'errors', 'flags')} for k, t in state['tasks'].items() if t['status'] != 'done'}, 'task_flags': dict(collections.Counter((flag for t in state['tasks'].values() for flag in t.get('flags', [])))), 'index_only_filled': _index_only_fills(state), 'id_corrected': _identity_corrections(state), 'answer_fallback': _answer_fallbacks(state), 'published_pages': len(docs), 'sizes': {n: (run / n).stat().st_size if (run / n).exists() else None for n in ['context.json', 'catalog.json']}, 'verify_output': (O / 'verify-final-d67.log').read_text() if (O / 'verify-final-d67.log').exists() else (O / 'verify.log').read_text() if (O / 'verify.log').exists() else None}
(O / 'metrics.json').write_text(json.dumps(m, indent=2))
print(json.dumps({k: v for k, v in m.items() if k in ['complete', 'first_complete', 'gateway', 'gateway_minus_summary', 'body_ratio', 'published_ratio', 'outside_frozen_inventory']}, indent=2))
