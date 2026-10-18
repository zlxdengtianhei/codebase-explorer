"""Deterministic deliverable checks against original artifacts."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import gzip, hashlib, json, statistics
from pathlib import Path
E = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text())
checks = []

def check(name, ok):
    checks.append({'name': name, 'passed': bool(ok)})
    assert ok, name
sample = read(E / 'sample.json')
ids = sample['q24']
dims = ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning']
h = read(E / 'harness-sha-check.json')
check('harness frozen SHA and patch reconstruction', h['all_passed'] and h['full_patch_reconstruction']['all_passed'])
for row in h['files']:
    check('current frozen harness SHA ' + row['path'], hashlib.sha256((E.parent / 'e1/harness' / row['path']).read_bytes()).hexdigest() == row['sha256'])
check('actual ToolHandler smoke 21 tests', read(E / 'tool-layer-smoke.json')['all_passed'] and len(read(E / 'tool-layer-smoke.json')['records']) == 21)
for item in read(E / 'reuse-manifest.json'):
    p = Path(item['source'])
    check('reuse SHA ' + item['kind'] + item['arm'] + str(item['qid']), hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'])
qs = {r['qid']: r['question'] for r in map(json.loads, (E / 'questions/all.jsonl').read_text().splitlines())}
for arm in ['S', 'C0', 'C', 'W']:
    ap = sorted((E / 'answers' / f'{arm}-25-r0').glob('q*.json'))
    jp = sorted((E / 'judge' / f'{arm}-25-r0').glob('q*.json'))
    check(arm + ' exact question denominator', [read(p)['qid'] for p in ap] == ids and [read(p)['qid'] for p in jp] == ids)
    for a_path, j_path in zip(ap, jp):
        a = read(a_path)
        j = read(j_path)
        check(str(a_path.relative_to(E)) + ' question/steps', a['question'] == qs[a['qid']] and a['max_steps'] == 25)
        check('answer retry upper bound', 1 <= len(a['attempts']) <= 3)
        check('judge retry upper bound', len(j['draws']) <= 3 and all((len(d['calls']) <= 3 for d in j['draws'])))
        check(str(j_path.relative_to(E)) + ' model', j['judge_model'] == 'codex/gpt-6.1-sol')
        if j['score']:
            check(str(j_path.relative_to(E)) + ' three-draw dimension medians', len(j['draws']) == 3 and all((j['score'][d] == statistics.median((x['score'][d] for x in j['draws'])) for d in dims)) and (j['main_total_na5'] == sum(j['score'].values())))
        else:
            check(str(j_path.relative_to(E)) + ' NA=5', j['main_total_na5'] == 5)
        for draw in j['draws']:
            if draw['score']:
                check('rubric dimension bounds', all((isinstance(draw['score'][d], int) and 1 <= draw['score'][d] <= 20 for d in dims)))
            for call in draw['calls']:
                check('judge requested model', call['requested_model'] == 'codex/gpt-6.1-sol')
new = [p for p in (E / 'answers').glob('*/q*.json') if not p.is_symlink()]
check('66 new answers', len(new) == 66)
check('new arm counts', [sum((p.parent.name == f'{a}-25-r0' for p in new)) for a in ['S', 'C0', 'C', 'W']] == [14, 14, 19, 19])
m = read(E / 'metrics.json')
check('bootstrap seed', m['bootstrap']['seed'] == 20261017)
check('sensitivity denominators', [m['sensitivity'][s]['C-S']['n'] for s in ['exclude_pilot', 'exclude_q32', 'exclude_q4_11_47']] == [14, 23, 21])
check('all 24 paired contrasts', all((p['n'] == 24 for p in m['all24'].values())))
old = E.parent / 'e1'
source_sha = read(old / 'input-before.json')['sha256']
hints = read(old / 'b2/archive-receipt.json')['hint_sha256']
check('four source copies unchanged', all((hashlib.sha256((old / 'arms' / arm / 'repo' / p).read_bytes()).hexdigest() == h for arm in ['S', 'C0', 'C', 'W'] for p, h in source_sha.items())))
check('frozen hints unchanged', all((hashlib.sha256((old / 'arms' / arm / 'hint.txt').read_bytes()).hexdigest() == h for arm, h in hints.items())))
raw = {arm: {read(p)['qid']: read(p)['main_total_na5'] for p in (E / 'judge' / f'{arm}-25-r0').glob('q*.json')} for arm in ['S', 'C0', 'C', 'W']}
check('raw group means recomputed', all((sum(raw[arm].values()) / 24 == m['groups'][f'{arm}-25-r0']['mean_total_na5'] for arm in raw)))
check('raw paired points recomputed', all((sum((raw[l][i] - raw[r][i] for i in ids)) / 24 == m['all24'][l + '-' + r]['mean'] for l, r in [('C', 'S'), ('C0', 'S'), ('C', 'C0'), ('C0', 'W'), ('C', 'W')])))
check('run settled', (E / 'RUN-DONE.json').exists() and (not (E / 'RUN-FAILED.txt').exists()))
import importlib.util
spec = importlib.util.spec_from_file_location('frozen_secret_scan', E.parent / 'e2/secret_scan.py')
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
check('credential scanner positive and negative controls', all(scanner.self_test().values()))
leaks = []
scan_paths = [p for p in E.rglob('*') if p.is_file() and (not p.is_symlink()) and (p.suffix in ['.json', '.jsonl', '.log', '.txt', '.md', '.csv', '.py', '.stdout'])]
report = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/opt_e2/e2b_result.md'))
if report.exists():
    scan_paths.append(report)
for p in scan_paths:
    if scanner.scan(p.read_bytes(), p.name):
        leaks.append(str(p))
check('no literal credential in local artifacts or report', not leaks)
(E / 'verification.json').write_text(json.dumps({'all_passed': True, 'checks': checks, 'scope': 'Deterministic author checks; coordinator independent acceptance pending'}, indent=2))
print('All', len(checks), 'checks passed')
