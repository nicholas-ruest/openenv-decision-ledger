"""Already-used Native case3100000 only; scripted controls, no model requests."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'research/software-helper-controller-20261031')]
import matched_protocol as helper
from action_example_protocol import Trial,schedule
from failure_advice import FailureAdviceTrial,failed_public_review,observation_tokens,canonical,materialize


def trial(arm):return FailureAdviceTrial(Trial(schedule('screen')[0]),arm=arm)


class AdviceTests(unittest.TestCase):
    def test_native_failed_proposal_changes_only_revision_advice(self):
        baseline=trial('standard_revision');treatment=trial('focused_failure_advice')
        self.assertEqual(baseline.messages,treatment.messages)
        source=json.loads(baseline.messages[1]['content'])['source']
        reply=json.dumps(dict(content=source))
        a=baseline.consume(reply,finish_reason='stop');b=treatment.consume(reply,finish_reason='stop')
        self.assertEqual(a['new_observations'],b['new_observations']);self.assertFalse(a['done'])
        self.assertFalse(a['advice_delivered']);self.assertTrue(b['advice_delivered'])
        self.assertEqual(treatment.messages[:-1],baseline.messages)
        self.assertEqual(b['controller_actions'],[])
        self.assertEqual(observation_tokens(b,len),sum(len(canonical(x)) for x in b['new_observations'])+len(treatment.messages[-1]['content']))
        # Advice never changes submitted source or the unchanged terminal grader.
        a=baseline.consume('{"content":""}',finish_reason='stop');b=treatment.consume('{"content":""}',finish_reason='stop')
        self.assertEqual(a['new_observations'],b['new_observations']);self.assertEqual(a['category'],b['category'])
        self.assertEqual(a['semantic_reward'],b['semantic_reward']);self.assertFalse(b['advice_delivered'])
        with self.assertRaises(ValueError):treatment.consume('{"content":""}',finish_reason='stop')

    def test_native_public_passing_proposal_receives_no_advice_or_finalization(self):
        from repair_env.tasks import make_task
        t=trial('focused_failure_advice');reply=json.dumps(dict(content=make_task(helper.TASK,3100000).reference_source))
        result=t.consume(reply,finish_reason='stop')
        self.assertFalse(result['done']);self.assertFalse(result['advice_delivered']);self.assertEqual(t.calls,1)
        result=t.consume('{"content":""}',finish_reason='stop');self.assertEqual(result['category'],'full')

    def test_truncation_format_and_empty_first_action_never_trigger_advice(self):
        t=trial('focused_failure_advice');before=t.messages
        with self.assertRaises(ValueError):t.consume('partial',finish_reason='length')
        self.assertEqual(t.messages,before);self.assertEqual(t.calls,0)
        result=t.consume('not-json',finish_reason='stop');self.assertTrue(result['done']);self.assertFalse(result['advice_delivered'])
        t=trial('focused_failure_advice');result=t.consume('{"content":""}',finish_reason='stop')
        self.assertTrue(result['done']);self.assertFalse(result['advice_delivered'])

    def test_hidden_unlabelled_malformed_or_passing_fields_cannot_trigger(self):
        review=dict(kind='public_field_check',public_only=True,hidden_access=False,passed=0,total=6)
        obs=dict(done=False,stage='revision',feedback=review)
        self.assertTrue(failed_public_review(obs))
        for field,value in [('public_only',False),('hidden_access',True),('passed',True),('passed',6),('passed',-1),('total',0),('kind','other')]:
            bad=copy.deepcopy(obs);bad['feedback'][field]=value
            with self.subTest(field=field,value=value):self.assertFalse(failed_public_review(bad))
        self.assertFalse(failed_public_review(dict(obs,done=True)))
        self.assertFalse(failed_public_review(dict(obs,feedback='invalid')))

    def test_actual_tokenizer_counts_the_emitted_advice_receipt(self):
        import argparse,importlib.util,os
        spec=importlib.util.spec_from_file_location('failure_advice_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        counter=m.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        t=trial('focused_failure_advice');source=json.loads(t.messages[1]['content'])['source']
        result=t.consume(json.dumps(dict(content=source)),finish_reason='stop')
        extra=counter.count(t.messages[-1]['content']);self.assertGreater(extra,0)
        self.assertEqual(observation_tokens(result,counter.count),sum(counter.count(canonical(x)) for x in result['new_observations'])+extra)

    def test_live_materialization_remains_blocked(self):
        with self.assertRaises(ValueError):materialize('screen')


if __name__=='__main__':unittest.main()
