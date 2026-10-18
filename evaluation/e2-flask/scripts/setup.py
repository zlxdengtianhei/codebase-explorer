"""E2 setup: no mutations outside E2; frozen E1 used directly."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, hashlib, json, re, shutil, subprocess
from pathlib import Path
E = Path(__file__).resolve().parent
OLD = E.parent / 'e1'
E.mkdir(exist_ok=True)
up = Path(os.path.expandvars('$HOME/clones/eval_research_20261017/SWE-QA-Bench'))
patch = (OLD / 'harness.patch').read_text()
expected = {}
for block in patch.split('diff --git ')[1:]:
    path = block.splitlines()[0].split('/runs/e1/harness/', 1)[1]
    expected[path] = re.search('index [a-f0-9]+\\.\\.([a-f0-9]+)', block)[1]
records = []
for p in sorted((OLD / 'harness').rglob('*')):
    if not p.is_file() or '.git' in p.parts or '__pycache__' in p.parts:
        continue
    rel = str(p.relative_to(OLD / 'harness'))
    data = p.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\x00' + data).hexdigest()
    passed = blob.startswith(expected[rel]) if rel in expected else (up / rel).is_file() and data == (up / rel).read_bytes()
    records.append({'path': rel, 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob_sha1': blob, 'e1_patch_blob': expected.get(rel), 'same_e1': passed})
assert all((r['same_e1'] for r in records)), [r for r in records if not r['same_e1']]
(E / 'harness-sha-check.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'method': 'Modified files compared with E1 patch new blob SHA; remaining files byte-compared to fixed upstream', 'all_passed': True, 'files': records}, indent=2))
qs = [{'question': r['question'], 'qid': i} for i, r in enumerate(map(json.loads, (OLD / 'harness/Benchmark/flask.jsonl').read_text().splitlines()))]
(E / 'questions').mkdir(exist_ok=True)
(E / 'questions/all.jsonl').write_text(''.join((json.dumps(q) + '\n' for q in qs)))
shutil.copy2(OLD / 'questions/labels.json', E / 'questions/labels.json')
pilot = [4, 6, 11, 12, 14, 20, 32, 41, 46, 47]
reused = []
for kind in ['answers', 'judge']:
    for arm in ['S', 'C0', 'C', 'W']:
        dest = E / kind / f'{arm}-10-r0'
        dest.mkdir(parents=True, exist_ok=True)
        for q in pilot:
            src = OLD / kind / f'{arm}-10-r0' / f'q{q:02}.json'
            target = dest / src.name
            if not target.exists():
                target.symlink_to(src)
            reused.append({'kind': kind, 'arm': arm, 'qid': q, 'source': str(src), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'origin': '复用 E1'})
(E / 'reuse-manifest.json').write_text(json.dumps(reused, indent=2))
src = (OLD / 'tool_layer_smoke_b2.py').read_text().replace('E=Path(__file__).resolve().parent', f'E=Path({str(OLD)!r})').replace("(E/'b2/tool-layer-smoke.json')", f"Path({str(E / 'tool-layer-smoke.json')!r})")
(E / 'tool_layer_smoke.py').write_text(src)
print(json.dumps({'harness_files': len(records), 'all_same_e1': True, 'reused_artifacts': len(reused), 'questions': len(qs)}))
