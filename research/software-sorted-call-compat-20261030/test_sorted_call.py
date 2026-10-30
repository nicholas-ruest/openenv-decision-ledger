"""Trusted CPython differentials for sorted(key=...), no model execution on host."""
import unittest,copy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'integrations/software-repair'))
from repair_env.runner import Program,Rejected

class SortedCallTests(unittest.TestCase):
 def compare(self,source,value):
  reference={};exec(source,reference)
  original=copy.deepcopy(value)
  actual=Program(source).run('solve',[value])
  self.assertEqual(actual,reference['solve'](copy.deepcopy(value)))
  self.assertEqual(value,original)
 def test_stable_lambda_reverse_and_closure(self):
  for reverse in ('True','False','1','0'):
   self.compare('def solve(xs):\n factor=-1\n return sorted(xs,key=lambda x: factor*x[0],reverse='+reverse+')\n',[[2,'a'],[1,'b'],[2,'c']])
 def test_sorted_returns_copy_and_list_sort_stays_in_place(self):
  self.compare('def solve(xs):\n out=sorted(xs,key=abs)\n return [xs,out]\n',[-3,1,-1,2])
  self.compare('def solve(xs):\n out=list(xs)\n ret=out.sort(key=abs)\n return [out,ret]\n',[-3,1,-1,2])
 def test_named_builtin_and_none_keys(self):
  for source,values in [
   ('def solve(xs):\n return sorted(xs,key=len,reverse=True)\n',['a','bbb','cc','ddd']),
   ('def solve(xs):\n return sorted(xs,key=None,reverse=False)\n',[3,1,2]),
   ('def key(x):\n return (-len(x),x)\ndef solve(xs):\n return sorted(xs,key=key)\n',['bb','a','ab'])]:
   self.compare(source,values)
 def test_existing_bounded_iterables(self):
  for expression,value in [('tuple(xs)',[3,1,2]),('set(xs)',[3,1,3]),('xs','baca'),('xs',{'bb':1,'a':2})]:
   self.compare('def solve(xs):\n return sorted('+expression+',key=None)\n',value)
 def test_callback_uses_same_step_budget(self):
  source='def key(x):\n while True:\n  pass\ndef solve(xs):\n return sorted(xs,key=key)\n'
  with self.assertRaisesRegex(Rejected,'execution step limit'):Program(source).run('solve',[[1]])
 def test_input_mutating_key_is_still_rejected(self):
  source='def key(x):\n x.append(1)\n return len(x)\ndef solve(xs):\n return sorted(xs,key=key)\n'
  with self.assertRaisesRegex(Rejected,'input mutation forbidden'):Program(source).run('solve',[[[2],[1]]])
 def test_wrong_keywords_unpacking_and_arity_refused(self):
  for expression in ['sorted(xs,bad=True)','sorted(xs,**{})','sorted(xs,key=None,key=abs)','sorted(xs,xs,key=abs)','sorted(key=abs)','sorted(xs,key=lambda x,y:x)','sorted(xs,reverse=lambda x:x)']:
   with self.subTest(expression=expression),self.assertRaises(Rejected):Program('def solve(xs):\n return '+expression+'\n')
 def test_invalid_reverse_and_key_fail_bounded(self):
  for expression in ['sorted(xs,reverse=1.5)','sorted(xs,key=xs)']:
   with self.subTest(expression=expression),self.assertRaises(Rejected):Program('def solve(xs):\n return '+expression+'\n').run('solve',[[2,1]])
if __name__=='__main__':unittest.main()
