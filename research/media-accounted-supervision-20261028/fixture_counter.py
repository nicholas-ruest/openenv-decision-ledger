"""Synthetic byte counter for offline composition; never production token costs."""
from observation_budget import TOKENIZER_SHA,canonical
class SyntheticByteCounter:
    mode='pinned_tokenizer';sha256=TOKENIZER_SHA
    def count(self,text):return len(text.encode())
    def context(self,messages):return self.count(canonical(messages))
