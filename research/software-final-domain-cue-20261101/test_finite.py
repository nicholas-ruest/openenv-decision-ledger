import argparse,copy,importlib.util,json,os,tempfile,threading,time,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import finite_caller as c
spec=importlib.util.spec_from_file_location('qualified_final_domain_transport',Path(__file__).with_name('guarded_transport.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from repair_env.tasks import make_task

class Backend:
    scripted=True
    def __init__(self,counter,responses,fault=None):
        self.counter=counter;self.responses=responses;self.fault=fault;self.calls=[];self.reservations=[];self.admissions=[];self.lock=threading.Lock()
        self.barriers={(s,t):threading.Barrier(2) for s in range(4) for t in range(2)}
        self.inflight=self.max_inflight=self.reserving=self.max_reserving=0
    def admit(self,*args):self.admissions.append(args)
    def reserve(self,label,*args):
        with self.lock:self.reserving+=1;self.max_reserving=max(self.max_reserving,self.reserving)
        time.sleep(.002);self.reservations.append(label)
        with self.lock:self.reserving-=1
    def call(self,payload,timeout,job,turn):
        with self.lock:self.calls.append((job['attempt_id'],turn));self.inflight+=1;self.max_inflight=max(self.max_inflight,self.inflight)
        try:
            self.barriers[job['sample'],turn].wait(timeout=30)
            if self.fault=='unknown_second' and job==c.p.jobs()[0] and turn==1:raise TimeoutError('synthetic unknown usage')
            value=copy.deepcopy(self.responses[job['attempt_id']][turn])
            if self.fault=='overrun_second' and job==c.p.jobs()[0] and turn==1:value['usage']['completion_tokens']=8097
            return value
        finally:
            with self.lock:self.inflight-=1
    def check_reply(self,response):pass
    def check_message(self,message):
        if message.get('role')!='assistant':raise ValueError('content-only message required')

class FiniteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        root=c.p.d.ROOT;sys.path.insert(0,str(root/'integrations/openenv-arena'))
        spec=importlib.util.spec_from_file_location('finite_domain_counter',root/'integrations/openenv-arena/scripts/calibrate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cls.counter=module.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        good=make_task('software_repair-ignore-d3',2560000).reference_source;cls.responses={}
        for job in c.p.jobs():
            trial=c.p.Trial(job);responses=[]
            for turn in range(2):
                proposal='def classify_ignore(lines, entries):\n    return {entry["path"]: False for entry in entries}\n'
                message=dict(role='assistant',content=json.dumps(dict(content=proposal if turn==0 else good)))
                value=dict(id='scripted-finite-'+job['attempt_id']+':'+str(turn),usage=dict(prompt_tokens=cls.counter.context(trial.messages),completion_tokens=cls.counter.count(message['content'])),choices=[dict(message=message,finish_reason='stop')])
                responses.append(value)
                if turn==0:trial.consume(message,'stop')
            cls.responses[job['attempt_id']]=responses

    def execute(self,fault=None):
        original=Backend(self.counter,self.responses,fault);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);out=Path(tmp.name)/'phase'
        rows,summary=c.run(b.AtomicDelegation(original),self.counter,out,time.monotonic()+1200)
        return original,rows,summary,out

    def test_complete_original_phase_reservations_and_max_two_inflight(self):
        original,rows,summary,out=self.execute()
        self.assertTrue(summary['complete']);self.assertEqual(len(original.calls),16);self.assertEqual(len(original.reservations),16)
        self.assertEqual(original.max_inflight,2);self.assertEqual(original.max_reserving,1);self.assertEqual(original.admissions[0][:2],([28672]*16,8096))
        self.assertEqual(sum(r['final_domain_reminder_exposed'] for r in rows),4)
        p=out/c.p.jobs()[0]['attempt_id']/'request-1.json';value=json.loads(p.read_text());value['max_tokens']+=1;p.write_text(json.dumps(value))
        with self.assertRaises(ValueError):c.assemble(out,self.counter)

    def test_unknown_second_preserves_known_prefix_and_all_reserved_slots(self):
        original,rows,summary,out=self.execute('unknown_second')
        self.assertFalse(summary['complete']);self.assertEqual(summary['unknown_usage_calls'],1);self.assertEqual(len(original.reservations),4)
        self.assertIsNone(rows[0]['generation_tokens']);self.assertGreater(rows[0]['known_generation_tokens'],0)
        report=c.assemble(out,self.counter);self.assertEqual(report['rows'][0]['known_prefix_responses_replayed'],1)
        self.assertEqual(sum(not r['recorded'] for r in report['rows']),6)
        p=out/c.p.jobs()[0]['attempt_id']/'request-1.json';value=json.loads(p.read_text());value['max_tokens']+=1;p.write_text(json.dumps(value))
        with self.assertRaises(ValueError):c.assemble(out,self.counter)

    def test_actual_provider_context_plus_review_overrun_is_not_discarded(self):
        original=Backend(self.counter,self.responses)
        def response(payload,timeout,job,turn):
            value=copy.deepcopy(self.responses[job['attempt_id']][turn]);value['usage']['prompt_tokens']=24576-value['usage']['completion_tokens'];return value
        original.call=response;backend=b.AtomicDelegation(original);deadline=time.monotonic()+1200;backend.admit([28672]*16,8096,deadline)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);c.write(out/'assignments.json',c.p.jobs())
            row=c.attempt(c.p.jobs()[0],backend,self.counter,out/c.p.jobs()[0]['attempt_id'],deadline,threading.Event(),set(),threading.Lock())
            self.assertEqual(row['category'],'budget');self.assertFalse(row['unknown_usage'])
            report=c.assemble(out,self.counter)
            self.assertEqual(report['rows'][0]['prefix_fault'],'actual_observation_overrun');self.assertIsNone(report['rows'][0]['semantic_reward'])

    def test_known_overrun_retains_usage_as_budget_failure(self):
        original,rows,summary,out=self.execute('overrun_second')
        self.assertFalse(summary['complete']);self.assertFalse(rows[0]['unknown_usage']);self.assertEqual(rows[0]['category'],'budget')
        self.assertGreater(rows[0]['generation_tokens'],8096)
        report=c.assemble(out,self.counter);self.assertEqual(report['rows'][0]['prefix_fault'],'actual_token_overrun')
        self.assertIsNone(report['rows'][0]['semantic_reward'])

    def test_native_fault_never_becomes_semantic_or_unknown_usage(self):
        with patch.object(c.replay.r.RevisionEnvironment,'step',side_effect=OSError('synthetic Native fault')):
            original,rows,summary,out=self.execute()
            self.assertFalse(summary['complete']);self.assertEqual(len(original.calls),2)
            self.assertTrue(all(r['failure_origin']=='native_execution_unverified' and not r['unknown_usage'] for r in rows))
            report=c.assemble(out,self.counter);self.assertTrue(all(r.get('prefix_fault')=='native_processing_unverified' for r in report['rows'] if r['recorded']))

    def test_deadline_after_terminal_replay_clears_semantic_reward(self):
        original=Backend(self.counter,self.responses);original.call=lambda payload,timeout,job,turn:copy.deepcopy(self.responses[job['attempt_id']][turn])
        backend=b.AtomicDelegation(original);deadline=time.monotonic()+1200;backend.admit([28672]*16,8096,deadline)
        clock=time.monotonic;verify=c.p.verify;expired=False
        def current():return clock()+(2000 if expired else 0)
        def verified(*args):
            nonlocal expired
            value=verify(*args);expired=True;return value
        with tempfile.TemporaryDirectory() as tmp,patch.object(c.time,'monotonic',side_effect=current),patch.object(c.p,'verify',side_effect=verified):
            row=c.attempt(c.p.jobs()[0],backend,self.counter,Path(tmp)/'attempt',deadline,threading.Event(),set(),threading.Lock())
        self.assertEqual(row['terminal_reward_observed'],1);self.assertEqual(row['category'],'budget');self.assertIsNone(row['semantic_reward'])

    def test_live_duplicate_out_of_order_and_reused_archives_refused(self):
        with self.assertRaises(ValueError):b.guarded_backend()
        with self.assertRaises(ValueError):b.AtomicDelegation(SimpleNamespace(scripted=False))
        with self.assertRaises(ValueError):c.run_screen()
        original=Backend(self.counter,self.responses);backend=b.AtomicDelegation(original);deadline=time.monotonic()+1200;backend.admit([28672]*16,8096,deadline);label=c.p.jobs()[0]['attempt_id']
        with self.assertRaises(ValueError):backend.reserve(label+':1',28672,1000,deadline)
        def reserve():
            try:backend.reserve(label+':0',28672,6000,deadline);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(lambda _:reserve(),range(2))),[False,True])
        for d in [float('nan'),time.monotonic()+1201,time.monotonic()-1]:
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):c.run(backend,self.counter,Path(tmp)/'phase',d)
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):c.run(backend,self.counter,Path(tmp),deadline)

    def test_pinned_supervisor_completion_stub_and_native_timeout(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(c,'run',return_value=([],dict(complete=True))):
            result=b.supervise_qualification(b.AtomicDelegation(Backend(self.counter,self.responses)),self.counter,Path(tmp)/'phase',10)
            self.assertEqual(result['status'],'completed');self.assertTrue(result['shutdown_verified']);self.assertFalse(result['remote_cancellation_attested'])
        with tempfile.TemporaryDirectory() as tmp:
            result=b.supervise_qualification(b.AtomicDelegation(Backend(self.counter,self.responses)),self.counter,Path(tmp)/'phase',.01)
            self.assertEqual(result['status'],'timed_out');self.assertTrue(result['shutdown_verified'])

if __name__=='__main__':unittest.main()
