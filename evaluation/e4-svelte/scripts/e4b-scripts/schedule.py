import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import subprocess, time, datetime, json
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
for i in range(2160):
    if any(((root / f'runs/e4/cbe-svelte-r{n}/generation.done').exists() for n in (1, 2))):
        with (scripts / 'r3-driver.log').open('w') as f:
            subprocess.Popen([str(root / 'codebase-explorer/.venv/bin/python'), str(scripts / 'execute.py'), '3'], stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        (scripts / 'r3-started').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
        break
    time.sleep(30)
else:
    (scripts / 'scheduler-expired').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
