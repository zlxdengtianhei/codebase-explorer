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
    ('Point', 'c/demo.c', 'struct { int x; }'),
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
    hit = next(h for h in hits if h['id'].startswith(path + '::'))
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
    assert [c['name'] for c in ordinary] == ['ONE', 'SINGLE', 'INSIDE', 'OTHER', 'AFTER']
    assert ordinary[0]['text'] == text[:text.index('int f')]
    run = tmp_path / 'run'
    render(tmp_path, run)
    for name in ['ONE', 'TWO', 'SINGLE', 'INSIDE', 'OTHER', 'AFTER']:
        hits = docs.find(run, name, limit=200)
        assert hits


def test_multiple_declarators_and_function_pointer(tmp_path):
    rows = chunks(tmp_path, 'a.c', 'static int first=1, second=2;\nint (*callback)(int);\nint prototype(int);\ntypedef void (*Handler)(int);\n')
    names = ', '.join(c['signature'] for c in rows if c['kind'] == 'module_region')
    for name in ['first', 'second', 'callback', 'Handler']:
        assert name in names
    assert 'prototype' not in names


def test_go_grouped_sibling_types_and_values(tmp_path):
    text = 'package p\ntype (\n A int\n B string\n C = int\n)\nvar (\n x, y int\n z=3\n)\nconst (\n ONE=1\n TWO\n)\n'
    rows = chunks(tmp_path, 'a.go', text)
    named = {c['name']: c for c in rows if c['kind'] != 'module_residual'}
    assert {'A', 'B', 'C', 'x', 'ONE'} <= named.keys()
    assert all(c['parent_id'] is None for c in named.values())
    assert named['A']['symbol_id'] == canonical_symbol_id('a.go', 'type', 'A', text.index('type'))
    assert named['A']['end_byte'] == text.index('A int') + len('A int')
    assert named['A']['full_end_byte'] == text.index(')') + 1


@pytest.mark.parametrize(('filename', 'text', 'expected'), [
    ('A.java', 'class A {\n static final int ONE=1;\n // gap\n int two=2, three=3;\n void f() {}\n int four;\n}\n', ['ONE', 'four']),
    ('a.rb', 'ONE=1\n# gap\nTWO=2\ndef f; 0; end\nTHREE=3\n', ['ONE', 'THREE']),
    ('a.js', 'export const ONE=1;\n// gap\nlet TWO=2;\nfunction f() {}\nvar THREE=3;\n', ['ONE', 'THREE']),
])
def test_value_runs_in_other_languages(tmp_path, filename, text, expected):
    rows = chunks(tmp_path, filename, text)
    assert [c['name'] for c in rows if c['kind'] == 'module_region'] == expected


def test_crlf_unicode_and_separate_aliases(tmp_path):
    text = '// café\r\n#define ONE 1\r\n#define TWO(x) \\\r\n ((x)+1)\r\ntypedef int Size;\r\ntypedef long Other;\r\n'
    rows = chunks(tmp_path, 'a.c', text)
    assert [c['name'] for c in rows if c['kind'] == 'module_region'] == ['ONE', 'Size', 'Other']
    macro = next(c for c in rows if c['name'] == 'ONE')
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


@pytest.mark.parametrize(('definition', 'kind', 'type_name'), [
    ('struct { int x; }', 'struct', ''),
    ('struct Tagged { int x; }', 'struct', 'Tagged'),
    ('union { int x; float y; }', 'union', ''),
    ('enum { RED, BLUE }', 'enum', ''),
])
def test_typedef_definition_reuses_type_identity(tmp_path, definition, kind, type_name):
    text = f'typedef {definition} Point;\ntypedef unsigned long Size;\ntypedef struct Foo Foo;\n'
    rows = chunks(tmp_path, 'a.c', text)
    declared = [c for c in rows if c['kind'] != 'module_residual']
    original = next(c for c in declared if c['kind'] == kind)
    assert original['symbol_id'] == canonical_symbol_id('a.c', kind, type_name, len('typedef '))
    assert (original['full_start_byte'], original['full_end_byte']) == (len('typedef '), len('typedef ' + definition))
    assert [c['name'] for c in declared if c['kind'] == 'module_region'] == ['Size', 'Foo']
    assert sum('Point' in c['signature'] for c in declared) == 1
    assert all(c['text'].strip() not in {'typedef', '} Point;'} for c in declared)
    run = tmp_path / 'run'
    render(tmp_path, run)
    hits = json.loads(cli(run, 'find', '--term', 'Point', '--json'))
    assert [h['id'] for h in hits] == [original['id']]
    record = json.loads(cli(run, 'query', '--id', original['id'], '--json'))
    assert 'Point' in record['signature']
    assert original['text'] == definition
    assert definition in cli(run, 'source', '--id', original['id'])
    for name in ['Size', 'Foo']:
        hits = docs.find(run, name)
        assert len(hits) == 1 and hits[0]['name'] == name


