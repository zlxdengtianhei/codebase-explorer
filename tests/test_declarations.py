"""Named ordinary declarations use real grammars, catalog search and frozen source."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from cbe import docs
from cbe.source_context import build_context, canonical_symbol_id
from cbe.symbols import inventory_from_context

FIXTURES = Path(__file__).parent / "fixtures" / "declarations"


def render(root, run):
    context = build_context(root)
    assert not [d for d in context['diagnostics'] if d['code'] == 'source_reassembly_fallback']
    for f in context['files']:
        chunks = sorted((c for c in context['chunks'] if c['path'] == f['path']), key=lambda c: c['start_byte'])
        assert ''.join(c['text'] for c in chunks).encode() == (root / f['path']).read_bytes()
    inv = inventory_from_context(context)
    units = {s['id']: {'id': s['id'], 'kind': s['kind'], 'name': s['name'],
                      'explain': 'Deterministic declaration probe.', 'members': [], 'relations': []}
             for entry in inv.values() for s in entry['symbols']}
    run.mkdir(exist_ok=True)
    (run / 'context.json').write_text(json.dumps(context))
    docs.render(run_dir=run, source_root=root, inventory=inv, units=units,
                dispositions={uid: {'how': 'unit', 'unit': uid} for uid in units},
                tree={'nodes': [{'id': 'root', 'parent': None, 'title': 'Declarations',
                                 'summary': 'Declaration probe.', 'unit_ids': list(units)}], 'depends_on': []},
                languages={f['path']: f['language'] for f in context['files']}, context=context)
    return context, inv


def cli(run, command, *args):
    result = subprocess.run([sys.executable, '-m', 'cbe', command, '--run-dir', str(run), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize(('name', 'path', 'source'), [
    ('LIMIT', 'c/demo.c', '#define LIMIT 8'),
    ('LIMIT', 'cpp/demo.cpp', 'constexpr int LIMIT = 8'),
    ('LIMIT', 'go/demo.go', 'const LIMIT = 8'),
    ('LIMIT', 'javascript/demo.js', 'export const LIMIT = 8'),
    ('LIMIT', 'typescript/demo.ts', 'export const LIMIT = 8'),
    ('counter', 'c/demo.c', 'static int counter = 0'),
    ('Point', 'c/demo.c', 'typedef struct { int x; } Point;'),
    ('Size', 'c/demo.c', 'typedef unsigned long Size;'),
    ('Size', 'cpp/demo.cpp', 'using Size = unsigned long;'),
    ('B', 'go/demo.go', 'B string'),
    ('INC', 'c/demo.c', '#define INC(x)'),
    ('LIMIT', 'java/Demo.java', 'static final int LIMIT = 8;'),
    ('LIMIT', 'ruby/demo.rb', 'LIMIT = 8'),
    ('CONST', 'ruby/demo.rb', 'CONST = 3'),
    ('FIELD', 'ruby/demo.rb', 'FIELD = 4'),
])
def test_find_query_source(tmp_path, name, path, source):
    if path.endswith('.rb'):
        pytest.importorskip('tree_sitter_ruby')
    run = tmp_path / 'run'
    render(FIXTURES, run)
    hits = json.loads(cli(run, 'find', '--term', name, '--limit', '200', '--json'))
    hit = next(h for h in hits if h['id'].startswith(path + '::') and name in h['name'])
    record = json.loads(cli(run, 'query', '--id', hit['id'], '--json'))
    assert record['ranges']
    assert source in cli(run, 'source', '--id', hit['id'])


def chunks(tmp_path, filename, text):
    if filename.endswith('.rb'):
        pytest.importorskip('tree_sitter_ruby')
    (tmp_path / filename).write_bytes(text.encode())
    ctx = build_context(tmp_path, paths=[filename])
    assert not ctx['diagnostics']
    assert ''.join(c['text'] for c in ctx['chunks']) == text
    return ctx['chunks']


@pytest.mark.parametrize(('filename', 'text', 'absent'), [
    ('a.c', 'int f(void) { int local=1; static int cached=2; return local; }\n', {'local', 'cached'}),
    ('a.c', 'int prototype(int x);\n', {'prototype', 'x'}),
    ('a.c', 'struct S { int field; }; enum E { RED, BLUE };\n', {'field', 'RED', 'BLUE'}),
    ('a.cpp', 'struct S { static int member; int field; };\n', {'member', 'field'}),
    ('a.js', 'function f() { const local=1; }\n{ let blockLocal=2; }\n', {'local', 'blockLocal'}),
    ('a.js', 'switch (0) { case 0: const caseLocal=1; }\n', {'caseLocal'}),
    ('A.java', 'class A { void f() { int local=1; final int cached=2; } }\n', {'local', 'cached'}),
    ('a.rb', 'local = 1\n$global = 2\nclass Box\n @instance = 3\n @@shared = 4\nend\n', {'local', '$global', '@instance', '@@shared'}),
    ('a.go', 'package p\nfunc f() { var local = 1; const cached = 2 }\n', {'local', 'cached'}),
    ('a.py', 'LIMIT=1\ncomputed=object()\nclass Box:\n FIELD=2\n', {'LIMIT', 'computed', 'FIELD'}),
])
def test_non_units(tmp_path, filename, text, absent):
    rows = chunks(tmp_path, filename, text)
    assert not (absent & {c['name'] for c in rows})
    assert not [c for c in rows if c['kind'] == 'module_region']


def test_macros_runs_comments_conditionals_and_multiline(tmp_path):
    text = '#define ONE 1\n/* gap */\n#define TWO(x) \\\n ((x)+1)\nint f(void) { return 0; }\n#define SINGLE 3\n#if ENABLED\n#define INSIDE 4\n#else\n#define OTHER 5\n#endif\n#define AFTER 6\n'
    rows = chunks(tmp_path, 'a.c', text)
    ordinary = [c for c in rows if c['kind'] == 'module_region']
    assert [c['name'] for c in ordinary] == ['ONE, TWO', 'SINGLE', 'INSIDE', 'OTHER', 'AFTER']
    assert ordinary[0]['text'] == text[:text.index('int f')]
    run = tmp_path / 'run'
    render(tmp_path, run)
    for name in ['ONE', 'TWO', 'SINGLE', 'INSIDE', 'OTHER', 'AFTER']:
        hits = docs.find(run, name, limit=200)
        assert any(name in h['name'] for h in hits)


def test_multiple_declarators_and_function_pointer(tmp_path):
    rows = chunks(tmp_path, 'a.c', 'static int first=1, second=2;\nint (*callback)(int);\nint prototype(int);\ntypedef void (*Handler)(int);\n')
    names = ', '.join(c['name'] for c in rows if c['kind'] == 'module_region')
    for name in ['first', 'second', 'callback', 'Handler']:
        assert name in names
    assert 'prototype' not in names


def test_go_grouped_sibling_types_and_values(tmp_path):
    text = 'package p\ntype (\n A int\n B string\n C = int\n)\nvar (\n x, y int\n z=3\n)\nconst (\n ONE=1\n TWO\n)\n'
    rows = chunks(tmp_path, 'a.go', text)
    named = {c['name']: c for c in rows if c['kind'] != 'module_residual'}
    assert {'A', 'B', 'C', 'x, y, z', 'ONE, TWO'} <= named.keys()
    assert all(c['parent_id'] is None for c in named.values())
    assert named['A']['symbol_id'] == canonical_symbol_id('a.go', 'type', 'A', text.index('type'))
    assert named['A']['end_byte'] == text.index('A int') + len('A int')
    assert named['A']['full_end_byte'] == text.index(')') + 1


@pytest.mark.parametrize(('filename', 'text', 'expected'), [
    ('A.java', 'class A {\n static final int ONE=1;\n // gap\n int two=2, three=3;\n void f() {}\n int four;\n}\n', ['ONE, two, three', 'four']),
    ('a.rb', 'ONE=1\n# gap\nTWO=2\ndef f; 0; end\nTHREE=3\n', ['ONE, TWO', 'THREE']),
    ('a.js', 'export const ONE=1;\n// gap\nlet TWO=2;\nfunction f() {}\nvar THREE=3;\n', ['ONE, TWO', 'THREE']),
])
def test_value_runs_in_other_languages(tmp_path, filename, text, expected):
    rows = chunks(tmp_path, filename, text)
    assert [c['name'] for c in rows if c['kind'] == 'module_region'] == expected


def test_crlf_unicode_and_separate_aliases(tmp_path):
    text = '// café\r\n#define ONE 1\r\n#define TWO(x) \\\r\n ((x)+1)\r\ntypedef int Size;\r\ntypedef long Other;\r\n'
    rows = chunks(tmp_path, 'a.c', text)
    assert [c['name'] for c in rows if c['kind'] == 'module_region'] == ['ONE, TWO', 'Size', 'Other']
    macro = next(c for c in rows if c['name'] == 'ONE, TWO')
    assert macro['start_byte'] == len('// café\r\n'.encode())


def test_go_aliases_keep_legacy_container_identity(tmp_path):
    text = 'package p\ntype Alias = int\ntype ( A = int; B string )\n'
    rows = chunks(tmp_path, 'a.go', text)
    # Alias-only declarations previously had an unnamed type container.
    legacy = canonical_symbol_id('a.go', 'type', '', text.index('type'))
    assert any(c['symbol_id'] == legacy and c['full_end_byte'] == text.index('\ntype (') for c in rows)
    assert {'Alias', 'A', 'B'} <= {c['name'] for c in rows}
    assert all(c['parent_id'] is None for c in rows)


def test_mixed_js_binding_keeps_function_identity_and_prefix(tmp_path):
    text = 'export const value=1, helper=()=>2;\n'
    rows = chunks(tmp_path, 'a.js', text)
    helper = next(c for c in rows if c['name'] == 'helper')
    assert helper['symbol_id'] == canonical_symbol_id('a.js', 'function', 'helper', 0)
    assert (helper['start_byte'], helper['end_byte']) == (0, text.index(';'))
    assert not [c for c in rows if c['kind'] == 'module_region']
    run = tmp_path / 'run'
    render(tmp_path, run)
    assert any(h['id'] == helper['symbol_id'] for h in docs.find(run, 'value'))
