import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, csv, decimal, hashlib, datetime
from pathlib import Path
from cbe.token_budget import count_text_tokens
BASE = Path(os.path.expandvars('$WORK/runs/e6'))
ms = json.loads((BASE / 'all-metrics.json').read_text())
rows = []
for m in ms:
    out = BASE / m['repo']
    run = out / 'run'
    docs = list((run / 'docs').rglob('*.md'))
    l = m.get('layers') or {}
    summary = json.loads((run / 'summary.json').read_text())
    catalog = json.loads((run / 'catalog.json').read_text())
    rawhits = list(csv.DictReader((out / 'usage.csv').open()))
    hits = [r for r in rawhits if r.get('session') == 'e6-cbe-' + m['repo'] and r.get('agent') == 'codebase-explorer']
    checks = dict(input_hashes_unchanged=not m['input_recheck_mismatches'], polyglot_content_id=m['repo'] != 'polyglot' or hashlib.sha256(''.join((r['sha256'] + '  ' + r['path'] + '\n' for r in sorted(json.loads((out / 'manifest.json').read_text()), key=lambda r: r['path']))).encode()).hexdigest() == m['input']['sha'], source_denominator=l.get('source_tokens') == m['source_denominator'], markdown_recount=sum((count_text_tokens(p.read_text()) for p in docs)) == l.get('semantic_tokens'), breakdown_partition=sum(l.get('semantic_breakdown', {}).values()) == l.get('semantic_tokens'), pages_recount=len(docs) == m['pages'], units_recount=len(catalog.get('units', {})) == m['units'], frozen_audit=bool((m.get('frozen_audit') or {}).get('ok')), max_two_resumes=m['resumes'] <= 2, gateway_session_filter=len(hits) == m['gateway']['requests'], gateway_phase_partition=m['gateway_outside_phases'] == 0, gateway_models=not m['gateway']['identity_anomalies'], gateway_summary_known_fields=all((v == 0 for v in m['gateway_minus_summary'].values() if v is not None and (not isinstance(v, str)))), gateway_raw_usage=all((v == 0 for v in m['gateway_minus_raw'].values())), gateway_cost_recount=str(sum((decimal.Decimal(r.get('cost_usd') or '0') for r in hits), decimal.Decimal(0))) == m['gateway']['cost_usd'], complete_from_original=bool(m['complete']) == (summary.get('status') == 'complete'), verify_from_original=json.loads((out / 'verify.log').read_text()).get('ok') == m['verify'].get('ok'))
    rows.append(dict(repo=m['repo'], checks=checks, all_measurement_checks=all(checks.values()), complete=m['complete'], verify=m['verify'].get('ok'), metric_sha256=hashlib.sha256((out / 'metrics.json').read_bytes()).hexdigest()))
    print(m['repo'], checks, flush=True)
total = sum((decimal.Decimal(m['gateway']['cost_usd']) for m in ms), decimal.Decimal(0))
result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), repositories=rows, total_cost_usd=str(total), within_total_budget=total <= 2, scope='Author verification of frozen input, structural CLI outcomes, counters, token accounting and gateway reconciliation; semantic truth and independent acceptance not measured; coordinator receives artifacts for acceptance.')
(BASE / 'verification.json').write_text(json.dumps(result, indent=2))
