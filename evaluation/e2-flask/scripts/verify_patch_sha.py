"""Reconstruct E1's five changed files from frozen upstream + saved unified patch."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, hashlib, json, re
from pathlib import Path
E = Path(__file__).resolve().parent
OLD = E.parent / 'e1'
UP = Path(os.path.expandvars('$HOME/clones/eval_research_20261017/SWE-QA-Bench'))
receipt = json.loads((E / 'harness-sha-check.json').read_text())
records = {r['path']: r for r in receipt['files']}
checked = []
for block in (OLD / 'harness.patch').read_text().split('diff --git ')[1:]:
    path = block.splitlines()[0].split('/runs/e1/harness/', 1)[1]
    old = (UP / path).read_text().splitlines(keepends=True)
    lines = block.splitlines(keepends=True)
    out = []
    cursor = 0
    i = 0
    while i < len(lines):
        hunk = re.match('@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@', lines[i])
        if not hunk:
            i += 1
            continue
        start = int(hunk[1]) - 1
        out.extend(old[cursor:start])
        cursor = start
        i += 1
        while i < len(lines) and (not lines[i].startswith('@@ ')):
            line = lines[i]
            tag = line[:1]
            if tag in (' ', '-'):
                assert old[cursor] == line[1:], (path, cursor, repr(old[cursor]), repr(line[1:]))
                cursor += 1
            if tag in (' ', '+'):
                out.append(line[1:])
            if tag == '\\':
                raise RuntimeError('Unexpected no-newline marker; handle explicitly before using this verifier')
            i += 1
    out.extend(old[cursor:])
    expected = ''.join(out).encode()
    actual = (OLD / 'harness' / path).read_bytes()
    assert expected == actual, path
    sha = hashlib.sha256(expected).hexdigest()
    assert sha == records[path]['sha256'], path
    records[path]['e1_patch_reconstructed_sha256'] = sha
    records[path]['full_sha256_matches_reconstructed_E1'] = True
    checked.append(path)
assert len(checked) == 5
receipt['full_patch_reconstruction'] = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'all_passed': True, 'files': checked, 'method': 'Apply saved E1 unified hunks in memory to fixed clean upstream, assert every context/deletion line, then byte-compare and SHA-256 compare complete reconstructed files with the pre-run manifest'}
(E / 'harness-sha-check.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt['full_patch_reconstruction'], indent=2))
