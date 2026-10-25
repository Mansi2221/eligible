"""Structured representation of trial eligibility criteria.

Free-text criteria ("HbA1c between 6.5% and 9.5%", "no type 1 diabetes") are
parsed into these machine-checkable records so the matching layer can evaluate
each one against a patient's OMOP profile instead of re-reading prose per patient.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["inclusion", "exclusion"]
Category = Literal["condition", "lab", "medication", "demographic", "procedure", "other"]
Operator = Literal[">=", "<=", ">", "<", "==", "in", "exists", "not_exists"]


class Criterion(BaseModel):
    kind: Kind = Field(description="Whether meeting this makes a patient eligible or excluded.")
    text: str = Field(description="The original criterion text, verbatim.")
    category: Category
    attribute: str | None = Field(
        default=None, description="Normalized concept, e.g. 'HbA1c', 'age', 'type 2 diabetes'."
    )
    operator: Operator | None = None
    value: str | None = Field(default=None, description="Threshold or value, e.g. '6.5', '18'.")
    unit: str | None = None
    temporal: str | None = Field(default=None, description="Time window, e.g. 'within 6 months'.")


class ParsedEligibility(BaseModel):
    nct_id: str
    criteria: list[Criterion]

    @property
    def inclusion(self) -> list[Criterion]:
        return [c for c in self.criteria if c.kind == "inclusion"]

    @property
    def exclusion(self) -> list[Criterion]:
        return [c for c in self.criteria if c.kind == "exclusion"]
