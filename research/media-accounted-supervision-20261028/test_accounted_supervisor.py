import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from accounted_supervisor import supervise_accounted
from accounting_archive import make_config
from test_observation_budget import SyntheticByteCounter
from test_trajectory_audit import fixture_data

WORKER='''import sys,json
from pathlib import Path
from test_accounting_archive import ArchiveTests
case=ArchiveTests();case.setUp();case.f.root=Path(sys.argv[1]);case.run_phase()
(case.f.root/'fixture-ledger.json').write_text(json.dumps(case.f.ledger))
case.doCleanups()
'''
VERIFIER='''import sys,json
from pathlib import Path
from test_accounting_archive import ArchiveTests
from durable_phase import durable_new
case=ArchiveTests();case.setUp();case.f.root=Path(sys.argv[1])
case.config=json.loads(Path(sys.argv[2]).read_text())
case.f.ledger=json.loads((case.f.root/'fixture-ledger.json').read_text())
raw=json.loads((case.f.root/'00-episode.json').read_text())['payload']
case.f.current=[e['native'] for e in raw['events'] if 'native' in e]
result=case.verify()
durable_new(Path(sys.argv[3]).parent,Path(sys.argv[3]).name,result)
case.doCleanups()
'''


class SupervisedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.root=self.base/'run'
        _,self.plan=fixture_data();self.config=make_config(SyntheticByteCounter())
        absolute=os.pathsep.join(str(Path(p).resolve()) for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p)
        env=patch.dict(os.environ,{'PYTHONPATH':absolute});env.start();self.addCleanup(env.stop)
    def script(self,name,text):
        p=self.base/name;p.write_text(text);return p,hashlib.sha256(p.read_bytes()).hexdigest()
    def launch(self,worker=WORKER,verifier=VERIFIER,seconds=10):
        w,ws=self.script('worker.py',worker);v,vs=self.script('verifier.py',verifier)
        return supervise_accounted(self.root,w,ws,v,vs,self.plan,'screen',self.config,deadline=time.monotonic()+seconds)
    def test_complete_requires_actual_independent_verifier_process(self):
        result=self.launch();self.assertEqual(result['status'],'completed');self.assertTrue(result['archive_verified'])
        self.assertEqual(result['verifier_status'],'completed');self.assertIsNone(result['provider_billing_stopped'])
        self.assertEqual(json.loads((self.root/'verification.json').read_text())['episodes_recomputed'],16)
        with self.assertRaises(FileExistsError):self.launch()
    def test_zero_exit_with_no_archive_is_not_success(self):
        r=self.launch(worker='pass');self.assertFalse(r['archive_verified']);self.assertEqual(r['status'],'verification_failed')
    def test_zero_exit_verifier_without_proof_is_not_success(self):
        r=self.launch(verifier='pass');self.assertEqual(r['status'],'invalid_accounted_archive');self.assertFalse(r['archive_verified'])
    def test_tampered_saved_costs_rejected_by_child_verifier(self):
        extra="\np=case.f.root/'00-episode.json';o=json.loads(p.read_text());o['validated']['local_accounting']['completion_used']=0;p.write_text(json.dumps(o))\n"
        r=self.launch(worker=WORKER+extra);self.assertEqual(r['status'],'verification_failed');self.assertFalse(r['archive_verified'])
    def test_worker_cannot_change_external_configuration(self):
        extra="\np=case.f.root.parent/'expected-accounting.json';o=json.loads(p.read_text());o['completion_limit']=8192;p.write_text(json.dumps(o))\n"
        r=self.launch(worker=WORKER+extra);self.assertEqual(r['status'],'invalid_accounted_archive');self.assertIsNone(r['verifier_status'])
    def test_preseeded_proof_refused(self):
        r=self.launch(worker=WORKER+"\n(case.f.root.parent/'verification.json').write_text('{}')\n")
        self.assertEqual(r['status'],'invalid_accounted_archive');self.assertIsNone(r['verifier_status'])
    def test_verifier_timeout_bounded_with_actual_process_identity(self):
        code="""import sys,os,time,json,signal
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
p=Path('/proc/self');Path('verify-identity.json').write_text(json.dumps({'pid':os.getpid(),'start':(p/'stat').read_text().split()[21],'argv':(p/'cmdline').read_bytes().decode().split('\\0')}))
while True:time.sleep(.01)
"""
        r=self.launch(verifier=code,seconds=1.5);self.assertEqual(r['status'],'verification_deadline');self.assertFalse(r['archive_verified'])
        ident=json.loads((self.root/'verify-identity.json').read_text());self.assertIn('verifier.py',ident['argv'][1]);p=Path(f"/proc/{ident['pid']}/stat")
        if p.exists():
            fields=p.read_text().split();self.assertTrue(fields[21]!=ident['start'] or fields[2]=='Z')
    def test_worker_deadline_does_not_launch_verifier(self):
        r=self.launch(worker='import time;time.sleep(10)',seconds=.1);self.assertEqual(r['status'],'deadline');self.assertIsNone(r['verifier_status'])
    def test_bad_pins_and_config_reject_before_root(self):
        w,ws=self.script('worker.py','pass');v,vs=self.script('verifier.py','pass')
        with self.assertRaises(ValueError):supervise_accounted(self.root,w,ws,v,'0'*64,self.plan,'screen',self.config,deadline=time.monotonic()+1)
        self.config['source_sha256']['verified_phase']='0'*64
        with self.assertRaises(ValueError):supervise_accounted(self.root,w,ws,v,vs,self.plan,'screen',self.config,deadline=time.monotonic()+1)
        self.assertFalse(self.root.exists())


if __name__=='__main__':unittest.main()
