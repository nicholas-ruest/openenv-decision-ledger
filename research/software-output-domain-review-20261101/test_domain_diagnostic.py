"""Already-seen qualification task; no provider or fresh screen/confirmation case."""
import ast,copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import domain_diagnostic as d
from repair_env.tasks import make_task,compact_literal
from repair_env import ignore_repair as original

class DomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t=make_task('software_repair-ignore-d3',2560000)
        cls.observation=dict(task_id=t.task_id,examples=compact_literal([(c.args,c.expected) for c in t.public]))
        # Preserve correct explicit decisions while incorrectly exposing internal ancestors.
        cls.extra=original.REFERENCE.replace('    return result\n','    for entry in entries:\n        path = entry["path"]\n        for i in range(len(path)):\n            if path[i] == "/" and path[:i] not in result:\n                result[path[:i]] = False\n    return result\n')

    def test_valid_reference_and_wrong_decisions_are_not_semantic_proof(self):
        good=d.diagnose(self.observation,original.REFERENCE)
        self.assertEqual((good['program_evaluations'],good['violations']),(30,0))
        wrong='def classify_ignore(ignore_lines, entries):\n    return {entry["path"]: False for entry in entries}\n'
        value=d.diagnose(self.observation,wrong)
        self.assertEqual(value['violations'],0)
        self.assertFalse(value['semantic_correctness_established'])

    def test_internal_ancestor_keys_detected_without_expected_answers(self):
        value=d.diagnose(self.observation,self.extra)
        self.assertGreater(value['violations'],0)
        examples=ast.literal_eval(self.observation['examples'])
        changed=dict(self.observation,examples=repr([(x[0],None) for x in examples]))
        self.assertEqual(d.diagnose(changed,self.extra),value)
        self.assertFalse(value['reference_answers_used'])

    def test_derived_inputs_keep_real_contract_and_originals(self):
        before=copy.deepcopy(self.observation)
        probes=list(d.probes(self.observation));self.assertEqual(len(probes),30)
        for _,moved,(_,entries) in probes:
            self.assertEqual(len(entries),4);self.assertEqual(len({e['path'] for e in entries}),4)
            self.assertTrue(all(e['path'].isascii() and len(e['path'])<=40 and len(e['path'].split('/'))<=3 for e in entries))
            explicit={e['path']:e['is_dir'] for e in entries}
            self.assertTrue(all(explicit.get(e['path'][:i],True) for e in entries for i,c in enumerate(e['path']) if c=='/'))
            if moved is not None:self.assertNotIn(entries[moved]['path'].split('/')[0],explicit)
        d.diagnose(self.observation,self.extra)
        self.assertEqual(self.observation,before)

    def test_control_withholds_result_but_availability_is_common(self):
        control=d.review(self.observation,self.extra,'domain_reminder')
        treatment=d.review(self.observation,self.extra,'computed_domain')
        self.assertEqual(control['relation'],treatment['relation'])
        self.assertEqual(control['diagnostic']['kind'],'computed_result_withheld')
        self.assertGreater(treatment['diagnostic']['violations'],0)
        self.assertEqual(d.review(self.observation,'import os','domain_reminder'),d.review(self.observation,'import os','computed_domain'))
        mutation='def classify_ignore(ignore_lines, entries):\n    entries[0]["path"] = "changed"\n    return {}\n'
        self.assertEqual(d.diagnose(self.observation,mutation)['reason'],'runtime_rejected')

if __name__=='__main__':unittest.main()
