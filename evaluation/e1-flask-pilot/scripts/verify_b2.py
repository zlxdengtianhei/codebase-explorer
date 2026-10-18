"""E1b2 author verification; inherits frozen input/rubric checks and adds real tool-boundary evidence."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, hashlib, importlib.util, json, re, statistics, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
B = E / 'b2'
R = E.parent.parent
sys.path.insert(0, str(E / 'harness/Experiment/Script/SWE-agent_QA'))
from agent_tools import ToolConfig, ToolHandler
from analyze_b2 import cli

def read(p):
    return json.loads(p.read_text())
assert (B / 'answers-DONE').exists() and (B / 'judge-DONE').exists()
with (B / 'baseline-verifier.log').open('w') as log:
    subprocess.run([str(E / 'venv/bin/python'), str(E / 'verify_final.py')], stdout=log, stderr=subprocess.STDOUT)
baseline = read(E / 'final-verification.json')
checks = dict(baseline['checks'])
checks.pop('blind_guess_20', None)
decision = read(B / 'W-decision.json')
checks.pop('W_ready_consumed_or_not_complete', None)
checks['W_B2_gate'] = decision['run'] and decision['readiness'].get('complete') is True if (E / 'answers/W-10-r0/batch.json').exists() else not decision['run'] and ((decision.get('readiness') or {}).get('complete') is False or (decision.get('readiness') is None and datetime.datetime.fromisoformat(decision['observed_utc']) >= datetime.datetime(2026, 10, 17, 11, 30, tzinfo=datetime.timezone.utc)))
checks['smoke_real_tool_handler'] = read(B / 'tool-layer-smoke.json')['all_passed']
checks['required_judge_model'] = read(E / 'judge/model-probe.json')['selected'] == 'codex/gpt-6.1-sol' and all((read(p)['judge_model'] == 'codex/gpt-6.1-sol' for a in ['C', 'W'] for s in [10, 25] for p in (E / 'judge' / f'{a}-{s}-r0').glob('q*.json')))
if decision['run']:
    published = Path(decision['readiness']['docs_path'])
    copied = E / 'arms/W/docs'
    checks['W_published_snapshot_matches'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in published.glob('*.md')} == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in copied.glob('*.md')}
receipt = read(B / 'archive-receipt.json')
checks['hints_unchanged'] = all((hashlib.sha256((E / 'arms' / a / 'hint.txt').read_bytes()).hexdigest() == h for a, h in receipt['hint_sha256'].items()))
upstream = Path(os.path.expandvars('$HOME/clones/eval_research_20261017/SWE-QA-Bench/Experiment/Script/SWE-agent_QA/agent_tools.py'))
spec = importlib.util.spec_from_file_location('b2_original_tools', upstream)
original = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = original
spec.loader.exec_module(original)
old = original.ToolHandler(original.ToolConfig(), None)
new = ToolHandler(ToolConfig(), None)
checks['default_blocklist_unchanged'] = original.ToolConfig().filter.blocklist == ToolConfig().filter.blocklist
checks['default_filter_actual_actions_identical'] = True
control_count = 0
for name in ['S-10-r0', 'S-25-r0', 'C0-10-r0', 'C0-25-r0', 'W-10-r0', 'W-25-r0', 'C-10-r0__bash-blocked', 'C-25-r0__bash-blocked']:
    for p in (E / 'answers' / name).glob('q*.json'):
        for attempt in read(p)['attempts']:
            for msg in attempt.get('history', []):
                if msg.get('role') != 'assistant':
                    continue
                action = new.parse_action(msg.get('content') or '')
                checks['default_filter_actual_actions_identical'] &= action == old.parse_action(msg.get('content') or '')
                if action:
                    control_count += 1
                    checks['default_filter_actual_actions_identical'] &= new._is_blocked(action.get('name', ''), action.get('arguments', {})) == old._is_blocked(action.get('name', ''), action.get('arguments', {}))
m = read(E / 'metrics.json')
old_metrics = read(B / 'old-metrics.json')
checks['old_C_scores_preserved'] = True
checks['actual_CLI_logs_match_audit'] = True
actual_calls = 0
for steps in [10, 25]:
    name = f'C-{steps}-r0'
    archive = name + '__bash-blocked'
    values = [read(p)['main_total_na5'] for p in (E / 'judge' / archive).glob('q*.json')]
    checks['old_C_scores_preserved'] &= statistics.mean(values) == old_metrics['groups'][name]['mean_total_na5'] and len(values) == old_metrics['groups'][name]['n']
    raw_count = 0
    for p in (E / 'answers' / name).glob('q*.json'):
        for a in read(p)['attempts']:
            for c in a.get('commands', []):
                kind = cli(c['command'])
                if kind and (not kind['help']):
                    raw_count += 1
    checks['actual_CLI_logs_match_audit'] &= raw_count == m['groups'][name]['cbe_agent_layer']['executed_count']
    actual_calls += raw_count
checks['actual_model_used_CLI'] = actual_calls > 0
checks['protocol_accounting'] = all((g['agent_protocol']['all_agent_replies'] == g['agent_protocol']['parsed_tool_replies'] + g['agent_protocol']['unparsed_all_replies'] and g['agent_protocol']['unparsed_loop_replies'] == g['unparsed_reply_count'] for g in m['groups'].values()))
checks['new_C_used_for_E2'] = all((m['projection'][str(s)]['observed_answers_per_arm']['C'] == (10 if s == 10 else 5) for s in [10, 25]))
checks['no_archive_in_E2'] = all((set(p['observed_answers_per_arm']) <= set(['S', 'C0', 'C', 'W']) for p in m['projection'].values()))
latest = max((datetime.datetime.fromisoformat(read(p)['finished_utc']) for a in ['C', 'W'] for s in [10, 25] for p in (E / 'answers' / f'{a}-{s}-r0').glob('q*.json')))
checks['gateway_export_after_new_answers'] = datetime.datetime.fromisoformat(read(E / 'usage-export-window.json')['export_started_utc']) >= latest
key = os.environ['MAGPIE_API_KEY'].encode()
leaks = []
for p in B.rglob('*'):
    if p.is_file() and p.suffix in ('.json', '.jsonl', '.log', '.csv', '.md', '.txt') and (key in p.read_bytes()):
        leaks.append(str(p.relative_to(E)))
checks['B2_artifacts_no_credential'] = not leaks
result = {'all_author_checks_pass': all(checks.values()), 'checks': checks, 'actual_CLI_executions': actual_calls, 'default_filter_actions_replayed': control_count, 'key_leak_paths': leaks, 'baseline_verification_path': 'final-verification.json', 'scope_note': 'Author verification; historical blind guessing is not reused as evidence about new C; W gate follows B2 deadline. Independent acceptance remains coordinator-owned.'}
(B / 'verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['all_author_checks_pass'] else 1)
