# Bounded native media WebSocket adapter, 2026-10-28

This implements a synchronous facade over a persistent native asyncio WebSocket in research/media-websocket-20261028/native_session.py. It does not implement a model/provider route, dataset write or Arena submission. Both reviewed requests/images remain frozen.

Each operation runs on the same asyncio.Runner under a total send+receive deadline of at most15seconds, bounded by the episode's finite remaining wall time (at most1800seconds). The only URL is ws://127.0.0.1:<explicit unprivileged port>/ws. Proxy use is disabled, no credential/header input exists, compression/pings are disabled, incoming messages are capped at64KiB and the queue at4. Reset is accepted once for one declared media task and integer seed. Steps validate the exact pinned action schema and the native outer done/reward transport. No automatic retry or reconnect occurs. A timed-out/failed operation closes and poisons the session. Close has a bounded0.3second graceful attempt followed by transport abort.

Seven local tests passed against websockets17.2, matching the frozen image lock: reset/step/close and fixed endpoint, cancellation of stalled handshake/send/receive, sanitized malformed envelopes, expired/invalid deadlines, reset reuse, invalid actions, and stalled close abort. Test sockets were injected deterministic doubles. They are not model rollouts.

The image integration workflow uses the unchanged qualified media image and actual TCP sessions. It checks the native reset/workspace manifests with trusted root inspection consuming no episode actions, one scripted full and one scripted wrong episode with enabled shell, plus10 sequential unfinished-session closes (more than the server's8-session concurrency limit), requiring each real workspace to disappear. These are cleanup/integration checks, not a new estimate of task difficulty. CI outcome must be checked before claiming this image test passed.

## Limits

This class is a single-threaded adapter, not a concurrent client. The event loop runs during each operation; provider work between operations remains separately bounded by the existing process supervisor. Graceful close/transport abort establishes local closure, not remote provider billing termination. Server workspace cleanup must be independently measured; disconnect alone is not assumed to prove it. Trusted workspace inspection and runtime attestation are external responsibilities, not exposed to the model. Actual episode/model dispatch admission and accounting remain locked behind their existing whole-phase guards.

The native controls use the attributed Profa-QE MIT oracle, never model outputs. No new model call, training, model confirmation or ranking improvement is claimed. Softwarev12/media-v13 exact requests/images are unchanged and unapproved.
