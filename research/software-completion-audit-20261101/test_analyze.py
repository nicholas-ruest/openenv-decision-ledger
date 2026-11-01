import copy,json,math,unittest
from pathlib import Path
from analyze import analyze

class AuditTests(unittest.TestCase):
    def setUp(self):self.rows=json.loads(Path(__file__).with_name('numeric-records.json').read_text())
    def test_preserved_numeric_evidence_keeps_unattested_semantics_unknown(self):
        v=analyze(self.rows)
        self.assertEqual(v['all_updates']['updates'],148)
        self.assertEqual(v['all_updates']['clip_one_updates'],134)
        self.assertEqual(v['all_updates']['clip_one_with_reward_one'],10)
        self.assertEqual(v['zero_retry_updates']['updates'],146)
        self.assertTrue(all(g['task_name'] is None for g in v['numeric_groups'].values()))
        self.assertFalse(v['provider_finish_reasons_available']);self.assertFalse(v['total_rollout_count_inferred'])
    def test_missing_nonfinite_or_duplicate_step_cannot_be_silent_zero(self):
        for kind in ('missing','nan','duplicate','bool','range'):
            rows=copy.deepcopy(self.rows)
            if kind=='missing':del rows[0]['completions/clipped_ratio']
            elif kind=='nan':rows[0]['reward']=math.nan
            elif kind=='duplicate':rows[1]['step']=rows[0]['step']
            elif kind=='bool':rows[0]['step/task']=True
            else:rows[0]['completions/clipped_ratio']=1.1
            with self.subTest(kind=kind),self.assertRaises(ValueError):analyze(rows)
    def test_incomplete_reordered_or_inconsistent_lengths_are_refused(self):
        with self.assertRaises(ValueError):analyze(self.rows[:-1])
        with self.assertRaises(ValueError):analyze(self.rows[::-1])
        self.rows[0]['completions/mean_length']=self.rows[0]['completions/max_length']+1
        with self.assertRaises(ValueError):analyze(self.rows)

if __name__=='__main__':unittest.main()
