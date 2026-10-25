"""Generate a deliberately messy 'legacy hospital' diagnosis export.

This simulates the second data silo an FDE actually meets: a different schema,
ICD-10 codes (not SNOMED), free-text sex, US-style dates, inconsistent casing,
whitespace, and missing values. It is an *independent* synthetic population
(distinct persons from the Synthea cohort), cross-source entity resolution is
intentionally out of scope for M1.

The harmonization layer's job is to clean this into the same OMOP shape as the
Synthea source, resolving ICD-10 -> standard concept via a curated crosswalk.

Run:  python ingestion/legacy_csv/generate_legacy.py
"""

from __future__ import annotations

import csv
import os
import random

OUT = os.environ.get("LEGACY_CSV", "data/legacy/legacy_diagnoses.csv")

# Curated ICD-10 -> (SNOMED, standard name). Well-known pairings; stands in for
# the full OHDSI Athena crosswalk until that vocabulary is loaded.
CONDITIONS = [
    ("E66.9", "162864005", "Obesity"),
    ("D64.9", "271737000", "Anemia"),
    ("R73.03", "714628002", "Prediabetes"),
    ("I10", "59621000", "Essential hypertension"),
    ("E11.9", "44054006", "Type 2 diabetes mellitus"),
    ("J20.9", "10509002", "Acute bronchitis"),
    ("J01.90", "444814009", "Acute sinusitis"),
    ("E78.5", "55822004", "Hyperlipidemia"),
    ("N18.3", "431857002", "Chronic kidney disease stage 3"),
    ("F32.9", "370143000", "Major depressive disorder"),
]

# Messy free-text renderings of sex, exactly the noise real exports contain.
SEX_RENDERINGS = ["M", "F", "Male", "Female", "male", "female", " m ", "F ", "MALE"]
RACE_RENDERINGS = ["White", "black", "ASIAN", "Hispanic", "  White ", "Other", "UNK", ""]


def _messy_date(y: int, m: int, d: int) -> str:
    # Randomly pick one of several US-style formats a legacy system might emit.
    fmt = random.choice(["{m}/{d}/{y}", "{m:02d}/{d:02d}/{y}", "{m}-{d}-{y}"])
    return fmt.format(m=m, d=d, y=y)


def main() -> None:
    random.seed(42)  # reproducible
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    rows = []
    for i in range(1, 26):  # 25 legacy patients
        mrn = f"MRN{i:05d}"
        sex = random.choice(SEX_RENDERINGS)
        birth = _messy_date(random.randint(1940, 2000), random.randint(1, 12), random.randint(1, 28))
        race = random.choice(RACE_RENDERINGS)
        for _ in range(random.randint(1, 4)):  # 1-4 diagnoses per patient
            icd10, _snomed, name = random.choice(CONDITIONS)
            # dirty the diagnosis text: casing + stray whitespace, sometimes blank
            dx_text = random.choice([name, name.upper(), name.lower(), f"  {name} ", ""])
            dx_date = _messy_date(random.randint(2015, 2023), random.randint(1, 12), random.randint(1, 28))
            rows.append(
                {
                    "MRN": mrn,
                    "PT_SEX": sex,
                    "DOB": birth,
                    "RACE_DESC": race,
                    "ICD10_CODE": icd10,
                    "DIAGNOSIS_TEXT": dx_text,
                    "DIAG_DATE": random.choice([dx_date, dx_date, ""]),  # some missing dates
                }
            )

    fields = ["MRN", "PT_SEX", "DOB", "RACE_DESC", "ICD10_CODE", "DIAGNOSIS_TEXT", "DIAG_DATE"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    patients = len({r["MRN"] for r in rows})
    print(f"wrote {len(rows)} diagnosis rows for {patients} legacy patients -> {OUT}")


if __name__ == "__main__":
    main()
