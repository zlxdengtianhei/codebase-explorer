import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import os, json, subprocess, shutil, hashlib, sys
from pathlib import Path
from measure import select_files, ENC
ROOT = Path(os.path.expandvars('$WORK'))
SPECS = [('tsdown', '2b1be7e0accdb1d6e903cd42642666431fc5e93d', os.path.expandvars('$HOME/clones/eval_research_20261017/rp/tsdown'), ['src', ':(exclude,glob)src/**/*.test.ts'], 43, 38670, 0.39), ('ruby_llm', '1e315ab4b3f3a150c443dc9a17f504756c2aad6f', os.path.expandvars('$HOME/clones/eval_research_20261017/rp/ruby_llm'), ['lib'], 115, 74885, 0.54), ('cjson', '6d9f2443ab071f86e5d9b43025a40929ec41c46c', str(ROOT / 'repos/cjson'), ['cJSON.c', 'cJSON.h', 'cJSON_Utils.c', 'cJSON_Utils.h'], 4, 34364, 0.36), ('fmt', 'b4ffa39b9994c961418406f47358791d89a5aa48', str(ROOT / 'repos/fmt'), ['include', 'src'], 20, 185053, 1.11), ('gson', 'e2292f9c9f2e07a4791827e8eea34aa7d80545d6', str(ROOT / 'repos/gson'), ['gson/src/main/java'], 87, 159939, 0.96)]

def main():
    result = []
    for name, sha, repo, paths, n, t, cap in SPECS:
        out = ROOT / 'runs/e6' / name
        out.mkdir(exist_ok=False)
        dest = ROOT / 'eval' / f'{name}-{sha[:7]}'
        dest.mkdir(exist_ok=False)
        cmd = ['git', '-C', repo, 'archive', sha, *paths]
        with (out / 'archive.tar').open('wb') as f:
            subprocess.run(cmd, stdout=f, check=True)
        subprocess.run(['tar', '-xf', str(out / 'archive.tar'), '-C', str(dest)], check=True)
        (out / 'archive.tar').unlink()
        m = measure(dest, out)
        row = dict(name=name, sha=sha, source=repo, paths=paths, archive_command=cmd, copy=str(dest), expected_files=n, expected_tokens=t, cap=cap, **m)
        (out / 'input.json').write_text(json.dumps(row, indent=2))
        result.append(row)
        for p in dest.rglob('*'):
            p.chmod(365 if p.is_dir() else 292)
        dest.chmod(365)
        print(name, m, flush=True)
    (ROOT / 'runs/e6/inputs.json').write_text(json.dumps(result, indent=2))

def measure(dest, out):
    seen, _ = select_files(str(dest), '.', [])
    rows = []
    for p in sorted(dest.rglob('*')):
        if p.is_file():
            b = p.read_bytes()
            rows.append(dict(path=str(p.relative_to(dest)), bytes=len(b), sha256=hashlib.sha256(b).hexdigest(), source=str(p.relative_to(dest)) in seen, tokens=len(ENC.encode(b.decode('utf-8', errors='replace'), disallowed_special=())) if str(p.relative_to(dest)) in seen else None))
    (out / 'manifest.json').write_text(json.dumps(rows, indent=2))
    return dict(files=len(seen), tokens=sum((x['tokens'] or 0 for x in rows)), all_files=len(rows))
if __name__ == '__main__':
    main()
