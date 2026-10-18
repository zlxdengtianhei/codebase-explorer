"""Materialize E2 calibration adapter in E3, preserving original direct prompt."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
R = Path(os.path.expandvars('$WORK'))
E = R / 'runs/e3'
s = (R / 'runs/e2/run_direct.py').read_text()
s = s.replace('pilot={4,6,11,12,14,20,32,41,46,47}', 'pilot=set()')
s = s.replace("'flask'", "'pytest'").replace("text=(OLD/'judge_pilot.py').read_text().replace(", "text=(OLD/'judge_pilot.py').read_text().replace('Benchmark/flask.jsonl','Benchmark/pytest.jsonl').replace(")
s = s.replace('term_5a37847d-2388-4a2c-a199-8e08819d2a2a', 'term_7f96a4eb-9683-40ed-999d-de345df3e938').replace('task_183a9ab0ba62', 'task_ebef506fc38a').replace('ctx_6a47ae0aa966', 'ctx_40994a64b448').replace('D-63 direct', 'E3 direct').replace('/38 answers', '/48 answers')
(E / 'run_direct.py').write_text(s)
s = (R / 'runs/e2/calibration_reduce.py').read_text().replace("ARMS=['S','C0','C','W']", "ARMS=['S','C0','C']").replace('Ten E1 direct answers reused.', 'All 48 pytest direct answers generated in E3.')
(E / 'calibration_reduce.py').write_text(s)
print('calibration scripts prepared')
