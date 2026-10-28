import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from prepare_review import build, canonical, request, sha, RevisionEnvironment, RevisionAction, SPLITS, ROOT


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.tmp.name) / 'first'
        cls.review = build(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_export_is_an_exact_native_reset_and_public_only(self):
        seen = set()
        for split, (start, count) in SPLITS.items():
            rows = [json.loads(s) for s in (self.output / (split + '.jsonl')).read_text().splitlines()]
            self.assertEqual(len(rows), 2 * count)
            for row in rows:
                self.assertEqual(set(row), {'task_id','seed','split','kind','observation','observation_sha256'})
                self.assertEqual(row['split'], split)
                self.assertIn(row['seed'], range(start, start + count))
                env = RevisionEnvironment()
                actual = env.reset(task_id=row['task_id'], seed=row['seed']).model_dump()
                self.assertEqual(row['observation'], actual)
                self.assertEqual(row['observation_sha256'], sha(canonical(actual).encode()))
                self.assertNotIn((row['task_id'], row['seed']), seen)
                seen.add((row['task_id'], row['seed']))
                self.assertNotIn('reference_source', actual)
                self.assertNotIn('hidden', actual)
        self.assertEqual(len(seen), 48)
        plan = json.loads((ROOT / 'research/software-public-check-20261028/revision-plan.json').read_text())
        for seeds in plan['seeds'].values():
            self.assertFalse({s for _, s in seen}.intersection(seeds))

    def test_exact_request_and_deterministic_source_manifest(self):
        second = build(Path(self.tmp.name) / 'second')
        self.assertEqual(self.review, second)
        req = json.loads((self.output / 'submission-candidate.json').read_text())
        self.assertEqual(req, request())
        self.assertEqual(self.review['request_sha256'], sha((self.output / 'submission-candidate.json').read_bytes()))
        with zipfile.ZipFile(self.output / 'environment-source.zip') as archive:
            self.assertEqual(set(archive.namelist()), set(self.review['source_file_sha256']))
            for name, expected in self.review['source_file_sha256'].items():
                self.assertEqual(sha(archive.read(name)), expected)
        for task in req['tasks']:
            self.assertEqual(task['tool_calls_total'], 2)
            self.assertEqual((task['completion_tokens'], task['context_tokens']), (8192, 24576))
            env = RevisionEnvironment(); env.reset(task_id=task['task_id'], seed=2363001)
            done = env.step(RevisionAction(**req['finish_action']))
            self.assertTrue(done.done); self.assertEqual(done.reward, 0)
        for key in ('approved', 'submitted', 'dataset_uploaded', 'fresh_model_confirmation', 'leaderboard_improvement'):
            self.assertIs(self.review[key], False)


if __name__ == '__main__':
    unittest.main()
