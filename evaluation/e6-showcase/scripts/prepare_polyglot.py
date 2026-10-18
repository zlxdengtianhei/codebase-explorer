import json,shutil,hashlib
from pathlib import Path
from prepare import ROOT,measure
src=ROOT/'repos/polyglot';lines=''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(src)}\n' for p in sorted(src.rglob('*')) if p.is_file());digest=hashlib.sha256(lines.encode()).hexdigest();assert digest.startswith('6b19d76603fb65d1')
out=ROOT/'runs/e6/polyglot';out.mkdir();(out/'content-sha256sum.txt').write_text(lines)
dest=ROOT/'eval/polyglot-6b19d76';shutil.copytree(src,dest)
m=measure(dest,out);row=dict(name='polyglot',sha=digest,source=str(src),copy=str(dest),expected_files=22,expected_tokens=1708,cap=.3,**m)
(out/'input.json').write_text(json.dumps(row,indent=2));p=ROOT/'runs/e6/inputs.json';rows=json.loads(p.read_text());rows.append(row);p.write_text(json.dumps(rows,indent=2))
for p in dest.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
dest.chmod(0o555);print(row)
