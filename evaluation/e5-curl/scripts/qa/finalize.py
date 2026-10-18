"""Bounded background finalization; never sends worker_done."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, gzip, hashlib, json, os, subprocess, time, traceback
from pathlib import Path
E = Path(__file__).resolve().parent
R = E.parents[2]
py = str(E / 'venv/bin/python')
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
try:
    for _ in range(4320):
        if (E / 'PIPELINE-FAILED.txt').exists():
            raise RuntimeError('Production pipeline failed; preserve artifacts and await coordinator handling')
        if (E / 'PIPELINE-DONE.json').exists():
            break
        time.sleep(5)
    else:
        raise TimeoutError('Production did not settle within six hours')
    for name in ['gateway.py', 'reduce.py']:
        with (E / (name + '.log')).open('w') as log:
            subprocess.run([py, str(E / name)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    evidence = {}
    F = R / 'runs/e5q/freeze'
    for p in (E / 'answers').glob('*/q*.json'):
        a = json.loads(p.read_text())
        jp = E / 'judge' / p.parent.name / p.name
        rub = E / 'rubric' / p.parent.name / p.name
        if not jp.exists():
            assert p.parent.name in ('S-25-r0', 'C-25-r0') and (not rub.exists())
            d = E / 'review' / p.parent.name / p.stem
            d.mkdir(parents=True, exist_ok=True)
            (d / 'question.txt').write_text(a['question'])
            (d / 'answer.txt').write_text(a['answer'])
            (d / 'UNJUDGED.json').write_text(json.dumps({'reason': 'Secondary judge budget stopped at a whole S/C pair boundary', 'not_NA_scored': True}, indent=2))
            continue
        j = json.loads(jp.read_text())
        r = json.loads(rub.read_text()) if rub.exists() else None
        if not a['valid'] or j['score'] is None or (r is not None and r.get('status') != 'ok'):
            d = E / 'review' / p.parent.name / p.stem
            d.mkdir(parents=True, exist_ok=True)
            (d / 'NA.json').write_text(json.dumps({'answer_valid': a['valid'], 'five_failure': j['failure_type'], 'rubric_status': r.get('status') if r else 'not_applicable_direct', 'rule': 'No fabricated judge text; missing raw replicates for no-answer NA are intentional'}, indent=2))
    bill = json.loads((E / 'gateway-usage.json').read_text())
    client = json.loads((E / 'STATUS.json').read_text())['usage']
    session_map = {'answer_main': 'e5-answer-main', 'answer_sec': 'e5-answer-main-sec', 'five_main': 'e5-fivedim-main', 'five_sec': 'e5-fivedim-main-sec', 'rubric_main': 'e5-rubric-main', 'rubric_sec': 'e5-rubric-main-sec', 'direct': 'e5-direct', 'five_direct': 'e5-fivedim-direct'}
    ledger = {}
    for name, session in session_map.items():
        c = client[name]
        b = bill[session]
        ledger[name] = {'client_observed_input_including_cache': c['input'], 'client_observed_output': c['output'], 'client_unknown_usage': c['unknown_usage'], 'gateway_requests': b['requests'], 'gateway_input_including_cache': b['input_tokens'] + b['cache_read_tokens'], 'gateway_output': b['output_tokens'], 'gateway_minus_client_input': b['input_tokens'] + b['cache_read_tokens'] - c['input'], 'gateway_minus_client_output': b['output_tokens'] - c['output'], 'session': session}
    (E / 'accounting.json').write_text(json.dumps(ledger, indent=2))
    evidence['secondary_pairing'] = len({tuple(sorted((p.name for p in (E / kind / f'{arm}-25-r0').glob('q*.json')))) for kind in ['judge', 'rubric'] for arm in ['S', 'C']}) == 1
    evidence['freeze'] = all((hashlib.sha256((F / n).read_bytes()).hexdigest() == h for h, n in (line.split(maxsplit=1) for line in (F / 'MANIFEST.sha256').read_text().splitlines())))
    evidence['harness'] = all((hashlib.sha256((E / 'harness' / row['path']).read_bytes()).hexdigest() == row['sha256'] for row in json.loads((E / 'harness-sha-check.json').read_text())['files']))
    evidence['eval_cbe_clean'] = subprocess.check_output(['git', '-C', str(R / 'eval-cbe2'), 'status', '--porcelain'], text=True) == ''
    evidence['private_python'] = subprocess.check_output([str(E / 'cbe-venv/bin/python'), '--version'], text=True).strip() == 'Python 3.12.13'
    evidence['wrapper'] = hashlib.sha256((E / 'arms/C/bin/cbe').read_bytes()).hexdigest() == json.loads((E / 'environment-provenance.json').read_text())['wrapper_sha256']
    evidence['gateway_models'] = not any((x['identity_anomalies'] for x in json.loads((E / 'gateway-usage.json').read_text()).values()))
    key = os.environ['MAGPIE_API_KEY'].encode()
    from credential_check import scan
    credential_audit = scan(E, key)
    (E / 'credential-scan.json').write_text(json.dumps(credential_audit, indent=2))
    evidence['credential_scan_files'] = credential_audit['files_scanned']
    evidence['credentials_absent'] = not credential_audit['credential_values_persisted']
    evidence['public_identifier_exceptions'] = credential_audit['public_identifier_exceptions']
    assert all((v for k, v in evidence.items() if isinstance(v, bool))), evidence
    (E / 'final-verification.json').write_text(json.dumps(evidence, indent=2))
    compressed = []
    for root in ['answers', 'judge', 'rubric', 'review']:
        for p in (E / root).rglob('*.json'):
            if p.stat().st_size > 10000000:
                raw = p.read_bytes()
                dest = p.with_suffix(p.suffix + '.gz')
                with gzip.open(dest, 'wb') as f:
                    f.write(raw)
                compressed.append({'path': str(p.relative_to(E)), 'gzip': str(dest.relative_to(E)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
                p.unlink()
    (E / 'compression.json').write_text(json.dumps({'files': compressed, 'context_catalog': 'Protected E5a run left plaintext and unchanged'}, indent=2))
    with (E / 'render.log').open('w') as log:
        subprocess.run([py, str(E / 'render.py')], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    (E / 'FINALIZE-DONE.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'verification': evidence}, indent=2))
except BaseException:
    (E / 'FINALIZE-FAILED.txt').write_text(traceback.format_exc())
    raise
