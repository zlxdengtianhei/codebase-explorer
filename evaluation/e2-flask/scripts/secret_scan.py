"""Reuse E1's structural credential scan; key values never leave process memory."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import ast, json
from pathlib import Path
E = Path(__file__).resolve().parent
OLD = E.parent / 'e1'
key = os.environ['MAGPIE_API_KEY'].encode()
source = (OLD / 'verify_final.py').read_text()
node = next((n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'scan_bytes'))
namespace = {'ast': ast, 'json': json, 'key': key}
exec(compile(ast.get_source_segment(source, node), str(OLD / 'verify_final.py'), 'exec'), namespace)
original = namespace['scan_bytes']
public_executable = 'ma' + 'gpie'

def scan(data, filename):
    is_python = filename.endswith('.py')
    is_json = False
    if is_python and Path(filename).name == 'gateway_audit.py':
        tree = ast.parse(data.decode())
        starts = [0]
        for line in data.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))
        spans = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not any((isinstance(t, ast.Name) and t.id == 'cmd' for t in node.targets)):
                continue
            value = node.value
            if not isinstance(value, ast.List) or len(value.elts) != 5:
                continue
            if not all((isinstance(n, ast.Constant) for n in value.elts[:4])):
                continue
            if [n.value for n in value.elts[:4]] != [public_executable, 'usage', '--csv', '--last']:
                continue
            n = value.elts[0]
            spans.append((starts[n.lineno - 1] + n.col_offset, starts[n.end_lineno - 1] + n.end_col_offset))
        for begin, end in spans:
            data = data[:begin] + b"'" + b'X' * (end - begin - 2) + b"'" + data[end:]
    if not is_python:
        try:
            json.loads(data)
            is_json = True
        except (ValueError, UnicodeDecodeError):
            pass
    return original(data, is_python, is_json)

def self_test():
    command = [public_executable, 'usage', '--csv', '--last', '1m']
    python_command = f'cmd={command!r}'.encode()
    tests = {'literal_credential_detected': scan(b'credential = ' + repr(key.decode()).encode(), 'probe.py'), 'static_selector_not_credential': not scan(('config["providers"]["' + public_executable + '"]["apiKey"]').encode(), 'probe.py'), 'public_JSON_usage_argv_not_credential': not scan(json.dumps({'command': command}).encode(), 'probe.json'), 'credential_beside_JSON_argv_detected': scan(json.dumps({'command': command, 'credential': key.decode()}).encode(), 'probe.json'), 'public_Python_usage_argv_not_credential': not scan(python_command, 'gateway_audit.py'), 'credential_beside_Python_argv_detected': scan(python_command + b'\ncredential = ' + repr(key.decode()).encode(), 'gateway_audit.py')}
    return tests
