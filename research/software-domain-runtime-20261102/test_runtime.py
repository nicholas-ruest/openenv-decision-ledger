import json,unittest
from unittest.mock import patch
from runtime_environment import DomainCueEnvironment,DirectRepairAction,FINISH_ACTION,FINISH_KEY,TASK_ID
from repair_env.direct_environment import DirectRepairEnvironment

class Runtime(unittest.TestCase):
    def env(self,arm='final_domain_reminder'):
        e=DomainCueEnvironment(arm=arm);o=e.reset(seed=2560000,task_id=TASK_ID);return e,o
    def test_common_first_prompt_and_only_late_reminder_changes(self):
        a,oa=self.env('common_review');b,ob=self.env();self.assertEqual(oa,ob);reviews=[]
        for e in (a,b):
            first=e.step(DirectRepairAction(content='import os'));self.assertFalse(first.done);self.assertEqual(first.reward,0);reviews.append(json.loads(first.feedback))
        self.assertTrue(reviews[1].pop('final_output_domain_reminder'));self.assertEqual(*reviews)
    def test_finalization_before_proposal_and_after_reference_preserves_native_grade(self):
        e,_=self.env();final=e.step(FINISH_ACTION);self.assertTrue(final.done);self.assertEqual(final.reward,0);self.assertEqual(e.state.step_count,1)
        e,_=self.env();source=e._direct._task.reference_source;first=e.step(DirectRepairAction(content=source));self.assertFalse(first.done);self.assertEqual(first.reward,0)
        final=e.step(FINISH_ACTION);self.assertTrue(final.done);self.assertEqual(final.reward,1);self.assertEqual(e.state.step_count,2);self.assertEqual(e.step(DirectRepairAction(content='import os')),final)
    def test_bad_finalization_does_not_mutate_state(self):
        for action in [DirectRepairAction(content='x',metadata={FINISH_KEY:True}),DirectRepairAction(content='',metadata={FINISH_KEY:1}),DirectRepairAction(content='',metadata={FINISH_KEY:True,'extra':True})]:
            e,_=self.env()
            with self.assertRaises(ValueError):e.step(action)
            self.assertEqual(e.state.step_count,0)
    def test_other_task_refused_before_native_generation(self):
        with patch.object(DirectRepairEnvironment,'reset',side_effect=AssertionError('no generation')):
            with self.assertRaises(ValueError):DomainCueEnvironment().reset(seed=2560000,task_id='other')
    def test_native_sdk_websocket_preserves_finalizer_metadata(self):
        from starlette.testclient import TestClient
        from runtime_app import app
        with TestClient(app) as client:
            with client.websocket_connect('/ws') as ws:
                ws.send_json({'type':'reset','data':{'task_id':TASK_ID,'seed':2560000}});reset=ws.receive_json();self.assertEqual(reset['type'],'observation');self.assertFalse(reset['data']['done'])
                ws.send_json({'type':'step','data':FINISH_ACTION.model_dump()});final=ws.receive_json();self.assertEqual(final['type'],'observation');self.assertTrue(final['data']['done']);self.assertEqual(final['data']['reward'],0)
if __name__=='__main__':unittest.main()
