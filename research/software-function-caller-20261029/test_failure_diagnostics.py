import json
import unittest
import urllib.error
from failure_diagnostics import safe_failure


class DiagnosticTests(unittest.TestCase):
    def test_http_status_timeout_and_stage_are_retained_without_provider_text(self):
        secret = 'FICTIONAL_CREDENTIAL_DO_NOT_LOG'
        exc = urllib.error.HTTPError('https://example.invalid/'+secret, 504, secret,
                                     {'Authorization': secret}, None)
        row = safe_failure(exc, 'provider', 124.4)
        self.assertEqual(row, dict(stage='provider', code='http_error',
                                   http_status=504, elapsed_ms=124400))
        self.assertNotIn(secret, json.dumps(row))
        self.assertEqual(safe_failure(TimeoutError(secret),'provider',2)['code'], 'timeout')
        self.assertEqual(safe_failure(urllib.error.URLError(TimeoutError(secret)),
                                     'provider',2)['code'], 'network_timeout')

    def test_unknown_exception_names_payloads_and_nonfinite_times_never_escape(self):
        exc_type = type('FICTIONAL_SECRET_CLASS', (Exception,), {})
        for elapsed in (float('nan'),float('inf'),-1,'secret'):
            row = safe_failure(exc_type('FICTIONAL_SECRET_PAYLOAD'), 'response_validation', elapsed)
            self.assertIsNone(row['elapsed_ms']);self.assertEqual(row['code'],'other_error')
            self.assertNotIn('SECRET',json.dumps(row,allow_nan=False))
        with self.assertRaises(ValueError):safe_failure(ValueError(), 'untrusted text',0)


if __name__ == '__main__': unittest.main()
