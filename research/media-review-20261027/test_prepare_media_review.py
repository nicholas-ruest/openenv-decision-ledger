import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from copy import deepcopy

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review',HERE/'prepare-media-review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
EVIDENCE=HERE/'fixtures/evidence'
UPSTREAM=HERE/'fixtures/upstream-request-v7.json'

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.e=self.root/'evidence';self.e.mkdir()
        for p in EVIDENCE.iterdir():
            (self.e/p.name).write_bytes(p.read_bytes())
        self.up=json.loads(UPSTREAM.read_text())
    def test_exact_schema_tasks_and_limits(self):
        r=m.request(self.e,self.up)
        self.assertEqual([t['task_id'] for t in r['tasks']],list(m.TASKS))
        self.assertEqual(r['schema'],self.up['schema'])
        self.assertEqual(r['tasks'],[t for t in self.up['tasks'] if t['task_id'] in m.TASKS])
    def test_wrong_image_rejected(self):
        (self.e/'image.txt').write_text(m.IMAGE+'x')
        with self.assertRaises(AssertionError):m.request(self.e,self.up)
    def test_source_drift_rejected(self):
        (self.e/'source.txt').write_text('other')
        with self.assertRaises(AssertionError):m.request(self.e,self.up)
    def test_schema_drift_rejected(self):
        self.up['schema']['action']['properties']['action_type']['enum'].append('other')
        with self.assertRaises(AssertionError):m.request(self.e,self.up)
    def test_unprivileged_shell_required(self):
        d=json.loads((self.e/'anonymous-tcp.json').read_text());d['uid_shell']=False;(self.e/'anonymous-tcp.json').write_text(json.dumps(d))
        with self.assertRaises(AssertionError):m.request(self.e,self.up)
    def test_output_never_overwrites_and_unapproved(self):
        o=self.root/'packet';a=m.prepare(self.e,self.up,o)
        self.assertFalse(a['approved']);self.assertFalse(a['submitted']);self.assertFalse(a['dataset_replaced'])
        with self.assertRaises(ValueError):m.prepare(self.e,self.up,o)
    def test_task_budget_drift_rejected(self):
        for t in self.up['tasks']:
            if t['task_id'] in m.TASKS:t['completion_tokens']=2048
        with self.assertRaises(AssertionError):m.request(self.e,self.up)

if __name__=='__main__':unittest.main()
