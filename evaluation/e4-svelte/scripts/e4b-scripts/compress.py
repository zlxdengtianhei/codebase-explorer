import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, gzip, shutil, datetime
from pathlib import Path
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
free = shutil.disk_usage(root).free
records = []
for n in (1, 2, 3):
    out = root / f'runs/e4/cbe-svelte-r{n}'
    for p in sorted(out.rglob('*.json')):
        if p.stat().st_size <= 10000000:
            continue
        if p.name in ('context.json', 'catalog.json') and (free >= 10 * 1024 ** 3 or n == 1):
            records.append({'path': str(p), 'action': 'keep_plaintext_exception', 'bytes': p.stat().st_size})
            continue
        size = p.stat().st_size
        with p.open('rb') as src, gzip.open(str(p) + '.gz', 'wb') as dst:
            shutil.copyfileobj(src, dst)
        with gzip.open(str(p) + '.gz', 'rb') as src:
            length = 0
            while (chunk := src.read(1024 * 1024)):
                length += len(chunk)
        assert length == size
        p.unlink()
        records.append({'path': str(p), 'action': 'gzip', 'bytes_before': size, 'bytes_after': Path(str(p) + '.gz').stat().st_size})
(scripts / 'compression.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'free_before_bytes': free, 'free_after_bytes': shutil.disk_usage(root).free, 'files': records}, indent=2))
print('Compressed/kept', len(records), 'large JSON files; free bytes', shutil.disk_usage(root).free)
