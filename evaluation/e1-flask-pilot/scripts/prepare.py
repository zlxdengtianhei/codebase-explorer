import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, shutil, os, random, collections
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e1'
levels = [2, 2, 4, 4, 3, 3, 2, 3, 3, 2, 4, 4, 2, 3, 2, 3, 2, 2, 3, 4, 3, 2, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 4, 3, 3, 3, 2, 2, 3, 1, 3, 3, 3, 3, 3, 4]
rows = [json.loads(x) for x in (E / 'harness/Benchmark/flask.jsonl').read_text().splitlines()]
labels = [{'qid': i, 'swe_type': r['question'].split()[0], 'layer': levels[i], 'reason': {1: 'Locate a named class or definition.', 2: 'Explain a local method, parameter, or algorithm.', 3: 'Trace calls, data, contexts, or deferred registration across units.', 4: 'Explain architectural choice, tradeoff, coupling, or performance implication.'}[levels[i]]} for i, r in enumerate(rows)]
(E / 'questions').mkdir(exist_ok=True)
(E / 'questions/labels.json').write_text(json.dumps({'method': 'Manual semantic annotation from original questions only. Layer precedence: design/impact > cross-unit flow > unit behavior > definition location; Where does not automatically mean layer 1. Zero-based qid is original JSONL row.', 'labels': labels}, indent=2))
rng = random.Random(20261017)
selected = []
allocation = {}
for typ, n in [('What', 3), ('How', 3), ('Why', 2), ('Where', 2)]:
    pool = [x for x in labels if x['swe_type'] == typ]
    if typ == 'Where':
        selected.append(41)
        pool = [x for x in pool if x['qid'] != 41]
        n -= 1
    strata = collections.defaultdict(list)
    for x in pool:
        strata[x['layer']].append(x['qid'])
    quotas = {k: int(len(v) * n / len(pool)) for k, v in strata.items()}
    order = sorted(strata, key=lambda k: (-(len(strata[k]) * n / len(pool) - quotas[k]), k))
    for k in order[:n - sum(quotas.values())]:
        quotas[k] += 1
    allocation[typ] = quotas
    for k, v in sorted(strata.items()):
        selected.extend(rng.sample(v, quotas[k]))
selected.sort()
(E / 'questions/sample.json').write_text(json.dumps({'seed': 20261017, 'qid_base': 0, 'qids': selected, 'design': 'Type quotas What/How/Why/Where = 3/3/2/2. Sole layer-1 q41 included with certainty; remaining quotas use largest-remainder allocation by layer inside type, random sample within cells.', 'allocation': allocation}, indent=2))
(E / 'questions/pilot.jsonl').write_text(''.join((json.dumps({'qid': i, 'question': rows[i]['question']}) + '\n' for i in selected)))
for tool in ['cat', 'grep', 'ls', 'find', 'head', 'tail', 'wc', 'sort', 'cut', 'tr', 'awk', 'sed', 'xargs', 'env', 'pwd', 'echo', 'true', 'false']:
    src = next((Path(p) / tool for p in ['/usr/bin', '/bin'] if (Path(p) / tool).exists()), None)
    dest = E / 'venv/bin' / tool
    if src and (not dest.exists()):
        dest.symlink_to(src)
for arm in ['S', 'C0', 'C', 'W']:
    base = E / 'arms' / arm
    base.mkdir(parents=True, exist_ok=True)
    if not (base / 'repo').exists():
        shutil.copytree(R / 'eval/flask-85c5d93', base / 'repo', ignore=shutil.ignore_patterns('.git', '__pycache__'))
    for p in (base / 'repo').rglob('*'):
        if p.is_file():
            p.chmod(292)
    allow = ['/bin', '/sbin', '/usr', '/System', '/Library/Apple', '/Library/Developer/CommandLineTools', str(E / 'venv'), '/opt/homebrew/Cellar/python@3.12', '/opt/homebrew/opt/python@3.12', '/opt/homebrew/Cellar/python@3.14', '/opt/homebrew/opt/python@3.14', str(base / 'repo')]
    if arm != 'S':
        allow.append(str(base / 'docs'))
    if arm == 'C':
        allow += [str(base / 'run'), str(base / 'bin'), str(R / 'eval-cbe/src'), str(R / 'codebase-explorer/.venv')]
    profile = '(version 1)\n(allow default)\n(deny network*)\n(deny file-read*)\n(deny file-write*)\n(allow file-read-metadata)\n'
    profile += '(allow file-read* ' + ' '.join(('(subpath ' + json.dumps(x) + ')' for x in allow)) + ')\n'
    profile += '(allow file-read* (literal "/") (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random") (literal "/private/etc/localtime") (subpath "/private/var/db/dyld"))\n(allow file-write* (literal "/dev/null"))\n'
    (base / 'sandbox.sb').write_text(profile)
    hint = '' if arm == 'S' else f'Repository documentation is available at {base}/docs.'
    if arm == 'C':
        (base / 'bin').mkdir(exist_ok=True)
        wrapper = base / 'bin/cbe'
        wrapper.write_text('#!/bin/sh\nexport PYTHONPATH=' + str(R / 'eval-cbe/src') + '\nexport PYTHONDONTWRITEBYTECODE=1\nexec ' + str(R / 'codebase-explorer/.venv/bin/python') + ' -m cbe "$@"\n')
        wrapper.chmod(493)
        hint += f' You may use {wrapper} query --run-dir {base}/run and {wrapper} find --run-dir {base}/run to locate relevant source code. Use --help to inspect arguments.'
    (base / 'hint.txt').write_text(hint)
print('Sample qids:', selected)
