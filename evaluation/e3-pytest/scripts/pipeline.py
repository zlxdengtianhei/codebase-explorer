"""Bounded E3 pipeline; no downstream run consumes an incomplete map."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import subprocess, json, time, shutil, datetime, hashlib
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
py = str(E / 'venv/bin/python')
start = time.time()
last = 0
for _ in range(2880):
    if (E / 'GENERATION-FAILED.json').exists():
        raise RuntimeError('Generation audit failed')
    if (E / 'cbe-pytest/generation.done').exists():
        break
    if time.time() - last >= 300:
        subprocess.run(['orca', 'orchestration', 'send', '--from', 'term_7f96a4eb-9683-40ed-999d-de345df3e938', '--type', 'heartbeat', '--subject', 'E3 frozen audit passed; generating pytest CBE', '--task-id', 'task_ebef506fc38a', '--dispatch-id', 'ctx_40994a64b448', '--phase', 'implementing'], stdout=subprocess.DEVNULL, check=False)
        last = time.time()
    time.sleep(30)
else:
    raise TimeoutError('Generation exceeded 24h observation bound')
s = E / 'cbe-pytest/run/summary.json'
assert s.exists() and json.loads(s.read_text())['status'] == 'complete', 'First plus one resume did not complete; stop evaluation'
for arm in ['C0', 'C']:
    dest = E / 'arms' / arm / 'docs'
    shutil.copytree(E / 'cbe-pytest/run/docs', dest, dirs_exist_ok=True)
    for p in dest.rglob('*'):
        if p.is_file():
            p.chmod(292)
p = E / 'arms/C/run'
if not p.exists():
    p.symlink_to(E / 'cbe-pytest/run', target_is_directory=True)
profile = E / 'arms/C/sandbox.sb'
body = profile.read_text()
target = str((E / 'cbe-pytest/run').resolve())
if target not in body:
    profile.write_text(body + '(allow file-read* (subpath ' + json.dumps(target) + '))\n')
checks = {}
for arm in ['S', 'C0', 'C']:
    checks[arm] = all((hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((E / 'arms' / arm / 'repo' / p.relative_to(R / 'eval/pytest-5989efe')).read_bytes()).digest() for p in (R / 'eval/pytest-5989efe').rglob('*') if p.is_file()))
assert all(checks.values())
(E / 'arm-copies-check.json').write_text(json.dumps(checks, indent=2))
for script, log in [('tool_layer_smoke.py', 'tool-layer-smoke.log'), ('run.py', 'run.log'), ('run_direct.py', 'direct.log')]:
    with (E / log).open('w') as f:
        subprocess.run([py, str(E / script)], stdout=f, stderr=subprocess.STDOUT, check=True, env={**__import__('os').environ, 'PYTHONDONTWRITEBYTECODE': '1'})
(E / 'PIPELINE-DONE.json').write_text(json.dumps({'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'wall_seconds': time.time() - start}, indent=2))
