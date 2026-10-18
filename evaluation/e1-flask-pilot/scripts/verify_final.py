"""Author-side E1 verification from raw artifacts; independent acceptance remains coordinator-owned."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import ast, collections, csv, datetime, hashlib, io, json, statistics, subprocess, sys, tarfile
from pathlib import Path
E = Path(__file__).resolve().parent
R = E.parent.parent
sys.path.insert(0, str(E / 'harness/Experiment/Script/SWE-agent_QA'))
from local_env import LocalEnv
checks = {}
details = {}
refs = [json.loads(l) for l in (E / 'harness/Benchmark/flask.jsonl').read_text().splitlines()]
sample = json.loads((E / 'questions/sample.json').read_text())['qids']
subset25 = json.loads((E / 'questions/sample25.json').read_text())['qids'] if (E / 'questions/sample25.json').exists() else sample
expected = {str(p.relative_to(R / 'eval/flask-85c5d93')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (R / 'eval/flask-85c5d93').rglob('*') if p.is_file()}
checks['frozen_commit'] = subprocess.check_output(['git', '-C', str(R / 'eval-cbe'), 'rev-parse', '--short', 'HEAD'], text=True).strip() == '9c6499e'
checks['frozen_tracked_clean'] = not subprocess.check_output(['git', '-C', str(R / 'eval-cbe'), 'status', '--porcelain'], text=True).strip()
source_archive = subprocess.check_output(['git', '-C', str(R / 'eval-cbe'), 'archive', '9c6499e', 'src'])
with tarfile.open(fileobj=io.BytesIO(source_archive)) as tar:
    checks['frozen_source_bytes_match_commit'] = all(((R / 'eval-cbe' / member.name).read_bytes() == tar.extractfile(member).read() for member in tar.getmembers() if member.isfile()))
details['ignored_bytecode_observation'] = [{'path': str(p.relative_to(R / 'eval-cbe')), 'mtime_utc': datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).isoformat()} for p in (R / 'eval-cbe').rglob('*.pyc')]
checks['upstream_commit'] = subprocess.check_output(['git', '-C', os.path.expandvars('$HOME/clones/eval_research_20261017/SWE-QA-Bench'), 'rev-parse', '--short', 'HEAD'], text=True).strip() == 'c13deac'

def judge_prompt_ast(path):
    tree = ast.parse(path.read_text())
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'score_answer'))
    value = next((n.value for n in fn.body if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'prompt' for t in n.targets))))
    return ast.dump(value, include_attributes=False)
checks['original_judge_rubric_unchanged'] = judge_prompt_ast(Path(os.path.expandvars('$HOME/clones/eval_research_20261017/SWE-QA-Bench/Benchmark construction/score/llm-as-a-judge.py'))) == judge_prompt_ast(E / 'harness/Benchmark construction/score/llm-as-a-judge.py')
checks['source_identical'] = all(({str(p.relative_to(E / 'arms' / a / 'repo')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (E / 'arms' / a / 'repo').rglob('*') if p.is_file()} == expected for a in ['S', 'C0', 'C', 'W']))
checks['no_git_in_arms'] = not list((E / 'arms').glob('*/repo/.git'))

def docs_hash(arm):
    base = E / 'arms' / arm / 'docs'
    return {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*.md')}
checks['C0_C_docs_identical'] = bool(docs_hash('C')) and docs_hash('C0') == docs_hash('C')
checks['W_published_markdown_only'] = all((p.suffix == '.md' for p in (E / 'arms/W/docs').rglob('*') if p.is_file()))
judge_selected = json.loads((E / 'judge/model-probe.json').read_text())['selected'].split('/', 1)[-1]
checks['judge_model_identity'] = True
folders = [f'{a}-{s}-r0' for a in ['S', 'C0', 'C'] for s in [10, 25]] + ['S-10-r1', 'S-10-r2', 'direct']
w_present = len(list((E / 'answers/W-10-r0').glob('q*.json'))) == len(sample) and len(list((E / 'answers/W-25-r0').glob('q*.json'))) == len(subset25)
if w_present:
    folders += ['W-10-r0', 'W-25-r0']
w_ready = json.loads((E / 'W-READY.json').read_text()) if (E / 'W-READY.json').exists() else None
checks['W_ready_consumed_or_not_complete'] = w_present and w_ready is not None and (w_ready.get('complete') is True) or (not w_present and (w_ready is None or w_ready.get('complete') is False))
details['W_readiness'] = w_ready
checks['question_invariant'] = True
checks['answer_denominators'] = True
checks['judge_denominators'] = True
checks['three_judge_draws_or_explicit_NA'] = True
checks['dimension_medians_recomputed'] = True
checks['retry_bounds'] = True
received_model_calls = 0
for name in folders:
    paths = sorted((E / 'answers' / name).glob('q*.json'))
    need = sample[:5] if name in ('S-10-r1', 'S-10-r2') else subset25 if name in ('C-25-r0', 'W-25-r0') else sample
    checks['answer_denominators'] &= {json.loads(p.read_text())['qid'] for p in paths} == set(need)
    details[name] = {'answer_count': len(paths), 'judge_count': 0, 'valid': 0}
    for p in paths:
        a = json.loads(p.read_text())
        received_model_calls += sum((sum((msg.get('role') == 'assistant' for msg in attempt.get('history', []))) for attempt in a['attempts'])) + sum((bool(attempt.get('usage')) for attempt in a['attempts'] if name == 'direct'))
        checks['question_invariant'] &= a['question'] == refs[a['qid']]['question']
        checks['retry_bounds'] &= 1 <= len(a['attempts']) <= 3
        details[name]['valid'] += int(a['valid'])
        if not a['valid']:
            checks['retry_bounds'] &= len(a['attempts']) == 3
        jp = E / 'judge' / name / p.name
        if not jp.exists():
            checks['judge_denominators'] = False
            continue
        j = json.loads(jp.read_text())
        details[name]['judge_count'] += 1
        if a['valid']:
            checks['judge_model_identity'] &= all((c.get('response_model', judge_selected).split('/', 1)[-1] == judge_selected for d in j['draws'] for c in d['calls'] if 'error' not in c))
            checks['three_judge_draws_or_explicit_NA'] &= len(j['draws']) == 3
            scores = [d['score'] for d in j['draws']]
            if all(scores):
                checks['three_judge_draws_or_explicit_NA'] &= all((set(s) == {'correctness', 'completeness', 'relevance', 'clarity', 'reasoning'} and all((isinstance(v, int) and (not isinstance(v, bool)) and (1 <= v <= 20) for v in s.values())) for s in scores))
                recomputed = {k: statistics.median((s[k] for s in scores)) for k in ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning']}
                checks['dimension_medians_recomputed'] &= j['score'] == recomputed and j['total'] == sum(recomputed.values()) and (j['judge_total_range'] == max((sum(s.values()) for s in scores)) - min((sum(s.values()) for s in scores)))
            else:
                checks['three_judge_draws_or_explicit_NA'] &= j['failure_type'] == 'judge_failure' and j['score'] is None
        else:
            checks['three_judge_draws_or_explicit_NA'] &= j['failure_type'] == 'no_answer' and j['main_total_na5'] == 5
phase_rows = [json.loads(line) for line in (E / 'cbe-flask/phases.jsonl').read_text().splitlines()]
earliest = min((datetime.datetime.fromisoformat(p['start_utc']) for p in phase_rows))
gateway_rows = [r for r in csv.DictReader((E / 'usage-final.csv').open()) if r.get('agent') == 'OpenAI' and r.get('requested_model') == 'zai/glm-5.3-flash' and (datetime.datetime.fromisoformat(r['time'].replace('Z', '+00:00')) >= earliest)]
bad_models = [{k: r.get(k) for k in ['time', 'request_id', 'requested_model', 'served_model', 'swapped', 'status']} for r in gateway_rows if r.get('swapped', 'false').lower() == 'true' or (r.get('served_model') and r['served_model'].rsplit('/', 1)[-1].casefold() != 'glm-5.3-flash')]
model_audit = {'scope': 'All OpenAI-agent GLM requests since first E1 phase; known mixed callers include CodeWiki raw OpenAI clustering/parent/overview stages, so this is not an answer-usage attribution', 'gateway_requests': len(gateway_rows), 'received_model_calls_minimum': received_model_calls, 'served_models': dict(collections.Counter((r.get('served_model') for r in gateway_rows))), 'statuses': dict(collections.Counter((r.get('status') for r in gateway_rows))), 'model_mismatches': bad_models}
(E / 'model-identity-audit.json').write_text(json.dumps(model_audit, indent=2))
checks['answer_gateway_coverage'] = len(gateway_rows) >= received_model_calls and received_model_calls > 0
checks['answer_no_model_substitution'] = not bad_models
probes = []
for arm in ['S', 'C0', 'C', 'W']:
    env = LocalEnv(E / 'arms' / arm / 'repo')
    tests = {'source_read': '/bin/cat src/flask/__init__.py', 'reference_read': '/bin/cat ' + str(E / 'harness/Benchmark/flask.jsonl'), 'secret_read': '/bin/cat $HOME/.cbe-denied-secret', 'cross_arm_read': '/bin/cat ' + str(E / 'arms' / ('C' if arm == 'S' else 'S') / 'repo/src/flask/__init__.py'), 'write': 'echo denied > must-not-exist', 'network': '/usr/bin/curl --max-time 2 http://127.0.0.1:3425/v1/models'}
    if arm != 'S' and (E / 'arms' / arm / 'docs').exists():
        tests['docs_read'] = '/bin/cat ' + str(next((E / 'arms' / arm / 'docs').rglob('*.md')))
    for name, cmd in tests.items():
        output = env.communicate(cmd)
        rc = env.commands[-1]['returncode']
        ok = rc == 0 if name in ('source_read', 'docs_read') else rc != 0
        probes.append({'arm': arm, 'test': name, 'returncode': rc, 'ok': ok})
    if arm == 'C' and (E / 'arms/C/run/catalog.json').exists():
        cmd = str(E / 'arms/C/bin/cbe') + ' find --run-dir ' + str(E / 'arms/C/run') + ' --term RequestContext --limit 1'
        text = env.communicate(cmd)
        probes.append({'arm': arm, 'test': 'cbe_find', 'returncode': env.commands[-1]['returncode'], 'ok': env.commands[-1]['returncode'] == 0 and 'RequestContext' in text})
        cmd = str(E / 'arms/C/bin/cbe') + ' query --run-dir ' + str(E / 'arms/C/run') + ' --id src/flask/ctx.py'
        text = env.communicate(cmd)
        probes.append({'arm': arm, 'test': 'cbe_query', 'returncode': env.commands[-1]['returncode'], 'ok': env.commands[-1]['returncode'] == 0 and 'src/flask/ctx.py' in text})
checks['sandbox_all_arms'] = all((r['ok'] for r in probes))
checks['C0_W_prompt_correspondence'] = (E / 'arms/C0/hint.txt').read_text().replace('/C0/docs', '/W/docs') == (E / 'arms/W/hint.txt').read_text()
checks['blind_guess_20'] = json.loads((E / 'blind-arm-guess/result.json').read_text()).get('n') == 20 if (E / 'blind-arm-guess/result.json').exists() else False
checks['cbe_complete_verified'] = json.loads((E / 'cbe-flask/run/summary.json').read_text()).get('status') == 'complete' and json.loads((E / 'cbe-flask/run/summary.json').read_text()).get('deterministic_checks_ok') is True
accounting = json.loads((E / 'cbe-flask/accounting.json').read_text())
checks['cbe_gateway_attribution_complete'] = accounting['attribution_complete']
checks['cbe_no_model_substitution'] = not accounting['model_mismatches'] and (not accounting['raw_model_mismatches'])
key = os.environ['MAGPIE_API_KEY'].encode()
leaks = []
selector_exemptions = []
public_cli_exemptions = []

def scan_bytes(data, is_python=False, is_json=False):
    if is_json:
        obj = json.loads(data)
        command = obj.get('command') if isinstance(obj, dict) else None
        if isinstance(command, list) and len(command) == 5 and (command[:4] == ['magpie', 'usage', '--csv', '--last']):
            obj['command'] = ['<PUBLIC_USAGE_EXECUTABLE>', *command[1:]]
            data = json.dumps(obj, ensure_ascii=False).encode()
    if is_python:
        tree = ast.parse(data.decode())
        line_starts = [0]
        for line in data.splitlines(keepends=True):
            line_starts.append(line_starts[-1] + len(line))
        spans = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            chain = []
            cur = node
            while isinstance(cur, ast.Subscript) and isinstance(cur.slice, ast.Constant) and isinstance(cur.slice.value, str):
                chain.append(cur.slice)
                cur = cur.value
            if [n.value for n in reversed(chain)] == ['providers', 'magpie', 'apiKey']:
                for n in chain:
                    spans.add((line_starts[n.lineno - 1] + n.col_offset, line_starts[n.end_lineno - 1] + n.end_col_offset))
        for start, end in spans:
            data = data[:start] + bytes(end - start) + data[end:]
    return key in data
self_test = {'in_memory_literal_detected': scan_bytes(b'credential = ' + repr(key.decode()).encode(), True), 'static_selector_not_credential': not scan_bytes(b'config["providers"]["magpie"]["apiKey"]', True), 'public_usage_argv_not_credential': not scan_bytes(json.dumps({'command': ['magpie', 'usage', '--csv', '--last', '306m']}).encode(), is_json=True), 'credential_beside_public_argv_detected': scan_bytes(json.dumps({'command': ['magpie', 'usage', '--csv', '--last', '306m'], 'credential': key.decode()}).encode(), is_json=True)}
checks['secret_scanner_positive_and_negative'] = all(self_test.values())

def scan_file(p):
    data = p.read_bytes()
    found = scan_bytes(data, p.suffix == '.py', p.suffix == '.json')
    if key in data and (not found):
        (selector_exemptions if p.suffix == '.py' else public_cli_exemptions).append(str(p.relative_to(E)))
    return found
for folder in ['answers', 'judge', 'cbe-flask', 'blind-arm-guess', 'arms']:
    for p in (E / folder).rglob('*'):
        if p.is_file() and p.suffix in ('.json', '.jsonl', '.csv', '.log', '.md', '.txt') and (p.stat().st_size < 150000000):
            if scan_file(p):
                leaks.append(str(p.relative_to(E)))
for p in E.iterdir():
    if p.is_file() and p.name.startswith(('pilot-', 'cbe-driver', 'judge', 'watch-judge', 'pipeline', 'finish-pipeline', 'usage-', 'accounting', 'metrics', 'guess_arms.py.', 'reduce.py.', 'verify_final.py.', 'render_report.py.')) and (p.stat().st_size < 150000000):
        if scan_file(p):
            leaks.append(str(p.relative_to(E)))
checks['no_key_in_artifacts'] = not leaks
details['secret_scan_static_selector_exemptions'] = selector_exemptions
details['secret_scan_public_cli_argv_exemptions'] = public_cli_exemptions
details['secret_scan_self_test'] = self_test
result = {'all_author_checks_pass': all(checks.values()), 'checks': checks, 'groups': details, 'sandbox_probes': probes, 'key_leak_paths': leaks, 'level': 'author self-verification; independent acceptance and reference-answer source review belong to coordinator'}
(E / 'final-verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
