"""Actual Native paired execution and inherited financial/timeout boundaries."""
import argparse,ast,json,tempfile,time,unittest
from pathlib import Path
from caller import ROOT,modules,phase,load
p,Trial=modules()
from repair_env.tasks import make_task
from assemble import verify_chunk,assess
def bool_probe(source):
 tree=ast.parse(source)
 for node in ast.walk(tree):
  if isinstance(node,ast.FunctionDef):node.body.insert(0,ast.parse('_probe = bool(False)').body[0])
 return ast.unparse(ast.fix_missing_locations(tree))
class Backend:
 scripted=True
 def __init__(self,counter,kind='reference'):self.counter=counter;self.kind=kind;self.calls=[];self.reserved=[]
 def admit(self,bounds,generation,deadline):
  assert bounds==[28672]*4 and generation==6000
  if self.kind=='deny':raise ValueError('no financial admission')
 def reserve(self,*args):self.reserved.append(args)
 def check_reply(self,response):pass
 def check_message(self,message):pass
 def call(self,payload,timeout,job):
  self.calls.append(payload)
  if self.kind=='unknown':raise TimeoutError('scripted unknown provider usage')
  source=make_task(job['task_id'],job['seed']).reference_source
  if self.kind=='compat':source=bool_probe(source)
  text=json.dumps(dict(content=source))
  return dict(id='scripted-'+str(len(self.calls)),usage=dict(prompt_tokens=self.counter.context(payload['messages']),completion_tokens=payload['max_tokens'] if self.kind=='truncate' else self.counter.count(text)),choices=[dict(message=dict(role='assistant',content=text),finish_reason='length' if self.kind=='truncate' else 'stop')])
class SharedProgramTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  helper=load('shared_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
  cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path('/home/ruv/arena-tokenizer.json'),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
 def test_exact_first_prompt_schema_and_reserved_confirmation(self):
  values=[p.bundle(i) for i in range(2)]
  self.assertEqual([j for b in values for j in b['screen_jobs']],p.schedule('screen'))
  self.assertEqual(len({p.capture(j)['prompt_sha256'] for j in p.schedule('screen')}),1)
  with self.assertRaises(ValueError):p.capture(p.schedule('confirmation')[0])
  with self.assertRaises(ValueError):p.bundle(True)
 def test_one_response_and_separate_native_classes(self):
  t=Trial(p.schedule('screen')[0]);ref=make_task(t.job['task_id'],t.job['seed']).reference_source
  v=t.consume(json.dumps(dict(content=ref)))
  self.assertTrue(v['done']);self.assertTrue(v['paired_native']['actual_same_program'])
  self.assertEqual(v['category'],'full');self.assertEqual(v['paired_native']['candidate']['category'],'full')
  self.assertNotEqual(type(t.env).__module__,type(t.other).__module__)
  with self.assertRaises(ValueError):t.consume(json.dumps(dict(content=ref)))
 def test_bool_compatibility_is_real_native_grade_not_host_model_execution(self):
  t=Trial(p.schedule('screen')[0]);source=bool_probe(make_task(t.job['task_id'],t.job['seed']).reference_source)
  value=t.consume(json.dumps(dict(content=source)));pair=value['paired_native']
  self.assertEqual(pair['baseline']['category'],'execution');self.assertEqual(pair['candidate']['category'],'full');self.assertTrue(pair['compatibility_exposure'])
 def test_scripted_phase_has_two_calls_and_exact_paired_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=Path(tmp)/'live';b=Backend(self.counter,'compat');bundle=p.bundle(0)
   rows=phase(bundle,p.digest(bundle),output,b,self.counter,time.monotonic()+90)
   self.assertEqual(len(b.calls),2);self.assertEqual(len(b.reserved),2)
   self.assertTrue(all(r['turns']==1 and r['paired_native']['candidate']['category']=='full' for r in rows))
   self.assertTrue(json.loads((output/'complete.json').read_text())['scripted'])
   events=[json.loads(l) for l in (output/'events.jsonl').read_text().splitlines()]
   verify_chunk(bundle,rows,events,self.counter)
   rows[0]['paired_native']['candidate']['semantic_reward']=0
   with self.assertRaises(ValueError):verify_chunk(bundle,rows,events,self.counter)
 def test_unknown_usage_stops_and_remains_unknown(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=Path(tmp)/'live';b=Backend(self.counter,'unknown');bundle=p.bundle(0)
   rows=phase(bundle,p.digest(bundle),output,b,self.counter,time.monotonic()+90)
   self.assertEqual(len(b.calls),1);self.assertIsNone(rows[0]['generation_tokens'])
   self.assertEqual([r['category'] for r in rows],['provider','budget'])
 def test_denial_precedes_archive_or_call(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=Path(tmp)/'live';b=Backend(self.counter,'deny');bundle=p.bundle(0)
   with self.assertRaises(ValueError):phase(bundle,p.digest(bundle),output,b,self.counter,time.monotonic()+90)
   self.assertEqual(b.calls,[]);self.assertFalse(output.exists())
 def test_truncation_never_becomes_native_solve(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=Path(tmp)/'live';b=Backend(self.counter,'truncate');bundle=p.bundle(0)
   rows=phase(bundle,p.digest(bundle),output,b,self.counter,time.monotonic()+90)
   self.assertEqual(len(b.calls),2);self.assertTrue(all(r['category']=='truncation' and r['paired_native'] is None for r in rows))
   events=[json.loads(l) for l in (output/'events.jsonl').read_text().splitlines()]
   verify_chunk(bundle,rows,events,self.counter)
 def test_all_four_assignments_and_no_lost_full_rule(self):
  rows=[]
  for i in range(2):
   with tempfile.TemporaryDirectory() as tmp:
    b=Backend(self.counter,'reference');bundle=p.bundle(i)
    rows+=phase(bundle,p.digest(bundle),Path(tmp)/'live',b,self.counter,time.monotonic()+90)
  result=assess(rows);self.assertFalse(result['statistical_gate']);self.assertEqual(result['assigned'],4)
  with self.assertRaises(ValueError):assess(rows[:3])
if __name__=='__main__':unittest.main()
