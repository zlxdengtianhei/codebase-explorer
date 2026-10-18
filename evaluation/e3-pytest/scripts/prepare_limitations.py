import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
s = (R / 'runs/e2/limitations_smoke.py').read_text().replace("['S','C0','C','W']", "['S','C0','C']").replace("str(OLD/'arms/C/bin/cbe')", "str(E/'arms/C/bin/cbe')").replace("LocalEnv(OLD/'arms'/arm/'repo')", "LocalEnv(E/'arms'/arm/'repo')").replace('src/flask/ctx.py', 'src/_pytest/fixtures.py').replace('Benchmark/flask.jsonl', 'Benchmark/pytest.jsonl').replace('E2_SECOND_COMMAND', 'E3_SECOND_COMMAND')
(E / 'limitations_smoke.py').write_text(s)
