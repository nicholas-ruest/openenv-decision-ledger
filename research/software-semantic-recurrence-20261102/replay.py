"""Posthoc replay of a hash-leased private saved-example diagnostic.

This does not independently authenticate provider provenance or select a study.
Model source is interpreted by Native, never executed by host Python.
"""
import argparse, ast, copy, hashlib, itertools, json, subprocess, sys
from pathlib import Path

ORIGINAL = '4d69e68c55715d32699f155f068b38a77b8d6d8f'

def is_name(node, value):
    return isinstance(node, ast.Name) and node.id == value

def modify(source, directory, parent):
    tree = ast.parse(source)
    entries = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'classify_ignore']
    if len(entries) != 1:
        raise ValueError('unique entrypoint required')
    entry = entries[0]
    helpers = [ast.dump(n) for n in tree.body if n is not entry]
    if directory:
        if any(is_name(n, 'candidate_entry') for n in ast.walk(tree)):
            raise ValueError('fresh local binding required')
        loops = [n for n in entry.body if isinstance(n, ast.For) and is_name(n.target, 'p') and is_name(n.iter, 'unique_paths')]
        if len(loops) != 1:
            raise ValueError('original own-status loop required')
        positions = [i for i, n in enumerate(loops[0].body) if isinstance(n, ast.Assign) and len(n.targets) == 1 and is_name(n.targets[0], 'is_dir')]
        if len(positions) != 1:
            raise ValueError('one original type heuristic required')
        patch = ast.parse("is_dir = True\nfor candidate_entry in entries:\n    if candidate_entry['path'] == p:\n        is_dir = candidate_entry['is_dir']\n        break\n").body
        i = positions[0]
        loops[0].body[i:i+1] = patch
    if parent:
        matches = []
        for loop in entry.body:
            if not isinstance(loop, ast.For) or not is_name(loop.target, 'entry') or not is_name(loop.iter, 'entries'):
                continue
            for i, branch in enumerate(loop.body):
                if not isinstance(branch, ast.If) or not branch.body or not isinstance(branch.body[-1], ast.Continue):
                    continue
                test = branch.test
                if (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                        and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value == 0
                        and isinstance(test.left, ast.Call) and isinstance(test.left.func, ast.Attribute)
                        and is_name(test.left.func.value, 'own_status') and test.left.func.attr == 'get'
                        and test.left.args and is_name(test.left.args[0], 'path')):
                    matches.append((loop, i))
        if len(matches) != 1:
            raise ValueError('unique negation shortcut required')
        loop, i = matches[0]
        del loop.body[i]
    if [ast.dump(n) for n in tree.body if n is not entry] != helpers:
        raise ValueError('helper or other top-level code changed')
    return ast.unparse(ast.fix_missing_locations(tree)) + '\n'

def replay(report, expected_sha, runtime):
    report, runtime = Path(report), Path(runtime)
    raw = report.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('private report lease mismatch')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip() != ORIGINAL or subprocess.check_output(['git','status','--porcelain'],cwd=runtime,text=True).strip():
        raise ValueError('exact clean original Native runtime required')
    sys.path.insert(0, str(runtime / 'integrations/software-repair'))
    from repair_env.runner import Program
    from repair_env.environment import exact
    data = json.loads(raw)
    if len(data['rows']) != 6 or data['record']['category'] != 'partial':
        raise ValueError('six saved examples and original partial required')
    if hashlib.sha256(data['source'].encode()).hexdigest() != data['source_sha256']:
        raise ValueError('saved program hash mismatch')
    results = []
    for directory, parent in itertools.product((False, True), repeat=2):
        code = modify(data['source'], directory, parent) if directory or parent else data['source']
        program, rows = Program(code), []
        for row in data['rows']:
            actual = program.run('classify_ignore', copy.deepcopy(row['args']))
            rows.append({'example':row['example'], 'passes':exact(actual,row['expected'])})
            if not directory and not parent and not exact(actual,row['actual']):
                raise ValueError('unchanged replay differs from saved diagnostic')
        results.append({'directory_typing':directory,'parent_block':parent,'passes':sum(r['passes'] for r in rows),'rows':rows})
    if report.read_bytes() != raw:
        raise ValueError('private report changed')
    return {'variants':results,'runtime_source':ORIGINAL,'private_report_sha256':expected_sha,
            'helper_asts_changed':False,'posthoc':True,'public_examples_only':True,'hidden_access':False,
            'new_model_calls':0,'new_cases':0,'model_improvement':False,'actual_metaharness_executed':False}

if __name__ == '__main__':
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--report',required=True,type=Path);p.add_argument('--expected-sha',required=True)
    p.add_argument('--runtime',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args = p.parse_args()
    if args.output.exists():raise ValueError('fresh private output required')
    result = replay(args.report,args.expected_sha,args.runtime)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'variants':[{k:r[k] for k in ('directory_typing','parent_block','passes')} for r in result['variants']],'new_model_calls':0}))
