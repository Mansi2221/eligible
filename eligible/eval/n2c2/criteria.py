"""The 13 n2c2 2018 Track 1 cohort-selection criteria + official definitions.

Each patient record is labeled `met` / `not met` for every criterion; the task
is to reproduce those labels from the free-text record. Definitions are from the
shared-task annotation guidelines.
"""

from __future__ import annotations

# code -> definition given to the classifier
N2C2_CRITERIA: dict[str, str] = {
    "ABDOMINAL": (
        "History of intra-abdominal surgery, small or large intestine resection, "
        "or small bowel obstruction."
    ),
    "MAJOR-DIABETES": (
        "Major diabetes-related complication, any of: amputation, kidney damage, "
        "skin conditions, retinopathy, nephropathy, or neuropathy resulting from "
        "or strongly correlated with uncontrolled diabetes."
    ),
    "ADVANCED-CAD": (
        "Advanced cardiovascular disease: 2 or more of: taking 2+ medications to "
        "treat CAD, history of myocardial infarction, currently experiencing angina, "
        "or ischemia (past or present)."
    ),
    "MI-6MOS": "Myocardial infarction in the past 6 months.",
    "KETO-1YR": "Diagnosis of ketoacidosis in the past year.",
    "DIETSUPP-2MOS": (
        "Taken a dietary supplement (excluding vitamin D) in the past 2 months."
    ),
    "ASP-FOR-MI": "Use of aspirin to prevent myocardial infarction.",
    "HBA1C": "Any hemoglobin A1c (HbA1c) value between 6.5% and 9.5%.",
    "CREATININE": "Serum creatinine above the upper limit of normal.",
    "DRUG-ABUSE": "Drug abuse, current or past.",
    "ALCOHOL-ABUSE": "Current alcohol use over the weekly recommended limits.",
    "ENGLISH": "Patient speaks English.",
    "MAKES-DECISIONS": "Patient makes their own medical decisions.",
}

CRITERIA_CODES: list[str] = list(N2C2_CRITERIA)
MET = "met"
NOT_MET = "not met"
