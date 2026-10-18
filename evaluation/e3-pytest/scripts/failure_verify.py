"""Verify a bounded failed-generation result; this does NOT certify QA completion."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import collections, csv, datetime, gzip, hashlib, json, os, subprocess
from pathlib import Path
from cbe.records import frozen_sources
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
O = E / 'cbe-pytest'

def read(p):
    if p.exists():
        return json.loads(p.read_text())
    with gzip.open(str(p) + '.gz', 'rt') as f:
        return json.load(f)
checks = []

def check(name, passed, detail=None):
    checks.append({'name': name, 'passed': bool(passed), 'detail': detail})
m = read(O / 'metrics.json')
state = read(O / 'run/host/state.json')
summary = m['summary']
phases = m['phases']
check('final generation incomplete', not m['complete'] and summary and (summary['status'] == 'partial'))
check('exactly first plus one resume', [p['phase'] for p in phases].count('first') == 1 and [p['phase'] for p in phases].count('resume') == 1)
check('module56 exhausted allowed attempts', state['tasks']['module_56']['status'] == 'failed' and state['tasks']['module_56']['attempts'] == 6, state['tasks']['module_56'].get('errors'))
check('module26 and53 recovered', all((state['tasks'][k]['status'] == 'done' for k in ['module_26', 'module_53'])))
check('source reassembly fallback zero', m['frozen_audit']['source_reassembly_fallback'] == 0 and m['frozen_audit']['ok'])
context = read(O / 'run/context.json')
sources = frozen_sources(context)
mismatches = [p for p, text in sources.items() if text.encode() != (R / 'eval/pytest-5989efe' / p).read_bytes()]
check('all225 frozen files reconstruct and match original', len(sources) == 225 and (not mismatches), {'files': len(sources), 'mismatches': mismatches})
head = subprocess.check_output(['git', '-C', str(R / 'eval-cbe2'), 'rev-parse', 'HEAD'], text=True).strip()
clean = subprocess.check_output(['git', '-C', str(R / 'eval-cbe2'), 'status', '--porcelain'], env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, text=True)
check('frozen code HEAD and clean worktree', head == m['commit'] and (not clean), {'head': head, 'status': clean})
for row in read(E / 'harness-sha-check.json')['files']:
    check('harness SHA ' + row['path'], hashlib.sha256((R / 'runs/e1/harness' / row['path']).read_bytes()).hexdigest() == row['sha256'])
manifest = []
for p in sorted((R / 'eval/pytest-5989efe').rglob('*')):
    if not p.is_file():
        continue
    rel = p.relative_to(R / 'eval/pytest-5989efe')
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    row = {'path': str(rel), 'input_sha256': digest, 'arms': {}}
    for arm in ['S', 'C0', 'C']:
        copy = E / 'arms' / arm / 'repo' / rel
        sha = hashlib.sha256(copy.read_bytes()).hexdigest()
        row['arms'][arm] = sha
        check(arm + ' source SHA ' + str(rel), sha == digest)
        check(arm + ' readonly ' + str(rel), copy.stat().st_mode & 146 == 0)
    manifest.append(row)
(E / 'arm-source-sha256.json').write_text(json.dumps(manifest, indent=2))
check('249 source files in each prepared copy', len(manifest) == 249)
first = read(O / 'first-summary.json')
first_calls = list(csv.DictReader((O / 'first-calls.csv').open()))
snap = read(O / 'first-round-snapshot.json')
check('first151 calls preserved', len(first_calls) == first['calls'] == 151)
check('first303 snapshots intact', len(snap['records']) == 303 and all((hashlib.sha256((O / r['snapshot']).read_bytes()).hexdigest() == r['sha256'] for r in snap['records'])))
check('no swapped or wrong generation model', not m['gateway']['identity_anomalies'], {'unknown_served': m['gateway']['unknown_served']})
check('gateway versus summary requests and usage', all((v == 0 for v in m['gateway_minus_summary'].values())), m['gateway_minus_summary'])
check('limitations smoke through ToolHandler', read(E / 'limitations-tool-smoke.json')['all_passed'])
counts = {'main_answers': len(list((E / 'answers').glob('*/q*.json'))), 'main_judged': len(list((E / 'judge').glob('*/q*.json'))), 'direct_answers': len(list((E / 'direct/answers').glob('q*.json'))), 'direct_judged': len(list((E / 'direct/judge').glob('q*.json')))}
check('QA was not run from incomplete docs', all((v == 0 for v in counts.values())) and (not (E / 'run-start.json').exists()), counts)
check('C run/docs not attached', not (E / 'arms/C/run').exists() and all((not (E / 'arms' / arm / 'docs').exists() for arm in ['C0', 'C'])))
check('no invented comparative result', not (E / 'metrics.json').exists() and (not (E / 'REDUCE-DONE.json').exists()))
key = os.environ['MAGPIE_API_KEY'].encode()
leaks = []
for p in E.rglob('*'):
    if p.is_symlink() or p.relative_to(E).parts[0] in ('harness', 'venv') or (not p.is_file()):
        continue
    opener = gzip.open if p.suffix == '.gz' else open
    with opener(p, 'rb') as stream:
        tail = b''
        while (chunk := stream.read(1024 * 1024)):
            data = tail + chunk
            if key in data:
                leaks.append(str(p.relative_to(E)))
                break
            tail = data[-(len(key) - 1):] if len(key) > 1 else b''
check('credential absent from owned artifacts', not leaks, leaks)
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'level': 'Author verification of failed generation and unperformed QA; not task success; independent coordinator acceptance pending', 'requested_experiment_complete': False, 'all_passed': all((c['passed'] for c in checks)), 'qa_records': counts, 'checks': checks, 'artifact_sha256': {str(p.relative_to(E)): hashlib.sha256(p.read_bytes()).hexdigest() for p in E.glob('*.py')}}
(E / 'verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'failure_evidence_verified': result['all_passed'], 'requested_experiment_complete': False, 'checks': len(checks), 'failed': [c for c in checks if not c['passed']]}, indent=2))
raise SystemExit(0 if result['all_passed'] else 1)
