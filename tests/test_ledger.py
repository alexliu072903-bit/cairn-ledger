import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        fixtures = Path(__file__).parent / 'test-runs'
        fixtures.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=str(fixtures)))
        self.home = self.root / 'runtime'
        self.home.mkdir()
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.src = self.root / 'sessions'
        self.src.mkdir()
        self.rules = self.root / 'self'
        self.rules.mkdir()
        for name in ['self.md', 'process.md', 'build.md', 'engineering.md', 'foundations.md']:
            (self.rules / name).write_text('- 排查问题先只读诊断，不擅自动手。\n')
        self.config = dict(sources={'codex': [str(self.src)]}, vault=str(self.vault), self_root=str(self.rules),
                           since='2026-10-18T00:00:00+08:00', debounce=600, poll=.01,
                           batch_limit=20, input_chars=24000, quote_chars=160, hour_limit=4, day_limit=24, timeout=180)
        self.config['classification_enabled']=True
        self.p = self.src / 'rollout.jsonl'
        self.data = [self.row('session_meta', dict(id='thread1', cwd=str(self.root), source='vscode')),
            self.event('item_completed', item={'type': 'AgentMessage', 'content': [{'type': 'Text', 'text': '已经替你改完文件。'}]}, turn_id='old'),
            self.event('task_started', turn_id='t1'),
            self.event('item_completed', item={'type': 'UserMessage', 'id': 'u1', 'content': [{'type': 'text', 'text': '先只读，别直接改。'}]}, turn_id='t1'),
            self.event('task_complete', turn_id='t1')]
        self.write()

    def tearDown(self):
        pass  # Keep synthetic fixtures available for inspection (ignored by Git).

    @staticmethod
    def row(kind, payload):
        return {'type': kind, 'timestamp': '2026-10-19T02:00:00Z', 'payload': payload}

    def event(self, kind, **kwargs):
        return self.row('event_msg', dict(type=kind, **kwargs))

    def write(self, path=None):
        (path or self.p).write_text(''.join(json.dumps(d, ensure_ascii=False) + '\n' for d in self.data))

    def classify(self, config, home, state, batch, rules, events):
        return [dict(event_id=m['event_id'], kind='correction', category_id='read_before_write', category_name='未先只读', quote='先只读，别直接改。', rule_ref='self.md:1', reason='explicit_method_correction') for m in batch], 'test-model'

    def run_worker(self, classifier=None):
        return ledger.process(self.home, self.config, force=True, classifier=classifier or self.classify)

    def test_real_structure_and_terminal(self):
        ms, status = ledger.parse_file(str(self.p), 'codex', self.home)
        self.assertEqual(ms[0]['context'], '已经替你改完文件。')
        self.assertEqual(ms[0]['terminal'], 'task_complete')
        self.data.pop();self.write()
        ms, status = ledger.parse_file(str(self.p), 'codex', self.home)
        self.assertEqual(status, 'pending_turn')
        self.assertEqual(ms[0]['terminal'], 'incomplete')

    def test_replay_and_fork_do_not_increment(self):
        self.assertEqual(self.run_worker()['events'], 1)
        self.write(self.src / 'fork.jsonl')
        self.assertEqual(self.run_worker()['events'], 1)
        self.assertEqual(len(ledger.load_events(self.config)), 1)

    def test_no_completed_turn_no_model(self):
        self.data.pop();self.write()
        def never(*args):
            self.fail('called model on uncompleted turn')
        self.assertEqual(self.run_worker(never)['added'], 0)

    def test_failure_keeps_cursor_and_shows_error(self):
        self.assertEqual(self.run_worker()['status'], 'ok')
        before = ledger.read_json(self.home / 'state.json', {})['files']
        self.data += [self.event('item_completed', item={'type': 'UserMessage', 'id': 'u2', 'content': [{'type': 'text', 'text': '先只读，别直接改。'}]}, turn_id='t2'), self.event('task_complete', turn_id='t2')]
        self.write()
        def fail(*args):
            raise ledger.LedgerError('injected_failure')
        self.assertEqual(self.run_worker(fail)['status'], 'failed')
        self.assertEqual(ledger.read_json(self.home / 'state.json', {})['files'], before)
        self.assertIn('injected_failure', (self.vault / 'regressions.md').read_text())
        self.assertEqual(self.run_worker()['events'], 2)

    def test_append_then_view_failure_recovers_without_duplicates(self):
        real = ledger.render
        with patch.object(ledger, 'render', side_effect=OSError('injected')):
            self.assertEqual(self.run_worker()['status'], 'failed')
        self.assertEqual(len(ledger.load_events(self.config)), 1)
        self.assertEqual(self.run_worker()['events'], 1)

    def test_negative_classes_do_not_enter_ledger(self):
        def negative(config, home, state, batch, rules, events):
            return [dict(event_id=m['event_id'], kind='content_edit', category_id='', category_name='', quote='', rule_ref='', reason='content_edit') for m in batch], 'test'
        self.assertEqual(self.run_worker(negative)['events'], 0)

    def test_invalid_quote_fails_whole_unit(self):
        def bad(*args):
            a, m = self.classify(*args);a[0]['quote'] = '模型编造的原话';return a,m
        self.assertEqual(self.run_worker(bad)['status'], 'failed')
        self.assertEqual(ledger.load_events(self.config), [])
        self.assertFalse(ledger.read_json(self.home / 'state.json', {})['files'])

    def test_ephemeral_cwd_excluded(self):
        self.data[0]['payload']['cwd'] = str(self.home / 'classifier');self.write()
        self.assertEqual(ledger.parse_file(str(self.p), 'codex', self.home), ([], 'self_excluded'))

    def test_relay_cwd_excluded_on_both_sources(self):
        relay = self.home.parent / 'relay' / 'runs' / 'id' / 'executor'
        self.data[0]['payload']['cwd'] = str(relay)
        self.write()
        self.assertEqual(ledger.parse_file(str(self.p), 'codex', self.home), ([], 'relay_excluded'))
        claude = [(dict(type='user', cwd=str(relay)), 1, 1)]
        self.assertEqual(ledger.parse_claude(self.p, claude, self.home), ([], 'relay_excluded'))
        self.assertIsNone(ledger.excluded_cwd(str(relay.parent.parent.with_name('runs-other')), self.home))

    def test_missing_cwd_is_not_human(self):
        self.data[0]['payload'].pop('cwd')
        self.write()
        self.assertEqual(ledger.parse_file(str(self.p), 'codex', self.home), ([], 'missing_cwd'))

    def test_truncation_and_bad_source_fail_visible(self):
        self.run_worker();before=ledger.read_json(self.home/'state.json', {})['files']
        self.p.write_text('{}\n')
        self.assertEqual(self.run_worker()['status'], 'failed')
        self.assertEqual(ledger.read_json(self.home/'state.json', {})['files'], before)
        self.assertIn('source_replaced_or_truncated', (self.vault/'regressions.md').read_text())

    def test_sensitive_quote_blocked(self):
        for value in ['sk-proj-abcdefghijklmnop', 'password=supersecret', 'person@example.com', '13812345678']:
            self.assertNotEqual(ledger.redact(value), value)

    def test_partial_json_line_waits(self):
        self.p.write_text(self.p.read_text().rsplit('\n', 2)[0] + '\n{"type":')
        self.assertEqual(ledger.parse_file(str(self.p), 'codex', self.home)[1], 'pending_turn')

    def test_claude_multiple_rounds_tool_results_not_human(self):
        source = self.src/'claude.jsonl'
        self.data=[]
        for i in range(2):
            self.data.extend([
                dict(type='user', timestamp='2026-10-19T02:00:00Z', sessionId='s', cwd=str(self.root), uuid='u'+str(i), origin={'kind':'human'}, message={'content':'别直接改'}),
                dict(type='user', message={'content':[{'type':'tool_result', 'content':'not human'}]}),
                dict(type='assistant', message={'content':[{'type':'text', 'text':'答复'}], 'stop_reason':'end_turn'})])
        self.write(source)
        ms,status=ledger.parse_file(str(source),'claude',self.home)
        self.assertEqual(len(ms),2)
        self.assertTrue(all(m['terminal']=='end_turn' for m in ms))

    def test_rate_limit_checked_before_model_launch(self):
        state={'calls':[{'at':ledger.time.time()}]*4}
        with self.assertRaisesRegex(ledger.LedgerError,'rate_limited'):
            ledger.invoke(self.config,self.home,state,[],[],[])

    def test_disabled_classifier_never_calls_codex(self):
        self.config['classification_enabled']=False
        with patch.object(ledger.subprocess,'run') as run:
            with self.assertRaisesRegex(ledger.LedgerError,'classification_not_authorized'):
                ledger.invoke(self.config,self.home,{},[],[],[])
        run.assert_not_called()

    def test_idle_watcher_does_not_spawn_processor(self):
        self.config['debounce']=600
        observed={str(self.p):{'fp':ledger.fingerprint(self.p),'pending':False,'changed_at':0}}
        ledger.atomic(self.home/'watch-state.json',observed)
        with patch.object(ledger.subprocess,'run') as run:
            ledger.watch(self.home,self.config,stop_after=.03)
        run.assert_not_called()

    def test_debounce_worker_runs_only_after_quiet_window(self):
        self.config['debounce']=.06
        self.config['poll']=.01
        ledger.atomic(self.home/'watch-state.json',{str(self.p):{'fp':ledger.fingerprint(self.p),'pending':True,'changed_at':ledger.time.time()}})
        calls=[]
        def worker(*args,**kwargs):
            calls.append(ledger.time.time())
            ledger.atomic(self.home/'state.json',{'files':{str(self.p):{'pending':False}}})
            return type('R',(),{'returncode':0})()
        start=ledger.time.time()
        with patch.object(ledger.subprocess,'run',side_effect=worker):
            ledger.watch(self.home,self.config,stop_after=.12)
        self.assertEqual(len(calls),1)
        self.assertGreaterEqual(calls[0]-start,.05)

    def test_incomplete_pending_not_retried_without_change(self):
        self.config['debounce']=.01
        self.config['poll']=.01
        ledger.atomic(self.home/'watch-state.json',{str(self.p):{'fp':ledger.fingerprint(self.p),'pending':True,'changed_at':0}})
        def worker(*args,**kwargs):
            ledger.atomic(self.home/'state.json',{'files':{str(self.p):{'pending':True,'pending_count':1,'ready_remaining':0}}})
            return type('R',(),{'returncode':0})()
        with patch.object(ledger.subprocess,'run',side_effect=worker) as run:
            ledger.watch(self.home,self.config,stop_after=.05)
        self.assertEqual(run.call_count,1)

    def test_source_read_failure_shows_top_error(self):
        with patch.object(ledger, 'discover', side_effect=ledger.LedgerError('source_unreadable:codex')):
            self.assertEqual(self.run_worker()['status'],'failed')
        self.assertIn('source_unreadable', (self.vault/'regressions.md').read_text())
        self.assertFalse(ledger.read_json(self.home/'state.json',{})['files'])

    def test_watcher_discovery_failure_visible_without_advancing_cursor(self):
        with patch.object(ledger, 'discover', side_effect=ledger.LedgerError('source_unreadable:codex')):
            ledger.watch(self.home, self.config, stop_after=.01)
        state=ledger.read_json(self.home/'state.json',{})
        self.assertEqual(state['files'],{})
        self.assertIn('watch_discovery_failed:source_unreadable:codex',(self.vault/'regressions.md').read_text())

    def test_missing_items_rejected_before_append(self):
        with self.assertRaisesRegex(ledger.LedgerError,'missing_or_duplicate'):
            ledger.validate_answers([{'event_id':'one'}],[],[],[], 'test',self.config)


if __name__=='__main__':
    unittest.main(verbosity=2)
