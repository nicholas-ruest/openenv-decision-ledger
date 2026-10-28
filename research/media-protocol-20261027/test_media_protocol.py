import copy
import unittest
from media_protocol import IMAGE,RUNTIME,SEEDS,FAMILIES,build,digest

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.schema={'action':{'type':'object'},'observation':{'type':'object'}};self.rows=[]
        for phase,tasks in SEEDS.items():
            for task,seeds in tasks.items():
                for position,seed in enumerate(seeds):
                    for repeat in range(2):
                        self.rows.append({'phase':phase,'task_id':task,'seed':seed,'repeat':repeat,'family':FAMILIES[task][position],'image':IMAGE,'runtime_source':RUNTIME,'uid_shell':True,'reset_transport':{'done':False,'reward':0,'observation':{'success':True,'instruction':f'{task}:{seed}'}},'workspace':{'input.json':{'sha256':digest(f'{task}:{seed}'),'bytes':10}}})
    def run_plan(self):return build(self.rows,self.schema)
    def test_complete_offline_identity_plan(self):
        p=self.run_plan();self.assertEqual(p['native_reset_controls'],16);self.assertFalse(p['budget_admitted']);self.assertFalse(p['model_phase_executed']);self.assertEqual(p['phases']['screen']['future_rollouts'],16)
    def test_missing_capture(self):
        self.rows.pop()
        with self.assertRaises(ValueError):self.run_plan()
    def test_duplicate_capture(self):
        self.rows[-1]=copy.deepcopy(self.rows[0])
        with self.assertRaises(ValueError):self.run_plan()
    def test_prompt_nondeterminism(self):
        self.rows[1]['reset_transport']['observation']['instruction']='changed'
        with self.assertRaises(ValueError):self.run_plan()
    def test_workspace_nondeterminism(self):
        self.rows[1]['workspace']['input.json']['sha256']='f'*64
        with self.assertRaises(ValueError):self.run_plan()
    def test_wrong_image(self):
        self.rows[0]['image']='other'
        with self.assertRaises(ValueError):self.run_plan()
    def test_disabled_shell(self):
        self.rows[0]['uid_shell']=False
        with self.assertRaises(ValueError):self.run_plan()
    def test_family_mismatch(self):
        self.rows[0]['family']='assets'
        with self.assertRaises(ValueError):self.run_plan()
    def test_cross_phase_case_leakage(self):
        for i in (8,9):self.rows[i]['workspace']=copy.deepcopy(self.rows[0]['workspace'])
        with self.assertRaises(ValueError):self.run_plan()
    def test_bad_digest(self):
        self.rows[0]['workspace']['input.json']['sha256']='short'
        with self.assertRaises(ValueError):self.run_plan()
    def test_failed_reset(self):
        self.rows[0]['reset_transport']['done']=True
        with self.assertRaises(ValueError):self.run_plan()

if __name__=='__main__':unittest.main()
