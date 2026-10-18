"""Run unmodified CodeWiki CLI with isolated credentials and UTC receipts."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import json, os, subprocess, datetime, shutil
ROOT = Path(os.path.expandvars('$WORK'))
RUN = ROOT / 'runs/e1'
CWHOME = RUN / 'cw_home'
MODEL = 'zai/glm-5.3-flash'

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    CWHOME.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(HOME=str(CWHOME), CODEWIKI_NO_KEYRING='1', LOGFIRE_SEND_TO_LOGFIRE='false', TMPDIR=str(RUN / 'tmp'))
    key = os.environ['MAGPIE_API_KEY']
    cfg = CWHOME / '.codewiki'
    cfg.mkdir(exist_ok=True)
    (cfg / 'credentials.json').write_text(json.dumps({'api_key': key}))
    (cfg / 'credentials.json').chmod(384)
    (cfg / 'config.json').write_text(json.dumps({'version': '1.0', 'provider': 'openai-compatible', 'base_url': 'http://127.0.0.1:3425/v1', 'main_model': MODEL, 'cluster_model': MODEL, 'fallback_model': MODEL, 'max_tokens': 32768, 'prompt_caching': False}))
    cmd = [str(ROOT / 'eval/cw_venv/bin/python'), str(RUN / 'codewiki_audit_cli.py'), 'generate', '--main-model', MODEL, '--cluster-model', MODEL, '--fallback-model', MODEL, '--max-tokens', '32768', '--no-prompt-caching', '--flat', '--no-artifacts', '--include', '*', '--exclude', '__E1_MATCHES_NOTHING__', '--no-gitignore', '--output', str(RUN / 'codewiki-flask')]
    receipt_path = RUN / 'codewiki-receipt.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'command': cmd, 'scope_warning': 'runtime override removes tests/test only; compare selected and opened files to manifest', 'attempts': []}
    attempt = len(receipt['attempts']) + 1
    generation_count = sum((1 for x in receipt['attempts'] if x.get('entered_generation', True)))
    try:
        if generation_count >= 3:
            raise RuntimeError('Initial generation plus two generation retries exhausted')
        start = now()
        log_path = RUN / f'codewiki-attempt{attempt}.log'
        with log_path.open('w') as log:
            code = subprocess.run(cmd, cwd=ROOT / 'eval/flask-85c5d93', env=env, input='y\n', text=True, stdout=log, stderr=subprocess.STDOUT).returncode
        entered = '[1/5] Dependency Analysis' in log_path.read_text()
        receipt['attempts'].append({'invocation': attempt, 'generation_attempt': generation_count + 1 if entered else None, 'entered_generation': entered, 'confirmation_stdin': 'y', 'start_utc': start, 'end_utc': now(), 'exit_code': code, 'pages': len(list((RUN / 'codewiki-flask').glob('*.md')))})
        (RUN / 'codewiki-receipt.json').write_text(json.dumps(receipt, indent=2))
    finally:
        shutil.rmtree(CWHOME)
if __name__ == '__main__':
    main()
