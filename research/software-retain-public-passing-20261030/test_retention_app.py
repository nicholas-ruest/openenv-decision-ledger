"""Actual OpenEnv transport for public-passing retention advice."""
import json,unittest
from fastapi.testclient import TestClient
from retention_app import app
from repair_env.tasks import make_task
from test_portable_app import exchange
TASK='software_repair-ignore-d3'
SEED=2940000
class RetentionAppTests(unittest.TestCase):
 def test_public_passing_reference_is_reviewed_then_explicitly_retained(self):
  ref=make_task(TASK,SEED).reference_source
  with TestClient(app) as client,client.websocket_connect('/ws') as ws:
   exchange(ws,'reset',dict(task_id=TASK,seed=SEED))
   review=exchange(ws,'step',dict(content=ref))
   self.assertFalse(review['done']);self.assertEqual(review['reward'],0)
   feedback=json.loads(review['observation']['feedback'])
   self.assertTrue(feedback['retention_advice']);self.assertEqual(feedback['passed'],6)
   final=exchange(ws,'step',{})
   self.assertTrue(final['done']);self.assertEqual(final['reward'],1)
 def test_empty_finish_remains_terminal_without_a_proposal(self):
  with TestClient(app) as client,client.websocket_connect('/ws') as ws:
   exchange(ws,'reset',dict(task_id=TASK,seed=SEED))
   final=exchange(ws,'step',{})
   self.assertTrue(final['done']);self.assertEqual(final['reward'],0)
if __name__=='__main__':unittest.main()
