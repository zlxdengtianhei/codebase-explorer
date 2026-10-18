"""Frozen CBE single generation, with at most one requested resume; secrets memory only."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, json, os, subprocess, time
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
out = root / 'runs/e1/cbe-flask'
out.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['PYTHONPATH'] = str(root / 'eval-cbe/src')
env['PYTHONDONTWRITEBYTECODE'] = '1'
env['CBE_API_KEY'] = os.environ['MAGPIE_API_KEY']
py = str(root / 'codebase-explorer/.venv/bin/python')
repo = str(root / 'eval/flask-85c5d93')
graph = str(out / 'graph.json')
run = out / 'run'

def execute(label, args):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t = time.monotonic()
    with (out / (label + '.log')).open('w') as f:
        p = subprocess.run([py, '-m', 'cbe'] + args, env=env, stdout=f, stderr=subprocess.STDOUT)
    rec = {'phase': label, 'start_utc': start, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'wall_seconds': time.monotonic() - t, 'exit_code': p.returncode}
    if (run / 'summary.json').exists():
        rec['summary'] = json.loads((run / 'summary.json').read_text())
        (out / (label + '-summary.json')).write_text(json.dumps(rec['summary'], indent=2))
    with (out / 'phases.jsonl').open('a') as f:
        f.write(json.dumps(rec) + '\n')
    return rec
assert execute('graph', ['graph', 'build', repo, '--output', graph, '--joern-home', str(root / 'tools/joern/joern-cli')])['exit_code'] == 0
args = ['generate', repo, '--host', 'api', '--jobs', '2', '--base-url', 'http://127.0.0.1:3425/v1', '--api-key-env', 'CBE_API_KEY', '--model', 'zai/glm-5.3-flash', '--graph', graph, '--run-dir', str(run)]
r = execute('first', args)
if r['exit_code'] != 0 or r.get('summary', {}).get('status') not in ('complete', 'completed'):
    execute('resume', args + ['--resume'])
execute('verify', ['host', 'verify', '--run-dir', str(run)])
(out / 'DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
