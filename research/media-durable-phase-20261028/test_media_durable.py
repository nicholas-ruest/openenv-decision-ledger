import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import media_durable as md
from media_protocol import IMAGE,RUNTIME,digest
from test_trajectory_audit import fixture_data


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'archive';self.data,self.plan=fixture_data();self.schema=self.data['schema']
        self.time=0;self.ledger=[];self.dispatched=[];self.closed=0;self.current=[]
        self.mode='full';self.raise_dispatch=False;self.late=False;self.bad_reset=False
    def snapshot(self,task,seed):
        c=next(c for c in self.data['captures'] if c['phase']=='screen' and (c['task_id'],c['seed'])==(task,seed))
        return copy.deepcopy({k:c[k] for k in ('image','runtime_source','uid_shell','reset_transport','workspace')})
    def open_env(self,task,seed):
        self.current=[];s=self.snapshot(task,seed)
        if self.bad_reset:s['workspace']={}
        def step(action,deadline):
            done=action['action_type']=='evaluate'
            native={'done':done,'reward':1 if done else 0,'observation':{'success':True,'error':'','output':''}}
            self.current.append(native);return native
        def close():self.closed+=1
        return {'reset_record':s,'step':step,'close':close}
    def replay(self,task,seed,actions):return {**self.snapshot(task,seed),'transports':copy.deepcopy(self.current[:len(actions)])}
    def reserve(self,label,history,remaining):self.ledger.append({'label':label,'usd':'.01','prompt_bound':200,'generation_bound':100})
    def dispatch(self,history,label,deadline):
        # Intent exists BEFORE worker entry; no newer call may precede validation.
        seq,idx=map(int,label.split(':')[1:]);stem=f'{seq:02d}-{idx:02d}'
        self.assertTrue((self.root/(stem+'-intent.json')).exists())
        if idx:self.assertTrue((self.root/f'{seq:02d}-{idx-1:02d}-validated.json').exists())
        self.dispatched.append(label)
        if self.raise_dispatch:raise RuntimeError('private credentials must never appear in archive')
        if self.late:self.time=101
        base={'kind':'call','status':'returned','call_id_sha256':digest('call-'+label),'reservation_label':label,'request_sha256':digest(history)}
        if self.mode=='provider' and len(self.dispatched)==1:base['status']='timeout';return base
        action={'action_type':'exec','command':'true'} if idx==0 else {'action_type':'evaluate'}
        base['response']={'response_id_sha256':digest('response-'+label),'finish_reason':'stop','content':json.dumps(action),'usage':{'prompt_tokens':100,'completion_tokens':10}}
        if self.mode=='bad_usage':base['response']['usage']['completion_tokens']=101
        if self.mode=='duplicate' and seq>0:base['response']['response_id_sha256']=digest('response-test:0:0')
        return base
    def run_phase(self,admitted=True,deadline=100):
        return md.run_phase(self.root,self.plan,self.schema,'screen','test',deadline,admitted,lambda:self.time,self.open_env,self.reserve,lambda:self.ledger,self.dispatch,self.replay)
    def test_complete_multiaction_phase(self):
        r=self.run_phase();self.assertEqual(r['attempts'],16);self.assertEqual(r['counts'],{'full':16});self.assertEqual(len(self.dispatched),32);self.assertEqual(self.closed,16)
        self.assertFalse(md.inspect_saved(self.root)['resume_authorized'])
    def test_failed_call_remains_in_denominator(self):
        self.mode='provider';r=self.run_phase();self.assertEqual(r['counts'],{'provider':1,'full':15});self.assertEqual(r['full_fraction_all_attempts'],15/16)
    def test_no_admission_or_bad_deadline_no_root(self):
        for admitted,deadline in [(False,100),(1,100),(True,float('inf')),(True,1801),(True,0)]:
            with self.assertRaises(ValueError):self.run_phase(admitted,deadline)
        self.assertFalse(self.root.exists());self.assertEqual(self.dispatched,[])
    def test_bad_reset_no_reservation_or_dispatch(self):
        self.bad_reset=True
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(self.ledger,[]);self.assertEqual(self.dispatched,[]);self.assertEqual(self.closed,1)
    def test_reservation_expiry_does_not_dispatch(self):
        reserve=self.reserve
        def expired(*args):reserve(*args);self.time=101
        self.reserve=expired
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(self.dispatched,[]);self.assertEqual(len(self.ledger),1)
    def test_failed_intent_write_prevents_dispatch(self):
        save=md.durable_new
        def fail(root,name,value):
            if name.endswith('-intent.json'):raise OSError('disk full')
            return save(root,name,value)
        with patch.object(md,'durable_new',fail):
            with self.assertRaises(OSError):self.run_phase()
        self.assertEqual(self.dispatched,[]);self.assertFalse((self.root/'complete.json').exists())
    def test_failed_raw_save_stops_before_native_action(self):
        save=md.durable_new
        def fail(root,name,value):
            if name.endswith('-provider.json'):raise OSError('disk full')
            return save(root,name,value)
        with patch.object(md,'durable_new',fail):
            with self.assertRaises(OSError):self.run_phase()
        self.assertEqual(len(self.dispatched),1);self.assertEqual(self.current,[])
    def test_late_provider_result_retained_without_next_action(self):
        self.late=True
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(len(self.dispatched),1);self.assertEqual(self.current,[]);self.assertTrue((self.root/'00-00-provider.json').exists())
    def test_invalid_usage_stops_before_next_call(self):
        self.mode='bad_usage'
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(len(self.dispatched),1);self.assertTrue((self.root/'00-00-event.json').exists());self.assertFalse((self.root/'complete.json').exists())
    def test_exception_type_only_and_no_resume(self):
        self.raise_dispatch=True
        with self.assertRaises(RuntimeError):self.run_phase()
        self.assertNotIn('private', (self.root/'aborted.json').read_text())
        with self.assertRaises(FileExistsError):self.run_phase()
        self.assertEqual(len(self.dispatched),1)
    def test_duplicate_response_stops_on_first_reused_reply(self):
        self.mode='duplicate'
        with self.assertRaises(ValueError):self.run_phase()
        self.assertEqual(len(self.dispatched),3);self.assertEqual(self.closed,2)
    def test_archive_tampering_rejected(self):
        self.run_phase();p=self.root/'00-00-provider.json';x=json.loads(p.read_text());x['payload']['status']='tampered';p.write_text(json.dumps(x))
        with self.assertRaises(ValueError):md.inspect_saved(self.root)


if __name__=='__main__':unittest.main()
