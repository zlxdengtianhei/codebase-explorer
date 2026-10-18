import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, re, pathlib, sys
root = pathlib.Path(os.path.expandvars('$WORK/eval/curl-2c04412'))
qs = [json.loads(x) for x in open(os.path.expandvars('$WORK/runs/e5q/candidates/A/questions.jsonl'))]
seen = set()
for q in qs[int(sys.argv[1]) - 1:int(sys.argv[2])]:
    print('\n===', q['cid'])
    for r in q['rubric']:
        for sec in r['source'].split(';'):
            parts = sec.strip().split(':', 1)
            p = root / parts[0].strip()
            if not p.is_file():
                continue
            lines = p.read_text().splitlines()
            names = re.findall('\\b[A-Za-z_]\\w*\\b', parts[1] if len(parts) > 1 else '')
            for name in names:
                for i, l in enumerate(lines):
                    if not re.search('\\b' + re.escape(name) + '\\s*\\(', l):
                        continue
                    if not (l.startswith(name + '(') or re.match('^(?:static )?(?:[\\w]+\\s+|struct \\w+\\s*\\*\\s*|const struct \\w+\\s*\\*\\s*)+' + name + '\\(', l)):
                        continue
                    if (str(p), i) in seen:
                        continue
                    j = i
                    while j < len(lines) and '{' not in lines[j] and (';' not in lines[j]):
                        j += 1
                    if j == len(lines) or ';' in lines[j]:
                        continue
                    seen.add((str(p), i))
                    depth = 0
                    k = j
                    while k < len(lines):
                        depth += lines[k].count('{') - lines[k].count('}')
                        if depth == 0:
                            break
                        k += 1
                    print('\n' + str(p.relative_to(root)) + ':' + str(i + 1))
                    print('\n'.join((f'{n + 1}: {lines[n]}' for n in range(max(0, i - 2), min(k + 1, len(lines))))))
