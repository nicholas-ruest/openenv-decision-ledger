# Media-only app and container validation — 2026-10-27

Implemented a separate MediaEnvironment subclass with only public v7 media-d1/d2 allowed, defaulting to media-d1. Non-media and media-d3 resets fail before upstream task generation. Reward, public task pools, action/observation models and terminal implementation remain inherited from Dragan Spiridonov/Profa-QE's MIT source at958198e55299eb18ad812f438a6b2ca6abaa7f5c.

**Eight HTTP/WebSocket app tests passed** on ruOS against Arena-pinned OpenEnv86a180e: health, exact action/observation schema, six reference/wrong/empty WebSocket episodes over both task IDs, and a non-media reset error. These use FastAPI TestClient and disabled shell mode; they do not establish TCP/container or enabled-isolation qualification. Two earlier adapter smoke tests also passed.

Added a fresh-context builder and bounded40-minute GitHub Actions build/test job. It retrieves the exact attributed public source, retains its Dockerfile stages/runtime pins/dependency lock, root-only source permissions and UID isolation implementation, includes the upstream MIT license, and switches the server command to our media-only app. The test image also includes pytest and upstream isolation tests; this is a validation image, not yet a released production artifact.

The build job is configured to run our app controls plus upstream root/UID isolation tests inside the actual image. Tests/scripts are explicitly included despite upstream Docker ignore rules. No image is pushed by this job. A local context-generation check passed; the Docker build result is pending. Do not claim the production image passes before inspecting CI.

After build and isolation succeed, test actual TCP/WebSocket/SDK behavior and publish an owned image with anonymous validation. Freeze exact request and dataset only after those checks, then obtain Nick's approval before HF replacement/Arena POST.

No new paid inference, model training, transfer gain or ranking gain. Software v12 and its review request remain unchanged.
