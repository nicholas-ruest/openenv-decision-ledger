"""Only actual Native first-review feedback can attest advice exposure."""
import json,tempfile,time,unittest
from pathlib import Path
import test_caller as scripted
from caller import phase
from assemble import verify_chunk,advice_exposure
class ExposureTests(unittest.TestCase):
 def test_scripted_replay_distinguishes_passed_and_failed_public_proposals(self):
  scripted.NativeFeedbackTests.setUpClass();p=scripted.NativeFeedbackTests.protocol;counter=scripted.NativeFeedbackTests.counter
  for reference,expected in [(False,0),(True,1)]:
   with tempfile.TemporaryDirectory() as tmp:
    output=Path(tmp)/'live';b=scripted.ScriptedBackend(counter,early=reference)
    rows=phase(p.bundle(0),p.digest(p.bundle(0)),output,b,counter,time.monotonic()+60)
    events=[json.loads(x) for x in (output/'events.jsonl').read_text().splitlines()]
    verify_chunk(p.bundle(0),rows,events,counter)
    self.assertEqual(advice_exposure([output]),dict(standard_review=0,retain_review=expected))
if __name__=='__main__':unittest.main()
