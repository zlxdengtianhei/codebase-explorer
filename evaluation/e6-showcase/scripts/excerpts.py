import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
from pathlib import Path
import json, re
BASE = Path(os.path.expandvars('$WORK/runs/e6'))
rows = json.loads((BASE / 'inputs.json').read_text())
out = ['# INDEX 原文素材', '', '每仓四行（若原件不足则照实保留）；保留原始行内容，下面的代码块不作文字改写。出处行号基于生成的最终 INDEX.md。', '']
for r in rows:
    p = BASE / r['name'] / 'run/docs/INDEX.md'
    if not p.exists():
        continue
    lines = p.read_text().splitlines()
    picked = []
    section = ''
    for n, line in enumerate(lines, 1):
        if line.startswith('## '):
            section = line[3:].strip()
        elif section == 'Overview' and line.strip() and (not line.startswith('#')) and (not picked):
            picked.append((n, line))
        elif section == 'Maintenance navigation' and line.strip() and (not line.strip().endswith(':')) and (len(picked) < 2):
            picked.append((n, line))
        elif section == 'Key flows' and line.startswith('- ') and (len(picked) < 4):
            picked.append((n, line))
    if len(picked) < 3:
        for n, line in enumerate(lines, 1):
            if re.match('^\\s*- \\[', line) and all((n != a for a, b in picked)):
                picked.append((n, line))
            if len(picked) >= 4:
                break
    out += ['## ' + r['name'], '']
    for n, line in picked[:5]:
        out += [f'出处：`{p}:{n}`', '```markdown', line, '```', '']
(BASE / 'index-excerpts.md').write_text('\n'.join(out) + '\n')
print('wrote', BASE / 'index-excerpts.md')
