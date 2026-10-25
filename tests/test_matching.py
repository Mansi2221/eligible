"""Tests for the eligibility decision rule and matcher wiring (no API key)."""

from eligible.criteria.schema import Criterion
from eligible.llm.client import LLMResponse
from eligible.matching.matcher import TrialMatcher
from eligible.matching.phenotype import PatientProfile
from eligible.matching.schema import CriterionVerdict, TrialMatch


def _v(kind, status):
    return CriterionVerdict(text="x", kind=kind, status=status, evidence="e")


def test_decision_eligible_when_all_pass():
    v = [_v("inclusion", "met"), _v("exclusion", "not_met")]
    assert TrialMatch.decide(v) == "eligible"


def test_decision_ineligible_on_failed_inclusion():
    assert TrialMatch.decide([_v("inclusion", "not_met")]) == "ineligible"


def test_decision_ineligible_on_met_exclusion():
    assert TrialMatch.decide([_v("exclusion", "met")]) == "ineligible"


def test_decision_needs_review_on_unknown():
    v = [_v("inclusion", "met"), _v("inclusion", "unknown")]
    assert TrialMatch.decide(v) == "needs_review"


class FakeClient:
    def complete(self, messages, **kwargs) -> LLMResponse:
        content = (
            '{"verdicts":[{"text":"Age 18-70","kind":"inclusion","status":"met","evidence":"age 63"},'
            '{"text":"type 1 diabetes","kind":"exclusion","status":"not_met","evidence":"has T2D"}]}'
        )
        return LLMResponse(content=content, reasoning="patient is 63 with T2D", model="fake", usage={})


def test_matcher_produces_eligible_match():
    profile = PatientProfile(
        person_id=1, source="synthea", sex="MALE", age=63, race="White",
        conditions=["Type 2 diabetes mellitus"], condition_codes=["44054006"],
        medications=["Metformin"], labs=[],
    )
    criteria = [
        Criterion(kind="inclusion", text="Age 18-70", category="demographic"),
        Criterion(kind="exclusion", text="type 1 diabetes", category="condition"),
    ]
    match = TrialMatcher(client=FakeClient()).evaluate(profile, "NCT001", criteria)
    assert match.decision == "eligible"
    assert len(match.verdicts) == 2
    assert match.reasoning == "patient is 63 with T2D"
