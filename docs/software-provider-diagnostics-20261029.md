# Fixed-code provider diagnostics — October 29, 2026

The manual comparison caller now records a fixed diagnostic stage, fixed error code, bounded elapsed time and an integer HTTP status when available. It never records exception text, response bodies, URLs, headers, exception class names or credentials. Unrecognized errors remain `other_error`. It records both reservation and post-reservation failures without changing failure labels, retaining unknown usage, retrying, dropping assigned outcomes or releasing reservations.

Tested source `c3d10e1f9d519cbd840e7ee92562667edb6a040b` passed ten tests on ruOS: the existing eight scripted native/fictional accounting tests plus two focused diagnostic tests. The scripted provider timeout test additionally verified exactly one failure event, its provider stage and fixed timeout code, preserved 32-assignment denominator and no retry. Fictional credential strings in HTTP URLs, reason text, headers, exception names and payloads were absent from diagnostic output; nonfinite elapsed times became null.

Log SHA-256: `63cb69efe516ea775331ba8ee354b511a941debabff524815c6db3c930ade929`.

Source inspection also established a transport distinction: the manual caller uses `calibrate.py:provider_call`, a non-streaming urllib request; the older software runner imports `provider_stream.py:provider_call`, a bounded SSE implementation requiring final usage. This is a hypothesis to investigate, not evidence of the cause of any earlier failure. This change does not switch transports or change the frozen request, tasks, sampling or comparison schedule. No network/model requests were made by these tests. These results establish diagnostics behavior, not model improvement or training.
