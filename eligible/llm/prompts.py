"""Cache-aware prompt assembly.

DeepSeek (like most providers) caches on an exact, continuous prompt prefix.
So the ordering rule is: everything *stable and reused* goes first, everything
*variable and per-request* goes last. Break the prefix and the cache is lost.

Assemble messages as:

    [ system instructions ]      <- stable
    [ reference blocks ... ]     <- stable (schemas, trial protocols, few-shot)
    [ the variable user query ]  <- changes every call

so that repeated evaluations against the same protocol/schema hit the cache.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromptBuilder:
    """Builds an OpenAI-style messages list with a stable prefix."""

    system: str
    # Stable reference material kept identical across calls (schemas, protocols,
    # few-shot examples, large reference docs). Order matters and must not vary.
    reference_blocks: list[str] = field(default_factory=list)

    def add_reference(self, block: str) -> "PromptBuilder":
        """Append a stable reference block to the cached prefix."""
        self.reference_blocks.append(block)
        return self

    def build(self, query: str) -> list[dict[str, str]]:
        """Return messages: stable prefix first, the variable query last."""
        prefix_parts = [self.system, *self.reference_blocks]
        messages = [{"role": "system", "content": "\n\n".join(prefix_parts)}]
        messages.append({"role": "user", "content": query})
        return messages
