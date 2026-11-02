"""Failure-before-Native boundary; full successful binding needs actual supervision."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import case_qualification_supervisor as q

class CaseSupervisionTests(unittest.TestCase):
    def test_incomplete_supervision_never_imports_components_or_attests(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'phase';out.with_suffix('.supervision.jsonl').write_text(json.dumps({'event':'terminal','status':'timed_out'})+'\n')
            with patch.object(q.support,'require_source'),patch.object(q,'components',side_effect=AssertionError('Native import')):
                value=q.assess(out,'a'*40,None)
            self.assertFalse(value['complete']);self.assertFalse(value['scripted_supervisor_binding_verified'])
            self.assertFalse(value['live_worker_binding_qualified']);self.assertFalse(value['execution_authorized'])
            self.assertFalse(value['model_improvement'])

if __name__=='__main__':unittest.main()
