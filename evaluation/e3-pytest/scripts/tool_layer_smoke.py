"""E1b2 positive/negative smoke through the actual agent ToolHandler boundary."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import datetime, json, sys
from pathlib import Path
E = Path(os.path.expandvars('$WORK/runs/e3'))
sys.path.insert(0, str(E / 'harness/Experiment/Script/SWE-agent_QA'))
from agent_tools import ToolConfig, ToolHandler
from local_env import LocalEnv
cbe = str(E / 'arms/C/bin/cbe')
run = str(E / 'arms/C/run')
config = ToolConfig()
config.filter.cbe_executable = cbe
env = LocalEnv(E / 'arms/C/repo')
handler = ToolHandler(config, env)
cases = [('find', f'{cbe} find --run-dir {run} --term FixtureRequest --limit 1', True), ('query', f'{cbe} query --run-dir {run} --id src/_pytest/fixtures.py', True), ('help', f'{cbe} --help', True), ('ordinary_bash', 'ls -la', False), ('compound', f'{cbe} find x; ls', False), ('nested_shell', 'bash -c "ls -la"', False)]
records = []
for name, command, allowed in cases:
    before = len(env.commands)
    output = handler.execute_action({'name': 'bash', 'arguments': {'command': command}}, env)
    executed = len(env.commands) > before
    good = executed and env.commands[-1]['returncode'] == 0 and bool(output.strip()) if allowed else not executed and "Command 'bash' is blocked" in output
    records.append({'test': name, 'command': command, 'expected_allowed': allowed, 'executed': executed, 'returncode': env.commands[-1]['returncode'] if executed else None, 'passed': good, 'output_excerpt': output[:500]})
for char in ';&|`$><\n\r':
    command = f'{cbe} find --run-dir {run} --term x' + char + 'x'
    before = len(env.commands)
    output = handler.execute_action({'name': 'bash', 'arguments': {'command': command}}, env)
    records.append({'test': 'forbidden_' + repr(char), 'executed': len(env.commands) > before, 'passed': len(env.commands) == before and "Command 'bash' is blocked" in output})
for arm in ['S', 'C0']:
    original = ToolConfig()
    other_env = LocalEnv(E / 'arms' / arm / 'repo')
    other = ToolHandler(original, other_env)
    for command in ['ls -la', f'{cbe} --help']:
        result = other.execute_action({'name': 'bash', 'arguments': {'command': command}}, other_env)
        records.append({'test': 'unchanged_' + arm, 'command': command, 'passed': not other_env.commands and "Command 'bash' is blocked" in result})
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'boundary': 'ToolHandler.execute_action -> _is_blocked -> LocalEnv -> sandbox-exec', 'all_passed': all((r['passed'] for r in records)), 'records': records}
Path(os.path.expandvars('$WORK/runs/e3/tool-layer-smoke.json')).write_text(json.dumps(result, indent=2))
print(json.dumps({'all_passed': result['all_passed'], 'tests': len(records), 'required_six': [{k: r[k] for k in ['test', 'executed', 'passed']} for r in records[:6]]}, indent=2))
raise SystemExit(0 if result['all_passed'] else 1)
