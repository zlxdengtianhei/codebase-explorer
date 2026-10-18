"""E1b2 sequence: complete new C, bounded five-minute W readiness checks, then W."""
import datetime,json,os,shutil,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent;B=E/'b2';py=str(E/'venv/bin/python')
cutoff=datetime.datetime(2026,10,17,11,30,tzinfo=datetime.timezone.utc)
def utc():return datetime.datetime.now(datetime.timezone.utc)
def state(phase,**kwargs):(B/'pipeline-state.json').write_text(json.dumps({'utc':utc().isoformat(),'phase':phase,**kwargs},indent=2))
state('waiting_C')
limit=time.monotonic()+4*3600
while not (E/'answers/C-25-r0/batch.json').exists():
    if time.monotonic()>limit:raise TimeoutError('C rerun bounded wait exceeded4h')
    time.sleep(10)
receipt=None
while True:
    ready=E/'W-READY.json';payload=json.loads(ready.read_text()) if ready.exists() else None
    with (B/'W-observations.jsonl').open('a') as f:f.write(json.dumps({'observed_utc':utc().isoformat(),'readiness':payload})+'\n')
    if payload is not None:
        if payload.get('complete') is True:
            receipt={'run':True,'readiness':payload,'observed_utc':utc().isoformat()}
        elif payload.get('complete') is False:
            receipt={'run':False,'reason':payload.get('reason','CodeWiki reported incomplete'),'readiness':payload,'observed_utc':utc().isoformat()}
        else:raise ValueError('W readiness complete must be JSON boolean')
        break
    remaining=(cutoff-utc()).total_seconds()
    if remaining<=0:
        receipt={'run':False,'reason':'No W-READY.json by 2026-10-17 13:30 CEST (11:30 UTC)','observed_utc':utc().isoformat()};break
    state('waiting_W',cutoff_utc=cutoff.isoformat(),next_check_utc=(utc()+datetime.timedelta(seconds=min(300,remaining))).isoformat())
    time.sleep(min(300,remaining))
(B/'W-decision.json').write_text(json.dumps(receipt,indent=2))
if receipt['run']:
    state('preparing_W')
    source=Path(receipt['readiness']['docs_path']);pages=list(source.glob('*.md'))
    if not pages:raise RuntimeError('Attested W docs have no flat Markdown')
    dest=E/'arms/W/docs';dest.mkdir(exist_ok=True)
    for p in pages:shutil.copy2(p,dest/p.name);(dest/p.name).chmod(0o444)
    for steps in [10,25]:
        state('running_W',steps=steps)
        with (B/'pilot-W.log').open('a') as log:
            code=subprocess.run([py,str(E/'run_pilot.py'),'--phase','W','--steps',str(steps)],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT).returncode
        if code:raise RuntimeError(f'W/{steps} runner exited{code}')
state('answers_done',W_ran=receipt['run']);(B/'answers-DONE').write_text(utc().isoformat())
