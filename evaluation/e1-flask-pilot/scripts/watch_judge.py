"""Incremental judge sweeps, at most one judge process and four judge workers."""
import datetime,json,os,subprocess,time
from pathlib import Path
E=Path(__file__).resolve().parent;deadline=time.monotonic()+4*3600
sweep=max([int(p.stem.rsplit('-',1)[-1]) for p in E.glob('judge-sweep-*.log')],default=1)+1
while time.monotonic()<deadline:
    pending=[p for p in (E/'answers').glob('*/q*.json') if not (E/'judge'/p.parent.name/p.name).exists()]
    if pending:
        with (E/f'judge-sweep-{sweep}.log').open('w') as log:
            code=subprocess.run([str(E/'venv/bin/python'),str(E/'judge_pilot.py')],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT).returncode
        if code:raise RuntimeError(f'Judge sweep {sweep} failed: {code}')
        sweep+=1
        continue
    if (E/'pipeline-DONE').exists():
        (E/'judge-DONE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat());break
    time.sleep(10)
else:raise TimeoutError('Judge monitor 4h bounded deadline exceeded')
