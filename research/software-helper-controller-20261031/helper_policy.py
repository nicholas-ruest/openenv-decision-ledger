"""Public-source helper preservation prototype; no paid execution entry point.

Only the two helpers explicitly declared complete by the public contract are
restored. There is no reference solution, grader, hidden case or task lookup.
This transforms controller actions; resulting solves are system outcomes.
"""
import ast
import copy
import hashlib
import json

DECLARATION = ('match_segment(pattern, word) and match_parts(pattern_parts, path_parts) '
               'are complete reusable glob helpers in the supplied module.')
HELPERS = ('match_segment', 'match_parts')


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def preserve_helpers(original, proposal, public_prompt):
    """Restore only declared helpers; malformed/ambiguous proposals stay intact."""
    result = dict(content=proposal, changed=False, restored_names=[], applicable=False)
    if DECLARATION not in public_prompt:
        return result
    before = ast.parse(original)
    supplied = {n.name: ast.get_source_segment(original, n) for n in before.body
                if isinstance(n, ast.FunctionDef) and n.name in HELPERS}
    if set(supplied) != set(HELPERS):
        raise ValueError('public declaration requires both original helper definitions')
    try:
        parsed = ast.parse(proposal)
    except (SyntaxError, ValueError, RecursionError):
        return result
    nodes = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in HELPERS]
    if len({n.name for n in nodes}) != len(nodes) or any(n.decorator_list for n in nodes):
        return result
    # Preserve byte-identical complete helpers, including proposals that only
    # change the actual repair targets. Do not manufacture cosmetic changes.
    changed = [name for name in HELPERS
               if not any(n.name == name and ast.get_source_segment(proposal, n) == supplied[name]
                          for n in nodes)]
    result['applicable'] = True
    if not changed:
        return result
    lines = proposal.splitlines(keepends=True)
    for n in sorted((n for n in nodes if n.name in changed), key=lambda n: n.lineno, reverse=True):
        lines[n.lineno-1:n.end_lineno] = []
    content = ''.join(lines).rstrip() + '\n\n' + '\n\n'.join(supplied[n] for n in changed) + '\n'
    # Parsing never executes the submitted module.
    ast.parse(content)
    return dict(content=content, changed=True, restored_names=changed, applicable=True,
                supplied_source_sha256=sha(original), proposal_before_sha256=sha(proposal),
                proposal_after_sha256=sha(content))


class HelperPreservationPolicy:
    """Compose over an existing Trial; no automatic public-pass finalization."""
    def __init__(self, trial, *, arm):
        if arm not in ('standard_revision', 'preserve_declared_helpers'):
            raise ValueError('explicit separate helper intervention required')
        self.trial = trial
        self.arm = arm
        reset = json.loads(trial.messages[1]['content'])
        self.source, self.prompt = reset['source'], reset['prompt']
        self.model_responses = 0
        self.controller_actions = []

    def consume_model(self, text, *, finish_reason):
        if finish_reason != 'stop':
            raise ValueError('incomplete responses cannot be recovered')
        effective = text
        controller_before = len(self.controller_actions)
        if self.arm == 'preserve_declared_helpers':
            try:
                action = json.loads(text)
            except (ValueError, TypeError):
                action = None
            if type(action) is dict and type(action.get('content')) is str and action['content']:
                transformed = preserve_helpers(self.source, action['content'], self.prompt)
                if transformed['changed']:
                    action = dict(action, content=transformed.pop('content'))
                    effective = json.dumps(action)
                    self.controller_actions.append(dict(transformed,
                        authored_by='controller', kind='preserve_declared_helpers',
                        generated_tokens=0, model_response_index=self.model_responses))
        before = len(self.trial.native)
        result = self.trial.consume(effective)
        controller_observations = []
        if effective != text and len(self.trial.native) > before:
            # Original Trial appends the submitted action as an assistant turn.
            # Keep the ACTUAL model response there, and expose the intervention
            # as a separate controller observation. Never impersonate a model.
            if self.trial.messages[-2] != dict(role='assistant', content=effective):
                raise ValueError('original Trial transcript shape changed')
            self.trial.messages[-2] = dict(role='assistant', content=text)
            controller_observations = [dict(controller_observation=copy.deepcopy(a),
                applied_before_native_step=True)
                for a in self.controller_actions[controller_before:]]
            for obs in controller_observations:
                self.trial.messages.append(dict(role='user', content=json.dumps(obs, sort_keys=True)))
        self.model_responses += 1
        return dict(result, model_responses=self.model_responses,
            controller_actions=copy.deepcopy(self.controller_actions),
            new_observations=copy.deepcopy(self.trial.native[before:]),
            controller_observations=controller_observations,
            is_training=False, model_improvement=False)


def observation_tokens(result, count):
    """Both original Native observations and controller receipts cost tokens."""
    return sum(count(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False))
               for x in result['new_observations'] + result['controller_observations'])
