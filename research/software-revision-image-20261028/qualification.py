"""In-image qualification controls; no model/provider/submission calls."""
import hashlib
import json
from urllib.request import urlopen
from revision_environment import RevisionAction,RevisionObservation,TASKS

with urlopen('http://127.0.0.1:8000/schema',timeout=5) as r:schema=json.load(r)
if schema['action']!=RevisionAction.model_json_schema():raise ValueError('native action schema mismatch')
if schema['observation']!=RevisionObservation.model_json_schema():raise ValueError('native observation schema mismatch')
print(json.dumps({'schema_matches':True,'schema_sha256':hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'tasks':TASKS,'new_model_calls':0}))
