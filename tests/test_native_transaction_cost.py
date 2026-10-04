import json
import time
from pathlib import Path

import pytest

from cbe import module_facts, native_handoff as native
from cbe.runner import analyze
from cbe.packets import PacketSourceError
from cbe.store import LedgerStore, StaleWriteError


def setup_claim(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'ops.py').write_text('def twice(x):\n    return x * 2\n')
    run = tmp_path / 'run'
    analyze(repo, run, documentation_profile='module-first-v2')
    module_facts.initialize(run)
    ledger = LedgerStore(run).open()
    tid = next(k for k,v in ledger['tasks'].items() if v['kind'] == 'fact_author')
    return run, tid, tid.removeprefix('task:fact_author:')


def measured(monkeypatch, operation):
    counts = {'reads': 0, 'writes': 0}
    read, write = LedgerStore.read_unlocked, LedgerStore.write_unlocked
    def r(self):
        counts['reads'] += 1
        return read(self)
    def w(self, ledger):
        counts['writes'] += 1
        return write(self, ledger)
    with monkeypatch.context() as m:
        m.setattr(LedgerStore, 'read_unlocked', r)
        m.setattr(LedgerStore, 'write_unlocked', w)
        wall, cpu = time.perf_counter(), time.process_time()
        value = operation()
        counts.update(wall=time.perf_counter()-wall, cpu=time.process_time()-cpu)
    return value, counts


def test_same_shape_offer_and_public_start_transaction_counts(tmp_path, monkeypatch):
    results = {}
    for old in (True, False):
        p = tmp_path / str(old); p.mkdir()
        run, tid, bid = setup_claim(p)
        def offer():
            claim = module_facts.claim(run, bid, owner='controller/fact_author',
                require_behavior_contract=True, _workflow_initialized=True,
                _defer_local_ready=not old)
            return native._offer(run, tid, claim, None)
        item, offer_counts = measured(monkeypatch, offer)
        original = native.record_event
        with monkeypatch.context() as m:
            if old:
                def legacy(*args, **kwargs):
                    kwargs.pop('_preview', None)
                    return original(*args, **kwargs)
                m.setattr(native, 'record_event', legacy)
            _, start_counts = measured(monkeypatch, lambda: native.record(run,
                item['call_id'], status='started', host='test', child_handle='child'))
        l = LedgerStore(run).open(); c = l['calls'][item['call_id']]
        assert c['state'] == 'sent' and c['extra']['usage_status'] == 'unavailable'
        assert c['extra']['preparation_stage'] == 'local_artifacts_ready'
        before = c
        assert native.record(run, item['call_id'], status='started', host='test',
                             child_handle='child')['idempotent']
        with pytest.raises(StaleWriteError):
            native.record(run, item['call_id'], status='started', host='test', child_handle='other')
        assert LedgerStore(run).open()['calls'][item['call_id']] == before
        packet = json.loads(Path(c['extra']['packet_path']).read_bytes())
        def stable(value):
            return (json.dumps(value, sort_keys=True).replace(str(run.resolve()), '<run>')
                    .replace(item['call_id'], '<call>')
                    .replace(packet['source_revision'], '<repository_revision>'))
        results[str(old)] = {'offer':offer_counts,'start':start_counts,
            'packet_keys':sorted(packet),'item_keys':sorted(item),
            'packet':stable(packet), 'item':stable(item),
            'dispatch':Path(item['dispatch_prompt_path']).read_text()}
    assert results['True']['offer']['reads'] == 3
    assert results['False']['offer']['reads'] == 2
    assert results['True']['offer']['writes'] == 3
    assert results['False']['offer']['writes'] == 2
    assert results['True']['start']['reads'] == 3
    assert results['False']['start']['reads'] == 2
    assert results['True']['start']['writes'] == results['False']['start']['writes'] == 1
    assert results['True']['packet_keys'] == results['False']['packet_keys']
    assert results['True']['item_keys'] == results['False']['item_keys']
    for key in ('packet','item','dispatch'):
        assert results['True'][key] == results['False'][key]
    print('TRANSACTION_MEASUREMENT', json.dumps({k:{a:b for a,b in v.items() if a not in {'packet','item','dispatch'}} for k,v in results.items()}, sort_keys=True))


