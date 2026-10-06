import json
from pathlib import Path
import pytest
from cbe import cli, module_facts
from cbe.native_handoff import next_work
from cbe.runner import analyze
from cbe.store import LedgerStore
from test_native_handoff import _record, _business_result


def repair_fixture(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    (repo/'ops.py').write_text('def rule(x):\n    return x * 2\n\ndef wrapper(x):\n    return rule(x)\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    l=LedgerStore(run).open();ids={s['name']:sid for sid,s in l['inventory']['symbols'].items()}
    while not all(ids[n] in LedgerStore(run).open()['details'] for n in ('rule','wrapper')):
        item=next_work(run,owner='controller')['items'][0]
        _record(tmp_path,run,item,'started');_record(tmp_path,run,item,'completed',_business_result(run,item))
    next_work(run,owner='controller')
    def legacy(l):
        d=l['details'][ids['rule']]
        d['provenance'].pop('behavior_contract',None)
        l['fact_reviews'][ids['rule']]['content_sha256']=module_facts._sha_json(d)
        task=l['tasks'][item['task_id']];task['state']='needs_repair';task['extra']['repair_ids']=[ids['wrapper']]
        return l
    LedgerStore(run).mutate(legacy)
    repaired=next_work(run,owner='controller')['items'][0]
    return run,repaired,ids


def test_cli_preserves_pairing_but_does_not_present_protected_as_running(tmp_path,capsys):
    repo=tmp_path/'repo';repo.mkdir();(repo/'ops.py').write_text('def f(x):\n    return x\n')
    run=tmp_path/'run';analyze(repo,run,documentation_profile='module-first-v2')
    assert cli.main(['native-next','--run-dir',str(run),'--owner','controller'])==0
    result=json.loads(capsys.readouterr().out);item=result['items'][0]
    assert all(item.get(k) is not None for k in ['call_id','task_id','generation','dispatch_prompt_path'])
    assert result['host_running_count'] is None
    assert 'not host running' in result['active_semantics']
    assert 'old ready and active are not retry' in result['dispatch_rule']
    prompt=Path(item['dispatch_prompt_path']).read_text()
    assert 'Cached ready is not retry' in prompt and 'ledger active means protected calls' in prompt
    before=LedgerStore(run).open()['calls'][item['call_id']]
    assert cli.main(['native-next','--run-dir',str(run),'--owner','controller'])==0
    waiting=json.loads(capsys.readouterr().out)
    assert waiting['status'] in {'ready','needs_reconciliation'}
    assert waiting['protected_call_count']==1 and waiting['host_running_count'] is None
    assert LedgerStore(run).open()['calls'][item['call_id']]==before


def test_legacy_dependency_keeps_behavior_but_shows_no_claimable_ids(tmp_path):
    run,item,ids=repair_fixture(tmp_path)
    call=LedgerStore(run).open()['calls'][item['call_id']]
    packet=json.loads(Path(call['extra']['packet_path']).read_bytes())
    owner=next(dep for dep in packet['accepted_dependencies'] if dep['symbol_id']==ids['rule'])
    assert owner['claims']==[] and owner['behavior']
    prompt=Path(item['dispatch_prompt_path']).read_text()
    assert 'Empty or omitted claims means no claimable IDs' in prompt
    assert 'dependency_id/reason object belongs only in local_view_gaps' in prompt


@pytest.mark.parametrize('ref,missing', [({'symbol_id':'OWNER'},'claim_id'),
    ({'dependency_id':'outside','reason':'not shown'},'symbol_id, claim_id'),
    ({'symbol_id':'OWNER','claim_id':'invented'},'no same-revision owner')])
def test_bad_reference_names_exact_item_path_and_keeps_rejection(tmp_path,ref,missing):
    run,item,ids=repair_fixture(tmp_path)
    ref={**ref}
    if ref.get('symbol_id')=='OWNER':ref['symbol_id']=ids['rule']
    result=_business_result(run,item);result['items'][0]['behavior_contract']['claim_refs']=[ref]
    before=LedgerStore(run).open()['details']
    _record(tmp_path,run,item,'started')
    with pytest.raises(ValueError) as error:_record(tmp_path,run,item,'completed',result)
    assert 'items[0].behavior_contract.claim_refs[0]' in str(error.value)
    assert missing in str(error.value)
    if 'dependency_id' in ref:assert 'belongs in local_view_gaps' in str(error.value)
    assert LedgerStore(run).open()['details']==before
