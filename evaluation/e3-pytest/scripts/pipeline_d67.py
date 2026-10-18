"""D-67 pipeline: final original artifact, verify receipt, real tool smoke, then full QA."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, hashlib, json, os, shutil, subprocess, time, traceback
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
O = E / 'cbe-pytest'
run = O / 'run'
py = str(E / 'venv/bin/python')
cp = str(R / 'codebase-explorer/.venv/bin/python')
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(R / 'eval-cbe2/src')}
start = time.time()
last = 0
try:
    for _ in range(2880):
        if (O / 'D67-generation.done').exists():
            break
        if time.time() - last >= 300:
            subprocess.run(['orca', 'orchestration', 'send', '--from', 'term_7f96a4eb-9683-40ed-999d-de345df3e938', '--type', 'heartbeat', '--subject', 'E3 D-67 generation active; awaiting final artifact', '--task-id', 'task_ebef506fc38a', '--dispatch-id', 'ctx_40994a64b448', '--phase', 'implementing'], stdout=subprocess.DEVNULL, check=False)
            last = time.time()
        time.sleep(30)
    else:
        raise TimeoutError('D67 generation did not settle in24h')
    assert json.loads((E / 'D67.json').read_text())['allow_partial_qa_after_final_verify_and_toolhandler_smoke']
    assert (O / 'verify-final-d67.log').exists()
    assert (run / 'catalog.json').is_file() and (run / 'docs/INDEX.md').is_file()
    assert json.loads((O / 'frozen-audit.json').read_text())['ok']
    for script, log in [('artifact_scope_d67.py', 'artifact-scope.log'), ('generation_metrics.py', 'generation-metrics.log')]:
        with (E / log).open('w') as f:
            subprocess.run([cp, str(E / script)], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    measured = json.loads((O / 'metrics.json').read_text())
    assert not measured['gateway']['identity_anomalies'], 'Wrong or swapped generation model; preserve evidence and stop'
    (E / 'GENERATION-MEASURED.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'authority': 'D-67', 'generation_status': json.loads((run / 'summary.json').read_text())['status']}, indent=2))
    for arm in ['C0', 'C']:
        dest = E / 'arms' / arm / 'docs'
        shutil.copytree(run / 'docs', dest, dirs_exist_ok=True)
        for p in dest.rglob('*'):
            if p.is_file():
                p.chmod(292)
    p = E / 'arms/C/run'
    if not p.exists():
        p.symlink_to(run, target_is_directory=True)
    profile = E / 'arms/C/sandbox.sb'
    body = profile.read_text()
    target = str(run.resolve())
    if target not in body:
        profile.write_text(body + '(allow file-read* (subpath ' + json.dumps(target) + '))\n')
    checks = {}
    for arm in ['S', 'C0', 'C']:
        checks[arm] = all((hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((E / 'arms' / arm / 'repo' / p.relative_to(R / 'eval/pytest-5989efe')).read_bytes()).digest() for p in (R / 'eval/pytest-5989efe').rglob('*') if p.is_file()))
    assert all(checks.values())
    (E / 'arm-copies-check.json').write_text(json.dumps(checks, indent=2))
    with (E / 'tool-layer-smoke.log').open('w') as f:
        smoke = subprocess.run([py, str(E / 'tool_layer_smoke.py')], env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    if smoke != 0:
        (E / 'D67-GATE-FAILED.json').write_text(json.dumps({'stage': 'ToolHandler smoke', 'returncode': smoke, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2))
        raise RuntimeError('D-67 actual tool smoke failed; no QA permitted')
    (E / 'QA-ELIGIBLE.json').write_text(json.dumps({'authority': 'D-67', 'generation_status': json.loads((run / 'summary.json').read_text())['status'], 'smoke_passed': True, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2))
    for script, log in [('run.py', 'run.log'), ('run_direct.py', 'direct.log')]:
        with (E / log).open('w') as f:
            subprocess.run([py, str(E / script)], env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
    (E / 'PIPELINE-DONE.json').write_text(json.dumps({'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'wall_seconds': time.time() - start, 'authority': 'D-67'}, indent=2))
except BaseException:
    (E / 'PIPELINE-FAILED.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'traceback': traceback.format_exc()}, indent=2))
    raise
