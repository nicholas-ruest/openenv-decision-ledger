"""Analysis-only terminal classification; never returns hidden information to the model."""
from repair_env.runner import Program,Rejected
from repair_env.environment import check
from repair_env.tasks import SOURCE_PATH


def classify(env,native):
    if not native['done']:raise ValueError('terminal native result required')
    reward=native['reward']
    result=dict(native_reward=reward,semantic_reward=None,compile_rejected=False,
                hidden_execution_errors=0,hidden_wrong_answers=0)
    if native['error']:
        return dict(result,category='execution',native_error=True)
    try:
        program=Program(env._direct._files[SOURCE_PATH])
    except (Rejected,RecursionError):
        return dict(result,category='execution',compile_rejected=True)
    # Repeat the identical bounded interpreter check only AFTER terminal grading.
    # Aggregate counts only: no inputs/answers/details enter messages or feedback.
    task=env._direct._task
    passed,details=check(program,task,task.hidden,details=True)
    errors=sum(x['error'] is not None for x in details)
    wrong=sum(not x['passed'] and x['error'] is None for x in details)
    result.update(hidden_execution_errors=errors,hidden_wrong_answers=wrong)
    if errors:return dict(result,category='execution')
    if reward==1 and passed!=len(task.hidden):raise ValueError('terminal native grade mismatch')
    return dict(result,category='full' if reward==1 else 'partial' if 0<reward<1 else 'wrong',semantic_reward=reward)
