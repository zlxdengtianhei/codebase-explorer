"""Export one complete final gateway ledger covering every E1a request window."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import datetime, json, math, subprocess
RUN = Path(os.path.expandvars('$WORK/runs/e1'))
now = lambda: datetime.datetime.now(datetime.timezone.utc)
starts = [datetime.datetime.fromisoformat(json.loads((RUN / 'cwb/cbe-receipt.json').read_text())['start_utc'])]
p = RUN / 'codewiki-receipt.json'
if p.exists():
    starts.extend((datetime.datetime.fromisoformat(x['start_utc']) for x in json.loads(p.read_text())['attempts']))
minutes = math.ceil((now() - min(starts)).total_seconds() / 60) + 5
cmd = ['magpie', 'usage', '--csv', '--last', f'{minutes}m']
start = now().isoformat()
with (RUN / 'usage-final.csv').open('w') as out, (RUN / 'usage-final.stderr').open('w') as err:
    result = subprocess.run(cmd, stdout=out, stderr=err)
(RUN / 'usage-final-receipt.json').write_text(json.dumps({'command': cmd, 'earliest_run_start': min(starts).isoformat(), 'export_start_utc': start, 'export_end_utc': now().isoformat(), 'exit_code': result.returncode}, indent=2))
