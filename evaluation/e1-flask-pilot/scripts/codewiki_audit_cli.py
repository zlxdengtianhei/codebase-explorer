"""Invoke upstream CLI unchanged; observe file opens only inside public input."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import atexit, json, os, sys
from pathlib import Path
root = Path(os.path.expandvars('$WORK/eval/flask-85c5d93')).resolve()
out = Path(os.path.expandvars('$WORK/runs/e1/codewiki-opened-files.txt'))
seen = set()

def audit(event, args):
    if event != 'open' or not isinstance(args[0], (str, bytes)):
        return
    try:
        p = Path(os.fsdecode(args[0])).resolve()
        if p.is_relative_to(root):
            seen.add(p.relative_to(root).as_posix())
    except (OSError, ValueError):
        pass

def save():
    prior = set(out.read_text().splitlines()) if out.exists() else set()
    out.write_text('\n'.join(sorted(prior | seen)) + '\n')
sys.addaudithook(audit)
atexit.register(save)
import codewiki
from codewiki.src.be.dependency_analyzer.utils import patterns
before = set(patterns.DEFAULT_IGNORE_PATTERNS)
patterns.DEFAULT_IGNORE_PATTERNS.difference_update({'tests', 'test'})
from codewiki.src.be.dependency_analyzer.analysis.repo_analyzer import RepoAnalyzer
selection = RepoAnalyzer(include_patterns=['*'], exclude_patterns=['__E1_MATCHES_NOTHING__'], use_gitignore=False).analyze_repository_structure(str(root))
selected = []

def walk(node):
    if node.get('type') == 'file':
        selected.append(node['path'])
    for child in node.get('children', []):
        walk(child)
walk(selection['file_tree'])
(root.parent.parent / 'runs/e1/codewiki-selected-files.txt').write_text('\n'.join(sorted(selected)) + '\n')
(root.parent.parent / 'runs/e1/codewiki-override.json').write_text(json.dumps({'removed': sorted(before - set(patterns.DEFAULT_IGNORE_PATTERNS)), 'added': sorted(set(patterns.DEFAULT_IGNORE_PATTERNS) - before), 'selected_count': len(selected)}, indent=2))
from codewiki.cli.main import cli
cli()
