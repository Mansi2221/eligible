"""Serialize a match result into FHIR (mCODE-aligned) resources.

Output leaves the system as FHIR so it can interoperate with EHRs, while the
internal reasoning substrate stays OMOP (ADR 0001). We emit a FHIR
``ResearchSubject`` linking patient to trial, with the per-criterion evaluation
carried as an extension for auditability.
"""

from __future__ import annotations

from eligible.matching.schema import TrialMatch

# FHIR R4 ResearchSubject.status value set (subset we use).
_STATUS_MAP = {
    "eligible": "eligible",
    "ineligible": "ineligible",
    "needs_review": "candidate",
}

ELIGIBILITY_EXT = "https://eligible.dev/fhir/StructureDefinition/criterion-evaluation"


def to_research_subject(match: TrialMatch) -> dict:
    """A FHIR ResearchSubject resource for one (patient, trial) decision."""
    return {
        "resourceType": "ResearchSubject",
        "status": _STATUS_MAP[match.decision],
        "study": {"identifier": {"system": "https://clinicaltrials.gov", "value": match.nct_id}},
        "individual": {"reference": f"Patient/{match.person_id}"},
        "extension": [
            {
                "url": ELIGIBILITY_EXT,
                "extension": [
                    {"url": "kind", "valueCode": v.kind},
                    {"url": "status", "valueCode": v.status},
                    {"url": "criterion", "valueString": v.text},
                    {"url": "evidence", "valueString": v.evidence},
                ],
            }
            for v in match.verdicts
        ],
    }


def to_bundle(matches: list[TrialMatch]) -> dict:
    """A FHIR searchset Bundle of ResearchSubject resources."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(matches),
        "entry": [{"resource": to_research_subject(m)} for m in matches],
    }
