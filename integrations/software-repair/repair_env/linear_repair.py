"""Original bounded concurrency-history repair problem and enumerative oracle."""
import hashlib
import itertools
import random

INSTRUCTIONS = """Repair check_history(initial, operations), an offline linearizability checker for one atomic integer register. Each operation has a unique string id, kind (read/write/cas), start integer, end integer or null, value integer, expect integer and result. The list is sorted by id. Event positions are distinct; every completed operation has start<end. At most6 operations, at most2 pending (end:null); values are0..3. Unused fields are present but irrelevant. Inputs are well-formed and must not be mutated.
A sequential explanation includes EVERY completed operation exactly once and may include or omit each pending operation. An operation cannot precede another operation that COMPLETED before it STARTED: if A.end is not null and A.end<B.start, A must appear before B whenever B is included. Overlapping operations may be ordered either way. A pending operation has no completion event but still cannot precede operations completed before its start.
Replay included operations on the register initially equal to initial. write sets the register to value and has result:null. A completed read's result must equal the current register; a pending read has no observed result and does not change it. cas compares current register with expect, succeeds exactly when equal and, on success, writes value. A completed cas result is the boolean success flag and MUST agree with that comparison. Pending cas has no observed result, so either outcome is determined by its position and current value. Failed cas does not write. Pending writes may explain later completed reads, but need not be included when unnecessary.
Find the lexicographically smallest ID-list among ALL legal explanations, including optional pending operations. Compare ID lists as usual: compare the first unequal IDs; if one is a prefix, the shorter list is smaller. This canonical witness is NOT generally call order, return order or a sorted list. Backtrack when an apparently legal prefix cannot explain later results. Different register states with the same used-operation set are distinct search states.
Return exactly {linearizable:boolean,witness:canonical_ID_list,final:register_after_witness,pending:sorted_IDs_of_omitted_pending_operations}. If no legal explanation exists, return {linearizable:false,witness:[],final:null,pending:ALL_pending_IDs_sorted}. A history with no completed operations is linearizable with empty witness, initial final value and all pending IDs omitted. Examples are independently instantiated; reason about the full contract. Partial reward requires improving exact meaningful result fields over the supplied defective checker; unchanged/cosmetic code gets0 and full reward requires every hidden case correct."""

REFERENCE = '''def search_order(ops, dependencies, required, used, value, failed):
    if used & required == required:
        return [[], value]
    key = (used, value)
    if key in failed:
        return None
    for i in range(len(ops)):
        bit = 1 << i
        if used & bit or dependencies[i] & used != dependencies[i]:
            continue
        op = ops[i]
        after = value
        if op["kind"] == "read":
            if op["end"] is not None and op["result"] != value:
                continue
        elif op["kind"] == "write":
            after = op["value"]
        else:
            matched = value == op["expect"]
            if op["end"] is not None and op["result"] != matched:
                continue
            if matched:
                after = op["value"]
        found = search_order(ops, dependencies, required, used | bit, after, failed)
        if found is not None:
            return [[op["id"]] + found[0], found[1]]
    failed.add(key)
    return None

def check_history(initial, operations):
    required = 0
    dependencies = []
    for i in range(len(operations)):
        op = operations[i]
        if op["end"] is not None:
            required |= 1 << i
        before = 0
        for j in range(len(operations)):
            prior = operations[j]
            if prior["end"] is not None and prior["end"] < op["start"]:
                before |= 1 << j
        dependencies.append(before)
    found = search_order(operations, dependencies, required, 0, initial, set())
    pending = [op["id"] for op in operations if op["end"] is None]
    if found is None:
        return {"linearizable": False, "witness": [], "final": None, "pending": pending}
    omitted = [identifier for identifier in pending if identifier not in found[0]]
    return {"linearizable": True, "witness": found[0], "final": found[1], "pending": omitted}
'''

# A valid-shaped but semantically incomplete checker. Unlike the repair arm,
# this does not disclose a search algorithm or a cache/state representation.
PLACEHOLDER = '''def check_history(initial, operations):
    pending = [op["id"] for op in operations if op["end"] is None]
    return {"linearizable": False, "witness": [], "final": None, "pending": pending}
'''
UNGUIDED_INSTRUCTIONS = INSTRUCTIONS.replace(
    " Backtrack when an apparently legal prefix cannot explain later results.", "").replace(
    " Different register states with the same used-operation set are distinct search states.", "")

