from __future__ import annotations


class SimpleTokenCounter:
    """
    Whitespace-split approximate token counter.

    This is intentionally crude and clearly flagged as such: real token
    counting must match whatever tokenizer the target LLM provider uses
    (e.g. tiktoken for OpenAI models), because token_saving_ratio (paper
    Eq. 4) is only meaningful if token counts are accurate. This class
    exists purely so Milestone 0 has zero external dependencies. Swap it
    for a real tokenizer in the LLM-provider-abstraction phase (section 15).
    """

    def count(self, text: str) -> int:
        return len(text.split())
