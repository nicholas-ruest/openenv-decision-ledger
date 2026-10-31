"""Analyzer regression: an empty first action must never reach Native grading."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import posthoc_public_review as audit


class EmptyActionTests(unittest.TestCase):
    def test_empty_first_actions_are_excluded_before_trial_consume(self):
        class Action:
            @staticmethod
            def model_validate_json(text, strict):
                assert strict is True
                return SimpleNamespace(content=json.loads(text)['content'])

        class Trial:
            action_type = Action
            messages = []
            def consume(self, text):
                raise AssertionError('empty action would invoke a hidden final grade')

        def bundle(i):
            return dict(confirmation_jobs=[dict(attempt_id=f'{i}-{arm}', arm=arm, sample=i)
                                           for arm in ('a', 'b')])

        protocol = SimpleNamespace(bundle=bundle, Trial=lambda job: SimpleNamespace(policy=SimpleNamespace(trial=Trial())),
            configure_gate=lambda *args: None,
            digest=lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest())
        caller = SimpleNamespace(modules=lambda: (protocol, None), load=lambda *args: None)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'assessment.json').write_text(json.dumps(dict(attempts=8, all_live_replies_verified=True)))
            for i in range(4):
                c = root/f'chunk{i}'
                (c/'live').mkdir(parents=True)
                (c/'inputs.json').write_text(json.dumps(bundle(i)))
                (c/'independent-verification.json').write_text(json.dumps(dict(clean_shutdown=True, all_workers_stopped=True)))
                (c/'live/complete.json').write_text(json.dumps(dict(scripted=False, assigned_attempts=2, recorded_attempts=2)))
                events = [dict(event='response', attempt_id=job['attempt_id'], turn=0,
                    response=dict(choices=[dict(finish_reason='stop', message=dict(content='{"content":""}'))]))
                    for job in bundle(i)['confirmation_jobs']]
                (c/'live/events.jsonl').write_text('\n'.join(json.dumps(x) for x in events))
            args = SimpleNamespace(source_root=root, expected_source='expected', archive=root,
                assessment_sha256=audit.sha(root/'assessment.json'), screen_gate=root/'unused', screen_gate_sha256='unused')
            with patch.dict('sys.modules', caller=caller), patch.object(audit.subprocess, 'check_output', side_effect=['expected\n', '']):
                result = audit.run(args)
            self.assertEqual(result['skip_reasons'], {'no_nonempty_source_proposal': 8})
            self.assertEqual(result['eligible_complete_proposals'], 0)
            self.assertEqual(result['public_field_review_unavailable'], 8)
            self.assertFalse(result['hidden_final_grades_consulted'])


if __name__ == '__main__':
    unittest.main()
