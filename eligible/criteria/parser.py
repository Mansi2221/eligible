"""LLM-backed eligibility-criteria parser.

Converts a trial's free-text eligibility section into structured `Criterion`
records. Uses the flash tier (extraction, not reasoning) and a cache-aware
prompt: the stable system + schema instructions form the cached prefix, the
variable per-trial criteria text is appended last.
"""

from __future__ import annotations

import json

from eligible.criteria.schema import ParsedEligibility
from eligible.llm.client import DeepSeekClient, Tier
from eligible.llm.prompts import PromptBuilder

SYSTEM = (
    "You are a clinical trials data engineer. Convert eligibility criteria into "
    "structured JSON. Split compound sentences into atomic criteria. Classify each "
    "as inclusion or exclusion. Do not infer criteria that are not stated."
)

SCHEMA_HINT = (
    "Return a JSON object: {\"criteria\": [ {criterion}, ... ]}. Each criterion has:\n"
    "  kind: 'inclusion' | 'exclusion'\n"
    "  text: the original text, verbatim\n"
    "  category: 'condition'|'lab'|'medication'|'demographic'|'procedure'|'other'\n"
    "  attribute: normalized concept (e.g. 'HbA1c', 'age', 'type 2 diabetes') or null\n"
    "  operator: '>='|'<='|'>'|'<'|'=='|'in'|'exists'|'not_exists' or null\n"
    "  value: threshold/value as string or null\n"
    "  unit: unit or null\n"
    "  temporal: time window (e.g. 'within 6 months') or null\n"
    "Example: 'Age 18-70 years' ->\n"
    '  {"kind":"inclusion","text":"Age 18-70 years","category":"demographic",'
    '"attribute":"age","operator":"in","value":"18-70","unit":"years","temporal":null}'
)


def _extract_json(content: str) -> dict:
    """Pull a JSON object out of the model response (tolerates code fences)."""
    s = content.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if "```" in s[3:] else s
        s = s.lstrip("json").strip("`").strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in response: {content[:200]!r}")
    return json.loads(s[start : end + 1])


class CriteriaParser:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self.client = client or DeepSeekClient()
        self._prompt = PromptBuilder(system=SYSTEM).add_reference(SCHEMA_HINT)

    def parse(self, nct_id: str, eligibility_text: str) -> ParsedEligibility:
        messages = self._prompt.build(
            f"Trial {nct_id} eligibility criteria:\n\n{eligibility_text}"
        )
        resp = self.client.complete(messages, tier=Tier.FLASH, temperature=0.0)
        payload = _extract_json(resp.content)
        return ParsedEligibility(nct_id=nct_id, criteria=payload.get("criteria", []))