def test_long_value_run_keeps_first_id_and_every_name_searchable(tmp_path):
    names = [f'value_{i:03d}' for i in range(120)]
    text = ''.join(f'int {name} = {i};\n' for i, name in enumerate(names))
    rows = chunks(tmp_path, 'a.c', text)
    regions = [c for c in rows if c['kind'] == 'module_region']
    assert len(regions) == 1
    first = regions[0]
    assert first['name'] == first['qualified_name'] == names[0]
    assert first['id'] == canonical_symbol_id('a.c', 'module_region', names[0], 0)
    assert ',' not in first['id']
    run = tmp_path / 'run'
    render(tmp_path, run)
    for name in names:
        assert [h['id'] for h in docs.find(run, name)] == [first['id']]
    # Appending adjacent declarations changes the span, not the run's identity.
    rows = chunks(tmp_path, 'a.c', text + 'int appended = 120;\n')
    assert next(c for c in rows if c['kind'] == 'module_region')['id'] == first['id']


@pytest.mark.parametrize('filename', ['a.cpp', 'a.h'])
@pytest.mark.parametrize('source', [
    'FMT_NORETURN FMT_API void compare(const char* s1, const char* s2);',
    'FMT_API int compare(const char* s1, const char* s2);',
    'FMT_CONSTEXPR auto compare(const char* s1, const char* s2) -> int { return 0; }',
    'template <typename Char> FMT_CONSTEXPR auto compare(const Char* s1, const Char* s2) -> int { return 0; }',
    'int prototype(int parameter);',
    'int *prototype(int parameter);',
    'int (prototype)(int parameter);',
    'int value, prototype(int parameter);',
    'int broken ERROR_TOKEN = 1;',
    'auto value = [] { return 1; }();',
])
def test_cpp_functions_and_uncertain_declarations_are_not_values(tmp_path, filename, source):
    (tmp_path / filename).write_text(source + '\n')
    context = build_context(tmp_path, paths=[filename])
    assert {d['code'] for d in context['diagnostics']} <= {'syntax_error', 'ambiguous_language'}
    assert ''.join(c['text'] for c in context['chunks']) == source + '\n'
    assert not [c for c in context['chunks'] if c['kind'] == 'module_region']


@pytest.mark.parametrize('source,name', [
    ('int (*fp)(int);', 'fp'),
    ('int (*callbacks[2])(int);', 'callbacks'),
    ('int (&ref)(int) = target;', 'ref'),
    ('static int counter = 0;', 'counter'),
    ('constexpr int LIMIT = 8;', 'LIMIT'),
    ('const int *pointer = nullptr;', 'pointer'),
    ('int array[4];', 'array'),
    ('typedef int Function(int);', 'Function'),
])
def test_cpp_variable_declarators_keep_the_declared_name(tmp_path, source, name):
    rows = chunks(tmp_path, 'a.cpp', source + '\n')
    assert [c['name'] for c in rows if c['kind'] == 'module_region'] == [name]


@pytest.mark.parametrize('filename,source,kind,name,start,end', [
    ('a.c', 'struct S { int x; } value;\n', 'struct', 'S', 0, 19),
    ('a.cpp', 'auto value = [] { struct Inner {}; return Inner{}; }();\n', 'struct', 'Inner', 18, 33),
    ('a.js', 'const value = class Inner { method() {} };\n', 'class', 'Inner', 0, 41),
    ('A.java', 'class A { static Object value = new Object() { void method() {} }; }\n', 'method', 'method', 47, 63),
])
def test_ordinary_region_never_encloses_existing_declaration(tmp_path, filename, source, kind, name, start, end):
    rows = chunks(tmp_path, filename, source)
    existing = next(c for c in rows if c['name'] == name and c['kind'] == kind)
    assert existing['symbol_id'] == canonical_symbol_id(filename, kind, name if filename != 'A.java' else 'A.method', start)
    assert (existing['full_start_byte'], existing['full_end_byte']) == (start, end)
    assert not [c for c in rows if c['kind'] == 'module_region']


