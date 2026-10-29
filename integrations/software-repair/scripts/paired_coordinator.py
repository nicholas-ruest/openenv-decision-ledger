"""Sequential isolated-worker coordination core; no provider or launch function."""
import time


def schedule(tasks, seeds):
    if (len(tasks) != 2 or len(set(tasks)) != 2 or len(seeds) != 2 or
            len(set(seeds)) != 2 or any(type(s) is not int or s < 0 for s in seeds)):
        raise ValueError("two tasks and two distinct integer seeds required")
    jobs = []
    arms = ('baseline', 'preserve_supplied')
    for task in tasks:
        for seed in seeds:
            for sample in range(4):
                # Counterbalance which arm runs first, without concurrent mutation.
                for arm in arms[::1 if sample % 2 == 0 else -1]:
                    jobs.append((arm, task, seed, sample))
    if len(jobs) != 32 or len(set(jobs)) != 32:
        raise ValueError('complete unique paired phase required')
    return jobs


def coordinate(jobs, worker, save, deadline, admitted, now=time.monotonic):
    """worker must run one job in a separate process and enforce its deadline.

    Admission is supplied by the existing whole-phase accounting gate. This core
    does not substitute for reconciliation, reservation, or process cleanup.
    """
    if admitted is not True:
        raise ValueError('whole-phase admission required')
    completed = []
    for job in jobs:
        if now() >= deadline:
            return {'complete': False, 'completed': completed, 'reason': 'deadline'}
        result = worker(job, deadline)
        save(job, result)  # Persist before proceeding; never retry a failed save.
        completed.append(job)
        if result.get('fatal_guard_failure'):
            return {'complete': False, 'completed': completed, 'reason': 'fatal_guard'}
    return {'complete': True, 'completed': completed}


def isolated_worker(argv, cwd, deadline, now=time.monotonic):
    """Supervise one separately launched worker; discard all stdout/stderr.

    This adapter uses existing local process-group cleanup. It does not add
    provider calls, admission, accounting, artifact validation or a paid CLI.
    """
    import math
    from training.lifecycle import bounded_worker
    seconds = deadline - now()
    if not math.isfinite(seconds) or not 0 < seconds <= 1800:
        raise ValueError('finite remaining wall deadline <=1800s required')
    result = bounded_worker(argv, cwd=cwd, seconds=seconds, grace=.2)
    return {'process_status': result['status'], 'returncode': result['returncode'],
            'fatal_guard_failure': result['status'] != 'completed',
            'provider_billing_stopped': None}
