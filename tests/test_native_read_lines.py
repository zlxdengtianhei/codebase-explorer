import json

import pytest

from cbe.native_handoff import _display_json, _dispatch_prompt, _readable_instruction, READ_LINE_LIMIT


def read_surface(text):
    return '\n'.join(line.encode('utf-16-le')[:READ_LINE_LIMIT*2].decode('utf-16-le',errors='surrogatepass')
                     for line in text.split('\n'))


@pytest.mark.parametrize('value', [
    [{'symbol_id':str(i),'claims':[{'id':'rule','effect':'x'*100}]} for i in range(80)],
    [{'effect':'界'*100,'nested':[False,None,3]} for _ in range(80)],
    [{'effect':'😀'*100,'nested':[False,None,3]} for _ in range(80)],
])
def test_structured_display_survives_official_per_line_read_limit(value):
    shown=_display_json(value)
    assert all(len(line.encode('utf-16-le'))//2<=READ_LINE_LIMIT for line in shown.split('\n'))
    assert json.loads(read_surface(shown))==value


def test_short_metadata_keeps_compact_bytes():
    value={'symbol_id':'a','claims':[]}
    assert _display_json(value)==json.dumps(value,ensure_ascii=False,separators=(',',':'))


def test_source_and_long_string_stay_verbatim_with_complete_reader_warning():
    source='Frozen source path ops.py:\nL1: diagnostic = '+repr('x'*4300)+'\n'
    packet={'instruction':'Explain. '+'words '*700,'assignments':[{'symbol_id':'a'}],
        'source':source,'behavior_contract_required':True,
        'accepted_dependencies':[{'symbol_id':'owner','claims':[],'behavior':'z'*4500}]}
    rendered=_dispatch_prompt(packet,'fact').decode()
    assert source in rendered  # No word-wrapped or rewritten source body.
    read=read_surface(rendered)
    assert 'Every assigned ID must be returned' in read
    assert 'behavior_contract containing claims' in read
    assert 'Read long-line boundary' in read
    assert 'complete-file reader' in read and 'permission denial is host_blocked' in read
    shown=rendered.split('Bound accepted dependency facts (static links do not prove runtime binding):\n',1)[1].split('\n\nEND_CBE_NATIVE_PACKET',1)[0]
    assert json.loads(shown)==packet['accepted_dependencies']
    assert 'Lossless JSON text chunks' not in rendered
    assert 'END_CBE_NATIVE_PACKET' in read
    assert source.split('\n')[1] not in read_surface(source)


def test_long_json_string_is_not_reencoded_into_a_new_protocol():
    value={'original':'"\\\n\t界'*1600}
    shown=_display_json(value)
    assert json.loads(shown)==value
    assert any(len(line)>READ_LINE_LIMIT for line in shown.split('\n'))
    with pytest.raises(json.JSONDecodeError):json.loads(read_surface(shown))


def test_nonbmp_source_and_owner_literal_trigger_complete_read_warning():
    packet={'instruction':'Explain.','assignments':[{'symbol_id':'a'}],
        'source':'L1: s = '+repr('😀'*1200)+'\n','behavior_contract_required':True,
        'accepted_dependencies':[{'symbol_id':'owner','behavior':'😀'*1200,'claims':[]}]}
    full=_dispatch_prompt(packet,'fact').decode()
    assert packet['source'] in full and packet['source'] not in read_surface(full)
    assert 'Read long-line boundary' in full
    assert '2000-UTF-16-code-unit' in full
    shown=full.split('Bound accepted dependency facts (static links do not prove runtime binding):\n',1)[1].split('\n\nEND_CBE_NATIVE_PACKET',1)[0]
    assert json.loads(shown)==packet['accepted_dependencies']
    assert shown.startswith('[\n')  # Python code-point length would keep compact JSON.


def test_nonbmp_instruction_wrap_uses_host_units_and_keeps_words():
    original='😀 word '*500
    displayed=_readable_instruction(original)
    assert all(len(line.encode('utf-16-le'))//2<=READ_LINE_LIMIT for line in displayed.split('\n'))
    assert displayed.split()==original.split()
