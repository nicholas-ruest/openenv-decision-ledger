# Explicit allocation amendment gate — October 29, 2026

The manual software caller can now accept an explicit authorization SHA-256 for an amended allocation. Without that argument the original two-dollar ceiling remains. The gate verifies the immutable authorization record, its agreement with the receipt, the before-receipt hash, unchanged ledger prefix, positive amendment arithmetic and preserved parent/cumulative accounting fields. Existing freshness, credit, total authorization, duplicate reservation, append-before-call and phase admission checks remain enforced. This source grants no additional spending authority and never purchases credits or resets reservations.

Tested source: `5a7ee015971c16b852463fcc7dbc65dfab9d207f`. Three focused tests passed locally and on ruOS with temporary fictional receipts. They execute the actual reservation class and cover retained reservations, denied duplicates and over-cap calls, altered authorization/history, removed reservations, stale observations, insufficient credit, changed parents and changed cumulative accounting. All eight existing caller tests also passed on ruOS, including five scripted native integration tests. No frozen task, grader, reviewed request, dataset or image changed.

Gate log SHA-256: `7b18c799dcebb9300295723a00ae8a3a23a383842ae040f61de62163e2201669`. Caller log SHA-256: `432939160cf43531f14abf88862e8b2ba9328f8ae54bc3a5d89930f3328e72b8`.

These are accounting and scripted execution tests, not model improvement or Arena qualification. A live comparison requires separate current private reconciliation and complete-phase admission. Confirmation and any Arena submission retain their existing gates.
