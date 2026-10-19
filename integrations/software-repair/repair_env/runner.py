"""A bounded interpreter for a documented, pure subset of Python.

Candidate text is parsed, never passed to Python eval/exec or a host subprocess.
Only JSON-like values cross the interpreter boundary. No imports, attributes,
filesystem, network, reflection, exception handlers, or first-class callables.
"""
from __future__ import annotations

import ast
import copy
import json
import math
import operator

MAX_SOURCE = 8192
MAX_ITEMS = 128
MAX_STRING = 2048
MAX_STEPS = 80000


class Rejected(ValueError):
    """Unsupported syntax, value, or exhausted interpreter work budget."""


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


def bounded(value, depth=0):
    if depth > 8:
        raise Rejected("value nesting limit")
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
               ast.LShift, ast.Pow, ast.ListComp, ast.SetComp, ast.DictComp, ast.comprehension)

    def __init__(self, source: str):
        if type(source) is not str or len(source.encode()) > MAX_SOURCE:
            raise Rejected("source size limit")
        try:
            tree = ast.parse(source)
        except (SyntaxError, RecursionError, ValueError):
            raise Rejected("invalid Python syntax") from None
        nodes = list(ast.walk(tree))
        if len(nodes) > 512 or any(not isinstance(n, self._syntax) for n in nodes):
            raise Rejected("unsupported Python syntax")
        self.functions = {}
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
                raise Rejected("module must contain named functions only")
            args = node.args
            if (node.decorator_list or node.returns or args.posonlyargs or args.kwonlyargs
                    or args.vararg or args.kwarg or args.defaults or args.kw_defaults
                    or any(a.annotation or a.arg.startswith("_") for a in args.args)
                    or node.name in self.functions):
                raise Rejected("unsupported function signature")
            if any(isinstance(n, ast.FunctionDef) for stmt in node.body for n in ast.walk(stmt)):
                raise Rejected("nested functions unsupported")
            self.functions[node.name] = node
        if not 1 <= len(self.functions) <= 4:
            raise Rejected("one to four functions required")
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
        if depth > 6 or name not in self.functions:
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
        if isinstance(target, ast.Name) and not target.id.startswith("_"):
            frame[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            if type(value) not in (list, tuple) or len(value) != len(target.elts):
                raise Rejected("unpack shape differs")
            for part, item in zip(target.elts, value):
                self._assign(part, item, frame, depth)
        elif isinstance(target, ast.Subscript):
            container = self._expr(target.value, frame, depth)
            key = self._expr(target.slice, frame, depth)
            if type(container) not in (list, dict) or type(key) not in (str, int):
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
                if node.orelse:
                    raise Rejected("loop else unsupported")
                values = self._expr(node.iter, frame, depth)
                if type(values) not in (list, tuple, str, dict, set):
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
            elif isinstance(node, ast.While):
                if node.orelse:
                    raise Rejected("loop else unsupported")
                while self._expr(node.test, frame, depth):
                    self._tick()
                    try:
                        self._block(node.body, frame, depth)
                    except _Break:
                        break
                    except _Continue:
                        continue
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

    def _expr(self, node, frame, depth):
        self._tick()
        ev = lambda n: self._expr(n, frame, depth)
        if isinstance(node, ast.Constant):
            return bounded(node.value)
        if isinstance(node, ast.Name):
            if node.id not in frame or node.id.startswith("_"):
                raise Rejected("unknown variable")
            return frame[node.id]
        if isinstance(node, ast.Set):
            return bounded({ev(n) for n in node.elts})
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            if len(node.generators) > 2 or any(g.is_async for g in node.generators):
                raise Rejected("comprehension limit")
            result = {} if isinstance(node, ast.DictComp) else set() if isinstance(node, ast.SetComp) else []
            local = dict(frame)
            def collect(index):
                if index == len(node.generators):
                    if len(result) >= MAX_ITEMS:
                        raise Rejected("comprehension size limit")
                    if isinstance(node, ast.DictComp):
                        result[self._expr(node.key, local, depth)] = self._expr(node.value, local, depth)
                    elif isinstance(node, ast.SetComp):
                        result.add(self._expr(node.elt, local, depth))
                    else:
                        result.append(self._expr(node.elt, local, depth))
                    bounded(result)
                    return
                generator = node.generators[index]
                values = self._expr(generator.iter, local, depth)
                if type(values) not in (list, tuple, dict, set, str):
                    raise Rejected("comprehension input unsupported")
                for item in values:
                    self._tick()
                    self._assign(generator.target, item, local, depth)
                    if all(self._expr(condition, local, depth) for condition in generator.ifs):
                        collect(index + 1)
            collect(0)
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
            raise Rejected("call unsupported")
        raise Rejected("expression unsupported")