def test_native_pending_survives_second_commit_failure(tmp_path, monkeypatch):
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    c = LedgerStore(run).open()['calls'][claim['call_id']]
    assert c['state'] == 'prepared' and c['extra']['preparation_stage'] == 'local_artifacts_pending'
    def crash(*args):
        raise RuntimeError('second commit unavailable')
    monkeypatch.setattr(LedgerStore, 'mutate', crash)
    with pytest.raises(RuntimeError, match='second commit'):
        native._offer(run, tid, claim, None)
    after = LedgerStore(run).open()['calls'][claim['call_id']]
    assert after == c and not after['extra'].get('native_handoff')


@pytest.mark.parametrize('change', ['generation','source_revision','source_bytes','dispatch_bytes'])
def test_offer_rechecks_locked_identity_and_artifacts(tmp_path, monkeypatch, change):
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    write = native.atomic_write_bytes
    def concurrent(path, data):
        write(path, data)
        if str(path).endswith('.native.txt'):
            if change == 'source_bytes':
                (tmp_path/'repo/ops.py').write_text('def twice(x):\n    return 0\n')
            elif change == 'dispatch_bytes':
                write(path, b'foreign')
            else:
                def mutate(l):
                    if change == 'generation': l['tasks'][tid]['generation'] += 1
                    else: l['source_revision'] = 'foreign'
                    return l
                LedgerStore(run).mutate(mutate)
    monkeypatch.setattr(native, 'atomic_write_bytes', concurrent)
    with pytest.raises((StaleWriteError, PacketSourceError)):
        native._offer(run, tid, claim, None)
    c = LedgerStore(run).open()['calls'][claim['call_id']]
    assert c['state'] == 'prepared' and not c['extra'].get('native_handoff')


def test_artifact_io_failure_keeps_formal_local_failure(tmp_path, monkeypatch):
    run, tid, bid = setup_claim(tmp_path)
    def fail(path, data):
        raise OSError('packet disk failure')
    monkeypatch.setattr(module_facts, 'atomic_write_bytes', fail)
    with pytest.raises(OSError, match='packet disk failure'):
        native._claim(run, tid, bid, 'fact_author', 'controller')
    l = LedgerStore(run).open()
    call = next(iter(l['calls'].values()))
    assert call['state'] == 'released'
    assert call['extra']['preparation_stage'] == 'local_artifacts_failed'
    assert call['extra']['send_evidence'] == 'not_sent_bootstrap'
    assert not call['extra'].get('native_handoff')


@pytest.mark.parametrize('change', ['generation', 'child', 'packet'])
def test_public_preview_never_replaces_final_locked_check(tmp_path, monkeypatch, change):
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    item = native._offer(run, tid, claim, None)
    original = LedgerStore.mutate
    fired = False
    def race(self, mutate):
        nonlocal fired
        if not fired:
            fired = True
            def concurrent(l):
                if change == 'generation': l['tasks'][tid]['generation'] += 1
                elif change == 'child':
                    l['calls'][item['call_id']]['extra']['native_handoff']['child_handle'] = 'other'
                else: Path(claim['packet_path']).write_bytes(b'foreign')
                return l
            original(self, concurrent)
        return original(self, mutate)
    monkeypatch.setattr(LedgerStore, 'mutate', race)
    with pytest.raises(StaleWriteError):
        native.record(run, item['call_id'], status='started', host='test', child_handle='child')
    c = LedgerStore(run).open()['calls'][item['call_id']]
    assert c['state'] == 'prepared' and not c['extra'].get('native_events')


@pytest.mark.parametrize('change', ['child', 'generation', 'usage', 'event_bytes'])
def test_duplicate_preview_requires_latest_locked_identity(tmp_path, monkeypatch, change):
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    item = native._offer(run, tid, claim, None)
    native.record(run, item['call_id'], status='started', host='test', child_handle='child')
    write = native.atomic_write_bytes
    fired = False
    def race(path, data):
        nonlocal fired
        write(path, data)
        if str(path).endswith('.request.pending.json') and not fired:
            fired = True
            def concurrent(l):
                c = l['calls'][item['call_id']]
                if change == 'child': c['extra']['native_handoff']['child_handle'] = 'foreign'
                elif change == 'generation': l['tasks'][tid]['generation'] += 1
                elif change == 'usage': c['usage'] = {'total_tokens':999}
                else: Path(c['extra']['native_event_ref']).write_bytes(b'foreign')
                return l
            LedgerStore(run).mutate(concurrent)
    monkeypatch.setattr(native, 'atomic_write_bytes', race)
    with pytest.raises(StaleWriteError):
        native.record(run, item['call_id'], status='started', host='test', child_handle='child')
    assert fired


