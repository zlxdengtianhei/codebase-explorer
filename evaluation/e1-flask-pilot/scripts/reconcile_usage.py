"""Reconcile exported Magpie usage without inventing client attribution."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import csv, json, datetime, collections, sys
from pathlib import Path
ROOT = Path(os.path.expandvars('$WORK/runs/e1'))
rows = list(csv.DictReader(open(sys.argv[1])))

def dt(t):
    return datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
fields = ['input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_write_tokens', 'reasoning_tokens', 'cost_usd']

def totals(rs):
    d = {'requests': len(rs), **{k: sum((float(r.get(k) or 0) for r in rs)) for k in fields}}
    d['served_model_unknown'] = sum((not r.get('served_model') for r in rs))
    d['requested_served_match'] = all((r['requested_model'] == r['provider'] + '/' + r['served_model'] for r in rs if r.get('served_model')))
    d['model_mismatches'] = [{'request_id': r['request_id'], 'asked': r['requested_model'], 'provider': r['provider'], 'served': r['served_model']} for r in rs if r.get('served_model') and r['requested_model'] != r['provider'] + '/' + r['served_model']]
    d['statuses'] = dict(collections.Counter((r['status'] for r in rs)))
    d['swapped'] = dict(collections.Counter((r['swapped'] for r in rs)))
    d['full_prompt_tokens'] = d['input_tokens'] + d['cache_read_tokens'] + d['cache_write_tokens']
    return d
probe_path = ROOT / 'attribution-probe.json'
probe = json.loads(probe_path.read_text()) if probe_path.exists() else {}

def is_probe(r):
    return bool(probe.get('response_id') and r.get('response_id') == probe['response_id']) or r.get('agent', '').startswith('codewiki-e1a-probe')
probe_rows = [r for r in rows if is_probe(r)]
summary = {'attribution_probe': {'receipt': probe, 'gateway_matches': [{k: r.get(k) for k in ['time', 'agent', 'session', 'response_id', 'requested_model', 'provider', 'served_model', 'input_tokens', 'output_tokens', 'reasoning_tokens', 'cache_read_tokens', 'cost_usd', 'status']} for r in probe_rows]}} if probe else {}
for kind in ['cbe', 'codewiki']:
    p = ROOT / 'cwb' / f'{kind}-receipt.json'
    if not p.exists():
        continue
    rec = json.loads(p.read_text())
    a, b = (dt(rec['start_utc']), dt(rec['end_utc']))
    window = [r for r in rows if a <= dt(r['time']) <= b and r['requested_model'] == rec['model']]
    selected = [r for r in window if r['agent'] == 'pydantic-ai']
    summary[kind + '_judge'] = {'window': [a.isoformat(), b.isoformat()], 'pydantic_ai': totals(selected), 'other_agents': dict(collections.Counter((r['agent'] for r in window if r['agent'] != 'pydantic-ai')))}
    with (ROOT / 'cwb' / f'{kind}-judge-requests.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(sorted(selected, key=lambda r: r['time']))
p = ROOT / 'codewiki-receipt.json'
if p.exists():
    rec = json.loads(p.read_text())
    windows = [(dt(x['start_utc']), dt(x['end_utc'])) for x in rec['attempts'] if x.get('entered_generation', True)]
    window = [r for r in rows if r['requested_model'] == 'zai/glm-5.3-flash' and (not is_probe(r)) and any((a <= dt(r['time']) <= b for a, b in windows))]
    summary['codewiki_generation'] = {'windows': [(a.isoformat(), b.isoformat()) for a, b in windows], 'all_model_window': totals(window), 'by_agent': {agent: totals([r for r in window if r['agent'] == agent]) for agent in sorted({r['agent'] for r in window})}, 'raw_OpenAI_attribution': 'ambiguous if other raw OpenAI callers overlap; pydantic-ai documentation client is separate from codebase-explorer and OpenAI'}
    with (ROOT / 'codewiki-window-requests.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(sorted(window, key=lambda r: r['time']))
(ROOT / 'accounting-summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
