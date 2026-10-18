import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import pathlib, json, csv, collections, datetime, time
out = pathlib.Path(os.path.expandvars('$WORK/runs/e5/cbe-curl'))
for i in range(6):
    if (out / 'generation.done').exists():
        break
    time.sleep(9)
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'done': (out / 'generation.done').exists()}
try:
    rows = list(csv.DictReader((out / 'run/calls.csv').open()))
    result['calls'] = len(rows)
    result['results'] = dict(collections.Counter((r.get('result') for r in rows)))
    result['last_calls'] = [{k: r[k] for k in ('task', 'attempt', 'result') if k in r} for r in rows[-2:]]
    s = json.loads((out / 'run/host/state.json').read_text())
    result['tasks'] = dict(collections.Counter((t['status'] for t in s['tasks'].values())))
except Exception as exc:
    result['reading'] = str(exc)
if (out / 'gateway-progress.json').exists():
    result['gateway'] = json.loads((out / 'gateway-progress.json').read_text())
print(result['utc'], 'done=' + str(result['done']), 'calls=' + str(result.get('calls')), 'tasks=' + str(result.get('tasks')), 'gateway=' + str({k: result.get('gateway', {}).get(k) for k in ('utc', 'requests', 'cost_usd')}), flush=True)
