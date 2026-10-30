"""A bounded interpreter for a documented, pure subset of Python.

Candidate text is parsed, never passed to Python eval/exec or a host subprocess.
Only JSON-like values cross the interpreter boundary. No imports, arbitrary attributes,
filesystem, network, reflection, exception handlers, or first-class callables.
"""
from __future__ import annotations

import ast
import copy
import json
import math
import operator
from collections import ChainMap

MAX_SOURCE = 8192
MAX_ITEMS = 128
MAX_STRING = 2048
MAX_STEPS = 80000
MAX_AST_NODES = 2048


class Rejected(ValueError):
    """Unsupported syntax, value, or exhausted interpreter work budget."""


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _Generator:
    """Internal lazy iterator with a bounded yield count; never exported as JSON."""
    def __init__(self, iterator):
        self.iterator, self.count = iterator, 0

    def __iter__(self):
        return self

    def __next__(self):
        value = next(self.iterator)
        self.count += 1
        if self.count > MAX_ITEMS:
            raise Rejected("generator yield limit")
        return bounded(value)


def bounded(value, depth=0):
    if depth > 8:
        raise Rejected("value nesting limit")
    if isinstance(value, _Generator):
        return value
    if value is None or type(value) is bool:
        return value
    if type(value) is int and value.bit_length() <= 128:
        return value
    if type(value) is float and math.isfinite(value) and abs(value) <= 10**12:
        return value
    if type(value) is str and len(value) <= MAX_STRING:
        return value
    if type(value) in (list, tuple, dict, set) and len(value) <= MAX_ITEMS:
        for item in (value.items() if type(value) is dict else value):
            bounded(item, depth + 1)
        return value
    raise Rejected("value size/type limit")


