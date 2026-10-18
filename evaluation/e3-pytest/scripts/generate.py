"""E3 generation driver: frozen code, audited plan before any model request."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, sys, json, subprocess, datetime, time, shutil
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
out = E / 'cbe-pytest'
out.mkdir(parents=True, exist_ok=True)
src = (R / 'runs/e4/e4b-scripts/audited_cli.py').read_text().replace('len(sources)==440', "set(sources)=={r['path'] for r in context['files']} and len(sources)==225").replace('440 files', '225 Python files')
(E / 'audited_cli.py').write_text(src)
(out / 'api-config.json').write_text(json.dumps({'extra_headers': {'X-Magpie-Agent': 'codebase-explorer', 'X-Magpie-Session': 'e3-cbe-pytest'}}, indent=2))
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(R / 'eval-cbe2/src'))
env['CBE_API_KEY'] = os.environ['MAGPIE_API_KEY']
py = str(R / 'codebase-explorer/.venv/bin/python')
subprocess.run([py, '-c', 'import cbe;print(cbe.__file__)'], env=env, check=True)
head = subprocess.check_output(['git', '-C', str(R / 'eval-cbe2'), 'rev-parse', 'HEAD'], text=True).strip()
print(head, flush=True)
assert head.startswith('a87674d')
cmd = [py, str(E / 'audited_cli.py'), 'generate', str(R / 'eval/pytest-5989efe'), '--host', 'api', '--jobs', '2', '--base-url', 'http://127.0.0.1:3425/v1', '--api-key-env', 'CBE_API_KEY', '--model', 'zai/glm-5.3-flash', '--graph', str(R / 'runs/e1c/pytest-5989efe-default.graph.json'), '--run-dir', str(out / 'run'), '--config', str(out / 'api-config.json')]
phases = []

def execute(name, args):
    start = datetime.datetime.now(datetime.timezone.utc)
    t = time.monotonic()
    with (out / (name + '.log')).open('w') as log:
        rc = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    phases.append(dict(phase=name, start=start.isoformat(), end=datetime.datetime.now(datetime.timezone.utc).isoformat(), wall_seconds=time.monotonic() - t, returncode=rc, command=args))
    (out / 'phases.json').write_text(json.dumps(phases, indent=2))
execute('first', cmd)
s = out / 'run/summary.json'
if s.exists():
    shutil.copy2(s, out / 'first-summary.json')
audit = json.loads((out / 'frozen-audit.json').read_text()) if (out / 'frozen-audit.json').exists() else {}
if not audit.get('ok'):
    (E / 'GENERATION-FAILED.json').write_text(json.dumps({'reason': 'Frozen audit failed', 'audit': audit}, indent=2))
    sys.exit(1)
if not (s.exists() and json.loads(s.read_text()).get('status') == 'complete'):
    execute('resume', cmd + ['--resume'])
    if s.exists():
        shutil.copy2(s, out / 'resume-summary.json')
execute('verify', [py, '-m', 'cbe', 'host', 'verify', '--run-dir', str(out / 'run')])
(out / 'generation.done').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