def test_query_does_not_repeat_coalesced_search_names(tmp_path):
    (tmp_path / 'a.c').write_text('int first = 1;\nint second = 2;\n')
    run = tmp_path / 'run'
    context, _ = render(tmp_path, run)
    region = next(c for c in context['chunks'] if c['kind'] == 'module_region')
    assert region['signature'] == 'first, second'
    record = json.loads(cli(run, 'query', '--id', region['id'], '--json'))
    assert record['signature'].count('first') == record['signature'].count('second') == 1


@pytest.mark.parametrize('filename', ['a.js', 'a.ts', 'a.tsx'])
def test_destructuring_names_are_bindings_not_properties_or_defaults(tmp_path, filename):
    source = ('export const {property: renamed, shorthand, missing = fallback, '
              'nested: {inner}, ...rest} = receiver.call(argument);\n'
              'const [first, , ...others] = receiver.values;\n')
    rows = chunks(tmp_path, filename, source)
    regions = [c for c in rows if c['kind'] == 'module_region']
    assert len(regions) == 1
    assert regions[0]['name'] == 'renamed'
    assert regions[0]['signature'] == 'renamed, shorthand, missing, inner, rest, first, others'


@pytest.mark.parametrize('filename,source,name', [
    ('A.java', 'class A { static Object holder = receiver.call(argument); }\n', 'holder'),
    ('a.go', 'package p\nvar holder = receiver.Call(argument)\n', 'holder'),
    ('a.rb', 'HOLDER = receiver.call(argument)\n', 'HOLDER'),
])
def test_other_language_values_use_declared_names(tmp_path, filename, source, name):
    rows = chunks(tmp_path, filename, source)
    assert [c['name'] for c in rows if c['kind'] == 'module_region'] == [name]
    assert [c['signature'] for c in rows if c['kind'] == 'module_region'] == [name]


@pytest.mark.parametrize('filename', ['a.h', 'a.cpp'])
@pytest.mark.parametrize('source', [
    'class X;\nstruct S;\nenum E;\n',
    'class Box { int data_; using value_type = int; };\n',
    'template <typename T> FMT_CONSTEXPR auto f(T parameter) -> int { int num_zeros=0; return num_zeros; }\n',
    'namespace ns { inline auto f(int x) -> int { int local=0; return local; } }\n',
])
def test_cpp_scope_recovery_never_indexes_locals_fields_or_forward_types(tmp_path, filename, source):
    (tmp_path / filename).write_text(source)
    context = build_context(tmp_path, paths=[filename])
    assert not [c for c in context['chunks'] if c['kind'] == 'module_region']
    assert ''.join(c['text'] for c in context['chunks']) == source


@pytest.mark.parametrize('filename,source,names', [
    ('a.cpp', 'namespace ns { constexpr int LIMIT=8; using Size=unsigned long; }\nstatic int counter=0;\n', ['LIMIT', 'Size', 'counter']),
    ('a.cpp', 'extern "C" { int value=1; }\ntemplate <typename T> constexpr T limit = 8;\n', ['value', 'limit']),
    ('a.h', 'static int counter=0;\nconstexpr int LIMIT=8;\nusing Size=Counter;\n', ['counter']),
    ('a.c', 'static int counter=0;\nextern int global;\n', ['counter']),
])
def test_permitted_c_cpp_declaration_scopes(tmp_path, filename, source, names):
    (tmp_path / filename).write_text(source)
    context = build_context(tmp_path, paths=[filename])
    assert [c['name'] for c in context['chunks'] if c['kind'] == 'module_region'] == names
    if filename == 'a.h':
        assert next(c['signature'] for c in context['chunks'] if c['kind'] == 'module_region') == 'counter, LIMIT, Size'
    assert ''.join(c['text'] for c in context['chunks']) == source


@pytest.mark.parametrize('filename', ['a.c', 'a.cpp', 'a.h'])
def test_macros_inside_functions_are_indexed_without_local_variables(tmp_path, filename):
    source = 'int f(void) {\n#define LOCAL_MACRO(x) ((x)+1)\n int local=0; return LOCAL_MACRO(local);\n}\n'
    (tmp_path / filename).write_text(source)
    context = build_context(tmp_path, paths=[filename])
    assert [c['name'] for c in context['chunks'] if c['kind'] == 'module_region'] == ['LOCAL_MACRO']
    function = next(c for c in context['chunks'] if c['kind'] == 'function')
    assert function['symbol_id'] == canonical_symbol_id(filename, 'function', 'f', 0)
    assert function['full_end_byte'] == len(source.rstrip())
    assert ''.join(c['text'] for c in context['chunks']) == source