class Program:
    _binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
               ast.BitAnd: operator.and_, ast.BitOr: operator.or_, ast.LShift: operator.lshift,
               ast.Pow: operator.pow}
    _compare = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
                ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
                ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
                ast.Is: operator.is_, ast.IsNot: operator.is_not}
    _syntax = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
               ast.Assign, ast.AugAssign, ast.Expr, ast.If, ast.For, ast.While,
               ast.Pass, ast.Name, ast.Constant, ast.List, ast.Tuple, ast.Dict,
               ast.Subscript, ast.Slice, ast.BinOp, ast.UnaryOp, ast.BoolOp,
               ast.Compare, ast.Call, ast.IfExp, ast.Load, ast.Store,
               ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
               ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
               ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
               ast.Attribute, ast.Break, ast.Continue, ast.Set, ast.BitAnd, ast.BitOr,
               ast.LShift, ast.Pow, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
               ast.keyword, ast.Lambda)

    def __init__(self, source: str):
        if type(source) is not str or len(source.encode()) > MAX_SOURCE:
            raise Rejected("source size limit")
        try:
            tree = ast.parse(source)
        except (SyntaxError, RecursionError, ValueError):
            raise Rejected("invalid Python syntax") from None
        nodes = list(ast.walk(tree))
        if len(nodes) > MAX_AST_NODES:
            raise Rejected("AST node limit2048")
        if any(not isinstance(n, self._syntax) for n in nodes):
            raise Rejected("unsupported Python syntax")
        self.functions = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("__"):
                raise Rejected("module must contain named functions only")
            args = node.args
            if (node.decorator_list or node.returns or args.posonlyargs or args.kwonlyargs
                    or args.vararg or args.kwarg or args.defaults or args.kw_defaults
                    or any(a.annotation or a.arg.startswith("__") for a in args.args)
                    or node.name in self.functions):
                raise Rejected("unsupported function signature")
            if any(isinstance(n, ast.FunctionDef) for stmt in node.body for n in ast.walk(stmt)):
                raise Rejected("nested functions unsupported")
            self.functions[node.name] = node
        if not 1 <= len(self.functions) <= 16:
            raise Rejected("one to sixteen functions required")
        parents = {id(child): parent for parent in nodes for child in ast.iter_child_nodes(parent)}
        for node in nodes:
            if isinstance(node, ast.keyword):
                call = parents[id(node)]
                is_method = (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                             and call.func.attr == "sort" and not call.args)
                is_sorted = (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                             and call.func.id == "sorted" and len(call.args) == 1)
                if (not (is_method or is_sorted)
                        or node.arg not in ("key", "reverse")
                        or len({item.arg for item in call.keywords}) != len(call.keywords)):
                    raise Rejected("only list.sort/sorted key/reverse keywords supported")
            if isinstance(node, ast.Lambda):
                parent = parents[id(node)]
                args = node.args
                if (not isinstance(parent, ast.keyword) or parent.arg != "key"
                        or len(args.args) != 1 or args.args[0].arg.startswith("__")
                        or args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg
                        or args.defaults or args.kw_defaults or args.args[0].annotation):
                    raise Rejected("lambda only supported as a one-argument sort key")
            if isinstance(node, (ast.Break, ast.Continue)):
                child = node
                parent = parents[id(child)]
                while not isinstance(parent, ast.FunctionDef):
                    if isinstance(parent, (ast.For, ast.While)) and child in parent.body:
                        break
                    child = parent
                    parent = parents[id(child)]
                if isinstance(parent, ast.FunctionDef):
                    raise Rejected("loop control outside a lexical loop")
        self.fingerprint = ast.dump(tree, include_attributes=False)

    def run(self, name, args):
        self.steps = MAX_STEPS
        original = copy.deepcopy(bounded(args))
        working = copy.deepcopy(original)
        try:
            result = bounded(self._call(name, working, 0))
        except (_Break, _Continue):
            raise Rejected("loop control outside a loop") from None
        if working != original:
            raise Rejected("input mutation forbidden")
        try:
            json.dumps(result, allow_nan=False)
        except (TypeError, ValueError):
            raise Rejected("result must be JSON serializable") from None
        return result

    def _tick(self):
        self.steps -= 1
        if self.steps < 0:
            raise Rejected("execution step limit")

    def _call(self, name, args, depth):
        self._tick()
        if depth > 16 or name not in self.functions:
            raise Rejected("function/depth limit")
        function = self.functions[name]
        if len(args) != len(function.args.args):
            raise Rejected("argument count differs")
        frame = dict(zip((a.arg for a in function.args.args), args))
        try:
            self._block(function.body, frame, depth + 1)
        except _Return as result:
            return result.value
        return None

    def _assign(self, target, value, frame, depth):
        self._tick()
        bounded(value)
        if isinstance(target, ast.Name) and not target.id.startswith("__"):
            frame[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            if type(value) not in (list, tuple) or len(value) != len(target.elts):
                raise Rejected("unpack shape differs")
            for part, item in zip(target.elts, value):
                self._assign(part, item, frame, depth)
        elif isinstance(target, ast.Subscript):
            container = self._expr(target.value, frame, depth)
            key = self._expr(target.slice, frame, depth)
            # Tuple keys already work in dictionary literals/comprehensions and
            # lookups. Assignment must accept the same bounded immutable keys;
            # a tuple is not, however, a valid list index. No host calls added.
            valid_key = type(key) in (str, int) or (type(container) is dict and type(key) is tuple)
            if type(container) not in (list, dict) or not valid_key:
                raise Rejected("assignment target unsupported")
            if type(container) is dict and key not in container and len(container) >= MAX_ITEMS:
                raise Rejected("mapping size limit")
            container[key] = value
            bounded(container)
        else:
            raise Rejected("assignment target unsupported")

    def _block(self, statements, frame, depth):
        for node in statements:
            self._tick()
            if isinstance(node, ast.Return):
                raise _Return(self._expr(node.value, frame, depth) if node.value else None)
            if isinstance(node, ast.Assign):
                value = self._expr(node.value, frame, depth)
                for target in node.targets:
                    self._assign(target, value, frame, depth)
            elif isinstance(node, ast.AugAssign):
                value = self._binary_value(node.op, self._expr(node.target, frame, depth),
                                           self._expr(node.value, frame, depth))
                self._assign(node.target, value, frame, depth)
            elif isinstance(node, ast.Expr):
                self._expr(node.value, frame, depth)
            elif isinstance(node, ast.If):
                branch = node.body if self._expr(node.test, frame, depth) else node.orelse
                self._block(branch, frame, depth)
            elif isinstance(node, ast.For):
                values = self._expr(node.iter, frame, depth)
                if type(values) not in (list, tuple, str, dict, set, _Generator):
                    raise Rejected("iteration type unsupported")
                for value in values:
                    self._tick()
                    self._assign(node.target, value, frame, depth)
                    try:
                        self._block(node.body, frame, depth)
                    except _Break:
                        break
                    except _Continue:
                        continue
                else:
                    self._block(node.orelse, frame, depth)
            elif isinstance(node, ast.While):
                while self._expr(node.test, frame, depth):
                    self._tick()
                    try:
                        self._block(node.body, frame, depth)
                    except _Break:
                        break
                    except _Continue:
                        continue
                else:
                    self._block(node.orelse, frame, depth)
            elif isinstance(node, ast.Break):
                raise _Break()
            elif isinstance(node, ast.Continue):
                raise _Continue()
            elif not isinstance(node, ast.Pass):
                raise Rejected("statement unsupported")

    def _binary_value(self, op, left, right):
        fn = self._binary.get(type(op))
        if fn is None:
            raise Rejected("operator unsupported")
        if isinstance(op, (ast.BitAnd, ast.BitOr)) and type(left) is set and type(right) is set:
            return bounded(fn(left, right))
        if isinstance(op, (ast.Pow, ast.LShift, ast.BitAnd, ast.BitOr)):
            if type(left) is not int or type(right) is not int:
                raise Rejected("integer operator requires integers")
            if isinstance(op, (ast.Pow, ast.LShift)):
                if not 0 <= right <= 127:
                    raise Rejected("exponent/shift limit")
                size = left.bit_length() * right if isinstance(op, ast.Pow) else left.bit_length() + right
                if size > 128:
                    raise Rejected("integer size limit")
        if isinstance(op, ast.Mult):
            for sequence, count in ((left, right), (right, left)):
                if type(sequence) in (list, tuple, str) and type(count) is int:
                    limit = MAX_STRING if type(sequence) is str else MAX_ITEMS
                    if len(sequence) * max(0, count) > limit:
                        raise Rejected("sequence multiplication limit")
        return bounded(fn(left, right))

    def _sort_key(self, node, frame, depth):
        if isinstance(node, ast.Constant) and node.value is None:
            return None
        if isinstance(node, ast.Lambda):
            argument = node.args.args[0].arg
            def evaluate(item):
                self._tick()
                return bounded(self._expr(node.body, ChainMap({argument: item}, frame), depth))
            return evaluate
        if isinstance(node, ast.Name):
            name = node.id
            if name in self.functions:
                def evaluate(item):
                    return bounded(self._call(name, [item], depth))
                return evaluate
            if name in ("len", "abs"):
                function = len if name == "len" else abs
                def evaluate(item):
                    self._tick()
                    return bounded(function(item))
                return evaluate
        raise Rejected("sort key must be None, a supported named function or a lambda")

    def _expr(self, node, frame, depth):
        self._tick()
        ev = lambda n: self._expr(n, frame, depth)
        if isinstance(node, ast.Constant):
            return bounded(node.value)
        if isinstance(node, ast.Name):
            if node.id not in frame or node.id.startswith("__"):
                raise Rejected("unknown variable")
            return frame[node.id]
        if isinstance(node, ast.Set):
            return bounded({ev(n) for n in node.elts})
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            if len(node.generators) > 2 or any(g.is_async for g in node.generators):
                raise Rejected("comprehension limit")
            result = {} if isinstance(node, ast.DictComp) else set() if isinstance(node, ast.SetComp) else []
            # Keep comprehension locals separate while preserving Python's late
            # binding of outer variables in a lazy generator expression.
            local = ChainMap({}, frame)
            first_values = ev(node.generators[0].iter)
            if type(first_values) not in (list, tuple, dict, set, str, _Generator):
                raise Rejected("comprehension input unsupported")
            first_iterator = iter(first_values)
            def generate(index):
                if index == len(node.generators):
                    if isinstance(node, ast.DictComp):
                        yield (self._expr(node.key, local, depth), self._expr(node.value, local, depth))
                    else:
                        yield self._expr(node.elt, local, depth)
                    return
                generator = node.generators[index]
                values = first_values if index == 0 else self._expr(generator.iter, local, depth)
                if type(values) not in (list, tuple, dict, set, str, _Generator):
                    raise Rejected("comprehension input unsupported")
                for item in (first_iterator if index == 0 else values):
                    self._tick()
                    self._assign(generator.target, item, local, depth)
                    if all(self._expr(condition, local, depth) for condition in generator.ifs):
                        yield from generate(index + 1)
            iterator = _Generator(generate(0))
            if isinstance(node, ast.GeneratorExp):
                return iterator
            for item in iterator:
                if isinstance(node, ast.DictComp):
                    result[item[0]] = item[1]
                elif isinstance(node, ast.SetComp):
                    result.add(item)
                else:
                    result.append(item)
                bounded(result)
            return result
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [ev(n) for n in node.elts]
            return bounded(tuple(values) if isinstance(node, ast.Tuple) else values)
        if isinstance(node, ast.Dict):
            return bounded({ev(k): ev(v) for k, v in zip(node.keys, node.values)})
        if isinstance(node, ast.BinOp):
            return self._binary_value(node.op, ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp):
            fn = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}.get(type(node.op))
            return bounded(fn(ev(node.operand)))
        if isinstance(node, ast.BoolOp):
            result = ev(node.values[0])
            for value in node.values[1:]:
                if isinstance(node.op, ast.And) and not result or isinstance(node.op, ast.Or) and result:
                    break
                result = ev(value)
            return result
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = ev(right_node)
                if not self._compare[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return ev(node.body if ev(node.test) else node.orelse)
        if isinstance(node, ast.Slice):
            return slice(ev(node.lower) if node.lower else None,
                         ev(node.upper) if node.upper else None,
                         ev(node.step) if node.step else None)
        if isinstance(node, ast.Subscript):
            return bounded(ev(node.value)[ev(node.slice)])
        if (isinstance(node, ast.Call) and node.keywords
                and ((isinstance(node.func, ast.Attribute) and node.func.attr == "sort")
                     or (isinstance(node.func, ast.Name) and node.func.id == "sorted"))):
            is_sorted = isinstance(node.func, ast.Name)
            if is_sorted:
                if len(node.args) != 1:
                    raise Rejected("sorted requires one positional iterable")
                value = ev(node.args[0])
                if type(value) not in (list, tuple, str, dict, set):
                    raise Rejected("sorted iterable unsupported")
                value = list(value)
            else:
                value = ev(node.func.value)
                if type(value) is not list or node.args:
                    raise Rejected("sort receiver/arguments unsupported")
            key = None
            reverse = False
            for keyword in node.keywords:
                if keyword.arg == "key":
                    key = self._sort_key(keyword.value, frame, depth)
                elif keyword.arg == "reverse":
                    reverse = ev(keyword.value)
                    if type(reverse) not in (bool, int):
                        raise Rejected("sort reverse must be an integer or bool")
                else:
                    raise Rejected("sort keyword unsupported")
            # CPython supplies stable ordering and one key evaluation per item.
            # The callback remains in this interpreter, sharing its step/depth
            # limits; no submitted source is executed by the host Python VM.
            value.sort(key=key, reverse=reverse)
            bounded(value)
            return value if is_sorted else None
        if isinstance(node, ast.Call) and not node.keywords:
            args = [ev(n) for n in node.args]
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name in self.functions:
                    return self._call(name, args, depth)
                if name == "range":
                    result = range(*args)
                    if len(result) > MAX_ITEMS:
                        raise Rejected("range size limit")
                    return list(result)
                builtins = {"len": len, "min": min, "max": max, "sum": sum,
                            "abs": abs, "sorted": sorted, "list": list, "set": set,
                            "tuple": tuple, "dict": dict, "any": any, "all": all,
                            "enumerate": lambda *xs: list(enumerate(*xs)),
                            "zip": lambda *xs: list(zip(*xs))}
                if name in builtins:
                    # list(integer) is invalid; no unbounded generator is reachable.
                    return bounded(builtins[name](*args))
            elif isinstance(node.func, ast.Attribute):
                value = ev(node.func.value)
                if type(value) is str:
                    methods = {"split": value.split, "rsplit": value.rsplit,
                               "startswith": value.startswith, "endswith": value.endswith,
                               "replace": value.replace, "strip": value.strip,
                               "lstrip": value.lstrip, "rstrip": value.rstrip,
                               "find": value.find, "rfind": value.rfind, "count": value.count,
                               "join": value.join, "lower": value.lower, "upper": value.upper}
                    if node.func.attr in methods:
                        return bounded(methods[node.func.attr](*args))
                if node.func.attr == "append" and type(value) is list and len(args) == 1:
                    if len(value) >= MAX_ITEMS:
                        raise Rejected("list size limit")
                    value.append(args[0])
                    bounded(value)
                    return None
                if node.func.attr == "get" and type(value) is dict and len(args) in (1, 2):
                    return bounded(value.get(*args))
                if type(value) is dict and not args and node.func.attr in ("items", "keys", "values"):
                    methods = {"items": value.items, "keys": value.keys, "values": value.values}
                    return bounded(list(methods[node.func.attr]()))
                if node.func.attr == "pop" and type(value) in (list, dict):
                    return bounded(value.pop(*args))
                if type(value) is list and not args and node.func.attr in ("sort", "reverse"):
                    if node.func.attr == "sort":
                        value.sort()
                    else:
                        value.reverse()
                    return None
                if type(value) is set and node.func.attr == "add" and len(args) == 1:
                    if len(value) >= MAX_ITEMS:
                        raise Rejected("set size limit")
                    value.add(args[0])
                    return None
                if type(value) in (set, list) and node.func.attr == "remove" and len(args) == 1:
                    value.remove(args[0])
                    return None
                if type(value) is set and node.func.attr == "discard" and len(args) == 1:
                    value.discard(args[0])
                    return None
                if type(value) in (list, dict, set) and node.func.attr == "copy" and not args:
                    return bounded(value.copy())
                if type(value) in (list, set) and len(args) == 1 and node.func.attr in ("extend", "update"):
                    items = args[0]
                    if type(items) not in (list, tuple, set) or len(items) + len(value) > MAX_ITEMS:
                        raise Rejected("collection update limit")
                    if type(value) is list and node.func.attr == "extend":
                        value.extend(items)
                    elif type(value) is set and node.func.attr == "update":
                        value.update(items)
                    else:
                        raise Rejected("collection method unsupported")
                    bounded(value)
                    return None
                if type(value) is set and node.func.attr in ("union", "intersection", "difference"):
                    if len(args) > 4 or any(type(item) not in (list, tuple, dict, set) or len(item) > MAX_ITEMS for item in args):
                        raise Rejected("set method input limit")
                    methods = {"union": value.union, "intersection": value.intersection, "difference": value.difference}
                    return bounded(methods[node.func.attr](*args))
            raise Rejected("call unsupported")
        raise Rejected("expression unsupported")
