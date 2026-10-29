"""Offline timeout fixture: native session open, no provider request."""
import json
import sys
import time
from pathlib import Path

from native_session import NativeSession

root=Path(sys.argv[1]);root.mkdir()
with NativeSession(deadline=time.monotonic()+60) as s:
    s.reset('qe_skill-media-d1',2290000)
    (root/'opened-native-session.json').write_text(json.dumps({'opened':True,'new_model_calls':0}))
    while True:time.sleep(.01)
