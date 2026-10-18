"""Convert a CBE docs dir (INDEX.md + nodes/*.md with 'Parent: [..](x.md)' lines) into the flat dir
that `codewikibench parse --docs-dir` reads: top-level <name>.md files + module_tree.json.
usage: cbe_to_cwb_input.py CBE_DOCS_DIR OUT_DIR
The CodeWikiBench parser (parse_generated_docs.parse_deepwiki) lists only top-level *.md files and uses
module_tree.json ({name: {"children": {...}}}) to number them; file basename = module name."""
import json, os, re, shutil, sys
src, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
parent = {}
names = []
for fn in sorted(os.listdir(os.path.join(src, 'nodes'))):
    if not fn.endswith('.md'): continue
    name = fn[:-3]; names.append(name)
    shutil.copyfile(os.path.join(src, 'nodes', fn), os.path.join(out, fn))
    text = open(os.path.join(src, 'nodes', fn), encoding='utf-8').read()
    m = re.search(r'^Parent: \[[^\]]*\]\(([^)#]+)\.md\)', text, re.M)
    if m: parent[name] = m.group(1)
# INDEX.md -> overview.md (rewrite nodes/ links to flat links)
idx = open(os.path.join(src, 'INDEX.md'), encoding='utf-8').read().replace('(nodes/', '(')
open(os.path.join(out, 'overview.md'), 'w', encoding='utf-8').write(idx)
children = {n: {} for n in names}
roots = {}
for n in names:
    p = parent.get(n)
    if p in children: children[p][n] = children[n]
    else: roots[n] = children[n]
def conv(d): return {k: ({'children': conv(v)} if v else {}) for k, v in d.items()}
json.dump(conv(roots), open(os.path.join(out, 'module_tree.json'), 'w'), indent=1)
print('pages', len(names), 'roots', list(roots), 'with parent', len(parent))
