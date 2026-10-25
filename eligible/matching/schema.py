"""Matching result types + the eligibility decision rule."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Status = Literal["met", "not_met", "unknown"]
Decision = Literal["eligible", "ineligible", "needs_review"]


class CriterionVerdict(BaseModel):
    text: str
    kind: Literal["inclusion", "exclusion"]
    status: Status
    evidence: str


class TrialMatch(BaseModel):
    nct_id: str
    person_id: int
    verdicts: list[CriterionVerdict]
    decision: Decision
    reasoning: str | None = None  # captured chain-of-thought (audit)

    @staticmethod
    def decide(verdicts: list[CriterionVerdict]) -> Decision:
        """Eligible iff every inclusion is met and no exclusion is met.
        Any unresolved criterion drops the pair to needs_review (never a silent pass).
        """
        for v in verdicts:
            if v.kind == "inclusion" and v.status == "not_met":
                return "ineligible"
            if v.kind == "exclusion" and v.status == "met":
                return "ineligible"
        if any(v.status == "unknown" for v in verdicts):
            return "needs_review"
        return "eligible"
