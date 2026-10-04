import pytest
from cbe import module_facts
from cbe.native_handoff import next_work
from cbe.store import LedgerStore,LeaseError
from test_native_handoff import _run
from cbe.runner import analyze
from cbe.native_handoff import _dispatch_prompt
from cbe.token_budget import count_text_tokens
import json
from pathlib import Path

@pytest.mark.parametrize('limit',[True,False,0,-1,999,24001,8192.0,'8192'])
def test_invalid_input_limit_rejected_without_mutation(tmp_path,limit):
    run=_run(tmp_path);before=LedgerStore(run).open()
    with pytest.raises(ValueError):next_work(run,owner='controller',max_input_tokens=limit)
    assert LedgerStore(run).open()==before

def test_limit_only_applies_to_fresh_claim_and_keeps_batch_plan(tmp_path):
    run=_run(tmp_path)
    module_facts.initialize(run,batched=True)
    before=LedgerStore(run).open()
    item=next_work(run,owner='controller',max_input_tokens=8192)['items'][0]
    after=LedgerStore(run).open();call=after['calls'][item['call_id']]
    assert after['fact_batches']==before['fact_batches']
    assert call['extra']['effective_max_input_tokens']==8192
    assert call['extra']['planned_max_input_tokens']==8000
    again=next_work(run,owner='controller',max_input_tokens=16384)
    assert again['status']!='ready'
    assert LedgerStore(run).open()['calls'].keys()==after['calls'].keys()
    assert LedgerStore(run).open()['calls'][item['call_id']]==call
    unit=item['task_id'].removeprefix('task:fact_author:')
    current=LedgerStore(run).open()
    with pytest.raises(LeaseError):module_facts.claim(run,unit,owner='controller',max_input_tokens=16384)
    assert LedgerStore(run).open()==current

def test_ordinary_nonbatched_limit_measures_complete_prompt_and_records_cap(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    (repo/'ops.py').write_text('def values():\n    return {\n'+''.join(f"        'key_{i}': {i},\n" for i in range(300))+'    }\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    module_facts.initialize(run,batched=False)
    before=LedgerStore(run).open()
    tid=next(t for t in before['tasks'] if t.startswith('task:fact_author:'))
    unit=tid.removeprefix('task:fact_author:')
    with pytest.raises(module_facts.PromptLayoutError):
        module_facts.claim(run,unit,owner='ordinary',max_input_tokens=1000)
    assert LedgerStore(run).open()==before
    claimed=module_facts.claim(run,unit,owner='ordinary',max_input_tokens=8192)
    after=LedgerStore(run).open();call=after['calls'][claimed['call_id']]
    packet=json.loads(Path(claimed['packet_path']).read_bytes())
    assert 1000<count_text_tokens(_dispatch_prompt(packet,'fact').decode())<=8192
    assert call['extra']['effective_max_input_tokens']==8192
    assert call['extra']['planned_max_input_tokens'] is None
    assert after['details']==before['details']
