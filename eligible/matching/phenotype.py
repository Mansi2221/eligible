"""Build a structured patient phenotype from the OMOP CDM.

Deterministic (no LLM): reads a patient's conditions, medications, and latest
lab/vital values out of OMOP and assembles a compact `PatientProfile`. This is
what the retrieval and matching layers reason over, one clean object per
patient instead of raw EHR sprawl.
"""

from __future__ import annotations

import os

import duckdb
from pydantic import BaseModel

DB_PATH = os.environ.get("ELIGIBLE_DB", "data/eligible.duckdb")
REFERENCE_YEAR = 2026  # for age derivation


class LabValue(BaseModel):
    name: str
    value: float | None
    unit: str | None
    date: str | None


class PatientProfile(BaseModel):
    person_id: int
    source: str
    sex: str | None
    age: int | None
    race: str | None
    conditions: list[str]
    condition_codes: list[str]
    medications: list[str]
    labs: list[LabValue]

    def to_prompt_text(self) -> str:
        """Compact rendering for retrieval / LLM matching."""
        lines = [f"Patient (age {self.age}, sex {self.sex}, race {self.race or 'unknown'})."]
        if self.conditions:
            lines.append("Conditions: " + "; ".join(sorted(set(self.conditions))))
        if self.medications:
            lines.append("Medications: " + "; ".join(sorted(set(self.medications))[:25]))
        if self.labs:
            labtxt = "; ".join(
                f"{l.name}={l.value}{(' ' + l.unit) if l.unit else ''}" for l in self.labs
            )
            lines.append("Latest labs/vitals: " + labtxt)
        return "\n".join(lines)


# Lab/vital names worth surfacing for eligibility reasoning (LOINC display substrings).
KEY_LABS = [
    "Hemoglobin A1c",
    "Glomerular filtration rate",
    "Body mass index",
    "Body Weight",
    "Body Height",
    "Systolic Blood Pressure",
    "Diastolic Blood Pressure",
    "Creatinine",
    "Glucose",
]


class PhenotypeBuilder:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.con = duckdb.connect(db_path, read_only=True)

    def build(self, person_id: int) -> PatientProfile:
        demo = self.con.execute(
            "SELECT source, gender, year_of_birth, race FROM main.person WHERE person_id = ?",
            [person_id],
        ).fetchone()
        if demo is None:
            raise ValueError(f"no person with id {person_id}")
        source, sex, yob, race = demo
        age = (REFERENCE_YEAR - yob) if yob else None

        conditions = self.con.execute(
            """SELECT DISTINCT condition_name, condition_concept_code
               FROM main.condition_occurrence WHERE person_id = ?""",
            [person_id],
        ).fetchall()
        cond_names = [c[0] for c in conditions if c[0]]
        cond_codes = [c[1] for c in conditions if c[1]]

        meds = self.con.execute(
            "SELECT DISTINCT drug_name FROM main.drug_exposure WHERE person_id = ? AND drug_name IS NOT NULL",
            [person_id],
        ).fetchall()

        # latest value per key lab/vital
        like = " OR ".join(["measurement_name ILIKE ?"] * len(KEY_LABS))
        labs = self.con.execute(
            f"""
            SELECT measurement_name, value_as_number, unit_source_value, measurement_date
            FROM (
                SELECT *, row_number() OVER (
                    PARTITION BY measurement_name ORDER BY measurement_date DESC) rn
                FROM main.measurement
                WHERE person_id = ? AND ({like})
            ) WHERE rn = 1
            ORDER BY measurement_name""",
            [person_id, *[f"%{k}%" for k in KEY_LABS]],
        ).fetchall()

        return PatientProfile(
            person_id=person_id,
            source=source,
            sex=sex,
            age=age,
            race=race,
            conditions=cond_names,
            condition_codes=cond_codes,
            medications=[m[0] for m in meds],
            labs=[
                LabValue(name=r[0], value=r[1], unit=r[2], date=str(r[3]) if r[3] else None)
                for r in labs
            ],
        )

    def diabetic_cohort(self, limit: int = 10) -> list[int]:
        """Convenience: person_ids with a diabetes diagnosis (for demos)."""
        rows = self.con.execute(
            """SELECT DISTINCT person_id FROM main.condition_occurrence
               WHERE lower(condition_name) LIKE '%diabetes mellitus type 2%'
                  OR lower(condition_name) LIKE '%type 2 diabetes%'
               ORDER BY person_id LIMIT ?""",
            [limit],
        ).fetchall()
        return [r[0] for r in rows]
