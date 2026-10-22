"""A genuine missing-component implementation task over the release contract."""
from . import release_plan

INSTRUCTIONS = (" The build_plan helper currently returns a placeholder with the correct "
    "result shape. Implement the complete affected-graph, cycle, blocked-module, "
    "topological-order and unknown-name behavior stated above. The plan_release "
    "consumer is supplied and must continue to satisfy the same full contract. "
    "You may repair or replace either function. No imports or host execution.")


def initial():
    # A runnable, semantically wrong placeholder, not a syntax/interpreter trap.
    # The independently checked suite-selection consumer is left intact.
    consumer = release_plan.REFERENCE[release_plan.REFERENCE.index("def plan_release("):]
    return ('def build_plan(graph, changed):\n'
            '    return {"order": [], "blocked": [], "cycles": [], "unknown": []}\n\n'
            + consumer)
