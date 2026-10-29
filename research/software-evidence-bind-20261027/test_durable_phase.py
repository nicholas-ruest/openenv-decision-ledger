import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
import durable_phase as dp
from raw_evidence import digest

ROOT=Path(os.environ.get('SOFTWARE_TEST_REPO',Path(__file__).resolve().parents[2]))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
CO=load('real_coordinator',ROOT/'integrations/software-repair/scripts/paired_coordinator.py')
AS=load('real_assessor',ROOT/'scripts/assess-software-helper-pair.py')

class DurableTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'archive';self.ledger=[];self.calls=[]
        self.protocol={'runtime_source':AS.RUNTIME,'settings_sha256':'a'*64}
        self.manifest={'phase':'screen','arms':AS.ARMS,'groups':[]}
        for task in AS.TASKS:
            for seed in AS.SEEDS['screen']:
                a=self.capture('baseline',task,seed)
                self.manifest['groups'].append({'task_id':task,'seed':seed,'case_sha256':a['case_sha256'],'workspace_sha256':a['workspace_sha256'], 'arms':{arm:{k:self.capture(arm,task,seed)[k] for k in ('prompt_sha256','reset_sha256')} for arm in AS.ARMS}})
        self.failure=None;self.fatal=False;self.raise_worker=False
    def capture(self,arm,task,seed):
        reset={'prompt':f'{arm}:{task}:{seed}'};files={'code':f'{task}:{seed}'}
        messages=[{'role':'system','content':'repair'},{'role':'user','content':json.dumps(reset)}]
        return {'messages':messages,'files':files,'reset':reset,'case_sha256':digest(seed),'base_prompt_sha256':digest({'reset':reset,'files':files}),'workspace_sha256':digest(files),'reset_sha256':digest(reset),'prompt_sha256':digest(messages)}
    def worker(self,job,deadline,label):
        self.calls.append(job)
        if self.raise_worker:raise RuntimeError('sensitive text must not persist')
        arm,task,seed,sample=job;s=self.capture(arm,task,seed);reward=1 if arm=='preserve_supplied' else .75
        failure=self.failure if len(self.calls)==1 else None
        self.ledger.append({'label':label,'usd':'0.1','prompt_bound':100,'generation_bound':100})
        messages=copy.deepcopy(s['messages']);calls=[];response=None
        if failure is None:
            response=digest(label);messages.append({'role':'assistant','content':json.dumps({'reward':reward})});messages.append({'role':'user','content':json.dumps({'done':True,'reward':reward})})
            calls=[{'client_call_label':label,'reserved_usd':.1,'provider_response_id_sha256':response,'finish_reason':'stop','prompt_tokens':10,'completion_tokens':10}]
        else:reward=0
        raw={'task_id':task,'seed':seed,'sample':sample,'prompt_sha256':s['base_prompt_sha256'],'messages':messages,'calls':calls,'reward':reward,'failure':failure}
        row={'arm':arm,'task_id':task,'seed':seed,'sample':sample,'runtime_source':AS.RUNTIME,'settings_sha256':'a'*64,**{k:s[k] for k in ('case_sha256','workspace_sha256','reset_sha256','prompt_sha256')},'client_call_label':label,'provider_response_id_sha256':response,'provider_call_observed':bool(calls),'reward':reward,'failure':failure}
        return {'raw':raw,'normalized':row,'fatal_guard_failure':self.fatal}
    def replay(self,arm,task,seed,message):
        reward=json.loads(message['content'])['reward'];return {'reward':reward,'observation':{'done':True,'reward':reward}}
    def run_phase(self,**overrides):
        args=dict(root=self.root,manifest=self.manifest,protocol=self.protocol,prefix='offline-fixture',worker=self.worker,coordinator=CO,assessor=AS,reservation_rows=lambda:self.ledger,capture=self.capture,replay=self.replay,classify=lambda r:r['failure'],deadline=100,admitted=True,now=lambda:0)
        args.update(overrides);return dp.run_phase(**args)
    def test_full32_chain_real_assessor(self):
        r=self.run_phase();self.assertTrue(r['complete']);self.assertEqual(r['assessment']['rollouts'],32);self.assertEqual(r['attestation']['native_replayed_valid_answers'],32)
        self.assertEqual(len(dp.load_saved(self.root)[1]),32);self.assertFalse(r['promotion'])
    def test_nonfatal_provider_failure_kept_in32(self):
        self.failure='provider';r=self.run_phase();self.assertEqual(r['assessment']['rollouts'],32);self.assertEqual(r['attestation']['reservation_only_jobs'],1)
        self.assertEqual(r['assessment']['groups'][0]['arms']['baseline']['failures'],{'provider':1})
    def test_fatal_result_saved_before_stop(self):
        self.failure='budget';self.fatal=True;r=self.run_phase();self.assertFalse(r['complete']);self.assertEqual(len(self.calls),1)
        self.assertEqual(dp.load_saved(self.root)[1][0]['result']['raw']['failure'],'budget');self.assertFalse((self.root/'complete.json').exists())
    def test_worker_exception_retained_without_fake_result(self):
        self.raise_worker=True
        with self.assertRaises(RuntimeError):self.run_phase()
        d=json.loads((self.root/'0000-worker-error.json').read_text());self.assertEqual(d['exception_type'],'RuntimeError');self.assertNotIn('sensitive',(self.root/'0000-worker-error.json').read_text());self.assertEqual(dp.load_saved(self.root)[1],[])
    def test_deadline_no_worker(self):
        r=self.run_phase(now=lambda:101);self.assertFalse(r['complete']);self.assertEqual(self.calls,[])
    def test_refuse_resume_completed_or_partial(self):
        self.run_phase(now=lambda:101)
        with self.assertRaises(FileExistsError):self.run_phase()
        self.assertEqual(self.calls,[])
    def test_unadmitted_no_root(self):
        with self.assertRaises(ValueError):self.run_phase(admitted=False)
        self.assertFalse(self.root.exists())
    def test_manifest_drift_before_work(self):
        self.manifest['groups'][0]['arms']['baseline']['prompt_sha256']='f'*64
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(self.calls,[])
    def test_wrong_runtime_before_work(self):
        self.protocol['runtime_source']='wrong'
        with self.assertRaises(ValueError):self.run_phase()
        self.assertFalse(self.root.exists())
    def test_atomic_write_never_replaces(self):
        self.root.mkdir();dp.durable_new(self.root,'entry.json',{'first':1});before=(self.root/'entry.json').read_bytes()
        with self.assertRaises(FileExistsError):dp.durable_new(self.root,'entry.json',{'other':2})
        self.assertEqual((self.root/'entry.json').read_bytes(),before)
    def test_interrupted_result_publication_stops_next_worker(self):
        real=dp.os.link
        def broken(src,dst):
            if str(dst).endswith('-result.json'):raise OSError('disk error')
            return real(src,dst)
        with patch.object(dp.os,'link',broken):
            with self.assertRaises(OSError):self.run_phase()
        self.assertEqual(len(self.calls),1);self.assertTrue((self.root/'aborted.json').exists());self.assertEqual(dp.load_saved(self.root)[1],[])
    def test_saved_checksum_tampering(self):
        self.failure='budget';self.fatal=True;self.run_phase();p=self.root/'0000-result.json';d=json.loads(p.read_text());d['payload']['result']['raw']['reward']=1;p.write_text(json.dumps(d))
        with self.assertRaises(ValueError):dp.load_saved(self.root)
    def test_nonfinite_deadline_no_work(self):
        with self.assertRaises(ValueError):self.run_phase(deadline=float('nan'))
        self.assertEqual(self.calls,[])
    def test_settings_identity_before_work(self):
        self.protocol['settings_sha256']='bad'
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(self.calls,[])
    def test_real_process_kill_before_atomic_link(self):
        code="import durable_phase as d, pathlib, os, signal; p=pathlib.Path(__import__('sys').argv[1]); p.mkdir(); d.durable_new(p,'claim.json',{'intent':True}); os.link=lambda *a: os.kill(os.getpid(),signal.SIGKILL); d.durable_new(p,'0000-result.json',{'pending':True})"
        env={**os.environ,'PYTHONPATH':str(Path(dp.__file__).parent)}
        r=subprocess.run([sys.executable,'-c',code,str(self.root)],env=env,timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.assertEqual(r.returncode,-9);self.assertFalse((self.root/'0000-result.json').exists());self.assertEqual(dp.load_saved(self.root)[1],[])
        self.assertTrue(list(self.root.glob('.pending-*')))
        with self.assertRaises(FileExistsError):self.run_phase()
    def test_fsync_failure_never_launches_worker(self):
        with patch.object(dp.os,'fsync',side_effect=OSError('fsync failure')):
            with self.assertRaises(OSError):self.run_phase()
        self.assertEqual(self.calls,[]);self.assertFalse((self.root/'complete.json').exists())
    def test_invalid_result_retained_but_not_complete(self):
        original=self.worker
        def bad(*args):
            r=original(*args);r['normalized']['reward']=.9;return r
        with self.assertRaises(ValueError):self.run_phase(worker=bad)
        self.assertEqual(len(self.calls),1);self.assertEqual(len(dp.load_saved(self.root)[1]),1);self.assertFalse((self.root/'complete.json').exists())

if __name__=='__main__':unittest.main()
