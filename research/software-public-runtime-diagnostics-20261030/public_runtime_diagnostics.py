"""Source locations from bounded Native execution of supplied public examples only."""
import ast
from repair_env.runner import Program, Rejected

ERRORS = (Rejected, ArithmeticError, TypeError, ValueError, KeyError, IndexError,
          RecursionError, RuntimeError)
MAX_PUBLIC_CASES = 8


class TracedProgram(Program):
    """Preserve Native evaluation and limits; observe the first failing expression."""
    def run(self, name, args):
        self.source_location = None
        return super().run(name, args)

    def _expr(self, node, frame, depth):
        try:
            return super()._expr(node, frame, depth)
        except ERRORS as error:
            if self.source_location is None:
                line, column = getattr(node, 'lineno', None), getattr(node, 'col_offset', None)
                if type(line) is int and line > 0 and type(column) is int and column >= 0:
                    self.source_location = dict(line=line, byte_column=column,
                                                node=type(node).__name__)
                    target = node.func if isinstance(node, ast.Call) else None
                    if isinstance(target, ast.Name) and len(target.id) <= 64:
                        self.source_location['call'] = target.id
            raise


def diagnose_public(source, task):
    """No hidden cases, expected values, actual values, arguments or exception text."""
    try:
        program = TracedProgram(source)
    except (Rejected, RecursionError, UnicodeError):
        return None  # Compile diagnostics are a separate intervention.
    diagnostics = []
    for index, case in enumerate(task.public):
        if index == MAX_PUBLIC_CASES:
            break
        try:
            program.run(task.entrypoint, case.args)
        except ERRORS as error:
            if program.source_location is not None:
                diagnostics.append(dict(public_example=index + 1,
                                        error_type=type(error).__name__,
                                        **program.source_location))
    return (dict(kind='public_example_runtime_source_locations',
                 scope='supplied_public_examples_only', diagnostics=diagnostics)
            if diagnostics else None)
