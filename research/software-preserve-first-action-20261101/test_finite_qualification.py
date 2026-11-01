import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import finite_qualification as f
import test_matched_protocol as fixtures


class Backend:
    scripted = True
    def __init__(self, responses):
        self.responses = copy.deepcopy(responses);self.calls=[];self.reservations=[]
    def admit(self, bounds, maximum, deadline):
        assert bounds == [28672]*8 and maximum == 6000
    def reserve(self, label, prompt, completion, deadline):
        self.reservations.append(label)
    def call(self, payload, seconds, job):
        self.calls.append(job['attempt_id'])
        assert payload['max_tokens'] == 6000 and 0 < seconds <= 360
        response = self.responses[len(self.calls)-1]
        if isinstance(response, Exception): raise response
        return response
    def check_reply(self, response): pass
    def check_message(self, message):
        if message.get('role') != 'assistant': raise ValueError('assistant reply required')


class FiniteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MatchedTests.setUpClass();cls.counter=fixtures.MatchedTests.counter
        cls.good = [copy.deepcopy(fixtures.MatchedTests.responses[0]) for _ in range(8)]
        for i, r in enumerate(cls.good): r['id']='finite-known:'+str(i)

    def run_backend(self, backend):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        out=Path(temp.name)/'phase'
        rows, summary=f.run(backend,self.counter,out,time.monotonic()+1200)
        return rows,summary,out

    def test_complete_original_phase_replays_but_scripted_fitness_cannot_select(self):
        backend=Backend(self.good);rows,summary,out=self.run_backend(backend)
        self.assertTrue(summary['complete']);self.assertFalse(summary['selection_passed'])
        self.assertEqual(len(backend.calls),8);self.assertEqual(len(backend.reservations),8)
        self.assertTrue((out/'qualification-evidence.json').exists())

    def test_unknown_usage_keeps_reservation_and_suppresses_complete_phase(self):
        backend=Backend([TimeoutError('synthetic timeout')]);rows,summary,out=self.run_backend(backend)
        self.assertEqual(len(backend.reservations),1);self.assertEqual(summary['unknown_usage_calls'],1)
        self.assertIsNone(rows[0]['generation_tokens']);self.assertFalse(summary['complete'])
        self.assertEqual(summary['uncalled_assignments'],7)
        self.assertFalse((out/'qualification-evidence.json').exists())

    def test_denial_and_expiry_never_call_or_refund(self):
        backend=Backend(self.good)
        with patch.object(backend,'reserve',side_effect=ValueError('denied')):
            rows,summary,_=self.run_backend(backend)
        self.assertEqual(backend.calls,[]);self.assertEqual(rows[0]['category'],'budget')
        backend=Backend(self.good)
        with patch.object(f.time,'monotonic',side_effect=[0,0,1,1000]):
            # Explicit original phase expires after reservation, before call.
            temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
            rows,summary=f.run(backend,self.counter,Path(temp.name)/'phase',10)
        self.assertEqual(backend.calls,[]);self.assertEqual(len(backend.reservations),1)

    def test_live_and_reused_archive_refused(self):
        backend=Backend(self.good);backend.scripted=False
        with self.assertRaises(ValueError):self.run_backend(backend)
        backend=Backend(self.good);_,_,out=self.run_backend(backend)
        with self.assertRaises(ValueError): f.run(backend,self.counter,out,time.monotonic()+1200)

    def test_duplicate_replies_and_actual_token_overrun_stop_without_new_attempt(self):
        replies=copy.deepcopy(self.good);replies[1]['id']=replies[0]['id']
        rows,summary,_=self.run_backend(Backend(replies))
        self.assertFalse(summary['complete']);self.assertEqual(summary['observed_calls'],2)
        self.assertEqual(rows[1]['category'],'provider')
        replies=copy.deepcopy(self.good);replies[0]['usage']['completion_tokens']=6001
        rows,summary,_=self.run_backend(Backend(replies))
        self.assertEqual(rows[0]['category'],'budget');self.assertFalse(rows[0]['unknown_usage'])
        self.assertEqual(summary['observed_calls'],1)


if __name__=='__main__':unittest.main()
