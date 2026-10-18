"""Finalize only after bounded generation and evaluation settle."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, json, os, subprocess, time, gzip, shutil
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
py = str(E / 'venv/bin/python')
cbe_py = str(R / 'codebase-explorer/.venv/bin/python')
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(R / 'eval-cbe2/src')}

def execute(script, python=py):
    with (E / (script + '.log')).open('w') as log:
        subprocess.run([python, str(E / (script + '.py'))], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
for _ in range(2880):
    if (E / 'cbe-pytest/generation.done').exists():
        break
    time.sleep(30)
else:
    raise TimeoutError('Generation did not settle within 24h')
execute('generation_metrics', cbe_py)
complete = json.loads((E / 'cbe-pytest/metrics.json').read_text())['complete']
if complete:
    for _ in range(2880):
        if (E / 'PIPELINE-DONE.json').exists():
            break
        if (E / 'RUN-FAILED.txt').exists() or (E / 'direct/FAILED.txt').exists() or 'Traceback (most recent call last)' in (E / 'pipeline.log').read_text():
            raise RuntimeError('Evaluation pipeline failed; inspect raw logs')
        time.sleep(30)
    else:
        raise TimeoutError('Evaluation did not settle within 24h')
    execute('reduce')
    execute('verify')
records = []
for p in E.rglob('*.json'):
    if p.is_symlink() or any((x in ('harness', 'venv') for x in p.relative_to(E).parts)) or p.stat().st_size <= 10000000:
        continue
    if p.resolve() == (E / 'cbe-pytest/run/context.json').resolve() and complete:
        records.append({'path': str(p.relative_to(E)), 'bytes': p.stat().st_size, 'kept_plaintext': 'C arm active run context'})
        continue
    size = p.stat().st_size
    with p.open('rb') as src, gzip.open(str(p) + '.gz', 'wb') as dst:
        shutil.copyfileobj(src, dst)
    p.unlink()
    records.append({'path': str(p.relative_to(E)), 'bytes': size, 'gzip_bytes': Path(str(p) + '.gz').stat().st_size})
(E / 'compression.json').write_text(json.dumps(records, indent=2))
execute('render')
(E / 'FINALIZATION-DONE.json').write_text(json.dumps({'complete': complete, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2))
