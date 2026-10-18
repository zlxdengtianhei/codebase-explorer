import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, pathlib, hashlib, re, subprocess, datetime, os, shutil
root = pathlib.Path(os.path.expandvars('$WORK'))
scripts = pathlib.Path(__file__).resolve().parent
out = root / 'runs/e5/cbe-curl'
run = out / 'run'
cache = scripts / 'tokenizer-cache'
cache.mkdir(exist_ok=True)
url = 'https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken'
shutil.copyfile(root / 'eval-cbe2/src/cbe/data/o200k_base.tiktoken', cache / hashlib.sha1(url.encode()).hexdigest())
os.environ['TIKTOKEN_CACHE_DIR'] = str(cache)
import tiktoken
enc = tiktoken.get_encoding('o200k_base')
m = json.loads((out / 'metrics.json').read_text())
context = json.loads((run / 'context.json').read_text())
checks = []

def check(name, ok, detail=None):
    checks.append({'check': name, 'ok': bool(ok), 'detail': detail})
check('frozen_commit', subprocess.check_output(['git', '-C', str(root / 'eval-cbe2'), 'rev-parse', 'HEAD'], text=True).strip() == 'a87674ddf570b1cc9fd2c322982a83e011132668')
check('tracked_frozen_worktree_clean', not subprocess.check_output(['git', '-C', str(root / 'eval-cbe2'), 'status', '--porcelain', '--untracked-files=no'], text=True).strip())
repo = root / 'eval/curl-2c04412'
all_tokens = 0
bad = []
count = 0
for line in (root / 'eval/curl-2c04412.manifest.txt').read_text().splitlines():
    sha, p = line.split(None, 1)
    p = p.strip()
    raw = (repo / p).read_bytes()
    count += 1
    all_tokens += len(enc.encode(raw.decode('utf-8', errors='replace'), disallowed_special=()))
    if hashlib.sha256(raw).hexdigest() != sha:
        bad.append(p)
check('all_506_manifest_SHA', count == 506 and (not bad), bad)
check('all_input_tokens', all_tokens == 1741311, all_tokens)
accepted = 0
changed = []
for row in context['files']:
    raw = (repo / row['path']).read_bytes()
    accepted += len(enc.encode(raw.decode(), disallowed_special=()))
    if hashlib.sha256(raw).hexdigest() != row['sha256']:
        changed.append(row['path'])
check('accepted_485_source_SHA', len(context['files']) == 485 and (not changed), changed)
check('accepted_source_tokens', accepted == m['frozen_audit']['accepted_source_tokens'], accepted)
check('context_matches_pre_API_audit', hashlib.sha256((run / 'context.json').read_bytes()).hexdigest() == m['frozen_audit']['context_sha256'])
check('audit_before_first_gateway_request', datetime.datetime.fromisoformat(m['frozen_audit']['utc']) <= min((datetime.datetime.fromisoformat(r['time']) for r in __import__('csv').DictReader((out / 'gateway-requests.csv').open())), default=datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)))
pages = list((run / 'docs').rglob('*.md'))
md = sum((len(enc.encode(p.read_text(), disallowed_special=())) for p in pages))
stripped = sum((len(enc.encode(''.join((l for l in p.read_text().splitlines(keepends=True) if not re.match('^\\s*\\[f\\d+\\]:', l))), disallowed_special=())) for p in pages))
check('published_markdown_recount', m['layers'] and md == m['layers']['semantic_tokens'], md)
check('seven_parts_partition', m['layers'] and sum(m['layers']['semantic_breakdown'].values()) == md)
check('stripped_markdown_recount', stripped == m['published_without_file_refs_tokens'], stripped)
check('gateway_requests_calls', m['gateway']['requests'] == m['calls'], [m['gateway']['requests'], m['calls']])
check('gateway_calls_tokens', all((v == 0 for v in m['gateway_minus_calls'].values())), m['gateway_minus_calls'])
check('gateway_raw_tokens', all((v == 0 for v in m['gateway_minus_raw'].values())), m['gateway_minus_raw'])
check('gateway_summary_available_fields', all((v in (0, None, '0') for v in m['gateway_minus_summary'].values())), m['gateway_minus_summary'])
check('gateway_model_identity', not m['gateway']['identity_anomalies'], m['gateway']['served_models'])
check('requests_attributed', m['gateway_outside_phases'] == 0)
check('max_two_resumes', sum((p['phase'].startswith('resume') for p in m['phases'])) <= 2)
if m['complete']:
    check('complete_has_verify', m['verify']['ok'])
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'author_self_check': True, 'checks': checks, 'all_ok': all((c['ok'] for c in checks)), 'not_checked': 'Document semantic truth, downstream QA and independent review remain with coordinator.'}
(out / 'verification-independent.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
