"""Actual OpenEnv HTTP/WebSocket contract tests, with no model calls."""
import json,unittest
from fastapi.testclient import TestClient
from diagnostic_app import app,ProposalAction,RevisionObservation
from repair_env.direct_environment import DirectRepairEnvironment
from repair_env.environment import RepairAction
from repair_env.tasks import make_task
TASK='software_repair-ignore-d3'
SEED=3040000

def exchange(ws,kind,data):
    ws.send_json(dict(type=kind,data=data))
    value=ws.receive_json()
    if value['type']!='observation':raise AssertionError(value)
    return value['data']

class PortableAppTests(unittest.TestCase):
    def test_actual_schema_has_content_only_and_matches_observation(self):
        with TestClient(app) as client:
            response=client.get('/schema')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['action'],ProposalAction.model_json_schema())
            self.assertEqual(response.json()['observation'],RevisionObservation.model_json_schema())
            self.assertNotIn('submit',response.json()['action']['properties'])
    def test_empty_finish_from_reset_reaches_unchanged_native_grade(self):
        direct=DirectRepairEnvironment();direct.reset(task_id=TASK,seed=SEED)
        expected=direct._core.step(RepairAction(op='submit')).reward
        with TestClient(app) as client,client.websocket_connect('/ws') as ws:
            exchange(ws,'reset',dict(task_id=TASK,seed=SEED))
            result=exchange(ws,'step',{})
            self.assertTrue(result['done']);self.assertEqual(result['reward'],expected)
            self.assertEqual(result['observation']['remaining_responses'],0)
    def test_public_feedback_and_empty_finish_preserve_reference_module(self):
        ref=make_task(TASK,SEED).reference_source
        with TestClient(app) as client,client.websocket_connect('/ws') as ws:
            reset=exchange(ws,'reset',dict(task_id=TASK,seed=SEED))
            self.assertIn('Empty content ends the episode at any point',reset['observation']['prompt'])
            review=exchange(ws,'step',dict(content=ref))
            self.assertFalse(review['done']);self.assertEqual(review['reward'],0)
            feedback=json.loads(review['observation']['feedback'])
            self.assertEqual((feedback['kind'],feedback['passed'],feedback['total']),('public_field_check',6,6))
            self.assertTrue(feedback['public_only']);self.assertFalse(feedback['hidden_access'])
            final=exchange(ws,'step',dict(content=''))
            self.assertTrue(final['done']);self.assertEqual(final['reward'],1)
            self.assertEqual(final['observation']['source'],'')
    def test_concurrent_sessions_keep_proposals_and_terminal_state_separate(self):
        ref=make_task(TASK,SEED).reference_source
        with TestClient(app) as client,client.websocket_connect('/ws') as one,client.websocket_connect('/ws') as two:
            exchange(one,'reset',dict(task_id=TASK,seed=SEED))
            exchange(two,'reset',dict(task_id=TASK,seed=SEED))
            review=exchange(one,'step',dict(content=ref))
            self.assertFalse(review['done'])
            other=exchange(two,'step',{})
            self.assertTrue(other['done']);self.assertEqual(other['reward'],0)
            final=exchange(one,'step',dict(content=ref))
            self.assertTrue(final['done']);self.assertEqual(final['reward'],1)
if __name__=='__main__':unittest.main()
