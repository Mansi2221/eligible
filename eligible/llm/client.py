"""DeepSeek client.

DeepSeek exposes an OpenAI-compatible API, so we drive it with the ``openai``
SDK pointed at DeepSeek's base URL. Two tiers are exposed:

- ``flash``, cheap, for extraction / formatting / routing.
- ``pro``  , reasoning tier; ``thinking=True`` enables chain-of-thought, which
  we capture (``reasoning_content``) for the audit trail on high-stakes calls.

Model IDs are configured via env so the code doesn't rot as names change.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from openai import OpenAI

from eligible.config import Settings, get_settings


class Tier(str, Enum):
    FLASH = "flash"
    PRO = "pro"


@dataclass
class LLMResponse:
    content: str
    reasoning: str | None  # chain-of-thought when thinking mode is on
    model: str
    usage: dict


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = OpenAI(
            api_key=self._settings.deepseek_api_key,
            base_url=self._settings.deepseek_base_url,
        )

    def _model_for(self, tier: Tier) -> str:
        return (
            self._settings.deepseek_model_pro
            if tier is Tier.PRO
            else self._settings.deepseek_model_flash
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        tier: Tier = Tier.FLASH,
        thinking: bool = False,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Single completion.

        ``thinking`` should only be enabled on the ``pro`` tier for high-stakes
        reasoning (e.g. eligibility matching), reasoning tokens bill as output,
        so leaving it on for routine extraction is wasteful.
        """
        extra_body = {"thinking": {"type": "enabled"}} if thinking else None
        resp = self._client.chat.completions.create(
            model=self._model_for(tier),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
        choice = resp.choices[0].message
        reasoning = getattr(choice, "reasoning_content", None)
        return LLMResponse(
            content=choice.content or "",
            reasoning=reasoning,
            model=resp.model,
            usage=resp.usage.model_dump() if resp.usage else {},
        )
