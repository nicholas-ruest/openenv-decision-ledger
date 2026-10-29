"""Fixed-code exception diagnostics, never provider text, URLs or credentials."""
import math
import urllib.error

STAGES = {'reservation', 'provider', 'response_validation', 'native_processing'}


def safe_failure(exc, stage, elapsed):
    if stage not in STAGES:
        raise ValueError('fixed diagnostic stage required')
    result = dict(stage=stage, code='other_error', http_status=None,
                  elapsed_ms=None)
    if type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0:
        result['elapsed_ms'] = round(min(elapsed, 1200)*1000)
    if isinstance(exc, urllib.error.HTTPError):
        result['code'] = 'http_error'
        if type(exc.code) is int and 100 <= exc.code <= 599:
            result['http_status'] = exc.code
    elif isinstance(exc, TimeoutError):
        result['code'] = 'timeout'
    elif isinstance(exc, urllib.error.URLError):
        result['code'] = 'network_timeout' if isinstance(exc.reason, TimeoutError) else 'network_error'
    elif isinstance(exc, UnicodeError):
        result['code'] = 'text_decode_error'
    elif isinstance(exc, ValueError):
        result['code'] = 'value_error'
    elif isinstance(exc, (KeyError, TypeError, IndexError)):
        result['code'] = 'response_shape_error'
    return result
