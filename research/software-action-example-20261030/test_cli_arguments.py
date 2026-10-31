"""CLI spelling must bind a file path and its hash to distinct exact options."""
import contextlib
import io
from pathlib import Path
import unittest
from caller import argument_parser


class ArgumentTests(unittest.TestCase):
    def test_canonical_case_path_and_digest_bind_separately(self):
        args = argument_parser().parse_args(['--case-audit', '/nonexistent/audit.json',
                                             '--case-audit-sha256', 'a'*64])
        self.assertEqual(args.case_audit, Path('/nonexistent/audit.json'))
        self.assertEqual(args.case_audit_sha256, 'a'*64)

    def test_explicit_legacy_spelling_has_same_binding(self):
        args = argument_parser().parse_args(['--case_audit', '/nonexistent/audit.json'])
        self.assertEqual(args.case_audit, Path('/nonexistent/audit.json'))
        self.assertIsNone(args.case_audit_sha256)

    def test_abbreviations_do_not_silently_bind_another_argument(self):
        for option in ('--case', '--case-audit-sha', '--expected-sourc'):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    argument_parser().parse_args([option, 'not-a-value'])


if __name__ == '__main__': unittest.main()
