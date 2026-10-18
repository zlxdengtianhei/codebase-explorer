import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import pathlib, time, subprocess, os, json, gzip, shutil, hashlib, datetime
root = pathlib.Path(os.path.expandvars('$WORK'))
out = root / 'runs/e5/cbe-curl'
scripts = pathlib.Path(__file__).resolve().parent
py = root / 'codebase-explorer/.venv/bin/python'
env = os.environ.copy()
env.update(PYTHONPATH=str(root / 'eval-cbe2/src'), PYTHONDONTWRITEBYTECODE='1')
for _ in range(1440):
    if (out / 'generation.done').exists():
        break
    time.sleep(60)
else:
    raise RuntimeError('Finalizer polling limit exceeded')
with (out / 'usage-final.csv').open('w') as f, (out / 'usage-final.stderr').open('w') as err:
    subprocess.run(['magpie', 'usage', '--csv', '--last', '48h'], stdout=f, stderr=err, check=True, timeout=1200)
subprocess.run([str(py), str(scripts / 'analyze.py'), str(out / 'usage-final.csv')], env=env, check=True)
subprocess.run([str(py), str(scripts / 'diagnostics.py')], env=env, check=True)
subprocess.run([str(py), str(scripts / 'report.py')], env=env, check=True)
m = json.loads((out / 'metrics.json').read_text())
checks = {}
checks['api_identity'] = not m['gateway']['identity_anomalies']
checks['all_requests_in_phases'] = m['gateway_outside_phases'] == 0
checks['gateway_calls_count'] = m['gateway']['requests'] == m['calls']
checks['gateway_calls_tokens'] = all((v == 0 for v in m['gateway_minus_calls'].values()))
checks['gateway_raw_tokens'] = all((v == 0 for v in m['gateway_minus_raw'].values()))
checks['gateway_summary'] = all((v in (0, None, '0') for v in m['gateway_minus_summary'].values()))
checks['d53_partition'] = sum(m['layers']['semantic_breakdown'].values()) == m['layers']['semantic_tokens'] if m['layers'] else False
checks['freeze_ok'] = m['frozen_audit']['ok']
checks['source_tokens'] = m['layers']['source_tokens'] == m['frozen_audit']['accepted_source_tokens'] if m['layers'] else False
checks['max_two_resumes'] = sum((p['phase'].startswith('resume') for p in m['phases'])) <= 2
(out / 'verification.json').write_text(json.dumps(checks, indent=2))
print('checks', checks, flush=True)
compressed = []
for p in sorted((root / 'runs/e5').rglob('*.json')):
    if p.name in ('context.json', 'catalog.json'):
        continue
    if p.stat().st_size <= 10000000:
        continue
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    size = p.stat().st_size
    with p.open('rb') as src, gzip.open(str(p) + '.gz', 'wb', compresslevel=6) as dst:
        shutil.copyfileobj(src, dst)
    with gzip.open(str(p) + '.gz', 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == sha
    compressed.append({'path': str(p), 'bytes': size, 'sha256': sha, 'gzip_bytes': pathlib.Path(str(p) + '.gz').stat().st_size})
    p.unlink()
(out / 'compression.json').write_text(json.dumps(compressed, indent=2))
(scripts / 'finalization.done').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
