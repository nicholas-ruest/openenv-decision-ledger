# Media-only v13 candidate review, 2026-10-27

Published image: `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:b80078c2cc8a05d3222fe22ee91321d29d881afff912097c6601a8cffd84c4e6`.
Runtime source74a8727fa14270e29cf363fc2ad79b0f7f9cbce1. CI40592567666 passed31 app/isolation tests, real TCP reference episodes, six pinned OpenEnv CLI checks, image publication and an anonymous manifest pull/replay. That pull reused cached layers; a separate fresh-runner workflow now pulls the exact digest from an empty host and repeats qualification, including full schema equality and enabled UID shell controls. Do not conflate the first manifest access with a fresh layer download.

Exact proposed request is `config/media-v13-review-20261027.json`, SHA256`e8ddb0bffeec2009c2fcfc7c4fb82f87eb664335526b1641e645f07f21763766`. This is NOT approved. `review/media-v13-dataset-20261027/` contains a staged replacement packet; no HF dataset has been changed. The request contains only the two media tasks; software v12 and its image remain unchanged as a separate choice.

`research/media-review-20261027/prepare-media-review.py` reproduces the request from exact artifact schema and source/image pins plus the upstream request's media task limits. Seven tests check exact task/schema/limits, wrong source/image/schema rejection, UID-shell evidence, overwrite refusal and unapproved state. The generator previously included the server's extra state schema; its exact-schema regression caught that and the request now includes only action/observation as required. Request bytes were regenerated in a fresh directory after the fix.

The image adapts Dragan Spiridonov / Profa-QE's MIT958198e55299eb18ad812f438a6b2ca6abaa7f5c public source. It is not a verified Ruv swarm recipe. Public mixed v7 media draws motivate a hypothesis; removing the five science/math task cells changes the recipe. No media-only model confirmation or causal transfer improvement exists. Binary grades can saturate; no productive model-group variance on these media tasks has been established. The existing software calibration demonstrates prerequisite variation, not a private software gain.

No paid inference, training, HF replacement or Arena POST occurred in this preparation. The next submission requires Nick's explicit approval of the final exact request. Approval pending does not stop independent software/media research.
