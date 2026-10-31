"""Offline assignment tests only. These fixtures are not Native/model results."""
import copy
import json
import unittest
from unittest.mock import patch
import action_example_protocol as protocol


class PlanTests(unittest.TestCase):
    def test_planning_never_materializes_native_or_confirmation(self):
        with patch.object(protocol, 'Trial', side_effect=AssertionError('no capture')):
            value = protocol.plan()
        self.assertFalse(value['confirmation_observations_materialized'])
        self.assertFalse(value['case_disjointness_verified'])
        self.assertFalse(value['paid_execution_ready'])
        for phase in ('screen', 'confirmation'):
            jobs = value[phase + '_jobs']
            self.assertEqual(len(jobs), 8)
            self.assertEqual(len({j['attempt_id'] for j in jobs}), 8)
            self.assertEqual({j['sample'] for j in jobs}, set(range(4)))
        self.assertTrue(set(j['attempt_id'] for j in value['screen_jobs']).isdisjoint(
            j['attempt_id'] for j in value['confirmation_jobs']))

    def test_original_order_alternates_and_identity_rejects_mutations(self):
        for phase in ('screen', 'confirmation'):
            jobs = protocol.schedule(phase)
            for sample in range(4):
                expected = list(protocol.ARMS if sample % 2 == 0 else reversed(protocol.ARMS))
                self.assertEqual([j['arm'] for j in jobs if j['sample'] == sample], expected)
            for key, bad in [('seed', 1), ('task_id', 'wrong'), ('arm', 'unbound'),
                             ('attempt_id', '0' * 64), ('sample', 8), ('sample', False),
                             ('seed', True), ('phase', []), ('phase', None)]:
                job = copy.deepcopy(jobs[0]); job[key] = bad
                with self.assertRaises(ValueError):
                    protocol.checked_job(job)

    def test_identical_sampler_budgets_and_no_mutable_global_leak(self):
        value = protocol.plan()
        self.assertEqual((value['max_calls'], value['first_generation_limit'],
                          value['completion_with_observations'], value['context'],
                          value['reserved_final_observation_tokens'], value['retries']),
                         (16, 6000, 8192, 24576, 96, 0))
        for job in value['screen_jobs'] + value['confirmation_jobs']:
            a = protocol.sampling_for(job, 0)
            self.assertEqual(a, protocol.sampling_for(job, 1))
            self.assertNotIn('chat_template_kwargs', a)
            a['temperature'] = 9
            self.assertEqual(protocol.sampling_for(job, 0)['temperature'], 0.7)
            for turn in (True, -1, 2, None):
                with self.assertRaises(ValueError): protocol.sampling_for(job, turn)

    def test_reserved_confirmation_and_invalid_chunks_refuse_before_native_import(self):
        with patch.object(protocol, 'Trial', side_effect=AssertionError('must not capture')):
            with self.assertRaisesRegex(ValueError, 'confirmation'):
                protocol.capture(protocol.schedule('confirmation')[0])
            for chunk in (True, -1, 4, None, '0'):
                with self.assertRaises(ValueError): protocol.bundle(chunk)
        with self.assertRaisesRegex(ValueError, 'separate selected and attested'):
            protocol.Trial(protocol.schedule('confirmation')[0])

    def test_bundle_binds_all_jobs_and_only_requested_chunk_without_claiming_native_validation(self):
        # Hash-only fixture deliberately bypasses Native generation. This verifies
        # assignment assembly, not prompt equality, execution, or model performance.
        def fixture(job):
            return dict(messages=[], prompt_sha256=protocol.digest(job['arm']),
                        problem_sha256=protocol.digest('fictional-problem'))
        with patch.object(protocol, 'capture', side_effect=fixture):
            bundles = [protocol.bundle(i) for i in range(4)]
        self.assertEqual([j for b in bundles for j in b['screen_jobs']], protocol.schedule('screen'))
        self.assertTrue(all(len(b['screen_jobs']) == 2 for b in bundles))
        self.assertTrue(all(not b['case_disjointness_verified'] for b in bundles))
        self.assertTrue(all(json.loads(json.dumps(b)) == b for b in bundles))


if __name__ == '__main__': unittest.main()
