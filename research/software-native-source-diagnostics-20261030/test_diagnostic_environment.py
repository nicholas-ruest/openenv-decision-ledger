"""Actual Native feedback, source scope and terminal semantics."""
import json,unittest,tempfile,time
from pathlib import Path
from caller import modules,phase
protocol,Trial=modules()
from diagnostic_environment import DiagnosticEnvironment
from mandatory_environment import ProposalAction
from repair_env.tasks import make_task
from source_diagnostics import diagnose
from assemble import verify_chunk,diagnostic_exposure
import test_caller as scripted
TASK='software_repair-ignore-d3'
class DiagnosticTests(unittest.TestCase):
 def test_identical_reset_and_only_source_diagnostic_differs(self):
  resets=[];reviews=[]
  for arm in protocol.ARMS:
   env=DiagnosticEnvironment(arm=arm);resets.append(env.reset(task_id=TASK,seed=2980000).model_dump())
   ops=[];core=env._direct._core;original=core.step
   def tracked(action,*args,**kwargs):
    ops.append(action.op);return original(action,*args,**kwargs)
   core.step=tracked
   source='def solve(x):\n    return sorted(x, reverse=True)\n'
   obs=env.step(ProposalAction(content=source));self.assertFalse(obs.done);self.assertEqual(obs.reward,0)
   self.assertEqual(ops,['write']);reviews.append(json.loads(obs.feedback))
  self.assertEqual(resets[0],resets[1]);diagnostic=reviews[1].pop('source_diagnostic')
  self.assertEqual(diagnostic,diagnose(source));self.assertEqual(reviews[0],reviews[1])
  self.assertEqual(diagnostic['nodes'][0]['node'],'keyword')
 def test_valid_reference_has_identical_feedback_and_native_reward(self):
  values=[]
  for arm in protocol.ARMS:
   env=DiagnosticEnvironment(arm=arm);env.reset(task_id=TASK,seed=2980000)
   first=env.step(ProposalAction(content=make_task(TASK,2980000).reference_source))
   self.assertNotIn('source_diagnostic',json.loads(first.feedback));values.append(first.model_dump())
   final=env.step(ProposalAction());self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(values[0],values[1])
 def test_early_empty_finish_has_no_diagnostic(self):
  env=DiagnosticEnvironment(arm='diagnostic_review');env.reset(task_id=TASK,seed=2980000)
  final=env.step(ProposalAction());self.assertTrue(final.done);self.assertNotIn('source_diagnostic',final.feedback)
 def test_unknown_arm_refused(self):
  with self.assertRaises(ValueError):DiagnosticEnvironment(arm='bypass')
 def test_sent_diagnostic_and_final_native_replay_are_bound(self):
  scripted.NativeFeedbackTests.setUpClass();counter=scripted.NativeFeedbackTests.counter
  class ParserBackend(scripted.ScriptedBackend):
   def call(self,payload,timeout,job):
    value=super().call(payload,timeout,job)
    if len(payload['messages'])==2:
     text=json.dumps(dict(content='def solve(x):\n    return sorted(x, reverse=True)\n'))
     value['choices'][0]['message']['content']=text;value['usage']['completion_tokens']=counter.count(text)
    return value
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'live';backend=ParserBackend(counter)
   rows=phase(protocol.bundle(0),protocol.digest(protocol.bundle(0)),out,backend,counter,time.monotonic()+90)
   events=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
   verify_chunk(protocol.bundle(0),rows,events,counter)
   self.assertEqual(diagnostic_exposure([out]),dict(standard_review=0,diagnostic_review=1))
   c=json.loads(backend.calls[1]['messages'][-1]['content']);t=json.loads(backend.calls[3]['messages'][-1]['content'])
   self.assertNotIn('source_diagnostic',json.loads(c['feedback']))
   self.assertEqual(json.loads(t['feedback'])['source_diagnostic']['kind'],'unsupported_syntax')
   self.assertTrue(all(r['category']=='full' for r in rows))
if __name__=='__main__':unittest.main()
