# Separate software revision image preparation

The candidate Dockerfile inherits the immutable validated software runtime dependencies, adds only the two-response app/environment and public-example checker, and changes the server command to the separate app. Existing v12/v13 images and review requests are untouched. No new dependency/model downloads, inference, GPU rental or training are introduced.

The workflow runs native unit controls before publishing a new, source-specific tag in the existing owned package. A separate fresh job must anonymously pull the resulting digest, pass Arena-pinned SDK validation, match the action/observation schemas and complete four scripted native WebSocket controls. CI40742200919 completed successfully:9 native unit tests before publication, then a fresh anonymous pull, all6 SDK checks, exact schema checks and4 scripted WebSocket controls. The SDK reported its standard simulation mode; these are environment qualification controls, not simulated model training or actual GRPO. The image runs as user10001 with tini and the revision_app server command.

Candidate image: `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:a842e4ec292f9aa5067514a7eb8a85b5fa1e43edda61ef2bb53b9704603f8144`.
Source: `ae301b0a4071b5a376d6eeef6812060fac789534`.
Schema SHA256: `b2828883f206a3976c8ed82f53380f5984a30e16ab88ed06d116233a6bee9814`.

The existing pinned tokenizer also measured two scripted proposal/feedback/reference paths on ruOS. Preliminary totals were2150 and2279 tokens, excluding the final observation and unverified production chat-template overhead. This is a local accounting diagnostic over reconstructed transport, not a budget-equivalence or model-rollout claim. No capacities were raised. This is candidate qualification, not evidence of model learning or private-task transfer. A qualified image alone grants no HF replacement or submission authority.
