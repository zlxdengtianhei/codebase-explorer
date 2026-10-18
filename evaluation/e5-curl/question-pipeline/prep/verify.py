#!/usr/bin/env python3
"""Verify real generated artifacts, then rerun extraction and compare bytes."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess
import sys

base=Path(__file__).resolve().parent
root=base.parents[2]
data=json.loads((base/'anchors.json').read_text()); anchors=data['anchors']
assert len(anchors)==80 and len({a['id'] for a in anchors})==80
assert {p.stem for p in (base/'cards').glob('*.md')}=={a['id'] for a in anchors}
for a in anchors:
    text=(root/'eval/curl-2c04412'/a['file']).read_text()
    assert a['name'] in '\n'.join(text.splitlines()[max(0,a['line']-2):a['line']+8]), a
    assert (base/'cards'/f"{a['id']}.md").is_file()
    if a['is_dispatch']:
        own=[s for s in a['related_dispatch_sites'] if s['function']==a['name'] and s['file']==a['file']]
        assert own, a['id']
    assert all(x['hop'] in (1,2) for x in a['callers']+a['callees'])
advanced=[a for a in anchors if a['suggested_layer']>=3]
assert sum(a['is_dispatch'] for a in advanced)/len(advanced)>=.4
splits=[json.loads((base/f'split_{tag}.json').read_text()) for tag in ('A','B')]
assert set(splits[0]['regions']).isdisjoint(splits[1]['regions'])
assert {a['id'] for s in splits for a in s['anchors']}=={a['id'] for a in anchors}
assert sum(len(s['anchors']) for s in splits)==80
for s in splits:
    assert sum(s['candidate_region_quota'].values())==28
    assert max(s['candidate_region_quota'].values())<=6
    if 'cli' in s['regions']: assert s['candidate_region_quota']['cli']>=4
seed=(base/'seed_templates.md').read_text()
assert len(re.findall(r'^## ',seed,re.M))==12
assert len(re.findall(r'^- ',seed,re.M))==36
scan=json.loads((base/'source_scan.json').read_text())
assert {t['type'] for t in scan['tables']}=={'Curl_protocol','Curl_cftype','Curl_ssl','Curl_cwtype'}
assert all(t['functions'] for t in scan['tables'])
# Compare the entire generated dataset and all authored delivery inputs.
files=sorted([base/'anchors.py',base/'verify.py',base/'seed_templates.md',base/'anchors.json',base/'source_scan.json',base/'split_A.json',base/'split_B.json']+list((base/'cards').glob('*.md')))
before={p.relative_to(base).as_posix():p.read_bytes() for p in files}
result=subprocess.run([sys.executable,str(base/'anchors.py')],capture_output=True,text=True)
(base/'generation.log').write_text(result.stdout+result.stderr)
assert result.returncode==0, result.stderr
lines=['Command: python3 runs/e5q/prep/verify.py','Extraction rerun: python3 runs/e5q/prep/anchors.py','Byte equality and SHA-256 comparison; no timestamps in generated artifacts.','Structural/source/quotas/templates checks: PASS',f'Compared files: {len(before)}','format: relative_path | before_sha256 | after_sha256 | byte_equal']
for name,raw in sorted(before.items()):
    after=(base/name).read_bytes(); equal=raw==after
    lines.append(f'{name} | {hashlib.sha256(raw).hexdigest()} | {hashlib.sha256(after).hexdigest()} | {equal}')
    assert equal, name
lines.append('PASS: all compared files are byte-for-byte identical.')
(base/'rerun-check.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[:6]+lines[-1:]))
print('regions',dict(collections.Counter(a['region'] for a in anchors)))
print('layers',dict(collections.Counter(a['suggested_layer'] for a in anchors)))
print('advanced dispatch',sum(a['is_dispatch'] for a in advanced),'/',len(advanced))
print('tables',dict(collections.Counter(t['type'] for t in scan['tables'])))
for s in splits:
 print('split',s['split'],'anchors',len(s['anchors']),'layers',dict(collections.Counter(a['suggested_layer'] for a in s['anchors'])),'regions',s['regions'])
