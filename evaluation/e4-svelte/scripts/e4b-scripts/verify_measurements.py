import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, csv, hashlib, re, datetime, subprocess
from pathlib import Path
import tiktoken
root = Path(os.path.expandvars('$WORK'))
scripts = Path(__file__).resolve().parent
enc = tiktoken.get_encoding('o200k_base')
metrics = json.loads((scripts / 'all-metrics.json').read_text())
checks = []

def check(name, ok, detail=None):
    checks.append({'check': name, 'ok': bool(ok), 'detail': detail})
check('frozen_commit', subprocess.check_output(['git', '-C', str(root / 'eval-cbe2'), 'rev-parse', 'HEAD'], text=True).strip() == 'a87674ddf570b1cc9fd2c322982a83e011132668')
check('frozen_worktree_tracked_clean', not subprocess.check_output(['git', '-C', str(root / 'eval-cbe2'), 'status', '--porcelain', '--untracked-files=no'], text=True).strip())
for m in metrics:
    n = m['run']
    out = root / f'runs/e4/cbe-svelte-r{n}'
    run = out / 'run'
    context = json.loads((run / 'context.json').read_text())
    files = context['files']
    check(f'r{n}_source_file_count', len(files) == 440, len(files))
    source_tokens = 0
    changed = []
    for row in files:
        raw = (root / 'eval/svelte-be645b4' / row['path']).read_bytes()
        source_tokens += len(enc.encode(raw.decode(), disallowed_special=()))
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            changed.append(row['path'])
    check(f'r{n}_source_digests_unchanged', not changed, changed)
    check(f'r{n}_source_tokens', source_tokens == 531705, source_tokens)
    check(f'r{n}_audit_before_first_api', (out / 'frozen-audit.json').stat().st_mtime <= min((p.stat().st_mtime for p in (run / 'raw').glob('*.api.json')), default=float('inf')))
    check(f'r{n}_context_matches_audit', hashlib.sha256((run / 'context.json').read_bytes()).hexdigest() == m['frozen_audit']['context_sha256'])
    check(f'r{n}_audit_valid', m['frozen_audit']['ok'] and m['frozen_audit']['files'] == 440 and (m['frozen_audit']['source_reassembly_fallback'] == 0))
    pages = list((run / 'docs').rglob('*.md'))
    md = sum((len(enc.encode(p.read_text(), disallowed_special=())) for p in pages))
    stripped = sum((len(enc.encode(''.join((l for l in p.read_text().splitlines(keepends=True) if not re.match('^\\s*\\[f\\d+\\]:', l))), disallowed_special=())) for p in pages))
    if m['layers']:
        check(f'r{n}_markdown_token_recount', md == m['layers']['semantic_tokens'], md)
        check(f'r{n}_seven_parts_sum', sum(m['layers']['semantic_breakdown'].values()) == md)
        check(f'r{n}_stripped_markdown_recount', stripped == m['published_without_file_refs_tokens'], stripped)
    check(f'r{n}_gateway_all_attributed_to_phases', m['gateway_outside_phases'] == 0, m['gateway_outside_phases'])
    check(f'r{n}_gateway_model_identity', not m['gateway']['identity_anomalies'], m['gateway']['served_models'])
    check(f'r{n}_gateway_calls_match', m['gateway']['requests'] == m['calls'], [m['gateway']['requests'], m['calls']])
    check(f'r{n}_gateway_minus_calls_zero', all((v == 0 for v in m['gateway_minus_calls'].values())), m['gateway_minus_calls'])
    check(f'r{n}_gateway_minus_raw_zero', all((v == 0 for v in m['gateway_minus_raw'].values())), m['gateway_minus_raw'])
    check(f'r{n}_summary_usage_matches', all((v == 0 or v is None for v in (m['gateway_minus_summary'] or {}).values())), m['gateway_minus_summary'])
    check(f'r{n}_at_most_one_resume', sum((p['phase'] == 'resume' for p in m['phases'])) <= 1)
    if m['complete']:
        check(f'r{n}_complete_has_verify', m['verify']['ok'])
manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for m in metrics for p in [root / f"runs/e4/cbe-svelte-r{m['run']}/metrics.json", root / f"runs/e4/cbe-svelte-r{m['run']}/gateway-requests.csv", root / f"runs/e4/cbe-svelte-r{m['run']}/phases.json"]}
report = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'author_self_check': True, 'checks': checks, 'all_ok': all((r['ok'] for r in checks)), 'manifest': manifest, 'not_checked': 'Documentation semantic truth, CodeWiki comparison and independent coverage judgment belong to coordinator.'}
(scripts / 'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
