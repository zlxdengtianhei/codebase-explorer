import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import json, collections, datetime
b = Path(os.path.expandvars('$WORK/runs/e6'))
print(datetime.datetime.now(datetime.timezone.utc).isoformat())
cur = json.loads((b / 'current.json').read_text())
print('current', cur)
r = b / cur['repo']
p = r / 'run/host/state.json'
if p.exists():
    s = json.loads(p.read_text())
    print('tasks', dict(collections.Counter((t['status'] for t in s['tasks'].values()))))
    print('active', [(k, t.get('attempts')) for k, t in s['tasks'].items() if t['status'] == 'leased'])
p = r / 'run/calls.csv'
if p.exists():
    print('recent calls\n' + '\n'.join(p.read_text().splitlines()[-1:]))
print('completed', [p.parent.name for p in b.glob('*/generation.done')])
for p in [b / 'batch.error', b / 'polyglot.error']:
    if p.exists():
        print('ERROR', p.read_text())
p = b / 'coordinator-messages.jsonl'
if p.exists():
    text = p.read_text()
    decoder = json.JSONDecoder()
    offset = 0
    while offset < len(text):
        try:
            d, n = decoder.raw_decode(text[offset:])
            offset += n
        except json.JSONDecodeError:
            offset += 1
            continue
        msgs = d.get('result', {}).get('messages', [])
        if msgs:
            print('COORDINATOR', msgs)
