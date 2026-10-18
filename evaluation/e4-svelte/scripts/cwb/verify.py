"""Deterministic verification of available finished judge runs."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, csv, hashlib, datetime, re, collections
from pathlib import Path
R = Path(__file__).resolve().parent
labels = json.loads((R / 'svelte-leaf-labels.json').read_text())
expected = {x['path'] for x in labels['leaves']}
label_sha = hashlib.sha256((R / 'svelte-leaf-labels.json').read_bytes()).hexdigest()
assert label_sha == (R / 'labels-sha256.txt').read_text().strip()
checks = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'strict_leaf_only_label_read_scope_met': False, 'method_exception': 'Initial rubric expansion displayed parent requirements as well as leaves before labeling. No generated documentation or judgments were inspected before freezing; labels were not changed. Frozen JSON basis overstates leaf-only read scope; see final report.', 'labels_frozen': True, 'labels_created_utc': labels['created_utc'], 'labels_sha256': label_sha, 'leaf_count': len(expected), 'weights': dict(collections.Counter((x['weight'] for x in labels['leaves']))), 'runs': {}}
for kind in ['cbe-r1', 'codewiki-1', 'cbe-r2', 'codewiki-2']:
    if not (R / (kind + '-judged.json')).exists():
        continue
    raw = {p.stem: json.loads(p.read_text()) for p in (R / (kind + '-leaves')).glob('*.json')}
    assert set(raw) == expected
    assert all((type(v['evaluation']['score']) is int and v['evaluation']['score'] in (0, 1) for v in raw.values()))
    assert all((datetime.datetime.fromisoformat(v['start_utc']) > datetime.datetime.fromisoformat(labels['created_utc']) for v in raw.values()))
    audit = [json.loads(l) for l in (R / (kind + '-http.jsonl')).read_text().splitlines()]
    responses = [e for e in audit if e['phase'] == 'response' and e['leaf'] != 'probe']
    assert all((e['model'] == 'codex/gpt-6.1-sol' for e in audit))
    assert all((e.get('served_model') in ('gpt-6.1-sol', 'codex/gpt-6.1-sol', None) for e in responses))
    record = {'leaves': len(raw), 'NA': sum((v['evaluation'].get('NA', False) for v in raw.values())), 'retries': sum((v['evaluation'].get('retry_count', 0) for v in raw.values())), 'audited_responses': len(responses), 'all_starts_after_labels': True, 'identity_canonical': 'codex + gpt-6.1-sol; gateway literal served_model omits codex/ prefix'}
    req = R / (kind + '-requests.csv')
    if req.exists():
        rows = list(csv.DictReader(req.open()))
        ids = {e.get('response_id') for e in responses}
        scored = [r for r in rows if r['response_id'] in ids]
        assert len(scored) == len(responses)
        assert all((r['agent'] == 'codewikibench' and r['session'] == 'e4q-judge-' + kind and (r['requested_model'] == 'codex/gpt-6.1-sol') and (r['provider'] == 'codex') and (r['served_model'] == 'gpt-6.1-sol') and (r['swapped'] == 'false') for r in scored))
        gw = {k: sum((int(r[k] or 0) for r in scored)) for k in ['input_tokens', 'cache_read_tokens', 'output_tokens']}
        api = {'input_tokens': 0, 'cache_read_tokens': 0, 'output_tokens': 0}
        for e in responses:
            u = e.get('usage') or {}
            cache = (u.get('prompt_tokens_details') or {}).get('cached_tokens', 0) or 0
            api['input_tokens'] += u.get('prompt_tokens', 0) - cache
            api['cache_read_tokens'] += cache
            api['output_tokens'] += u.get('completion_tokens', 0)
        assert gw == api, (kind, gw, api)
        record.update(gateway_requests_matched=len(scored), gateway_api_token_totals_equal=True, gateway_tokens=gw, overhead_rows=len(rows) - len(scored))
    checks['runs'][kind] = record
secret = os.environ['MAGPIE_API_KEY'].encode()
hits = []
for p in R.rglob('*'):
    if p.is_file() and p.name not in ('verification.json',) and (p.stat().st_size < 20000000):
        data = p.read_bytes()
        if p.suffix == '.py':
            data = data.replace(b"['providers']['magpie']['apiKey']", b'CONFIG_SELECTOR')
        if secret and secret in data:
            hits.append(str(p.relative_to(R)))
assert not hits
checks['credential_scan'] = 'No credential matches after excluding literal configuration-selector identifiers in source files; scanned artifacts smaller than 20MB.'
(R / 'verification.json').write_text(json.dumps(checks, indent=2))
print(json.dumps(checks, indent=2))
