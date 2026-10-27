# Media terminal protocol reproduction — 2026-10-27

The earlier local `openenv` import blocker is resolved for this scoped check by using ruOS's existing test environment and an isolated source checkout at Arena's exact OpenEnv revision:
`86a180ede21e044f7929b9a7783ad83aa67d83a3`.

Actual import path was verified under that checkout's `src/openenv`, not the installed distribution. The installed package alone reported0.6.1.dev0 with no attested commit; we did not use that version label as revision evidence. A full source tar exceeded the deliberately bounded download size, so a sparse Git checkout retrieved the required pinned source without downloading model assets. Existing venv packages were not changed.

## Actual test result

**14 parameterized protocol tests passed against the pinned OpenEnv source**, covering all public v7 media-d1/d2 family cells at seeds2230000 and2230100:
- d1:timecode,catalogue,assets.
- d2:subtitles,timecode,catalogue,assets.

Each test exercises three separate episodes: reference output, a named wrong method, and no output. Reference write_file/evaluate returns done with reward1; wrong/missing outputs return reward0. A repeated evaluate retains terminal reward. Disabled-mode exec is refused without ending the episode.

These are14 fixtures/42 control episodes, not model solves. No model, inference API or training job was used.

The harness verifies hashes of the public terminal/shell/skill files before testing. Public upstream source is `proffesor-for-testing/openenv-qe-arena@958198e55299eb18ad812f438a6b2ca6abaa7f5c`, MIT, copyright2026 Dragan Spiridonov. The harness and reproduction script are independent additions; no upstream implementation is relabeled as ours or Reuven's.

## Reproduce

The published controls intentionally sit outside automatic test discovery because they require the external public source. Use an existing Python environment containing pytest and OpenEnv's real dependencies:

```bash
export OPENENV_SOURCE=/path/to/sparse/OpenEnv
export MEDIA_SOURCE=/path/to/pinned/openenv-qe-arena
export MEDIA_TEST_PYTHON=/path/to/test-venv/bin/python
bash integrations/media-reproduction/reproduce-terminal.sh
```

The script checks Git HEAD, verifies actual OpenEnv import location and runs the external protocol controls. It performs no package installation or credential loading.

## Scope and next step

This uses **deliberately disabled shell mode**: the probe is monkeypatched to return disabled, not the OpenEnv interface or grader. It validates data-file write/evaluate behavior and refusal of shell commands. It does **not** verify enabled shell/UID isolation, WASM code execution, HTTP/WebSocket server/SDK compatibility, anonymous image validation or a production Docker build. Wasmtime was absent from this test environment; content grading here does not require it.

Next prepare an attributed media-only server/build configuration, retain the upstream enabled-shell security design when implementing that path, and validate the actual published image before proposing any exact Arena request. Changing the original mixed science/math/media recipe to media-only remains an untested transfer hypothesis.

Software/v12 and the existing dataset remain unchanged. No training, new paid inference, Arena submission or ranking improvement is claimed.
