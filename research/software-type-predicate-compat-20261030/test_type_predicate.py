"""Trusted static CPython controls; no model source is executed by host Python."""
import copy
import importlib.util
from pathlib import Path
import unittest

target=Path(__file__).with_name('runner.py')
if not target.exists():
    target=Path(__file__).resolve().parents[2]/'integrations/software-repair/repair_env/runner.py'
spec=importlib.util.spec_from_file_location('type_candidate',target)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Program,Rejected=module.Program,module.Rejected

class TypePredicateTests(unittest.TestCase):
    def compare(self,source,value):
        trusted={}
        exec(source,trusted)
        self.assertEqual(Program(source).run('solve',[value]),trusted['solve'](copy.deepcopy(value)))

    def test_supported_types_match_cpython(self):
        for tag in ('bool','int','str','list','tuple','dict','set'):
            for value in (True,3,'x',[1],(1,),{'x':1},{1},None):
                self.compare('def solve(x):\n return isinstance(x,'+tag+')\n',value)

    def test_bool_int_subclass_semantics(self):
        self.assertTrue(Program('def solve(x):\n return isinstance(x,int)\n').run('solve',[True]))
        self.assertFalse(Program('def solve(x):\n return isinstance(x,bool)\n').run('solve',[1]))

    def test_nested_and_empty_type_tuples(self):
        for value in (1,'x',[1],None):
            self.compare('def solve(x):\n return (isinstance(x,()),isinstance(x,(str,(tuple,list))))\n',value)

    def test_value_expression_evaluated_once(self):
        source=('def get_value(xs):\n xs.append(1)\n return xs\n'
                'def solve(x):\n trace=[]\n ok=isinstance(get_value(trace),list)\n return (ok,len(trace))\n')
        self.compare(source,None)

    def test_dynamic_unknown_and_first_class_types_rejected(self):
        expressions=('isinstance(x,object)','isinstance(x,"int")','isinstance(x,[int])',
                     'isinstance(x,type(1))','isinstance(x,(int,object))','tuple',
                     'isinstance(x)','isinstance(x,int,bool)')
        for expression in expressions:
            with self.subTest(expression=expression),self.assertRaises(Rejected):
                Program('def solve(x):\n return '+expression+'\n').run('solve',[1])

    def test_shadowed_type_names_rejected(self):
        with self.assertRaises(Rejected):
            Program('def solve(x):\n int=3\n return isinstance(x,int)\n').run('solve',[1])
        with self.assertRaises(Rejected):
            Program('def int(x):\n return x\ndef solve(x):\n return isinstance(x,int)\n').run('solve',[1])

    def test_step_limit_remains(self):
        with self.assertRaises(Rejected):
            Program('def loop(x):\n while True:\n  x=x\n return x\ndef solve(x):\n return isinstance(loop(x),int)\n').run('solve',[1])

    def test_input_mutation_guard_remains(self):
        value=[1]
        with self.assertRaises(Rejected):
            Program('def solve(x):\n x.append(2)\n return isinstance(x,list)\n').run('solve',[value])
        self.assertEqual(value,[1])

if __name__=='__main__':unittest.main()
