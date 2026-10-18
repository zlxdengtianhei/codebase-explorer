"""E5 isolated preparation; frozen E3 harness and prompts, relocated paths only."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import hashlib, json, shutil, subprocess, datetime
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e5/qa'
F = R / 'runs/e5q/freeze'
old = R / 'runs/e3'
checks = []
for line in (F / 'MANIFEST.sha256').read_text().splitlines():
    h, n = line.split(maxsplit=1)
    a = hashlib.sha256((F / n).read_bytes()).hexdigest()
    assert h == a
    checks.append({'path': n, 'sha256': a})
(E / 'freeze-check.json').write_text(json.dumps(checks, indent=2))
for n in ['harness', 'venv']:
    if not (E / n).exists():
        (E / n).symlink_to(R / 'runs/e1' / n, target_is_directory=True)
expected = json.loads((old / 'harness-sha-check.json').read_text())['files']
for row in expected:
    assert hashlib.sha256((E / 'harness' / row['path']).read_bytes()).hexdigest() == row['sha256']
assert len(expected) == 68
(E / 'harness-sha-check.json').write_text(json.dumps({'all_passed': True, 'files': expected}, indent=2))
Q = sorted(map(json.loads, (F / 'questions_frozen.jsonl').read_text().splitlines()), key=lambda x: x['cid'])
assert len(Q) == 40
(E / 'questions').mkdir(exist_ok=True)
qs = [{'qid': i, 'cid': q['cid'], 'question': q['question'] + '\n\nBuild assumptions: ' + q['build_assumptions']} for i, q in enumerate(Q)]
for name in ['all.jsonl', 'pilot.jsonl']:
    (E / 'questions' / name).write_text(''.join((json.dumps(q) + '\n' for q in qs)))
(E / 'questions/manifest.json').write_text(json.dumps({'sha256': hashlib.sha256((E / 'questions/all.jsonl').read_bytes()).hexdigest(), 'cid_order': [q['cid'] for q in qs]}, indent=2))
for arm in ['S', 'C0', 'C']:
    b = E / 'arms' / arm
    b.mkdir(parents=True, exist_ok=True)
    if not (b / 'repo').exists():
        shutil.copytree(R / 'eval/curl-2c04412', b / 'repo', ignore=shutil.ignore_patterns('.git', '__pycache__'))
    for p in (b / 'repo').rglob('*'):
        if p.is_file():
            p.chmod(292)
    hint = (old / 'arms' / arm / 'hint.txt').read_text().replace(str(old / 'arms' / arm), str(b))
    (b / 'hint.txt').write_text(hint)
    if arm != 'S':
        shutil.copytree(R / 'runs/e5/cbe-curl/run/docs', b / 'docs', dirs_exist_ok=True)
        for p in (b / 'docs').rglob('*'):
            if p.is_file():
                p.chmod(292)
    profile = (old / 'arms' / arm / 'sandbox.sb').read_text().replace(str(old / 'arms' / arm), str(b)).replace(str(R / 'codebase-explorer/.venv'), str(E / 'cbe-venv')).replace(str(old / 'cbe-pytest/run'), str(R / 'runs/e5/cbe-curl/run'))
    (b / 'sandbox.sb').write_text(profile)
    if arm == 'C':
        (b / 'bin').mkdir(exist_ok=True)
        w = (old / 'arms/C/bin/cbe').read_text().replace(str(R / 'codebase-explorer/.venv'), str(E / 'cbe-venv'))
        (b / 'bin/cbe').write_text(w)
        (b / 'bin/cbe').chmod(493)
        if not (b / 'run').exists():
            (b / 'run').symlink_to(R / 'runs/e5/cbe-curl/run', target_is_directory=True)
print('Prepared 40 questions, 3 isolated arms, harness68 match', flush=True)
