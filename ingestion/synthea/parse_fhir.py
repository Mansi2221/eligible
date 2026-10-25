"""Parse Synthea FHIR R4 patient bundles into flat raw tables in DuckDB.

Each Synthea file is a transaction Bundle for a single synthetic patient. We
extract the clinical resources we need for OMOP (Patient, Condition,
MedicationRequest, numeric Observations) and land them in a ``raw`` schema.
Name/telecom/address are deliberately dropped, no PHI-shaped fields carried
into the model.

Coding systems (confirmed): Condition=SNOMED, Observation=LOINC,
MedicationRequest=RxNorm. We keep both the code and the system so the OMOP
layer can resolve them to standard concepts.

Run:  python ingestion/synthea/parse_fhir.py
"""

from __future__ import annotations

import glob
import json
import os

import duckdb
import pandas as pd

SRC_DIR = os.environ.get("SYNTHEA_DIR", "data/synthea")
DB_PATH = os.environ.get("ELIGIBLE_DB", "data/eligible.duckdb")

# Observation categories worth keeping as OMOP measurements.
KEEP_OBS_CATEGORIES = {"laboratory", "vital-signs"}


def _first_coding(concept: dict | None) -> dict:
    if not concept:
        return {}
    coding = concept.get("coding") or []
    return coding[0] if coding else {}


def _obs_categories(resource: dict) -> set[str]:
    cats = set()
    for cat in resource.get("category", []):
        for c in cat.get("coding", []):
            cats.add(c.get("code", ""))
    return cats


def parse_bundle(path: str) -> dict[str, list[dict]]:
    bundle = json.load(open(path))
    entries = [e["resource"] for e in bundle.get("entry", [])]

    patient = next((r for r in entries if r["resourceType"] == "Patient"), None)
    if patient is None:  # hospital/practitioner metadata files
        return {}
    pid = patient["id"]

    rows: dict[str, list[dict]] = {
        "patients": [],
        "conditions": [],
        "medications": [],
        "measurements": [],
    }

    # --- demographics (race/ethnicity live in US-Core extensions) ---
    race = ethnicity = None
    for ext in patient.get("extension", []):
        url = ext.get("url", "")
        if url.endswith("us-core-race"):
            race = _ombtext(ext)
        elif url.endswith("us-core-ethnicity"):
            ethnicity = _ombtext(ext)
    rows["patients"].append(
        {
            "patient_id": pid,
            "gender": patient.get("gender"),
            "birth_date": patient.get("birthDate"),
            "deceased_date": patient.get("deceasedDateTime"),
            "race": race,
            "ethnicity": ethnicity,
            "marital_status": _first_coding(patient.get("maritalStatus")).get("code"),
        }
    )

    for r in entries:
        rt = r["resourceType"]
        if rt == "Condition":
            c = _first_coding(r.get("code"))
            rows["conditions"].append(
                {
                    "patient_id": pid,
                    "condition_code": c.get("code"),
                    "code_system": c.get("system"),
                    "condition_name": c.get("display"),
                    "onset_date": r.get("onsetDateTime"),
                    "abatement_date": r.get("abatementDateTime"),
                    "clinical_status": _first_coding(r.get("clinicalStatus")).get("code"),
                }
            )
        elif rt == "MedicationRequest":
            c = _first_coding(r.get("medicationCodeableConcept"))
            rows["medications"].append(
                {
                    "patient_id": pid,
                    "drug_code": c.get("code"),
                    "code_system": c.get("system"),
                    "drug_name": c.get("display"),
                    "authored_on": r.get("authoredOn"),
                    "status": r.get("status"),
                }
            )
        elif rt == "Observation":
            if not (KEEP_OBS_CATEGORIES & _obs_categories(r)):
                continue
            vq = r.get("valueQuantity")
            if not vq:  # skip non-numeric obs for the measurement table
                continue
            c = _first_coding(r.get("code"))
            rows["measurements"].append(
                {
                    "patient_id": pid,
                    "measurement_code": c.get("code"),
                    "code_system": c.get("system"),
                    "measurement_name": c.get("display"),
                    "value": vq.get("value"),
                    "unit": vq.get("unit"),
                    "measured_at": r.get("effectiveDateTime"),
                }
            )
    return rows


def _ombtext(ext: dict) -> str | None:
    """Pull the readable race/ethnicity text out of a US-Core extension."""
    for sub in ext.get("extension", []):
        if sub.get("url") == "text":
            return sub.get("valueString")
    return None


def main() -> None:
    files = [f for f in sorted(glob.glob(f"{SRC_DIR}/*.json"))]
    acc: dict[str, list[dict]] = {"patients": [], "conditions": [], "medications": [], "measurements": []}
    n_patients = 0
    for path in files:
        parsed = parse_bundle(path)
        if not parsed:
            continue
        n_patients += 1
        for k, v in parsed.items():
            acc[k].extend(v)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for name, records in acc.items():
        df = pd.DataFrame(records)  # noqa: F841, referenced by duckdb below
        con.execute(f"CREATE OR REPLACE TABLE raw.synthea_{name} AS SELECT * FROM df")
        print(f"raw.synthea_{name:14s} {len(records):>8,} rows")
    con.close()
    print(f"\nparsed {n_patients} patients -> {DB_PATH}")


if __name__ == "__main__":
    main()
