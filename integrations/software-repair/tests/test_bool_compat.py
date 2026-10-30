"""Static CPython compatibility controls; never execute model text on the host."""
import copy
import unittest
from repair_env.runner import Program,Rejected

class BoolCompatibilityTests(unittest.TestCase):
 def test_supported_json_values_match_cpython(self):
  program=Program('def solve(value):\n    return bool(value)\n')
  for value in [None,False,True,0,1,-2,'','x',[],[False],{}, {'x':False}]:
   with self.subTest(value=value):
    before=copy.deepcopy(value)
    self.assertIs(program.run('solve',[value]),bool(value))
    self.assertEqual(value,before)
 def test_zero_arguments_and_truthiness_is_not_length_iteration(self):
  self.assertIs(Program('def solve():\n    return bool()\n').run('solve',[]),False)
  self.assertIs(Program('def solve():\n    return bool(x for x in [])\n').run('solve',[]),True)
 def test_arity_matches_python_and_keywords_still_rejected(self):
  with self.assertRaises(TypeError):Program('def solve():\n    return bool(1,2)\n').run('solve',[])
  with self.assertRaises(Rejected):Program('def solve():\n    return bool(x=1)\n').run('solve',[])
 def test_no_first_class_host_type_or_attribute_access(self):
  for source in ['def solve():\n    return bool\n','def solve():\n    return bool.__class__\n']:
   with self.subTest(source=source):
    with self.assertRaises(Rejected):Program(source).run('solve',[])
 def test_local_value_named_bool_is_not_a_host_callable(self):
  source='def solve(value):\n    bool=7\n    return bool(value)\n'
  with self.assertRaises(Rejected):Program(source).run('solve',[1])
 def test_user_function_shadowing_is_unchanged(self):
  source='def bool(value):\n    return 7\ndef solve():\n    return bool(False)\n'
  self.assertEqual(Program(source).run('solve',[]),7)
if __name__=='__main__':unittest.main()
