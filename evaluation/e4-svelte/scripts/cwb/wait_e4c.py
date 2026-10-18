"""Bounded availability/stability watcher for E4c; never reads report contents."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, time, datetime
from pathlib import Path
R = Path(__file__).resolve().parent
report = Path(os.path.expandvars('$TASK_DIR/scratch/opt_e4/e4c_result.md'))
start = time.time()
deadline = start + 8 * 3600
while time.time() < deadline:
    now = time.time()
    exists = report.exists()
    mtime = report.stat().st_mtime if exists else None
    state = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'start_epoch': start, 'deadline_epoch': deadline, 'exists': exists, 'mtime': mtime, 'age_seconds': now - mtime if mtime else None, 'ready': bool(exists and now - mtime >= 600)}
    (R / 'e4c-wait-state.json').write_text(json.dumps(state, indent=2))
    if state['ready']:
        (R / 'e4c-ready.json').write_text(json.dumps(state, indent=2))
        break
    for _ in range(3):
        time.sleep(60)
else:
    (R / 'e4c-wait-timeout.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'reason': 'E4c report unavailable or not stable for ten minutes within eight-hour bound'}))
