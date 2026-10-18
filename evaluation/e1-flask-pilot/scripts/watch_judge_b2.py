"""Incremental E1b2 judging; archived C outputs have identically archived cached scores."""
import datetime,json,os,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent;B=E/'b2';deadline=time.monotonic()+6*3600;sweep=1
while time.monotonic()<deadline:
    pending=[p for group in ['C-10-r0','C-25-r0','W-10-r0','W-25-r0'] for p in (E/'answers'/group).glob('q*.json') if not (E/'judge'/group/p.name).exists()]
    if pending:
        with (B/f'judge-sweep-{sweep}.log').open('w') as log:
            code=subprocess.run([str(E/'venv/bin/python'),str(E/'judge_pilot.py')],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT).returncode
        if code:raise RuntimeError(f'Judge sweep{sweep} failed {code}')
        sweep+=1;continue
    if (B/'answers-DONE').exists():
        (B/'judge-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat());break
    time.sleep(10)
else:raise TimeoutError('B2 judge wait exceeded6h')
