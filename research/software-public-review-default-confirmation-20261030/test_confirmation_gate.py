"""Fictional refusal fixtures; never materialize reserved confirmation cases."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from confirmation_gate import verify_gate,method_unchanged,roles
class ConfirmationAdmissionTests(unittest.TestCase):
 def attempt(self,value,expected=None):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'gate.json';p.write_text(json.dumps(value))
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   return verify_gate(p,expected if expected is not None else digest)
 def test_missing_or_changed_lease_refused(self):
  with self.assertRaises(ValueError):self.attempt({},'0'*64)
 def test_fictional_positive_flag_without_source_is_not_evidence(self):
  with self.assertRaises(ValueError):self.attempt({'selection_passed':True})
 def test_complete_unique_inventory_is_required(self):
  with self.assertRaises(ValueError):self.attempt(dict(kind='independently-replayed-screen-selection',screen_source='33c0c708e823bd42ae9de8150c025c78d5c8fe5b',inventory=[]))
 def test_changed_artifacts_refused_before_any_native_case(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'fictional';p.write_text('fictional')
   inventory=[dict(role=r,path=str(p),sha256='0'*64) for r in roles()]
   with self.assertRaises(ValueError):self.attempt(dict(kind='independently-replayed-screen-selection',screen_source='33c0c708e823bd42ae9de8150c025c78d5c8fe5b',inventory=inventory))
 def test_trial_sampling_and_native_intervention_are_identical(self):
  method_unchanged()
if __name__=='__main__':unittest.main()
