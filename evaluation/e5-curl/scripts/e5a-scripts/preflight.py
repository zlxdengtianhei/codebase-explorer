import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import pathlib, hashlib, json, gzip, shutil, subprocess, datetime
root = pathlib.Path(os.path.expandvars('$WORK'))
out = root / 'runs/e5/cbe-curl'
repo = root / 'eval/curl-2c04412'
rows = []
for line in (root / 'eval/curl-2c04412.manifest.txt').read_text().splitlines():
    sha, name = line.split(None, 1)
    name = name.strip()
    p = repo / name
    rows.append({'path': name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'expected': sha})
actual = {str(p.relative_to(repo)) for p in repo.rglob('*') if p.is_file()}
assert len(rows) == 506 and actual == {r['path'] for r in rows} and all((r['sha256'] == r['expected'] for r in rows))
with gzip.open(root / 'runs/e1d/curl.graph.json.gz', 'rb') as src, (out / 'graph.json').open('wb') as dst:
    shutil.copyfileobj(src, dst)
p = out / 'graph.json'
size = p.stat().st_size
assert size == 205284930
record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'input_files': len(rows), 'input_bytes': sum(((repo / r['path']).stat().st_size for r in rows)), 'manifest_sha256': hashlib.sha256((root / 'eval/curl-2c04412.manifest.txt').read_bytes()).hexdigest(), 'manifest_all_match': True, 'graph_bytes': size, 'graph_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'graph_gzip_sha256': hashlib.sha256((root / 'runs/e1d/curl.graph.json.gz').read_bytes()).hexdigest(), 'disk': subprocess.check_output(['df', '-h', str(root)], text=True), 'memory_pressure': subprocess.check_output(['memory_pressure'], text=True)}
(out / 'preflight.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
