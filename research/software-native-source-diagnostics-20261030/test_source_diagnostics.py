"""Actual Native parser boundaries; no generated case or provider calls."""
import unittest
from source_diagnostics import diagnose
class SourceDiagnosticsTests(unittest.TestCase):
 def test_supported_module_has_no_diagnostic(self):
  self.assertIsNone(diagnose('def solve(x):\n    return x\n'))
 def test_real_keyword_rejection_names_only_submitted_node(self):
  value=diagnose('def solve(x):\n    return sorted(x, reverse=True)\n')
  self.assertEqual(value['kind'],'unsupported_syntax')
  self.assertEqual(value['nodes'][0]['node'],'keyword')
  self.assertEqual(value['nodes'][0]['line'],2)
  self.assertTrue(value['public_submitted_source_only']);self.assertFalse(value['hidden_access'])
  self.assertNotIn('source',value);self.assertNotIn('expected',value)
 def test_actual_syntax_error_location(self):
  value=diagnose('def solve(x)\n    return x\n')
  self.assertEqual(value['kind'],'syntax_error');self.assertEqual(value['line'],1)
  self.assertGreater(value['column'],0)
 def test_source_like_text_inside_a_string_is_not_code(self):
  self.assertIsNone(diagnose('def solve(x):\n    return "sorted(x, reverse=True)"\n'))
 def test_output_is_bounded_even_with_many_rejected_keywords(self):
  source='def solve(x):\n    return fn(x,'+','.join('k%d=%d'%(i,i) for i in range(12))+')\n'
  value=diagnose(source);self.assertEqual(len(value['nodes']),8);self.assertEqual(value['total_nodes'],12)
 def test_source_limit_and_wrong_type_are_not_parsed(self):
  self.assertIsNone(diagnose(b'not text'));self.assertIsNone(diagnose('x'*8193))
if __name__=='__main__':unittest.main()
