"""Capture per-phase rendered evidence without touching the generator or its run."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, time, shutil, datetime, hashlib, sys
from pathlib import Path
out = Path(os.path.expandvars('$WORK/runs/e6')) / (sys.argv[1] if len(sys.argv) > 1 else 'fmt')
run = out / 'run'
deadline = time.monotonic() + 24 * 3600
records = []
for label in ('first', 'resume1', 'resume2'):
    marker = out / (label + '-summary.json')
    while not marker.exists():
        if (out / 'generation.done').exists() or (out.parent / 'batch.error').exists() or (out.parent / (out.name + '.error')).exists():
            break
        if time.monotonic() >= deadline:
            raise SystemExit('24h snapshot wait bound reached')
        time.sleep(1)
    if not marker.exists():
        break
    summary = json.loads(marker.read_text())
    catalog = run / 'catalog.json'
    row = {'phase': label, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'summary_status': summary.get('status'), 'summary_units': summary.get('units')}
    if catalog.exists():
        b = catalog.read_bytes()
        snap = out / (label + '-catalog.json')
        snap.write_bytes(b)
        d = json.loads(b)
        row.update(catalog_sha256=hashlib.sha256(b).hexdigest(), catalog_units=len(d.get('units', {})), catalog_matches_summary=len(d.get('units', {})) == summary.get('units'))
    docs = run / 'docs'
    if docs.exists():
        dest = out / (label + '-docs')
        shutil.copytree(docs, dest)
        row['pages'] = len(list(dest.rglob('*.md')))
    records.append(row)
    (out / 'render-snapshots.json').write_text(json.dumps(records, indent=2))
    print(row, flush=True)
(out / 'snapshot.done').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat())
