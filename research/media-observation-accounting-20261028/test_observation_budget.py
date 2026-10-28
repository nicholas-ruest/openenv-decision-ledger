import json
from pathlib import Path
import tempfile
import unittest

from observation_budget import EpisodeBudget,PinnedCounter,TOKENIZER_SHA,canonical
import accounted_phase
import test_media_durable as fixtures


class SyntheticByteCounter:
    # Deterministic unit double; not evidence of real tokenizer/Arena parity.
    mode='pinned_tokenizer';sha256=TOKENIZER_SHA
    def count(self,text):return len(text.encode())
    def context(self,messages):return self.count(canonical(messages))


class BudgetTests(unittest.TestCase):
    def test_reset_context_only_observation_includes_full_transport(self):
        counter=SyntheticByteCounter();initial=[{'role':'user','content':'reset'}];budget=EpisodeBudget(counter,initial)
        self.assertEqual(budget.snapshot()['completion_used'],0);self.assertEqual(budget.initial_context,len(canonical(initial)))
        obs={'done':False,'reward':0,'observation':{'output':'unicodeé','success':True}}
        history=initial+[{'role':'assistant','content':'action'},{'role':'user','content':canonical(obs)}]
        budget.reply(10);budget.observation(obs,history)
        self.assertEqual(budget.observed,counter.count(canonical(obs)));self.assertEqual(budget.snapshot()['completion_used'],10+budget.observed)
        self.assertEqual(budget.context_used,counter.context(history));self.assertFalse(budget.snapshot()['arena_wrapper_equivalent'])
    def test_exact_boundary_versus_overflow(self):
        counter=SyntheticByteCounter();obs={'done':True};cost=counter.count(canonical(obs));b=EpisodeBudget(counter,[],completion=cost+10,context=1000)
        b.reply(10);b.observation(obs,[]);self.assertIsNone(b.snapshot()['overflow_reason']);self.assertEqual(b.allowance([]),0)
        b.reply(1);self.assertEqual(b.snapshot()['overflow_reason'],'generation')
    def test_context_allowance_and_nonfinite_generation_rejected(self):
        b=EpisodeBudget(SyntheticByteCounter(),[],completion=10,context=20)
        self.assertEqual(b.allowance([{'x':'long'*20}]),0)
        for n in (-1,True,None,float('nan')):
            with self.assertRaises(ValueError):b.reply(n)
    def test_missing_wrong_or_symlink_tokenizer_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'tokenizer';p.write_text('{}');link=Path(tmp)/'link';link.symlink_to(p)
            for file in (p,link,p.parent/'missing'):
                with self.assertRaises(ValueError):PinnedCounter(file)


class AccountedPhaseTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PhaseTests();self.f.setUp();self.addCleanup(self.f.tmp.cleanup)
    def run_phase(self,completion=4096,context=8192):
        f=self.f
        return accounted_phase.run_phase(f.root,f.plan,f.schema,'screen','test',100,True,lambda:f.time,f.open_env,f.reserve,lambda:f.ledger,f.dispatch,f.replay,
            accounting_factory=lambda history:EpisodeBudget(SyntheticByteCounter(),history,completion=completion,context=context))
    def test_normal_phase_preserves_old_semantic_outcomes_and_records_costs(self):
        report=self.run_phase();self.assertEqual(report['counts'],{'full':16})
        row=json.loads((self.f.root/'00-episode.json').read_text())['validated'];self.assertGreater(row['local_accounting']['postreset_observation_tokens'],0)
        self.assertEqual(row['local_accounting']['generation_tokens'],20)
    def test_oversized_nonterminal_observation_stops_next_calls(self):
        open_original=self.f.open_env
        def open_env(*args):
            env=open_original(*args);step=env['step']
            def large(*values):
                obs=step(*values);obs['observation']['output']='x'*5000;return obs
            env['step']=large;return env
        self.f.open_env=open_env;report=self.run_phase();self.assertEqual(report['counts'],{'budget':16});self.assertEqual(len(self.f.dispatched),16)
        self.assertTrue(all(label.endswith(':0') for label in self.f.dispatched))
    def test_terminal_native_reward1_overflow_remains_budget_in_analysis(self):
        open_original=self.f.open_env
        def open_env(*args):
            env=open_original(*args);step=env['step']
            def large(*values):
                obs=step(*values)
                if obs['done']:obs['observation']['output']='x'*5000
                return obs
            env['step']=large;return env
        self.f.open_env=open_env;report=self.run_phase();self.assertEqual(report['counts'],{'budget':16})
        row=json.loads((self.f.root/'00-episode.json').read_text());self.assertEqual(row['payload']['events'][-1]['native']['reward'],1)
        self.assertEqual(row['validated']['native_audit_category'],'full');self.assertIsNone(row['validated']['semantic_reward'])
    def test_initial_context_overflow_no_reservation_no_dispatch(self):
        report=self.run_phase(1,1);self.assertEqual(report['counts'],{'budget':16});self.assertEqual(self.f.ledger,[]);self.assertEqual(self.f.dispatched,[])
    def test_reserved_generation_cannot_exceed_accounted_allowance(self):
        original=self.f.reserve
        def overreserve(label,history,remaining):
            original(label,history,remaining);self.f.ledger[-1]['generation_bound']=remaining+1
        self.f.reserve=overreserve
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(self.f.dispatched,[])


if __name__=='__main__':unittest.main()
