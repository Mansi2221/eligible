"""LLM classifier for the 13 n2c2 criteria.

One pro+thinking call per patient: the 13 criterion definitions form the stable
(cached) prompt prefix; the variable patient record is appended last. Returns a
met / not met label per criterion, the same adjudication the trial matcher does,
pointed at the benchmark's fixed criteria and free-text records.
"""

from __future__ import annotations

import json

from eligible.eval.n2c2.criteria import CRITERIA_CODES, MET, N2C2_CRITERIA, NOT_MET
from eligible.llm.client import DeepSeekClient, Tier
from eligible.llm.prompts import PromptBuilder

SYSTEM = (
    "You are a clinical trial eligibility annotator. Read the patient record and "
    "decide, for each listed criterion, whether the patient MEETS it. Judge only "
    "on evidence in the record."
)

_DEFS = "\n".join(f"- {code}: {desc}" for code, desc in N2C2_CRITERIA.items())
INSTRUCTIONS = (
    "Criteria:\n" + _DEFS + "\n\n"
    'Return a JSON object mapping every criterion code to "met" or "not met", '
    'e.g. {"ABDOMINAL":"not met","HBA1C":"met", ...}. Include all 13 codes.'
)


def _normalize(value: str | None) -> str:
    return MET if (value or "").strip().lower() == MET else NOT_MET


def _extract_json(content: str) -> dict:
    s = content.strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {content[:200]!r}")
    return json.loads(s[start : end + 1])


class N2C2Classifier:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self.client = client or DeepSeekClient()
        self._prompt = PromptBuilder(system=SYSTEM).add_reference(INSTRUCTIONS)

    def classify(self, text: str) -> dict[str, str]:
        resp = self.client.complete(
            self._prompt.build(f"PATIENT RECORD:\n{text}"),
            tier=Tier.PRO,
            thinking=True,
            temperature=0.0,
        )
        raw = _extract_json(resp.content)
        return {code: _normalize(raw.get(code)) for code in CRITERIA_CODES}
