# Standard loop-else compatibility candidate

Fresh helper-screen responses encountered an interpreter rejection for `for ... else`. The visible Python subset advertises `for` and `while` and forbids several other constructs explicitly, but does not exclude loop `else`. This candidate removes that avoidable language mismatch. It implements ordinary Python exhaustion-versus-break behavior for both loop forms, including empty loops, continue, nested loops and control in an inner loop's else suite targeting an outer loop.

The interpreter remains bounded and never runs submitted code on the host. Source size, AST size, collections, call depth and execution-step limits are unchanged. Else suites consume the same ordinary step accounting. Break/continue validation is tightened so an else suite does not itself create a loop-control scope. Invalid control outside an enclosing loop remains rejected.

This is a separate runtime compatibility candidate. It does not change task cases, expected answers, reward formulas, helper-preservation treatment or the currently running screen. Replaying a saved answer after a runtime change is posthoc evidence, not a fresh model solve or evidence of training improvement. No frozen reviewed runtime, submission request, image or dataset is replaced.
