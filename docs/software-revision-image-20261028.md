# Separate software revision image preparation

The candidate Dockerfile inherits the immutable validated software runtime dependencies, adds only the two-response app/environment and public-example checker, and changes the server command to the separate app. Existing v12/v13 images and review requests are untouched. No new dependency/model downloads, inference, GPU rental or training are introduced.

The workflow runs native unit controls before publishing a new, source-specific tag in the existing owned package. A separate fresh job must anonymously pull the resulting digest, pass Arena-pinned SDK validation, match the action/observation schemas and complete four scripted native WebSocket controls. Results and digest will be recorded only after completion. This is candidate qualification, not evidence of model learning or private-task transfer. A qualified image alone grants no HF replacement or submission authority.
