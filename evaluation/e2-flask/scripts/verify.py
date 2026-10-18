"""Independent recomputation of E2 structural invariants; no model calls."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, gzip, hashlib, json, statistics
from pathlib import Path
E = Path(__file__).resolve().parent
OLD = E.parent / 'e1'
read = lambda p: json.loads(p.read_text())
checks = {}
errors = []
qs = list(map(json.loads, (OLD / 'harness/Benchmark/flask.jsonl').read_text().splitlines()))
manifest = read(E / 'reuse-manifest.json')
checks['reuse_80_artifacts_unchanged'] = len(manifest) == 80 and all((hashlib.sha256(Path(r['source']).read_bytes()).hexdigest() == r['sha256'] and (E / r['kind'] / f"{r['arm']}-10-r0" / f"q{r['qid']:02}.json").resolve() == Path(r['source']).resolve() for r in manifest))
checks['toolhandler_21_smokes'] = read(E / 'tool-layer-smoke.json')['all_passed'] and len(read(E / 'tool-layer-smoke.json')['records']) == 21
checks['harness_SHA_unchanged'] = all((hashlib.sha256((OLD / 'harness' / r['path']).read_bytes()).hexdigest() == r['sha256'] for r in read(E / 'harness-sha-check.json')['files']))
key = os.environ['MAGPIE_API_KEY'].encode()
leaks = []
import secret_scan
scan_tests = secret_scan.self_test()
checks['secret_scanner_positive_and_negative'] = all(scan_tests.values())
scan_exemptions = []
for p in E.rglob('*'):
    if p.is_file() and (not p.is_symlink()) and (p.suffix in ['.json', '.jsonl', '.log', '.txt', '.md', '.csv', '.py', '.stdout']):
        data = p.read_bytes()
        found = secret_scan.scan(data, p.name)
        if found:
            leaks.append(str(p))
        elif key in data:
            scan_exemptions.append(str(p.relative_to(E)))
checks['harness_full_patch_SHA_proof'] = read(E / 'harness-sha-check.json')['full_patch_reconstruction']['all_passed'] and all((r.get('full_sha256_matches_reconstructed_E1', True) for r in read(E / 'harness-sha-check.json')['files']))
checks['no_literal_key_in_artifacts'] = not leaks
checks['all_raw_invariants'] = True
new_answers = new_judges = reused_answers = reused_judges = draws = 0
for arm in ['S', 'C0', 'C', 'W']:
    ap = list((E / 'answers' / f'{arm}-10-r0').glob('q*.json'))
    jp = list((E / 'judge' / f'{arm}-10-r0').glob('q*.json'))
    checks[f'{arm}_48_answers_48_judgments'] = len(ap) == len(jp) == 48
    checks[f'{arm}_all_qids'] = sorted((read(p)['qid'] for p in ap)) == list(range(48)) and sorted((read(p)['qid'] for p in jp)) == list(range(48))
    for p in ap:
        a = read(p)
        j = read(E / 'judge' / p.parent.name / p.name)
        new_answers += not p.is_symlink()
        reused_answers += p.is_symlink()
        try:
            assert a['question'] == qs[a['qid']]['question'] == j['question']
            assert a['arm'] == j['arm'] == arm and a['max_steps'] == j['max_steps'] == 10
            assert 1 <= len(a['attempts']) <= 3
            assert j['judge_model'] == 'codex/gpt-6.1-sol'
            assert a['valid'] == j['answer_valid']
            if a['valid']:
                assert len(j['draws']) == 3
                for d in j['draws']:
                    assert 1 <= len(d['calls']) <= 3
                    for c in d['calls']:
                        assert c['requested_model'] == 'codex/gpt-6.1-sol'
                if all((d['score'] is not None for d in j['draws'])):
                    expected = {k: statistics.median((d['score'][k] for d in j['draws'])) for k in ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning']}
                    assert expected == j['score'] and sum(expected.values()) == j['main_total_na5']
                else:
                    assert j['score'] is None and j['main_total_na5'] == 5
            else:
                assert j['score'] is None and j['main_total_na5'] == 5
        except (AssertionError, KeyError) as ex:
            checks['all_raw_invariants'] = False
            errors.append(str(p) + ': ' + str(ex))
    for p in jp:
        new_judges += not p.is_symlink()
        reused_judges += p.is_symlink()
        draws += len(read(p)['draws'])
checks['new_and_reuse_denominators'] = (new_answers, new_judges, reused_answers, reused_judges) == (152, 152, 40, 40)
sha = read(OLD / 'input-before.json')['sha256']
checks['all_four_source_copies'] = all((hashlib.sha256((OLD / 'arms' / arm / 'repo' / p).read_bytes()).hexdigest() == h for arm in ['S', 'C0', 'C', 'W'] for p, h in sha.items()))
hints = read(OLD / 'b2/archive-receipt.json')['hint_sha256']
checks['E1_hints_unchanged'] = all((hashlib.sha256((OLD / 'arms' / arm / 'hint.txt').read_bytes()).hexdigest() == h for arm, h in hints.items()))
checks['run_settled'] = (E / 'RUN-DONE.json').exists() and (not (E / 'RUN-FAILED.txt').exists())
checks['new_answers_152'] = read(E / 'RUN-DONE.json')['new_answers'] == 152 if checks['run_settled'] else False
checks['direct_D63_complete'] = (E / 'direct/DONE.json').exists() and (not (E / 'direct/FAILED.txt').exists())
checks['direct_48_raw_invariants'] = True
direct_new = direct_reuse = 0
if checks['direct_D63_complete']:
    direct_a = list((E / 'direct/answers').glob('q*.json'))
    direct_j = list((E / 'direct/judge').glob('q*.json'))
    checks['direct_48_denominators'] = len(direct_a) == len(direct_j) == 48 and sorted((read(p)['qid'] for p in direct_a)) == list(range(48)) and (sorted((read(p)['qid'] for p in direct_j)) == list(range(48)))
    for p in direct_a:
        a = read(p)
        j = read(E / 'direct/judge' / p.name)
        direct_new += not p.is_symlink()
        direct_reuse += p.is_symlink()
        try:
            assert a['question'] == qs[a['qid']]['question'] == j['question'] and a['arm'] == j['arm'] == 'direct'
            assert 1 <= len(a['attempts']) <= 3 and a['valid'] == j['answer_valid'] and (j['judge_model'] == 'codex/gpt-6.1-sol')
            if a['valid']:
                assert len(j['draws']) == 3
                for draw in j['draws']:
                    assert 1 <= len(draw['calls']) <= 3 and all((c['requested_model'] == 'codex/gpt-6.1-sol' for c in draw['calls']))
                if all((d['score'] for d in j['draws'])):
                    expected = {k: statistics.median((d['score'][k] for d in j['draws'])) for k in ['correctness', 'completeness', 'relevance', 'clarity', 'reasoning']}
                    assert expected == j['score'] and sum(expected.values()) == j['main_total_na5']
                else:
                    assert j['score'] is None and j['main_total_na5'] == 5
            else:
                assert j['score'] is None and j['main_total_na5'] == 5
        except (AssertionError, KeyError) as ex:
            checks['direct_48_raw_invariants'] = False
            errors.append(str(p) + ': ' + str(ex))
    checks['direct_38new_10reused'] = (direct_new, direct_reuse) == (38, 10)
    checks['direct_reuse_SHA'] = all((hashlib.sha256(Path(r['source']).read_bytes()).hexdigest() == r['sha256'] and (E / 'direct' / r['kind'] / f"q{r['qid']:02}.json").resolve() == Path(r['source']).resolve() for r in read(E / 'direct/reuse-manifest.json')))
    import ast
    source = (OLD / 'harness/Experiment/Script/llm_direct/main.py').read_text()
    node = next((n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'get_llm_answer'))
    checks['direct_original_prompt_function_unchanged'] = hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest() == read(E / 'direct/prompt-provenance.json')['function_sha256']
    checks['direct_after_main_judging'] = read(E / 'direct/start.json')['epoch'] >= read(E / 'RUN-DONE.json')['finished_epoch']
checks['D63_tool_limits_reproduced'] = read(E / 'limitations-tool-smoke.json')['all_passed']
checks['reduction_settled'] = (E / 'REDUCE-DONE.json').exists()
if checks['reduction_settled']:
    m = read(E / 'metrics.json')
    raw = {arm: {read(p)['qid']: read(p) for p in (E / 'judge' / f'{arm}-10-r0').glob('q*.json')} for arm in ['S', 'C0', 'C', 'W']}
    checks['group_means_recomputed'] = all((statistics.mean((j['main_total_na5'] for j in raw[arm].values())) == m['groups'][f'{arm}-10-r0']['mean_total_na5'] for arm in raw))
    checks['all_five_paired_points_recomputed'] = all((statistics.mean((raw[left][i]['main_total_na5'] - raw[right][i]['main_total_na5'] for i in range(48))) == m['all48']['pairs'][left + '-' + right]['mean'] for left, right in [('C', 'S'), ('C0', 'S'), ('C', 'C0'), ('C0', 'W'), ('C', 'W')]))
    direct = {read(p)['qid']: read(p) for p in (E / 'direct/judge').glob('q*.json')}
    dc = m['difficulty_calibration']
    checks['direct_median_recomputed'] = statistics.median((j['main_total_na5'] for j in direct.values())) == dc['median']
    checks['direct_strata_recomputed'] = True
    for split, threshold in [('median', dc['median']), ('threshold80', 80)]:
        for tier, high in [('high', True), ('low', False)]:
            ids = [i for i in range(48) if (direct[i]['main_total_na5'] >= threshold) == high]
            record = dc['strata'][split][tier]
            point = statistics.mean((raw['C'][i]['main_total_na5'] - raw['S'][i]['main_total_na5'] for i in ids)) if ids else None
            checks['direct_strata_recomputed'] &= record['qids'] == ids and record['C-S']['mean'] == point
out = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'all_author_checks_pass': all(checks.values()), 'checks': checks, 'errors': errors, 'leak_paths': leaks, 'secret_scan_exemptions': scan_exemptions, 'secret_scan_self_tests': scan_tests, 'new_answers': new_answers, 'new_judges': new_judges, 'reused_answers': reused_answers, 'reused_judges': reused_judges, 'judge_draws': draws, 'scope': 'Author structural verification and recomputation; independent acceptance and semantic reference-answer audit remain coordinator-owned.'}
(E / 'verification.json').write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
raise SystemExit(0 if out['all_author_checks_pass'] else 1)
