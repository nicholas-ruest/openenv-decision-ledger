"""Whole-phase controls; fake provider and already-used Native case only."""
import contextlib,io,json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import live_advice_screen as worker
import failure_protocol as p
import finite_qualification as c
from test_live_failure_screen import MockBackend,old
import test_finite_qualification as fixture

class PhaseDeadlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.FiniteTests.setUpClass();cls.counter=fixture.FiniteTests.counter
    def args(self,root):return SimpleNamespace(expected_source='test',case_audit='unused',case_audit_sha256='a'*64,output=root/'phase')
    @contextlib.contextmanager
    def guards(self,backend):
        with patch.object(worker.b,'verify_clean_source'),patch.object(worker.b,'operating_seconds',return_value=1200),patch.object(worker.b,'verify_dependencies'),patch.object(c,'require_live_ready',return_value={'case_audit_sha256':'a'*64}),patch.object(worker.b,'guarded_backend',return_value=backend):yield
    def test_one_backend_and_absolute_deadline_cover_all_original_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.args(Path(tmp));backend=MockBackend(self.counter);deadline=time.monotonic()+120
            with self.guards(backend),patch.object(p,'materialize',side_effect=lambda job,*a:p.QualificationTrial(old(job))):
                self.assertEqual(worker.execute_phase(deadline,args),0)
            report=json.loads((args.output/'phase-evidence.json').read_text())
            self.assertEqual((report['recorded'],report['independently_replayed'],report['actual_calls']),(8,8,16))
            self.assertTrue(report['complete']);self.assertEqual(len(backend.quotes),5)
            self.assertTrue(all(q==([28672]*16,8096,deadline) for q in backend.quotes))
            self.assertEqual(len(backend.reserved),16)
    def fake_report(self,category='wrong'):
        return dict(recorded=2,independently_replayed=2,complete=False,rows=[dict(recorded=True,category=category)])
    def test_deadline_after_first_chunk_cannot_refresh_for_later_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.args(Path(tmp));backend=Mock(counter=self.counter);clock=[0]
            def chunk(*a):args.output.mkdir();clock[0]=101
            with self.guards(backend),patch.object(worker.time,'monotonic',side_effect=lambda:clock[0]),patch.object(c,'run_screen_chunk',side_effect=chunk) as run,patch.object(worker,'assemble_screen',return_value=self.fake_report()):
                self.assertEqual(worker.execute_phase(100,args),1)
            self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[4],100)
    def test_failed_or_incompletely_replayed_prefix_stops_without_later_chunk(self):
        for report in [self.fake_report('provider'),self.fake_report('budget'),self.fake_report('execution'),dict(self.fake_report(),independently_replayed=1)]:
            with self.subTest(report=report),tempfile.TemporaryDirectory() as tmp:
                args=self.args(Path(tmp));backend=Mock(counter=self.counter)
                with self.guards(backend),patch.object(c,'run_screen_chunk',side_effect=lambda *a:args.output.mkdir()) as run,patch.object(worker,'assemble_screen',return_value=report):
                    self.assertEqual(worker.execute_phase(time.monotonic()+60,args),1)
                self.assertEqual(run.call_count,1)
    def test_cli_uses_one_supervisor_and_refuses_separate_chunk_clock(self):
        argv=['live_advice_screen.py','--execute','--receipt','r','--reconciliation','a','--tokenizer','t','--output','o','--case-audit','c','--case-audit-sha256','a'*64,'--expected-source','s','--amendment-sha256','b'*64]
        supervisor=Mock();supervisor.run_bounded.return_value={'status':'completed'}
        with patch('sys.argv',argv),patch.object(worker.b,'require_live_supervision',return_value=1200),patch.object(worker,'no_other_workers'),patch.object(worker,'open',create=True) as opened,patch.object(worker.fcntl,'flock'),patch.object(worker.b,'load',return_value=supervisor),contextlib.redirect_stdout(io.StringIO()):
            worker.main()
        self.assertEqual(supervisor.run_bounded.call_count,1)
        self.assertIs(supervisor.run_bounded.call_args.args[0],worker.execute_phase)
        self.assertEqual(supervisor.run_bounded.call_args.args[2],1200)
        for extra in [['--chunk','0'],['--prior','old']]:
            with patch('sys.argv',argv+extra),patch.object(worker.b,'require_live_supervision',side_effect=AssertionError('no admission')):
                with self.assertRaises(ValueError):worker.main()

if __name__=='__main__':unittest.main()
