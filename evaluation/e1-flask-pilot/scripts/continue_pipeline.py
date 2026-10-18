"""Revised coordinator order: finish C0/25, C10, W10 if ready, C25/W25 on fixed five."""
import datetime,json,os,shutil,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parent.parent;py=str(E/'venv/bin/python');deadline=time.monotonic()+4*3600

def wait_for(path):
    while not path.exists():
        if time.monotonic()>deadline:raise TimeoutError(f'4h bounded sequencing wait for {path}')
        time.sleep(10)
def run(arm,steps):
    marker=E/'answers'/f'{arm}-{steps}-r0'/'batch.json'
    if marker.exists():return
    with (E/f'pilot-{arm}.log').open('a') as log:
        code=subprocess.run([py,str(E/'run_pilot.py'),'--phase',arm,'--steps',str(steps)],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT).returncode
    if code:raise RuntimeError(f'{arm}/{steps} failed: {code}')
    print(datetime.datetime.now(datetime.timezone.utc).isoformat(),arm,steps,'finished',flush=True)
def prepare_c():
    dest=E/'arms/C'
    if (dest/'READY').exists():return
    shutil.copytree(E/'cbe-flask/run/docs',dest/'docs',dirs_exist_ok=True)
    shutil.copytree(E/'cbe-flask/run',dest/'run',dirs_exist_ok=True)
    shutil.rmtree(dest/'run/docs')
    for top in ['docs','run']:
        for p in (dest/top).rglob('*'):
            if p.is_file():p.chmod(0o444)
    (dest/'READY').write_text('Frozen CBE first complete run; source and docs unchanged across caps.')
def prepare_w():
    ready=E/'W-READY.json'
    if not ready.exists():return False
    dest=E/'arms/W'
    if (dest/'READY').exists():return True
    info=json.loads(ready.read_text())
    if info.get('complete') is not True:return False
    source=Path(info['docs_path']);md=list(source.glob('*.md'))
    if not md:raise RuntimeError('W attested directory has no flat published Markdown')
    (dest/'docs').mkdir(exist_ok=True)
    for p in md:shutil.copy2(p,dest/'docs'/p.name);(dest/'docs'/p.name).chmod(0o444)
    (dest/'READY').write_text(json.dumps(info));return True

wait_for(E/'answers/C0-25-r0/batch.json')
for p in ['answers/S-25-r0/batch.json','answers/S-10-r1/batch.json','answers/S-10-r2/batch.json','answers/direct/answers.jsonl','cbe-flask/DONE','cbe-flask/verify-final.log']:
    assert (E/p).exists(),p
summary=json.loads((E/'cbe-flask/run/summary.json').read_text());assert summary['status']=='complete' and summary['deterministic_checks_ok']
prepare_c();run('C',10)
(E/'C10-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
if prepare_w():run('W',10)
run('C',25)
(E/'primary-S-C0-C-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
if prepare_w():
    run('W',10);run('W',25)
else:
    (E/'W-skipped.json').write_text(json.dumps({'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':json.loads((E/'W-READY.json').read_text()).get('reason','No attested complete CodeWiki artifacts when all other answer conditions finished; task permits skipping W.') if (E/'W-READY.json').exists() else 'No attested complete CodeWiki artifacts when all other answer conditions finished; task permits skipping W.'},indent=2))
(E/'pipeline-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
