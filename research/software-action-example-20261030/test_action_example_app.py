"""Actual OpenEnv HTTP/WebSocket controls; no model calls or held-out claims."""
import json
import unittest
from fastapi.testclient import TestClient
from action_example_app import app, ProposalAction, RevisionObservation
from action_example_environment import ACTION_EXAMPLE_NOTE
from repair_env.tasks import make_task

TASK = 'software_repair-ignore-d2'
SEED = 42


def exchange(ws, kind, data):
    ws.send_json(dict(type=kind, data=data))
    result = ws.receive_json()
    if result['type'] != 'observation':
        raise AssertionError(result)
    return result['data']


class ActualSdkTests(unittest.TestCase):
    def test_http_schema_keeps_unchanged_action_and_observation(self):
        with TestClient(app) as client:
            result = client.get('/schema')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['action'], ProposalAction.model_json_schema())
            self.assertEqual(result.json()['observation'], RevisionObservation.model_json_schema())

    def test_actual_websocket_reset_note_public_review_and_reference_retention(self):
        reference = make_task(TASK, SEED).reference_source
        with TestClient(app) as client, client.websocket_connect('/ws') as ws:
            initial = exchange(ws, 'reset', dict(task_id=TASK, seed=SEED))
            self.assertTrue(initial['observation']['prompt'].endswith(ACTION_EXAMPLE_NOTE))
            review = exchange(ws, 'step', dict(content=reference, submit=True))
            self.assertFalse(review['done'])
            self.assertEqual(review['reward'], 0)
            feedback = json.loads(review['observation']['feedback'])
            self.assertTrue(feedback['public_only'])
            self.assertFalse(feedback['hidden_access'])
            final = exchange(ws, 'step', dict(content=''))
            self.assertTrue(final['done'])
            self.assertEqual(final['reward'], 1)

    def test_concurrent_sessions_preserve_separate_modules_and_final_grades(self):
        reference = make_task(TASK, SEED).reference_source
        with TestClient(app) as client, client.websocket_connect('/ws') as one, client.websocket_connect('/ws') as two:
            for ws in (one, two):
                exchange(ws, 'reset', dict(task_id=TASK, seed=SEED))
            self.assertFalse(exchange(one, 'step', dict(content=reference))['done'])
            wrong = exchange(two, 'step', {})
            self.assertTrue(wrong['done'])
            self.assertEqual(wrong['reward'], 0)
            full = exchange(one, 'step', dict(content=''))
            self.assertTrue(full['done'])
            self.assertEqual(full['reward'], 1)


if __name__ == '__main__': unittest.main()
