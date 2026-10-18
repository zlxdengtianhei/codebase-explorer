import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, sys, json, subprocess, datetime, time, shutil
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
out = root / f'runs/e4/cbe-svelte-r{sys.argv[1]}'
out.mkdir(parents=True, exist_ok=False)
(out / 'api-config.json').write_text(json.dumps({'extra_headers': {'X-Magpie-Agent': 'codebase-explorer', 'X-Magpie-Session': f'e4-cbe-svelte-r{sys.argv[1]}'}}, indent=2))
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root / 'eval-cbe2/src'))
env['CBE_API_KEY'] = os.environ['MAGPIE_API_KEY']
py = str(root / 'codebase-explorer/.venv/bin/python')
subprocess.run([py, '-c', 'import cbe; print(cbe.__file__)'], env=env, check=True)
subprocess.run(['git', '-C', str(root / 'eval-cbe2'), 'rev-parse', 'HEAD'], check=True)
cmd = [py, str(scripts / 'audited_cli.py'), 'generate', str(root / 'eval/svelte-be645b4'), '--host', 'api', '--jobs', '2', '--base-url', 'http://127.0.0.1:3425/v1', '--api-key-env', 'CBE_API_KEY', '--model', 'zai/glm-5.3-flash', '--graph', str(root / 'runs/e1c/svelte-be645b4-default.graph.json'), '--run-dir', str(out / 'run'), '--config', str(out / 'api-config.json')]
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
complete = s.exists() and json.loads(s.read_text()).get('status') == 'complete'
if audit.get('ok') and (not complete):
    execute('resume', cmd + ['--resume'])
    if s.exists():
        shutil.copy2(s, out / 'resume-summary.json')
execute('verify', [py, '-m', 'cbe', 'host', 'verify', '--run-dir', str(out / 'run')])
(out / 'generation.done').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
