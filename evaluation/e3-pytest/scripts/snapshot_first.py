"""Preserve first-round evidence before resume can reuse task/attempt filenames."""
import datetime,json,time,shutil,hashlib
from pathlib import Path
E=Path(__file__).resolve().parent;O=E/'cbe-pytest';run=O/'run'
for _ in range(172800):
 p=O/'phases.json'
 if p.exists() and any(r['phase']=='first' for r in json.loads(p.read_text())):break
 time.sleep(.5)
else:raise TimeoutError('First round did not settle within 24h')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();records=[]
for src in [run/'calls.csv',*(run/'raw').glob('*')]:
 if not src.is_file():continue
 dest=O/'first-calls.csv' if src.name=='calls.csv' else O/'first-raw'/src.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(src,dest)
 records.append({'source':str(src.relative_to(O)),'snapshot':str(dest.relative_to(O)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'mtime':src.stat().st_mtime})
(O/'first-round-snapshot.json').write_text(json.dumps({'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':records},indent=2))
