import ast
import unittest
from partial_diagnosis import functions,restore,same_function

class DiagnosisTests(unittest.TestCase):
    def test_format_only_change_is_not_semantic_edit(self):
        self.assertTrue(same_function(functions('def f(x): return x+1')['f'],functions('def f(x):\n    return x + 1\n')['f']))
    def test_single_function_restoration_preserves_other_function(self):
        original='def f(x): return x+1\ndef g(x): return x*2'
        candidate='def f(x): return 0\ndef g(x): return x*3'
        result=functions(restore(candidate,original,['f']))
        self.assertTrue(same_function(result['f'],functions(original)['f']))
        self.assertTrue(same_function(result['g'],functions(candidate)['g']))
    def test_missing_and_duplicate_functions_are_not_silently_repaired(self):
        with self.assertRaises(ValueError):restore('def g(x): return 0','def f(x): return 1',['f'])
        with self.assertRaises(ValueError):functions('def f(): return 0\ndef f(): return 1')
    def test_ast_parsing_never_invokes_candidate_code(self):
        s='def f():\n    raise RuntimeError("never execute")'
        self.assertIn('raise RuntimeError',restore(s,s,['f']))

if __name__=='__main__':unittest.main()
