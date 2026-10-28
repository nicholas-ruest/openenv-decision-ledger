import copy
import unittest
from raw_evidence import bind,digest
R='0b8ccc3ca70a67fed5fc5837b69022261cc60497';S='a'*64

class RawTests(unittest.TestCase):
    def setUp(self):
        self.snapshot={'messages':[{'role':'system','content':'policy'},{'role':'user','content':'reset'}], 'files':{'src/solution.py':'code'},'reset':{'prompt':'task'},'case_sha256':'b'*64,'base_prompt_sha256':'c'*64}
        for name,field in [('prompt','messages'),('workspace','files'),('reset','reset')]:self.snapshot[name+'_sha256']=digest(self.snapshot[field])
        self.raw={'task_id':'software_repair-ignore-d3','seed':2200000,'sample':0,'prompt_sha256':'c'*64,'messages':self.snapshot['messages']+[{'role':'assistant','content':'{"content":"code"}'}], 'reward':.75,'failure':None,'calls':[{'client_call_label':'job0','reserved_usd':.1,'prompt_tokens':10,'completion_tokens':20,'finish_reason':'stop','provider_response_id_sha256':'d'*64}]}
        self.jobs=[{'arm':'baseline','task_id':self.raw['task_id'],'seed':2200000,'sample':0,'planned_call_label':'job0','raw':self.raw}]
        self.records=[{'arm':'baseline','task_id':self.raw['task_id'],'seed':2200000,'sample':0,'runtime_source':R,'settings_sha256':S,**{k:self.snapshot[k] for k in ['case_sha256','reset_sha256','workspace_sha256','prompt_sha256']},'client_call_label':'job0','provider_response_id_sha256':'d'*64,'provider_call_observed':True,'failure':None,'reward':.75}]
        self.ledger=[{'label':'job0','usd':'0.100000000000000001','prompt_bound':100,'generation_bound':100}]
        self.reward=.75
    def run_bind(self):
        return bind(self.jobs,self.records,self.ledger,R,S,lambda *args:copy.deepcopy(self.snapshot),lambda *args:self.reward,lambda r:r['failure'])
    def test_valid_partial_native_replay(self):
        r=self.run_bind();self.assertEqual(r['native_replayed_valid_answers'],1);self.assertFalse(r['reservation_order_attested'])
    def test_lost_response_keeps_reservation(self):
        self.raw.update(failure='provider',calls=[],messages=self.snapshot['messages'],reward=0)
        self.records[0].update(failure='provider',provider_call_observed=False,provider_response_id_sha256=None,reward=0)
        r=self.run_bind();self.assertEqual(r['reservation_only_jobs'],1);self.assertEqual(r['native_replayed_valid_answers'],0)
    def test_unreserved_budget_failure_distinct(self):
        self.raw.update(failure='budget',calls=[],messages=self.snapshot['messages'],reward=0);self.ledger=[]
        self.records[0].update(failure='budget',provider_call_observed=False,provider_response_id_sha256=None,reward=0)
        self.assertEqual(self.run_bind()['unreserved_jobs'],1)
    def test_missing_reservation(self):
        self.ledger=[]
        with self.assertRaises(ValueError):self.run_bind()
    def test_duplicate_ledger(self):
        self.ledger*=2
        with self.assertRaises(ValueError):self.run_bind()
    def test_changed_amount(self):
        self.ledger[0]['usd']='0.11'
        with self.assertRaises(ValueError):self.run_bind()
    def test_invalid_amounts(self):
        for bad in ['NaN','Infinity','-1',True]:
            self.ledger[0]['usd']=bad
            with self.assertRaises(ValueError):self.run_bind()
    def test_observed_call_must_match_planned_label(self):
        self.raw['calls'][0]['client_call_label']='other'
        with self.assertRaises(ValueError):self.run_bind()
    def test_request_drift(self):
        self.raw['messages']=copy.deepcopy(self.raw['messages']);self.raw['messages'][0]['content']='wrong'
        with self.assertRaises(ValueError):self.run_bind()
    def test_snapshot_hash_drift(self):
        self.snapshot['files']['src/solution.py']='drift'
        with self.assertRaises(ValueError):self.run_bind()
    def test_native_reward_drift(self):
        self.reward=1
        with self.assertRaises(ValueError):self.run_bind()
    def test_normalized_reward_tampering(self):
        self.records[0]['reward']=1
        with self.assertRaises(ValueError):self.run_bind()
    def test_single_call_only(self):
        self.raw['calls']*=2
        with self.assertRaises(ValueError):self.run_bind()
    def test_duplicate_job(self):
        self.jobs*=2;self.records*=2
        with self.assertRaises(ValueError):self.run_bind()
    def test_semantic_result_needs_response(self):
        self.raw['calls'][0]['provider_response_id_sha256']=None
        with self.assertRaises(ValueError):self.run_bind()
    def test_boolean_sample_rejected(self):
        self.raw['sample']=False
        with self.assertRaises(ValueError):self.run_bind()
    def test_incomplete_archive(self):
        self.records=[]
        with self.assertRaises(ValueError):self.run_bind()
    def test_usage_over_reservation(self):
        self.raw['calls'][0]['completion_tokens']=101
        with self.assertRaises(ValueError):self.run_bind()
    def test_length_finish_not_valid_semantic(self):
        self.raw['calls'][0]['finish_reason']='length'
        with self.assertRaises(ValueError):self.run_bind()
    def test_unknown_failure_rejected(self):
        self.raw['failure']='mystery'
        with self.assertRaises(ValueError):self.run_bind()

if __name__=='__main__':unittest.main()
