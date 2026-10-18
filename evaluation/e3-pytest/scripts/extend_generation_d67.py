"""D-67: after the already-running first resume, allow one unchanged second resume."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
O = E / 'cbe-pytest'
run = O / 'run'
for _ in range(2880):
    if (O / 'generation.done').exists():
        break
    time.sleep(30)
else:
    raise TimeoutError('First resume did not settle within24h')
phases = json.loads((O / 'phases.json').read_text())
summary = run / 'summary.json'
if summary.exists():
    shutil.copy2(summary, O / 'resume1-summary.json')
for src in [run / 'calls.csv', *(run / 'raw').glob('*')]:
    if not src.is_file():
        continue
    dest = O / 'resume1-calls.csv' if src.name == 'calls.csv' else O / 'resume1-raw' / src.name
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(src, dest)
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(R / 'eval-cbe2/src')}
env['CBE_API_KEY'] = os.environ['MAGPIE_API_KEY']
py = str(R / 'codebase-explorer/.venv/bin/python')
subprocess.run([py, '-c', 'import cbe;print(cbe.__file__)'], env=env, check=True)
head = subprocess.check_output(['git', '-C', str(R / 'eval-cbe2'), 'rev-parse', 'HEAD'], text=True).strip()
print(head, flush=True)
assert head.startswith('a87674d')

def execute(name, args):
    start = datetime.datetime.now(datetime.timezone.utc)
    t = time.monotonic()
    with (O / (name + '.log')).open('w') as log:
        rc = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    phases.append({'phase': name, 'start': start.isoformat(), 'end': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'wall_seconds': time.monotonic() - t, 'returncode': rc, 'command': args})
    (O / 'phases.json').write_text(json.dumps(phases, indent=2))
complete = summary.exists() and json.loads(summary.read_text()).get('status') == 'complete'
if not complete:
    assert sum((p['phase'] in ('resume', 'resume2') for p in phases)) == 1
    execute('resume2', phases[0]['command'] + ['--resume'])
    if summary.exists():
        shutil.copy2(summary, O / 'resume2-summary.json')
    execute('verify-final-d67', [py, '-m', 'cbe', 'host', 'verify', '--run-dir', str(run)])
else:
    shutil.copy2(O / 'verify.log', O / 'verify-final-d67.log')
final = json.loads(summary.read_text()) if summary.exists() else {}
(O / 'D67-generation.done').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': final.get('status'), 'resumes': sum((p['phase'] in ('resume', 'resume2') for p in phases)), 'authority': 'D67.json'}, indent=2))
