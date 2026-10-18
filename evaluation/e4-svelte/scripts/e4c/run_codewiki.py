"""Run at most initial+two resumptions, preserving UTC and each metadata/tree."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import os, json, subprocess, datetime, hashlib, shutil, sys
ROOT = Path(os.path.expandvars('$WORK'))
ADMIN = ROOT / 'runs/e4/e4c'
MODEL = 'zai/glm-5.3-flash'

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def pages(output):
    t = output / 'module_tree.json'
    if not t.exists():
        return {'complete': False, 'missing': ['module_tree.json'], 'pages': len(list(output.glob('*.md'))), 'modules': 0}

    def names(d):
        result = set()
        for k, v in d.items():
            result.add(k + '.md')
            result.update(names(v.get('children', {})))
        return result
    required = names(json.loads(t.read_text())) | {'overview.md'}
    actual = {p.name for p in output.glob('*.md') if p.read_text().strip()}
    return {'complete': not required - actual, 'missing': sorted(required - actual), 'extra': sorted(actual - required), 'pages': len(actual), 'modules': len(required) - 1}

def main(n):
    record = ADMIN / f'run{n}'
    record.mkdir(exist_ok=True)
    home = ROOT / f'runs/e4/cw_home_{n}'
    home.mkdir(exist_ok=False)
    tmp = record / 'tmp'
    tmp.mkdir(exist_ok=True)
    cfg = home / '.codewiki'
    cfg.mkdir()
    key = os.environ['MAGPIE_API_KEY']
    p = cfg / 'credentials.json'
    fd = os.open(p, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 384)
    with os.fdopen(fd, 'w') as f:
        json.dump({'api_key': key}, f)
    (cfg / 'config.json').write_text(json.dumps({'version': '1.0', 'provider': 'openai-compatible', 'base_url': 'http://127.0.0.1:3425/v1', 'main_model': MODEL, 'cluster_model': MODEL, 'fallback_model': MODEL, 'max_tokens': 32768, 'prompt_caching': False}))
    env = os.environ.copy()
    env.update(HOME=str(home), CODEWIKI_NO_KEYRING='1', LOGFIRE_SEND_TO_LOGFIRE='false', TMPDIR=str(tmp), PYTHONDONTWRITEBYTECODE='1', E4_SESSION=f'e4-codewiki-svelte-{n}', E4_HTTP_AUDIT=str(record / 'http.jsonl'), E4_RUN_RECORD=str(record))
    output = ROOT / f'runs/e4/codewiki-svelte-{n}'
    cmd = [str(ROOT / 'eval/cw_venv/bin/python'), str(ADMIN / 'codewiki_audit_cli.py'), 'generate', '--main-model', MODEL, '--cluster-model', MODEL, '--fallback-model', MODEL, '--max-tokens', '32768', '--no-prompt-caching', '--flat', '--no-artifacts', '--include', '*', '--exclude', '__E1_MATCHES_NOTHING__', '--no-gitignore', '--output', str(output)]
    receipt = {'command': cmd, 'session': env['E4_SESSION'], 'start_utc': now(), 'attempts': [], 'pid': os.getpid()}
    for a in range(1, 4):
        env['E4_ATTEMPT'] = str(a)
        attempt = {'number': a, 'start_utc': now()}
        receipt['active_attempt'] = attempt
        (record / 'receipt.json').write_text(json.dumps(receipt, indent=2))
        with (record / f'attempt{a}.log').open('w') as log:
            proc = subprocess.Popen(cmd, cwd=ROOT / 'eval/svelte-be645b4', env=env, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
            receipt['child_pid'] = proc.pid
            (record / 'receipt.json').write_text(json.dumps(receipt, indent=2))
            proc.communicate('y\n')
        attempt.update(end_utc=now(), exit_code=proc.returncode, **pages(output))
        for name in ('metadata.json', 'module_tree.json'):
            if (output / name).exists():
                shutil.copy2(output / name, record / f'attempt{a}-{name}')
        receipt['attempts'].append(attempt)
        receipt.pop('active_attempt', None)
        (record / 'receipt.json').write_text(json.dumps(receipt, indent=2))
        if attempt['complete']:
            break
    receipt.update(end_utc=now(), final=pages(output))
    (record / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    (record / 'generation.done').write_text(now())
if __name__ == '__main__':
    main(int(sys.argv[1]))
