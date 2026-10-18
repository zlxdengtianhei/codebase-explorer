"""D-67 closeout: QA eligibility is tool smoke, not complete-only generation status."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, gzip, json, os, shutil, subprocess, time
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
py = str(E / 'venv/bin/python')
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(R / 'eval-cbe2/src')}

def execute(script):
    with (E / (script + '.log')).open('w') as log:
        subprocess.run([py, str(E / (script + '.py'))], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
for _ in range(2880):
    if (E / 'GENERATION-MEASURED.json').exists():
        break
    if (E / 'PIPELINE-FAILED.json').exists():
        raise RuntimeError('D67 preparation failed; inspect PIPELINE-FAILED.json')
    time.sleep(30)
else:
    raise TimeoutError('Generation measurement not ready within24h')
full = False
for _ in range(2880):
    if (E / 'PIPELINE-DONE.json').exists():
        full = True
        break
    if (E / 'D67-GATE-FAILED.json').exists():
        break
    if (E / 'PIPELINE-FAILED.json').exists() or (E / 'RUN-FAILED.txt').exists() or (E / 'direct/FAILED.txt').exists():
        raise RuntimeError('QA pipeline failed; preserve and inspect raw logs')
    time.sleep(30)
else:
    raise TimeoutError('QA did not settle within24h')
if full:
    execute('reduce')
    execute('verify')
records = []
for p in E.rglob('*.json'):
    if p.is_symlink() or p.relative_to(E).parts[0] in ('harness', 'venv') or p.stat().st_size <= 10000000:
        continue
    if p.resolve() == (E / 'cbe-pytest/run/context.json').resolve():
        records.append({'path': str(p.relative_to(E)), 'bytes': p.stat().st_size, 'kept_plaintext': 'C group context retained under D-67, including partial artifact'})
        continue
    size = p.stat().st_size
    with p.open('rb') as src, gzip.open(str(p) + '.gz', 'wb') as dst:
        shutil.copyfileobj(src, dst)
    p.unlink()
    records.append({'path': str(p.relative_to(E)), 'bytes': size, 'gzip_bytes': Path(str(p) + '.gz').stat().st_size})
(E / 'compression.json').write_text(json.dumps(records, indent=2))
execute('render')
(E / 'FINALIZATION-DONE.json').write_text(json.dumps({'requested_experiment_complete': full, 'generation_status': json.loads((E / 'GENERATION-MEASURED.json').read_text())['generation_status'], 'authority': 'D-67', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2))
