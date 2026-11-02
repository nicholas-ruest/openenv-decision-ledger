"""Prepared finite integration on the already-seen fixture; no real provider."""
import copy,json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import case_caller as c
import test_case_replay as fixture


class Original:
    scripted=False
    def __init__(self,tests,fault=False):
        self.counter=tests.counter;self.responses={t['job']['attempt_id']:t['responses'] for t in tests.traces}
        self.first=tests.jobs[0];self.fault=fault;self.reserved=[];self.calls=[]
        self.barriers={(s,t):threading.Barrier(2) for s in range(4) for t in (0,1)}
    def reserve(self,label,*args):self.reserved.append(label)
    def call(self,payload,timeout,job):
        turn=sum(x==job['attempt_id'] for x in self.calls);self.calls.append(job['attempt_id'])
        self.barriers[job['sample'],turn].wait(10)
        if self.fault and job==self.first and turn==1:raise TimeoutError('synthetic unknown second response')
        return copy.deepcopy(self.responses[job['attempt_id']][turn])
    def check_reply(self,response):pass
    def check_message(self,message):pass


class CallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.BoundReplayTests.setUpClass();cls.addClassCleanup(fixture.BoundReplayTests.doClassCleanups)
        cls.f=fixture.BoundReplayTests

    def backend(self,fault=False):
        original=Original(self.f,fault)
        return original,c.transport._AtomicOriginal(original,dict(self.f.verdict,independently_regenerated=True))

    def test_complete_original_native_phase_reconstructed_without_live_authority(self):
        original,backend=self.backend()
        with tempfile.TemporaryDirectory() as tmp,patch.object(c.transport.bridge,'preflight_complete_plan'):
            rows,summary,report=c.phase(self.f.args,backend,Path(tmp)/'phase',time.monotonic()+1100)
            self.assertEqual(len(rows),8);self.assertEqual(summary['observed_calls'],16)
            self.assertEqual(len(original.reserved),16);self.assertEqual(len(backend.called),16)
            self.assertTrue(summary['complete']);self.assertTrue(report['all_assigned_in_denominator'])
            self.assertTrue(all(r['semantic_reward']==1 for r in rows))
            self.assertFalse(summary['selection_passed']);self.assertFalse(summary['provider_provenance_attested'])
            self.assertFalse(summary['live_supervisor_binding_qualified'])
            self.assertEqual(sum(r['final_domain_reminder_exposed'] for r in rows),4)

    def test_unknown_second_retains_known_prefix_and_uncalled_denominator(self):
        original,backend=self.backend(True)
        with tempfile.TemporaryDirectory() as tmp,patch.object(c.transport.bridge,'preflight_complete_plan'):
            rows,summary,report=c.phase(self.f.args,backend,Path(tmp)/'phase',time.monotonic()+1100)
            self.assertFalse(summary['complete']);self.assertEqual(summary['recorded'],2)
            self.assertEqual(len(report['rows']),8)
            row=next(r for r in report['rows'] if r['job']==self.f.jobs[0])
            self.assertTrue(row['unknown_usage']);self.assertIsNone(row['generation_tokens'])
            self.assertGreater(row['known_generation_tokens'],0);self.assertIsNone(row['reconstructed_terminal_reward'])
            self.assertEqual(sum(not r['recorded'] for r in report['rows']),6)
            self.assertEqual(len(original.calls),4);self.assertEqual(len(original.reserved),4)

    def test_public_entry_and_unsealed_phase_refuse_before_support_or_provider(self):
        with patch.object(c,'_support',side_effect=AssertionError('Native loaded')):
            with self.assertRaisesRegex(ValueError,'unqualified'):c.run_screen(None)
            with patch.object(c.gate,'require_case',side_effect=ValueError('unsealed')):
                with self.assertRaisesRegex(ValueError,'unsealed'):c.phase(None,None,'/absent',0)

if __name__=='__main__':unittest.main()
