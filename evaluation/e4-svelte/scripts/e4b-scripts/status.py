import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, csv, datetime, collections
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
print(datetime.datetime.now(datetime.timezone.utc).isoformat(), flush=True)
for n in (1, 2, 3):
    out = root / f'runs/e4/cbe-svelte-r{n}'
    run = out / 'run'
    p = run / 'host/state.json'
    if not p.exists():
        print(n, 'not planned')
        continue
    try:
        state = json.loads(p.read_text())
        calls = list(csv.DictReader((run / 'calls.csv').open())) if (run / 'calls.csv').exists() else []
        audit = json.loads((out / 'frozen-audit.json').read_text()) if (out / 'frozen-audit.json').exists() else {}
        print(n, state['status'], dict(collections.Counter((t['status'] for t in state['tasks'].values()))), 'calls', len(calls), 'results', dict(collections.Counter((r['result'] for r in calls))), 'audit', audit.get('ok'), 'done', (out / 'generation.done').exists(), flush=True)
        if (out / 'generation.done').exists():
            print('FINAL', json.loads((run / 'summary.json').read_text()).get('status'), 'verify', json.loads((out / 'verify.log').read_text()).get('ok'))
    except Exception as exc:
        print(n, repr(exc))
