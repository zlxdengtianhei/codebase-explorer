import json

import pytest

from cbe import cli, native_handoff as native
from cbe.store import LedgerStore
from test_native_transaction_cost import setup_claim


def offered(tmp_path):
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    return run, native._offer(run, tid, claim, None)


def test_public_placeholder_rejects_before_event_or_accounting(tmp_path, capsys):
    run, item = offered(tmp_path)
    before = LedgerStore(run).open()
    assert cli.main(['native-record','--run-dir',str(run),'--call-id',item['call_id'],
        '--status','started','--host','zcode','--child-handle','agent_new_2f3f']) == 2
    assert 'host-metadata' in capsys.readouterr().err
    assert LedgerStore(run).open() == before
    assert not list((run/'native').glob('*.started.*'))


def test_low_level_placeholder_and_real_shape_keep_evidence_grade(tmp_path):
    run, item = offered(tmp_path)
    event = {'schema':native.SCHEMA,'call_id':item['call_id'],'task_id':item['task_id'],
        'generation':item['generation'],'prompt_sha256':item['prompt_sha256'],
        'host':'zcode','status':'started','child_handle':'agent_new_2f3f',
        'evidence_level':'controller_attested','transport':'file','additional_reads':'unknown'}
    path=tmp_path/'event.json';path.write_text(json.dumps(event))
    before = LedgerStore(run).open()
    with pytest.raises(ValueError,match='placeholder'):
        native.record_event(run,item['call_id'],path)
    assert LedgerStore(run).open() == before
    handle='agent_a180b5c6-87c0-4e23-a688-af4eed50976e'
    native.record(run,item['call_id'],status='started',host='zcode',child_handle=handle)
    call=LedgerStore(run).open()['calls'][item['call_id']]
    assert call['state']=='sent' and call['extra']['native_handoff']['child_handle']==handle
    assert call['extra']['delivery_evidence']=='controller_attested'
    assert call['extra']['usage_status']=='unavailable'


def test_other_host_and_accepted_legacy_zcode_replay_stay_compatible(tmp_path, monkeypatch):
    run,item=offered(tmp_path)
    native.record(run,item['call_id'],status='started',host='codex',child_handle='child-placeholder')
    p=tmp_path/'legacy';p.mkdir();run,item=offered(p)
    with monkeypatch.context() as m:
        # Accepted historical evidence from the old implementation is retained.
        m.setattr(native,'_fresh_zcode_child',lambda *args:None)
        native.record(run,item['call_id'],status='started',host='zcode',child_handle='agent_new_2f3f')
    before=LedgerStore(run).open()
    assert native.record(run,item['call_id'],status='started',host='zcode',child_handle='agent_new_2f3f')['idempotent']
    assert LedgerStore(run).open()==before
