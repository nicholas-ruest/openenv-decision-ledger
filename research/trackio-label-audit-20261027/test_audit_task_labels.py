import copy
import unittest
from audit_task_labels import audit,allowlists,event_step_audit
SOURCE="STRING_CONFIG = {'run_id','model','recipe'}\nNUMBER_CONFIG = {'train_tasks'}"
class AuditTests(unittest.TestCase):
    def setUp(self):
        self.logs=[{'step':1,'step/task':2,'reward':.5},{'step':3,'step/task':1,'reward':1}]
        self.summary={'num_logs':2,'config':{'train_tasks':2}}
        self.records={'reward':[{'step':3,'value':1},{'step':1,'value':.5}]}
    def run_audit(self):return audit(self.summary,self.logs,self.records,SOURCE)
    def test_numeric_only_stays_unknown(self):
        x=self.run_audit();self.assertFalse(x['mapping_complete']);self.assertEqual(x['explicit_task_labels'],{});self.assertEqual(x['metric_values_cross_checked'],2)
    def test_task_list_never_infers_numeric_order(self):
        self.summary['config']['tasks']=['name1','name2'];self.assertFalse(self.run_audit()['mapping_complete'])
    def test_explicit_mapping_accepted(self):
        self.summary['config']['task_id_map']={'1':'a','2':'b'};self.assertTrue(self.run_audit()['mapping_complete'])
    def test_per_step_explicit_labels(self):
        self.logs[0]['step/task_name']='b';self.logs[1]['step/task_name']='a';self.assertTrue(self.run_audit()['mapping_complete'])
    def test_incomplete_map_rejected(self):
        self.summary['config']['task_id_map']={'1':'a'}
        with self.assertRaises(ValueError):self.run_audit()
    def test_conflicting_names_rejected(self):
        self.logs[0]['step/task_name']='other';self.summary['config']['task_id_map']={'1':'a','2':'b'}
        with self.assertRaises(ValueError):self.run_audit()
    def test_duplicate_step_rejected(self):
        self.logs[1]['step']=1
        with self.assertRaises(ValueError):self.run_audit()
    def test_raw_metric_mismatch_rejected(self):
        self.records['reward'][0]['value']=0
        with self.assertRaises(ValueError):self.run_audit()
    def test_missing_metric_not_zero(self):
        self.records['reward'].pop()
        with self.assertRaises(ValueError):self.run_audit()
    def test_summary_count_mismatch(self):
        self.summary['num_logs']=3
        with self.assertRaises(ValueError):self.run_audit()
    def test_ast_source_never_executed(self):
        x=allowlists(SOURCE+"\nraise RuntimeError('must not execute')")
        self.assertEqual(x['NUMBER_CONFIG'],['train_tasks'])
    def test_alert_steps_do_not_shift_to_optimizer_steps(self):
        x=event_step_audit([{'step':65},{'step':65},{'step':133},{'step':133}],[{'step':66,'step/retries':1},{'step':134,'step/retries':1}])
        self.assertEqual(x['alert_rows'],4);self.assertEqual(x['optimizer_retry_steps'],[66,134]);self.assertEqual(x['same_number_overlap'],[]);self.assertIsNone(x['alert_to_task_attribution']);self.assertFalse(x['inferred_offset_applied'])
    def test_duplicate_names_not_bijective(self):
        self.summary['config']['task_id_map']={'1':'same','2':'same'}
        with self.assertRaises(ValueError):self.run_audit()
    def test_boolean_task_id_rejected(self):
        self.logs[0]['step/task']=True
        with self.assertRaises(ValueError):self.run_audit()

if __name__=='__main__':unittest.main()
