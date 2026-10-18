"""Finish diagnostics and final evidence once all primary/noise/direct jobs settle."""
import datetime,json,os,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent;py=str(E/'venv/bin/python');deadline=time.monotonic()+4*3600
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
for marker in ['pipeline-DONE','judge-DONE']:
    while not (E/marker).exists():
        if time.monotonic()>deadline:raise TimeoutError(f'Postprocess waiting for {marker}')
        time.sleep(10)
for name in ['guess_arms.py','reduce.py']:
    with (E/(name+'.log')).open('w') as log:
        code=subprocess.run([py,str(E/name)],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    if code:raise RuntimeError(f'{name} failed {code}')
phase_rows=[json.loads(line) for line in (E/'cbe-flask/phases.jsonl').read_text().splitlines()]
earliest=min(datetime.datetime.fromisoformat(p['start_utc']) for p in phase_rows)
export_at=datetime.datetime.now(datetime.timezone.utc)
last_minutes=int((export_at-earliest).total_seconds()//60)+11
(E/'usage-export-window.json').write_text(json.dumps({'export_started_utc':export_at.isoformat(),'last':str(last_minutes)+'m','coverage_start_utc':earliest.isoformat(),'padding_minutes':10},indent=2))
with (E/'usage-final.csv').open('w') as out,(E/'usage-final.stderr').open('w') as err:
    code=subprocess.run(['magpie','usage','--csv','--last',str(last_minutes)+'m'],stdout=out,stderr=err,timeout=900).returncode
if code:raise RuntimeError('Final gateway CSV export failed')
for name in ['accounting.py','verify_final.py','render_report.py']:
    with (E/(name+'.log')).open('w') as log:
        code=subprocess.run([py,str(E/name)],env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    if code:raise RuntimeError(f'{name} failed {code}')
(E/'postprocess-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
