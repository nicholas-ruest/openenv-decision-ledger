import unittest
from token_audit import costs, canonical

class Counter:
    def count(self,s):return len(s)
    def context(self,m):return self.count(canonical(m))

def frame(done=False,payload=''):
    return {'type':'observation','data':{'done':done,'observation':{'feedback':payload}}}

class CostTests(unittest.TestCase):
    def test_terminal_observation_is_charged_and_reset_excluded(self):
        c=Counter();a=[{'content':'x'},{'submit':True}];o=[frame(),frame(True,'terminal'*40)]
        v=costs(c,frame(payload='reset'*100),a,o)
        self.assertEqual(v['completion_total'],sum(c.count(canonical(x)) for x in a+o))
        self.assertEqual(v['final_observation_tokens'],c.count(canonical(o[-1])))
        self.assertEqual(v['reset_completion_tokens'],0)
        small=costs(c,frame(),a,o)
        self.assertEqual(v['completion_total'],small['completion_total'])
        self.assertGreater(v['context_max'],small['context_max'])
    def test_transport_and_data_are_distinct(self):
        v=costs(Counter(),frame(),[{},{}],[frame(),frame(True)])
        self.assertTrue(all(a>b for a,b in zip(v['postreset_frame_tokens'],v['postreset_data_tokens'])))
    def test_incomplete_or_nonterminal_trajectory_is_not_costed_as_complete(self):
        for actions,obs in [([{}],[frame(True)]),([{},{}],[frame(),frame()])]:
            with self.assertRaises(ValueError):costs(Counter(),frame(),actions,obs)

if __name__=='__main__':unittest.main()
