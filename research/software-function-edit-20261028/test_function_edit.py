import ast
import unittest
from function_edit import replace_function,FunctionEditEnvironment,FunctionEditAction,TARGETS

def definition(code,name):
    n=next(x for x in ast.parse(code).body if isinstance(x,ast.FunctionDef) and x.name==name)
    return ''.join(code.splitlines(keepends=True)[n.lineno-1:n.end_lineno])

class FunctionTests(unittest.TestCase):
    def env(self,task='software_repair-ignore-d3'):
        e=FunctionEditEnvironment();o=e.reset(task_id=task,seed=2400000);return e,o
    def test_reference_function_and_module_modes_use_same_full_grader(self):
        for task,target in TARGETS.items():
            e,o=self.env(task);ref=e._direct._task.reference_source
            a=e.step(FunctionEditAction(content=definition(ref,target)))
            e.reset(task_id=task,seed=2400000);b=e.step(FunctionEditAction(mode='module',content=ref))
            self.assertEqual(a.reward,1);self.assertEqual(a.reward,b.reward)
    def test_other_helpers_remain_byte_identical(self):
        e,o=self.env();ref=e._direct._task.reference_source;target=TARGETS[o.task_id]
        merged=replace_function(o.source,definition(ref,target),target)
        for n in ast.parse(o.source).body:
            if isinstance(n,ast.FunctionDef) and n.name!=target:
                self.assertEqual(definition(o.source,n.name),definition(merged,n.name))
    def test_invalid_target_multi_function_and_host_code_are_not_executed(self):
        for code in ['def unrelated(a): return a','import os','def classify_ignore(a,b): return {}\ndef extra(): return 1']:
            e,o=self.env();r=e.step(FunctionEditAction(content=code))
            self.assertTrue(r.done);self.assertEqual(r.reward,0);self.assertTrue(r.error)
    def test_zero_reward_unchanged_and_terminal_idempotence(self):
        e,o=self.env();r=e.step(FunctionEditAction(content=definition(o.source,TARGETS[o.task_id])))
        self.assertEqual(r.reward,0);self.assertTrue(r.done)
        self.assertEqual(e.step(FunctionEditAction(mode='module',content=e._direct._task.reference_source)),r)
        self.assertEqual(e.state.step_count,1)
    def test_same_existing_complete_source_byte_limit(self):
        e,o=self.env();r=e.step(FunctionEditAction(content='def classify_ignore(a,b):\n    return "'+'é'*4000+'"'))
        self.assertEqual(r.reward,0);self.assertTrue(r.error)
    def test_reset_scope_and_empty_finish(self):
        e,o=self.env();self.assertEqual(e.step(FunctionEditAction()).reward,0)
        e.reset(task_id='software_repair-ignore-d4',seed=2400001);self.assertEqual(e.state.step_count,0)
        with self.assertRaises(ValueError):e.reset(task_id='software_repair-ignore-d2')

if __name__=='__main__':unittest.main()
