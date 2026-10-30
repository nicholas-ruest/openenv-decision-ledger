import ast
import json
import unittest
from feedback_protocol import Trial, schedule
from repair_env.tasks import make_task


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_only_treatment_observation_has_public_runtime_locations(self):
        jobs = schedule('screen')[:2]
        trials = [Trial(j) for j in jobs]
        self.assertEqual(trials[0].messages, trials[1].messages)
        task = make_task(jobs[0]['task_id'], jobs[0]['seed'])
        tree = ast.parse(task.reference_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                node.body.insert(0, ast.parse('_probe = range([])').body[0])
        source = ast.unparse(ast.fix_missing_locations(tree))
        visible = {}
        for trial in trials:
            result = trial.consume(json.dumps(dict(content=source)))
            self.assertFalse(result['done'])
            self.assertEqual(result['native_reward'], 0)
            visible[trial.job['arm']] = json.loads(trial.native[0]['feedback'])
            final = trial.consume(json.dumps(dict(content=task.reference_source)))
            self.assertEqual(final['category'], 'full')
        control = visible['standard_review']
        treatment = visible['diagnostic_review']
        diagnostic = treatment.pop('source_diagnostic')
        self.assertEqual(treatment, control)
        self.assertEqual(diagnostic['scope'], 'supplied_public_examples_only')
        self.assertTrue(diagnostic['diagnostics'])
        self.assertTrue(all(d.get('call') == 'range' for d in diagnostic['diagnostics']))


if __name__ == '__main__':
    unittest.main()
