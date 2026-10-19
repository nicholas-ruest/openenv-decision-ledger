"""A bounded interpreter for a documented, pure subset of Python.

Candidate text is parsed, never passed to Python eval/exec or a host subprocess.
Only JSON-like values cross the interpreter boundary. No imports, attributes,
filesystem, network, reflection, exception handlers, or first-class callables.
"""
from __future__ import annotations

import ast
import copy
import math
import operator

MAX_SOURCE = 8192
MAX_ITEMS = 128
MAX_STRING = 2048
MAX_STEPS = 12000


class Rejected(ValueError):
    """Unsupported syntax, value, or exhausted interpreter work budget."""


class _Return(Exception):
    def __init__(self, value):
        self.value = value


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
    if type(value) in (list, tuple, dict) and len(value) <= MAX_ITEMS:
        for item in (value.items() if type(value) is dict else value):
            bounded(item, depth + 1)
        return value
    raise Rejected("value size/type limit")


class Program:
    _binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
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
               ast.Attribute)

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
        result = bounded(self._call(name, working, 0))
        if working != original:
            raise Rejected("input mutation forbidden")
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
                if type(values) not in (list, tuple, str, dict):
                    raise Rejected("iteration type unsupported")
                for value in values:
                    self._tick()
                    self._assign(node.target, value, frame, depth)
                    self._block(node.body, frame, depth)
            elif isinstance(node, ast.While):
                if node.orelse:
                    raise Rejected("loop else unsupported")
                while self._expr(node.test, frame, depth):
                    self._tick()
                    self._block(node.body, frame, depth)
            elif not isinstance(node, ast.Pass):
                raise Rejected("statement unsupported")

    def _binary_value(self, op, left, right):
        fn = self._binary.get(type(op))
        if fn is None:
            raise Rejected("operator unsupported")
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
                            "abs": abs, "sorted": sorted, "list": list}
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
            raise Rejected("call unsupported")
        raise Rejected("expression unsupported")
