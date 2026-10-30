# Bounded bool-call compatibility: posthoc result

Source `fecf100bffa6625fc3ac11e9f0268854a78fdc73` adds only direct calls to Python's `bool` to the existing bounded interpreter builtin map. It exposes no first-class host type, attributes, imports, extra syntax, fuel, or allocation limit.

Five new static compatibility tests passed: JSON-value truthiness against CPython, zero arguments, generator-object truthiness without iteration, arity/keyword rejection, inaccessible first-class types/attributes, and user-function shadowing. A selected four-file pytest suite passed **71 tests and 14 subtests**. A broader six-file run exceeded its 50-second test budget before completing; it remains incomplete. This source is not runtime-image qualified.

Independent posthoc replay of all eight saved final attempts from the parent-status screen changed one `call unsupported` execution failure into a partial result (0.7167). The other seven classifications and rewards were unchanged. **Full solves remained 0/8 before and after.** A separate candidate's string-method failure on a non-string value remained an execution failure. No model reply was run with host Python; replay used the bounded native interpreter.

These are saved-response counterfactuals with zero new model calls. No fresh comparison, model improvement, training, promotion, leaderboard gain, Arena submission, or HF replacement is claimed. The compatibility change is separate from other interpreter candidates, frozen v12, and the active thinking-request screen.
