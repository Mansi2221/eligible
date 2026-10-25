"""Per-trial eligibility matcher.

For one (patient, trial) pair, adjudicates every structured criterion in a
single reasoning call (pro tier + thinking mode). The thinking trace is captured
for the audit log, it is the justification an auditor needs for why a patient
was ruled in or out.
"""

from __future__ import annotations

import json

from eligible.criteria.schema import Criterion
from eligible.llm.client import DeepSeekClient, Tier
from eligible.llm.prompts import PromptBuilder
from eligible.matching.phenotype import PatientProfile
from eligible.matching.schema import CriterionVerdict, TrialMatch

SYSTEM = (
    "You are a clinical trial eligibility adjudicator. Given a patient profile and a "
    "trial's criteria, decide for EACH criterion whether it is met, not_met, or unknown "
    "based ONLY on the profile. If the profile lacks the information, say 'unknown', never "
    "guess. Give one short evidence phrase citing the profile for each decision."
)

INSTRUCTIONS = (
    'Return JSON: {"verdicts":[{"text","kind","status","evidence"}, ...]}. '
    "status is 'met'|'not_met'|'unknown'. kind is 'inclusion'|'exclusion' (copy from input). "
    "Return one verdict per input criterion, in order."
)


def _extract_json(content: str) -> dict:
    s = content.strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {content[:200]!r}")
    return json.loads(s[start : end + 1])


class TrialMatcher:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self.client = client or DeepSeekClient()
        self._prompt = PromptBuilder(system=SYSTEM).add_reference(INSTRUCTIONS)

    def evaluate(
        self, profile: PatientProfile, nct_id: str, criteria: list[Criterion]
    ) -> TrialMatch:
        crit_payload = [
            {"text": c.text, "kind": c.kind, "category": c.category, "attribute": c.attribute}
            for c in criteria
        ]
        query = (
            f"PATIENT PROFILE:\n{profile.to_prompt_text()}\n\n"
            f"TRIAL {nct_id} CRITERIA:\n{json.dumps(crit_payload, indent=2)}"
        )
        resp = self.client.complete(
            self._prompt.build(query), tier=Tier.PRO, thinking=True, temperature=0.0
        )
        payload = _extract_json(resp.content)
        verdicts = [CriterionVerdict(**v) for v in payload.get("verdicts", [])]
        return TrialMatch(
            nct_id=nct_id,
            person_id=profile.person_id,
            verdicts=verdicts,
            decision=TrialMatch.decide(verdicts),
            reasoning=resp.reasoning,
        )
