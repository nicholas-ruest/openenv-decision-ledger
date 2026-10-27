#!/usr/bin/env bash
set -euo pipefail
: "${OPENENV_SOURCE:?Set the isolated OpenEnv source checkout}"
: "${MEDIA_SOURCE:?Set the attributed QE source checkout}"
: "${MEDIA_TEST_PYTHON:?Set the Python executable with pytest and OpenEnv dependencies}"
expected=86a180ede21e044f7929b9a7783ad83aa67d83a3
actual=$(git -C "$OPENENV_SOURCE" rev-parse HEAD)
if [[ "$actual" != "$expected" ]]; then
  echo 'OpenEnv revision mismatch' >&2
  exit 1
fi
export PYTHONPATH="$OPENENV_SOURCE/src:$MEDIA_SOURCE"
"$MEDIA_TEST_PYTHON" -c 'import os,pathlib,openenv; assert pathlib.Path(openenv.__file__).is_relative_to(pathlib.Path(os.environ["OPENENV_SOURCE"]) / "src"); print("Pinned OpenEnv source import verified")'
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
"$MEDIA_TEST_PYTHON" -m pytest -q "$script_dir/protocol_controls.py"
