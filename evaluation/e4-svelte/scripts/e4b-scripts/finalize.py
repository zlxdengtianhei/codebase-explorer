import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, subprocess, time, datetime
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
py = str(root / 'codebase-explorer/.venv/bin/python')
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root / 'eval-cbe2/src'))
for i in range(2160):
    if all(((root / f'runs/e4/cbe-svelte-r{n}/generation.done').exists() for n in (1, 2, 3))):
        break
    time.sleep(30)
else:
    raise RuntimeError('18-hour finalization bound reached')
with (scripts / 'usage.csv').open('w') as f, (scripts / 'usage.stderr').open('w') as err:
    subprocess.run(['magpie', 'usage', '--csv', '--last', '24h'], stdout=f, stderr=err, check=True)
for name in ('analyze', 'verify_measurements', 'compress', 'report'):
    print('Starting', name, datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
    subprocess.run([py, str(scripts / (name + '.py'))], env=env, check=True)
(scripts / 'finalization.done').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