MUTATIONS = (
    ('if prior["end"] is not None and prior["end"] < op["start"]:', 'if False:', 'ignore_realtime'),
    ('        op = ops[i]\n        after = value', '        op = ops[i]\n        if op["end"] is None:\n            continue\n        after = value', 'ignore_pending'),
    ('if op["end"] is not None:\n            required |=', 'if True:\n            required |=', 'require_pending'),
    ('if op["end"] is not None and op["result"] != value:', 'if False:', 'ignore_read_results'),
    ('if op["end"] is not None and op["result"] != matched:', 'if False:', 'ignore_cas_results'),
    ('        if found is not None:', '        if found is None:\n            return None\n        if found is not None:', 'greedy_prefix'),
    ('key = (used, value)', 'key = used', 'collapse_register_states'),
    ('for i in range(len(ops)):', 'for i in range(len(ops)-1, -1, -1):', 'wrong_canonical_order'),
    ('            if matched:', '            if True:', 'failed_cas_writes'),
)


def mutate(indices):
    source = REFERENCE
    for index in sorted(indices):
        before, after, name = MUTATIONS[index]
        assert before in source, name
        source = source.replace(before, after, 1)
    return source


def initial(seed, difficulty):
    if difficulty == 3:return PLACEHOLDER
    if difficulty == 4:difficulty = 2
    rng = random.Random(int.from_bytes(hashlib.sha256(f'linear-v1|{seed}|{difficulty}'.encode()).digest(),'big'))
    return mutate(rng.sample(range(len(MUTATIONS)), 2 if difficulty == 1 else 4))


def reference(args):
    """Independent exhaustive permutations; no DFS, memo, bitmask or shared transition helper."""
    initial_value, ops = args
    complete = {o['id'] for o in ops if o['end'] is not None}
    pending = sorted(o['id'] for o in ops if o['end'] is None)
    best, best_value = None, None
    for size in range(len(complete),len(ops)+1):
        for order in itertools.permutations(ops,size):
            names=[o['id'] for o in order]
            if not complete.issubset(names) or (best is not None and not names < best):
                continue
            positions={o['id']:i for i,o in enumerate(order)}
            if any(a['end'] is not None and a['end']<b['start'] and positions[a['id']]>positions[b['id']]
                   for a in order for b in order):
                continue
            register=initial_value
            legal=True
            for op in order:
                if op['kind']=='write':
                    register=op['value']
                elif op['kind']=='read':
                    if op['end'] is not None and type(op['result']) is int and op['result'] != register:
                        legal=False;break
                else:
                    success=register==op['expect']
                    if op['end'] is not None and op['result'] is not success:
                        legal=False;break
                    if success:register=op['value']
            if legal:best,best_value=names,register
    if best is None:return {'linearizable':False,'witness':[],'final':None,'pending':pending}
    return {'linearizable':True,'witness':best,'final':best_value,'pending':[p for p in pending if p not in best]}


def _op(identifier,kind,start,end,*,value=0,expect=0,result=None):
    return {'id':identifier,'kind':kind,'start':start,'end':end,'value':value,'expect':expect,'result':result}


def witnesses(rng):
    v0,v1,v2=rng.sample(range(4),3)
    offset=rng.randrange(10000); scale=rng.randrange(1,6)
    def case(ops):
        for op in ops:
            op['start']=offset+op['start']*scale
            if op['end'] is not None:op['end']=offset+op['end']*scale
        return [v0,ops]
    return [
        case([_op('a','write',0,1,value=v1),_op('b','read',2,3,result=v0)]),
        case([_op('a','write',0,None,value=v1),_op('b','read',1,2,result=v1)]),
        case([_op('a','read',0,1,result=v0),_op('z','write',2,None,value=v1)]),
        case([_op('a','write',0,3,value=v1),_op('b','write',1,2,value=v2),_op('c','read',4,5,result=v1)]),
        case([_op('a','write',0,3,value=v1),_op('b','write',1,2,value=v2)]),
        case([_op('a','cas',0,3,value=v2,expect=v0,result=False),_op('b','write',1,2,value=v1),_op('c','read',4,5,result=v1)]),
    ]


def inputs(rng, count):
    for args in witnesses(rng)[:count]:yield args
    emitted=min(6,count)
    attempts=0
    while emitted<count:
        attempts+=1
        if attempts>count*1000:raise ValueError('insufficient balanced concurrency cases')
        n=rng.randrange(2,7)
        slots=list(range(2*n));rng.shuffle(slots)
        ops=[];pending=0
        for i in range(n):
            start,end=sorted(slots[2*i:2*i+2]);kind=rng.choice(['read','write','cas'])
            if pending<2 and rng.randrange(5)==0:end=None;pending+=1
            result=(rng.randrange(4) if kind=='read' else bool(rng.randrange(2)) if kind=='cas' else None) if end is not None else None
            ops.append(_op(chr(97+i),kind,start,end,value=rng.randrange(4),expect=rng.randrange(4),result=result))
        args=[rng.randrange(4),ops]
        want=(emitted%2)==0
        if reference(args)['linearizable'] != want:continue
        yield args
        emitted+=1
