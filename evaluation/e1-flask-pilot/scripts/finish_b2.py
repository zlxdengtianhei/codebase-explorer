"""Deterministic finalization after B2 answers/judging; never sends worker_done."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, json, os, subprocess, time
from pathlib import Path
E = Path(__file__).resolve().parent
B = E / 'b2'
py = str(E / 'venv/bin/python')
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
deadline = time.monotonic() + 6 * 3600
for marker in ['answers-DONE', 'judge-DONE']:
    while not (B / marker).exists():
        if time.monotonic() > deadline:
            raise TimeoutError('B2 postprocess wait exceeded6h')
        time.sleep(10)

def run(name):
    with (B / (name + '.log')).open('w') as log:
        code = subprocess.run([py, str(E / name)], stdout=log, stderr=subprocess.STDOUT, env=env).returncode
    if code:
        raise RuntimeError(f'{name} failed {code}')
run('analyze_b2.py')
phases = [json.loads(l) for l in (E / 'cbe-flask/phases.jsonl').read_text().splitlines()]
earliest = min((datetime.datetime.fromisoformat(p['start_utc']) for p in phases))
at = datetime.datetime.now(datetime.timezone.utc)
minutes = int((at - earliest).total_seconds() // 60) + 11
(E / 'usage-export-window.json').write_text(json.dumps({'export_started_utc': at.isoformat(), 'last': str(minutes) + 'm', 'coverage_start_utc': earliest.isoformat(), 'padding_minutes': 10, 'task': 'E1b2'}, indent=2))
with (E / 'usage-final.csv').open('w') as out, (E / 'usage-final.stderr').open('w') as err:
    result = subprocess.run(['magpie', 'usage', '--csv', '--last', str(minutes) + 'm'], stdout=out, stderr=err, timeout=900)
if result.returncode:
    raise RuntimeError('B2 final gateway export failed')
run('accounting.py')
run('verify_b2.py')
run('render_b2.py')
report = Path(os.path.expandvars('$TASK_DIR/scratch/opt_e1/e1b2_result.md'))
key = os.environ['MAGPIE_API_KEY'].encode()
assert key not in report.read_bytes()
(B / 'report-READY').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
