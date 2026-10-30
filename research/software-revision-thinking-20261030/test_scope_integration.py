"""Actual frozen protocol to actual assessor integration; fictional rows only."""
import json,subprocess,tempfile,unittest
from pathlib import Path
from caller import modules

class FrozenScopeIntegrationTests(unittest.TestCase):
    def test_actual_declared_jobs_are_accepted_and_other_seed_rejected(self):
        protocol,_=modules()
        bundle=dict(namespace=protocol.NAMESPACE,confirmation_observations_materialized=False,
                    screen_jobs=protocol.schedule('screen'),screen_groups=protocol.bundle(0)['screen_groups'])
        rows=[]
        for job in bundle['screen_jobs']:
            bound=protocol.capture(job)
            rows.append(dict(job,prompt_sha256=bound['prompt_sha256'],problem_sha256=bound['problem_sha256'],
                category='wrong',semantic_reward=0,terminal_reward_observed=0,generation_tokens=10,
                finish_reason='stop',call_id='fictional-call-'+job['attempt_id'],
                response_id='fictional-response-'+job['attempt_id'],
                reservation_label='fictional-reservation-'+job['attempt_id'],scripted=True))
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp)/'fictional.json'
            assessor=Path(__file__).with_name('assess.mjs').as_uri()
            js=('import {readFileSync} from "node:fs";import {assess} from '+json.dumps(assessor)+';'
                'const x=JSON.parse(readFileSync('+json.dumps(str(data))+'));'
                'const r=assess(x.bundle,x.rows);if(r.attempts!==8||r.screen_selection_passed)throw Error("fictional tie must fail selection");')
            data.write_text(json.dumps(dict(bundle=bundle,rows=rows)))
            good=subprocess.run(['node','--input-type=module','-e',js],capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr)
            bundle['screen_jobs'][0]['seed']+=12345
            data.write_text(json.dumps(dict(bundle=bundle,rows=rows)))
            bad=subprocess.run(['node','--input-type=module','-e',js],capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn('frozen screen task/seed scope required',bad.stderr)

if __name__=='__main__':unittest.main()
