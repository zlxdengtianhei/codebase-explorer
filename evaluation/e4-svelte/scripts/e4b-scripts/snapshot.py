import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import csv, json, datetime, shutil, time
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
for i in range(2160):
    for n in (1, 2, 3):
        out = root / f'runs/e4/cbe-svelte-r{n}'
        snap = out / 'first-snapshot.json'
        if not (out / 'first-summary.json').exists() or snap.exists():
            continue
        phases = json.loads((out / 'phases.json').read_text())
        end = datetime.datetime.fromisoformat(phases[0]['end']).timestamp()
        files = []
        for p in (out / 'run/raw').glob('*'):
            if p.is_file() and p.stat().st_mtime <= end:
                target = out / 'first-raw' / p.name
                target.parent.mkdir(exist_ok=True)
                shutil.copy2(p, target)
                files.append(p.name)
        rows = list(csv.DictReader((out / 'run/calls.csv').open()))
        count = json.loads((out / 'first-summary.json').read_text()).get('calls', len(rows))
        with (out / 'first-calls.csv').open('w') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows[:count])
        snap.write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'first_calls': count, 'raw_files_copied': files}, indent=2))
    if all(((root / f'runs/e4/cbe-svelte-r{n}/generation.done').exists() for n in (1, 2, 3))):
        break
    time.sleep(10)
