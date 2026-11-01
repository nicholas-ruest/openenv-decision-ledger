import copy,json,subprocess,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import finite_qualification as c
import failure_protocol as p
from assemble_archives import assemble
import test_failure_protocol as fixture


class Backend:
    scripted=True
    def __init__(self,counter,deny=None,unknown=None):self.counter=counter;self.deny=deny;self.unknown=unknown;self.reserved=[];self.calls=[];self.intents=0
    def reserve(self,label,prompt,generation,deadline):
        self.intents+=1
        if self.intents==self.deny:raise ValueError('denied')
        self.reserved.append(label)
    def check_reply(self,r):pass
    def check_message(self,m):pass
    def call(self,payload,timeout,job):
        from repair_env.tasks import make_task
        self.calls.append(payload)
        if len(self.calls)==self.unknown:raise TimeoutError('unknown usage')
        source=json.loads(payload['messages'][1]['content'])['source'] if len(payload['messages'])==2 else make_task(p.TASK,3100000).reference_source
        text=json.dumps(dict(content=source))
        return dict(id=job['attempt_id']+':'+str(len(self.calls)),usage=dict(prompt_tokens=self.counter.context(payload['messages']),completion_tokens=self.counter.count(text)),choices=[dict(finish_reason='stop',message=dict(role='assistant',content=text))])


def score(report):
    module=Path(__file__).with_name('assess_archives.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assessArchive} from "+json.dumps(module)+";console.log(JSON.stringify(assessArchive(JSON.parse(readFileSync(0,'utf8')))));"
    r=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(report),text=True,capture_output=True,check=True)
    return json.loads(r.stdout)


class FiniteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.MatchedTests.setUpClass();cls.counter=fixture.MatchedTests.counter
    def test_complete_four_chunks_reserve_before_each_call_and_independently_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for i in range(4):
                path=Path(tmp)/str(i);paths.append(path);b=Backend(self.counter)
                rows,done=c.run_chunk(i,b,self.counter,path,time.monotonic()+120)
                self.assertEqual(len(b.calls),len(b.reserved));self.assertEqual(len(b.calls),4);self.assertFalse(done['stopped_on_failure'])
            a=assemble(paths,self.counter);result=score(a)
            self.assertTrue(a['complete']);self.assertEqual(a['independently_replayed'],8)
            self.assertEqual(result['actual_module'],'fitness.mjs:scoreCell');self.assertFalse(result['selection_passed'])
            rows=[json.loads(l) for l in (paths[0]/'records.jsonl').read_text().splitlines()];rows[1]['advice_observation_tokens']=0
            (paths[0]/'records.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):assemble(paths,self.counter)
    def test_unknown_after_known_reply_retains_all_reservations_and_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'0';b=Backend(self.counter,unknown=2)
            rows,done=c.run_chunk(0,b,self.counter,out,time.monotonic()+60)
            self.assertEqual(len(b.reserved),2);self.assertEqual(len(b.calls),2);self.assertIsNone(rows[0]['generation_tokens']);self.assertTrue(rows[0]['unknown_usage'])
            a=assemble([out]+[root/str(i) for i in range(1,4)],self.counter)
            self.assertEqual(a['assigned'],8);self.assertEqual(a['unexecuted'],7);self.assertIsNone(score(a)['actual_module'])
    def test_reservation_denial_and_native_initialization_never_make_unreserved_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);b=Backend(self.counter,deny=2)
            rows,done=c.run_chunk(0,b,self.counter,root/'denial',time.monotonic()+60)
            self.assertEqual(len(b.calls),1);self.assertEqual(len(b.reserved),1);self.assertEqual(rows[0]['category'],'budget');self.assertFalse(rows[0]['unknown_usage'])
            b=Backend(self.counter)
            with patch.object(p,'QualificationTrial',side_effect=RuntimeError('unavailable')):
                rows,done=c.run_chunk(0,b,self.counter,root/'native',time.monotonic()+60)
            self.assertEqual(b.calls,[]);self.assertEqual(rows[0]['category'],'execution')
    def test_deadline_after_reservation_or_native_processing_cannot_be_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);now=[0.0];b=Backend(self.counter);reserve=b.reserve
            def delayed(*args):reserve(*args);now[0]=700
            b.reserve=delayed
            with patch.object(c.time,'monotonic',side_effect=lambda:now[0]):rows,done=c.run_chunk(0,b,self.counter,root/'reserve',1200)
            self.assertEqual(b.calls,[]);self.assertEqual(len(b.reserved),1);self.assertEqual(rows[0]['category'],'budget')
            now=[0.0];process=p._process
            def late(*args):result=process(*args);now[0]=700;return result
            with patch.object(c.time,'monotonic',side_effect=lambda:now[0]),patch.object(p,'_process',side_effect=late):
                rows,done=c.run_chunk(0,Backend(self.counter),self.counter,root/'processing',1200)
            self.assertEqual(rows[0]['category'],'budget');self.assertTrue(done['stopped_on_failure'])
    def test_archive_reuse_and_live_backend_are_refused_before_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);b=Backend(self.counter)
            with self.assertRaises(ValueError):c.run_chunk(0,b,self.counter,out,time.monotonic()+60)
            b.scripted=False
            with self.assertRaises(ValueError):c.run_chunk(0,b,self.counter,out/'new',time.monotonic()+60)
            self.assertEqual(b.calls,[])
            with self.assertRaises(ValueError):c.require_live_ready()
    def test_archive_identity_and_later_chunk_after_stop_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=[root/str(i) for i in range(4)]
            c.run_chunk(0,Backend(self.counter,unknown=1),self.counter,paths[0],time.monotonic()+60)
            c.run_chunk(1,Backend(self.counter),self.counter,paths[1],time.monotonic()+60)
            with self.assertRaises(ValueError):assemble(paths,self.counter)
            rows=[json.loads(l) for l in (paths[0]/'records.jsonl').read_text().splitlines()];rows[0]['generation_tokens']=0;rows[0]['unknown_usage']=False
            (paths[0]/'records.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):assemble([paths[0]]+[root/('missing'+str(i)) for i in range(1,4)],self.counter)


if __name__=='__main__':unittest.main()
