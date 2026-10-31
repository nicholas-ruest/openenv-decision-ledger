"""Confirmation selection/assignment leases reject altered or absent evidence."""
import json
from pathlib import Path
import tempfile
import unittest
import feedback_protocol as p


class BindingTests(unittest.TestCase):
    def test_selected_screen_and_original_reservation_are_bound(self):
        selected=p.check_selection()
        self.assertTrue(selected['selection_passed'])
        self.assertEqual(p.reserved_jobs(),p.schedule('confirmation'))
        self.assertEqual({j['seed'] for j in p.reserved_jobs()},{3070000})
        self.assertTrue(all(j['phase']=='confirmation' for j in p.reserved_jobs()))

    def test_changed_selection_and_jobs_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'changed.json'
            for name,check in [('screen-selection.json',p.check_selection),
                               ('reserved-confirmation-jobs.json',p.reserved_jobs)]:
                original=Path(__file__).with_name(name).read_text()
                f.write_text(original+' ')
                with self.assertRaises(ValueError):
                    check(f)

    def test_missing_or_forged_case_audit_cannot_admit_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'audit.json'
            with self.assertRaises(FileNotFoundError):
                p.check_case_audit(f)
            f.write_text(json.dumps(dict(verified=True,input_overlap=0,prior_cases=44)))
            with self.assertRaises(ValueError):
                p.check_case_audit(f)


if __name__=='__main__':
    unittest.main()
