import unittest
from candidate import load_pair

class DepthCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old,cls.new=load_pair()
    def test_small_acyclic_mapping_reproducer_and_list_contrast(self):
        mapping='def f():\n    x = {"a":{"b":{"c":{"d":{"e":0}}}}}\n    return 1\n'
        sequence='def f():\n    x = [[[[[0]]]]]\n    return 1\n'
        with self.assertRaisesRegex(self.old.Rejected,'value nesting'):self.old.Program(mapping).run('f',[])
        self.assertEqual(self.new.Program(mapping).run('f',[]),1)
        self.assertEqual(self.old.Program(sequence).run('f',[]),1);self.assertEqual(self.new.Program(sequence).run('f',[]),1)
    def test_logical_depth_eight_allowed_nine_rejected(self):
        for wrap in (lambda x:[x],lambda x:{'x':x}):
            value=0
            for _ in range(8):value=wrap(value)
            self.new.bounded(value)
            with self.assertRaisesRegex(self.new.Rejected,'value nesting'):self.new.bounded(wrap(value))
    def test_existing_size_numeric_cycle_and_step_protections(self):
        for module in (self.old,self.new):
            for v in ([0]*129,'x'*2049,1<<128,float('inf')):
                with self.assertRaises(module.Rejected):module.bounded(v)
            cycle=[];cycle.append(cycle)
            with self.assertRaises(module.Rejected):module.bounded(cycle)
            with self.assertRaises(module.Rejected):module.Program('def f():\n    while True:\n        pass\n').run('f',[])
    def test_resource_constants_and_source_limit_unchanged(self):
        for name in ('MAX_SOURCE','MAX_ITEMS','MAX_STRING','MAX_STEPS','MAX_AST_NODES'):self.assertEqual(getattr(self.old,name),getattr(self.new,name))
        for module in (self.old,self.new):
            with self.assertRaisesRegex(module.Rejected,'source size'):module.Program(' '*8193)
if __name__=='__main__':unittest.main()
