# Media container test-entrypoint diagnosis, 2026-10-27

The first image build succeeded in CI40584987706. The combined suite reported30 passed/1 failed: `test_a_process_name_that_is_not_utf8_does_not_break_cleanup`. The failure output contains `fork: retry: Resource temporarily unavailable`; its required odd-name child was not observed.

The workflow had used `docker run --entrypoint python`, replacing upstream's `/usr/bin/tini --`. Upstream explicitly relies on tini reaping killed detached episode processes. This launch error is consistent with stale zombie processes exhausting the UID process limit after the earlier fork stress test; the first run did not record `/proc` zombie counts, so that causal explanation remains an inference until a corrected run is measured.

The correction removes the entrypoint override and runs the exact same31 tests under the image's native tini entrypoint. No isolation assertion, resource limit, grader, task or software/v12 file is relaxed or changed. Local context validation confirmed the sole inherited ENTRYPOINT is tini, the workflow keeps it, and the TCP checker is copied into the image.

A separate step now starts the normal uvicorn CMD and checks real TCP health/schema, two WebSocket reference episodes and unprivileged exec UID. It also requires PID1=tini. Reference successes are controls, not model solves. The image remains test-only, unpushed and unqualified pending the corrected CI; no paid inference/training/submission occurs.

## Corrected result

CI40592232854 completed successfully on6b83de2255fe9c04614909c73a686f8084d09ac2. All31 unchanged app/UID tests passed; normal CMD TCP controls also passed with PID1=tini and enabled UID shell. Two native media reference episodes earned1. This supports the test-entrypoint diagnosis, not a model-improvement claim.

The next workflow revision retains those gates and adds the actual pinned OpenEnv CLI validation before any push, an exclusive owned media tag in the existing package, an unauthenticated pinned pull, repeated CLI/TCP checks and schema/package/image evidence artifacts. Publication/anonymous validation are pending until that workflow completes. No HF replacement or Arena POST is authorized by this change. Software v12 remains frozen.
