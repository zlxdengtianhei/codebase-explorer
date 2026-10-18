import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import time, subprocess
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
for i in range(216):
    if all(((root / f'runs/e4/cbe-svelte-r{n}/generation.done').exists() for n in (1, 2, 3))):
        break
    subprocess.run(['orca', 'orchestration', 'send', '--from', 'term_a670c7ee-bcf6-4abb-aafa-f9bb4b923ae0', '--type', 'heartbeat', '--subject', 'E4b generation active', '--task-id', 'task_bae86c9d41d8', '--dispatch-id', 'ctx_ae1822cbbc3f', '--phase', 'implementing'], check=False)
    for j in range(10):
        if all(((root / f'runs/e4/cbe-svelte-r{n}/generation.done').exists() for n in (1, 2, 3))):
            break
        time.sleep(30)