def test_imported_duplicate_uses_original_epoch_without_write(tmp_path, monkeypatch):
    from test_native_handoff import _business_result
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    item = native._offer(run, tid, claim, None)
    native.record(run, item['call_id'], status='started', host='test', child_handle='child')
    result = run/'business.json'; result.write_text(json.dumps(_business_result(run,item)))
    native.record(run, item['call_id'], status='completed', host='test', child_handle='child', result_path=result)
    def new_epoch(l):
        l['tasks'][tid]['generation'] += 2
        l['tasks'][tid]['extra']['call_id'] = 'new-call'
        l['tasks'][tid]['state'] = 'pending'
        return l
    LedgerStore(run).mutate(new_epoch)
    before = LedgerStore(run).open()
    value, counts = measured(monkeypatch, lambda:native.record(run,item['call_id'],
        status='completed',host='test',child_handle='child',result_path=result))
    assert value['idempotent'] and counts['reads'] == 2 and counts['writes'] == 0
    assert LedgerStore(run).open() == before


def test_not_sent_public_replay_keeps_absent_child_and_new_epoch(tmp_path, monkeypatch):
    run, tid, bid = setup_claim(tmp_path)
    claim = native._claim(run, tid, bid, 'fact_author', 'controller')
    item = native._offer(run, tid, claim, None)
    host = tmp_path/'host.json';host.write_text(json.dumps({'status':'rejected_before_send'}))
    native.record(run,item['call_id'],status='not_sent',host='test',host_result=host)
    call = LedgerStore(run).open()['calls'][item['call_id']]
    digest = call['extra']['native_events']['not_sent']
    accepted = run/'native'/f"{item['call_id']}.not_sent.{digest}.json"
    assert json.loads(accepted.read_bytes())['child_handle'] is None
    fresh = native.next_work(run,owner='controller')
    assert fresh['status'] == 'ready'
    before = LedgerStore(run).open()
    replay, counts = measured(monkeypatch,lambda:native.record(run,item['call_id'],
        status='not_sent',host='test',host_result=host))
    assert replay['idempotent'] and counts['reads'] == 2 and counts['writes'] == 0
    with pytest.raises(StaleWriteError,match='dispatched child'):
        native.record(run,item['call_id'],status='not_sent',host='test',host_result=host,child_handle='foreign')
    assert LedgerStore(run).open() == before


@pytest.mark.parametrize('change', ['source_revision','host_blocked','member','manifest'])
def test_member_replay_uses_shared_aggregate_guard(tmp_path, change):
    from test_native_bundles import bundle
    from cbe.native_bundles import record_invocation
    run, items, item = bundle(tmp_path)
    iid = item['invocation_id']
    record_invocation(run,iid,status='started',host='test',child_handle='reviewer')
    cid = items[0]['call_id'];call = LedgerStore(run).open()['calls'][cid]
    digest = call['extra']['native_events']['started']
    event = run/'native'/f'{cid}.started.{digest}.json'
    assert native.record_event(run,cid,event)['idempotent']
    def alter(l):
        inv = l['native_invocations'][iid]
        if change == 'source_revision': inv['source_revision'] = 'foreign'
        elif change == 'host_blocked': inv['host_blocked'] = True
        elif change == 'member': inv['members'][0]['input_hash'] = 'foreign'
        else: Path(inv['manifest_path']).write_bytes(b'foreign')
        return l
    LedgerStore(run).mutate(alter)
    before = LedgerStore(run).open()
    with pytest.raises((StaleWriteError,ValueError)):
        native.record_event(run,cid,event)
    assert LedgerStore(run).open() == before
