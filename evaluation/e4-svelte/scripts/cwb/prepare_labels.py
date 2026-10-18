"""Freeze rubric and pre-judgment labels using requirements text only."""
import os
os.environ.setdefault('WORK', os.environ.get('CBE_WORK_ROOT', os.getcwd()))
os.environ.setdefault('TMP', os.environ.get('TMPDIR', '/tmp'))
import json, datetime, hashlib, collections
from pathlib import Path
R = Path(__file__).resolve().parent
src = Path(os.path.expandvars('$HOME/context-infra-lab-1/adhoc_jobs/codebase_explorer_20261016/scratch/cbe-e92_evalresearch_1017-0406/raw/cwb_svelte.json'))
d = json.loads(src.read_text())['rubrics']
(R / 'svelte-rubrics.json').write_text(json.dumps(d, indent=2))
yes = {'0.0.0': 'Explicitly parses the script, markup and style blocks of a single-file component.', '0.0.1': 'Explicitly concerns preprocessor and script-language syntax in a component.', '0.0.2': 'Module script is a component source block syntax feature.', '0.1.0': 'Explicitly transforms component template syntax during compilation.', '0.1.1': 'Explicitly concerns compiler rewriting of rune syntax.', '0.1.2': 'Explicitly concerns compilation of component styles and generated CSS.', '0.2.0': 'Explicitly concerns generated component JavaScript output.', '0.2.1': 'Explicitly concerns the component SSR compilation target.', '0.2.2': 'Explicitly concerns compilation controlled by component options syntax.', '0.3.0': 'Explicitly concerns compiler output options and static accessibility checks.', '0.3.1': 'Compiler diagnostics concern parsing or compilation feedback.', '1.0.1.2': 'Destructuring derived declarations concerns source syntax transformation.', '1.0.3.2': 'Property renaming and type syntax concern component source declarations.', '1.2.0': 'Explicitly concerns instrumenting source assignments into generated DOM code.', '1.2.1': 'Explicitly concerns the legacy reactive statement syntax.', '1.2.2': 'Explicitly concerns legacy component export-let declaration syntax.', '2.0.1': 'Explicitly names encapsulation inside a single .svelte source file.', '2.2.0.1': 'Explicitly names the component template render tag syntax.', '2.2.1': 'Legacy slots are component template syntax for content projection.', '3.0.0.0': 'Explicitly concerns attribute binding and spread template syntax.', '3.0.0.2': 'Text expression interpolation is component template syntax.', '3.0.1.0': 'Explicitly concerns if-block syntax compilation.', '3.0.1.1': 'Explicitly concerns each-block syntax and generated reconciliation.', '3.0.1.2': 'Explicitly concerns await-block syntax and generated state machines.', '3.0.1.3': 'Explicitly concerns the key-block template construct.', '3.1.0': 'Explicitly concerns the HTML template directive.', '3.1.1': 'Explicitly concerns the compile-time const template directive.', '3.1.2': 'Explicitly concerns the debug template directive.', '3.1.3': 'Explicitly concerns special element template syntax.', '3.3.0': 'Explicitly concerns use-directive syntax attaching element behavior.', '3.3.1.0': 'Explicitly concerns transition, in and out directive syntax.', '3.3.1.1': 'Explicitly concerns animate-directive syntax.', '3.3.1.3': 'Transition local/global scope is a component directive scoping rule.', '4.0.0': 'Component CSS scoping and hash generation concern style compilation.', '4.0.1': 'Scoped keyframe renaming concerns component style compilation.', '4.0.2': 'Specificity wrappers concern generated component CSS.', '4.1.0': 'Explicitly concerns the global modifier in component styles.', '4.1.1': 'Explicitly concerns global style-block syntax.', '4.2.1': 'Explicitly concerns component class-directive syntax.', '4.2.2': 'Explicitly concerns component style-directive syntax.', '5.0.0': 'Explicitly concerns a special component template element.', '5.0.1': 'Explicitly concerns special component template elements.', '5.1.0': 'Explicitly concerns the boundary template element.', '5.2.0': 'Explicitly concerns component options element syntax.', '7.0.0': 'Explicitly concerns source-syntax migration of export-let declarations.', '7.0.1': 'Explicitly concerns source-syntax migration of reactive statements.', '7.0.2': 'Explicitly concerns source-syntax migration of slots to snippets.'}
leaves = []

def walk(ns, p=''):
    for i, n in enumerate(ns):
        q = f'{p}.{i}' if p else str(i)
        if n.get('sub_tasks'):
            walk(n['sub_tasks'], q)
        else:
            leaves.append({'path': q, 'requirements': n['requirements'], 'weight': n['weight'], 'svelte_related': q in yes, 'label': '是' if q in yes else '否', 'reason': yes.get(q, 'The requirement primarily describes runtime behavior or an API, rather than single-file parsing, compilation, or syntax.')})
walk(d['rubrics'])
assert len(leaves) == 96
out = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'basis': 'Only leaf requirements text; no generated documentation or judgment results inspected. Syntax/compilation is included; runtime APIs alone are excluded. Ambiguous wording is classified by its primary stated mechanism.', 'rubric_sha256': hashlib.sha256((R / 'svelte-rubrics.json').read_bytes()).hexdigest(), 'leaves': leaves}
p = R / 'svelte-leaf-labels.json'
assert not p.exists()
p.write_text(json.dumps(out, ensure_ascii=False, indent=2))
p.chmod(292)
(R / 'labels-sha256.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest() + '\n')
print('leaves', len(leaves), 'yes', sum((x['svelte_related'] for x in leaves)), 'weights', dict(collections.Counter((x['weight'] for x in leaves))), 'UTC', out['created_utc'])
